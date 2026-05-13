"""
原版海龟交易系统 — 自定义管理命令

盘中实时监控唐奇安通道，价格触发即执行。
最大仓位 3 个单位（原版为 4）。

用法:
    python manage.py run_turtle --mode monitor     # 实时监控（主模式）
    python manage.py run_turtle --mode once         # 单次检测
    python manage.py run_turtle --mode exit_only    # 强制平仓
"""
import time
import traceback
import signal
import pandas as pd
from decimal import Decimal
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from tqsdk import TargetPosTask

from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.order_execution import (
    wait_for_target_position,
    record_and_reset_position,
)
from stock.models import (
    TradingAccount, PositionState, DailyStrategySignal,
    ClosedPositionRecord, FullContractList, AccountContractConfig,
)
from stock.utils.log_util import log_trade, log_error
from stock.core.signal_checker import check_duplicate_pending_signal
from stock.core.atr import calculate_atr


FSM = 'run_turtle'
TURTLE_ACCOUNT_NAME = '510988'  # 海龟对比测试专用账户


class RestartSignal(Exception):
    """定时重启信号 — 用于关闭旧连接并重新建立"""
    pass


class Command(BaseCommand):
    help = '原版海龟交易系统 — 盘中实时监控，触发即执行'

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str,
                            choices=['monitor', 'once', 'exit_only'],
                            default='monitor',
                            help='运行模式: monitor=实时监控, once=单次检测, exit_only=强制平仓')

    # ==================== 入口 ====================

    def handle(self, *args, **options):
        account = self._get_account()
        mode = options['mode']

        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)

            self.stdout.write(f"[Turtle] 启动 {mode} 模式 | 账户: {account.name}")

            if mode == 'monitor':
                while True:
                    try:
                        self._handle_monitor(api, account)
                        break  # 退出内层后若 RestartSignal 不触发则正常结束
                    except RestartSignal:
                        self.stdout.write("[Turtle] ⏰ 定时重启连接...")
                        safe_close_api(api)
                        time.sleep(35)  # 等待服务器重启
                        api = create_tqapi(account)
                        api.wait_update(deadline=time.time() + 15)
                        self.stdout.write("[Turtle] 连接已重建，继续监控")
            elif mode == 'once':
                self._handle_once(api, account)
            elif mode == 'exit_only':
                self._handle_exit_only(api, account)

            self.stdout.write(self.style.SUCCESS(f"[Turtle] {mode} 模式完成"))
        except KeyboardInterrupt:
            self.stdout.write("\n[Turtle] 用户中断")
        except Exception as e:
            log_error(FSM, f"命令执行失败: {traceback.format_exc()}", account=account, notify=True)
            raise CommandError(str(e))
        finally:
            safe_close_api(api)

    def _get_account(self):
        try:
            return TradingAccount.objects.get(name=TURTLE_ACCOUNT_NAME, is_active=True)
        except TradingAccount.DoesNotExist:
            raise CommandError(f"海龟账户 '{TURTLE_ACCOUNT_NAME}' 不存在或已停用")

    def _get_active_contracts(self, account):
        """获取账户活跃的主力合约列表"""
        configs = AccountContractConfig.objects.filter(
            account=account, is_active=True, allow_open=True
        )
        contracts = []
        for cfg in configs:
            contract = FullContractList.objects.filter(
                product_code=cfg.product_code
            ).first()
            if contract:
                contracts.append(contract)
        return contracts

    def _already_signaled_today(self, account, symbol, trade_type):
        """检查今日是否已生成过该类型的成功/执行中信号"""
        return DailyStrategySignal.objects.filter(
            account=account, symbol=symbol,
            trade_type=trade_type,
            trade_date=timezone.now().date(),
        ).exclude(executed_status='FAILED').exists()

    # ==================== 唐奇安通道计算 ====================

    def _compute_symbol_levels(self, api, symbol, klines):
        """计算单个品种的唐奇安通道(20日入场/10日出场)和N值"""
        if len(klines) < 22:
            return None

        from tqsdk.tafunc import hhv, llv

        # 20日唐奇安（入场用）, shift(1)避免前视偏差
        high_20_series = hhv(klines['high'].shift(1), 20)
        low_20_series = llv(klines['low'].shift(1), 20)
        h20 = float(high_20_series.iloc[-1]) if not pd.isna(high_20_series.iloc[-1]) else None
        l20 = float(low_20_series.iloc[-1]) if not pd.isna(low_20_series.iloc[-1]) else None

        # 10日唐奇安（出场用）
        high_10_series = hhv(klines['high'].shift(1), 10)
        low_10_series = llv(klines['low'].shift(1), 10)
        h10 = float(high_10_series.iloc[-1]) if not pd.isna(high_10_series.iloc[-1]) else None
        l10 = float(low_10_series.iloc[-1]) if not pd.isna(low_10_series.iloc[-1]) else None

        # N值 = ATR(20)
        n_value = calculate_atr(api, symbol, period=20)

        return {
            'h20': h20, 'l20': l20,
            'h10': h10, 'l10': l10,
            'n_value': n_value,
        }

    def _compute_all_levels(self, api, account, symbols):
        """批量计算所有品种的通道和N值"""
        levels = {}
        for symbol in symbols:
            try:
                klines = api.get_kline_serial(symbol, duration_seconds=86400, data_length=65)
                api.wait_update(deadline=time.time() + 2)  # 等待K线数据
                level = self._compute_symbol_levels(api, symbol, klines)
                if level and level['h20'] and level['l20'] and level['n_value']:
                    levels[symbol] = level
                    self.stdout.write(f"  {symbol}: N={level['n_value']:.2f}, "
                                      f"20H={level['h20']:.2f}, 20L={level['l20']:.2f}")
                else:
                    self.stdout.write(self.style.WARNING(f"  {symbol}: 数据不足,跳过"))
            except Exception as e:
                log_error(FSM, f"计算 {symbol} 通道失败: {e}")
        return levels

    # ==================== 海龟仓位计算 ====================

    def _turtle_unit_lots(self, api, symbol, account, n_value):
        """
        海龟仓位计算：
        1 Unit = floor(Account Equity × 1% / (2 × N × Contract Multiplier))
        """
        account.refresh_from_db()
        equity = float(account.current_equity or Decimal('1000000'))

        try:
            quote = api.get_quote(symbol)
            volume_multiple = int(quote.volume_multiple) if quote and quote.volume_multiple else 10
        except Exception:
            volume_multiple = 10

        if n_value is None or n_value <= 0:
            return 1

        risk_amount = equity * 0.01       # 账户权益的 1%
        unit_value = 2.0 * n_value * volume_multiple  # 1单位的价格风险

        if unit_value <= 0:
            return 1

        return max(1, int(risk_amount / unit_value))

    @staticmethod
    def _calc_hard_stop(direction, entry_price, n_value):
        """硬止损价 = 入场价 ± 2×N"""
        if direction == 1:
            return entry_price - 2.0 * n_value
        else:
            return entry_price + 2.0 * n_value

    # ==================== 实时监控主循环 ====================

    def _handle_monitor(self, api, account):
        """
        实时监控主循环（盘中使用）:
        1. 计算所有品种的唐奇安通道 + N值
        2. 订阅报价，进入 wait_update 循环
        3. 每次报价更新检查: 入场/出场/硬止损/加仓/移仓
        4. 在 8:55 和 20:55 定时重启连接（应对服务端重启）
        """
        contracts = self._get_active_contracts(account)
        if not contracts:
            self.stdout.write(self.style.WARNING("该账户没有配置活跃品种"))
            return

        symbols = [c.symbol for c in contracts]
        product_codes = {c.symbol: c.product_code for c in contracts}
        last_prices = {}

        # 预计算通道和N值
        self.stdout.write("[Turtle] 计算唐奇安通道和N值...")
        levels = self._compute_all_levels(api, account, symbols)
        if not levels:
            self.stdout.write(self.style.ERROR("无法计算任何品种的通道数据"))
            return

        # 订阅报价
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = api.get_quote(symbol)
            last_prices[symbol] = None

        self.stdout.write(self.style.SUCCESS(
            f"[Turtle] 开始实时监控 {len(levels)} 个品种 (Ctrl+C 退出)..."))

        # 注册信号处理，优雅退出
        running = True
        orig_handler = signal.getsignal(signal.SIGINT)

        def _signal_handler(sig, frame):
            nonlocal running
            running = False
            self.stdout.write("\n[Turtle] 正在退出...")

        signal.signal(signal.SIGINT, _signal_handler)

        # 定时重启状态跟踪，防止重复触发
        last_restart_key = None

        try:
            while running:
                api.wait_update()

                # === 定时重启检查 ===
                now = datetime.now()
                # 8:55, 13:25, 20:55 触发重启
                restart_key = None
                if (now.hour == 8 and now.minute == 55) or \
                   (now.hour == 13 and now.minute == 25) or \
                   (now.hour == 20 and now.minute == 55):
                    restart_key = now.strftime('%Y-%m-%d-%H%M')
                if restart_key and restart_key != last_restart_key:
                    last_restart_key = restart_key
                    self.stdout.write(f"[Turtle] 触法定时重启 ({now.strftime('%H:%M')})")
                    raise RestartSignal()

                for symbol in symbols:
                    quote = quotes.get(symbol)
                    if not quote or quote.last_price is None:
                        continue

                    price = float(quote.last_price)

                    # 价格未变则跳过
                    if last_prices.get(symbol) == price:
                        continue
                    last_prices[symbol] = price

                    level = levels.get(symbol)
                    if not level:
                        continue

                    # 获取当前持仓
                    try:
                        position = PositionState.objects.get(
                            account=account, symbol=symbol, units__gt=0
                        )
                    except PositionState.DoesNotExist:
                        position = None

                    if not position:
                        self._check_entry(api, account, symbol,
                                          product_codes.get(symbol, ''), price, level)
                    else:
                        self._check_exit(api, account, position, price, level)
                        self._check_hard_stop(api, account, position, price, level)
                        self._check_add_on(api, account, position, price, level)
                        self._check_rollover(api, account, position)
        finally:
            signal.signal(signal.SIGINT, orig_handler)

    # ==================== 入场检查 ====================

    def _check_entry(self, api, account, symbol, product_code, price, level):
        """检查20日唐奇安突破入场"""
        if self._already_signaled_today(account, symbol, 'ENTRY'):
            return

        direction = 0
        if level['h20'] and price > level['h20']:
            direction = 1
        elif level['l20'] and price < level['l20']:
            direction = -1
        else:
            return

        self.stdout.write(f"[Turtle] 突破信号: {symbol} {'多' if direction == 1 else '空'} "
                          f"价格={price:.2f}, 20H={level['h20']:.2f}, 20L={level['l20']:.2f}")
        self._execute_entry(api, account, symbol, product_code, direction, price, level)

    # ==================== 入场执行 ====================

    def _execute_entry(self, api, account, symbol, product_code, direction, price, level):
        """执行入场: 计算仓位 → TargetPosTask → 记录持仓"""
        n_value = level['n_value']
        unit_lots = self._turtle_unit_lots(api, symbol, account, n_value)
        order_volume = 1 * unit_lots

        self.stdout.write(f"[Turtle] 入场 {symbol}: {direction == 1 and '多' or '空'} "
                          f"1 Unit × {unit_lots}手 = {order_volume}手, N={n_value:.2f}")

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=symbol, product_code=product_code,
            trade_date=timezone.now().date(),
            trade_type='ENTRY',
            signal_direction=direction,
            executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
            donchian_upper=Decimal(str(level['h20'])) if level['h20'] else None,
            donchian_lower=Decimal(str(level['l20'])) if level['l20'] else None,
            remark=f"Turtle突破入场: 价格={price:.2f}",
        )

        target_pos = TargetPosTask(api, symbol)
        target_lots = order_volume if direction == 1 else -order_volume
        target_pos.set_target_volume(target_lots)

        result = wait_for_target_position(api, target_pos, symbol,
                                          target_lots, 'turtle_entry')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[Turtle] 入场失败: {symbol}"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

        # 获取成交价(用最后报价近似)
        for _ in range(3):
            api.wait_update()
        quote = api.get_quote(symbol)
        fill_price = float(quote.last_price) if quote and quote.last_price else price
        hard_stop = self._calc_hard_stop(direction, fill_price, n_value)

        with transaction.atomic():
            PositionState.objects.update_or_create(
                account=account, symbol=symbol,
                defaults={
                    'product_code': product_code,
                    'direction': direction,
                    'units': 1,
                    'contract_total_position': order_volume,
                    'last_add_price': Decimal(str(fill_price)),
                    'first_open_price': Decimal(str(fill_price)),
                    'cost_price': Decimal(str(fill_price)),
                    'highest_close': Decimal(str(fill_price)),
                    'lowest_close': Decimal(str(fill_price)),
                    'latest_close_price': Decimal(str(fill_price)),
                    'open_date': timezone.now().date(),
                    'entry_atr': Decimal(str(n_value)),
                    'indicators': {
                        'locked_n': n_value,
                        'unit_prices': [fill_price],
                        'hard_stop_price': hard_stop,
                    },
                }
            )
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status'])

        log_trade('turtle_entry',
                  f"{symbol} 入场 {direction == 1 and '多' or '空'} {order_volume}手 @ {fill_price:.2f}, "
                  f"N={n_value:.2f}, hard_stop={hard_stop:.2f}",
                  symbol=symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[Turtle] ✅ 入场成功: {symbol} {order_volume}手 @ {fill_price:.2f}"))

    # ==================== 出场检查（10日反向突破） ====================

    def _check_exit(self, api, account, position, price, level):
        """检查10日唐奇安反向突破出场"""
        if self._already_signaled_today(account, position.symbol, 'STOP_LOSS'):
            return

        triggered = False
        reason = ''
        if position.direction == 1 and level['l10'] and price < level['l10']:
            triggered = True
            reason = f"10日反向突破: 价格{price:.2f} < 下轨{level['l10']:.2f}"
        elif position.direction == -1 and level['h10'] and price > level['h10']:
            triggered = True
            reason = f"10日反向突破: 价格{price:.2f} > 上轨{level['h10']:.2f}"

        if triggered:
            self.stdout.write(f"[Turtle] 出场信号: {position.symbol} - {reason}")
            self._execute_exit(api, account, position, reason)

    # ==================== 硬止损检查 ====================

    def _check_hard_stop(self, api, account, position, price, level):
        """检查2N硬止损"""
        indicators = position.indicators or {}
        hard_stop = indicators.get('hard_stop_price')
        if hard_stop is None:
            return

        if self._already_signaled_today(account, position.symbol, 'STOP_LOSS'):
            return

        triggered = False
        reason = ''
        if position.direction == 1 and price <= hard_stop:
            triggered = True
            reason = f"2N硬止损: 价格{price:.2f} <= 止损价{hard_stop:.2f}"
        elif position.direction == -1 and price >= hard_stop:
            triggered = True
            reason = f"2N硬止损: 价格{price:.2f} >= 止损价{hard_stop:.2f}"

        if triggered:
            self.stdout.write(f"[Turtle] 硬止损: {position.symbol} - {reason}")
            self._execute_exit(api, account, position, reason)

    # ==================== 加仓检查 ====================

    def _check_add_on(self, api, account, position, price, level):
        """检查0.5N加仓"""
        if position.units >= 3:
            return

        if self._already_signaled_today(account, position.symbol, 'ADD_ON'):
            return

        indicators = position.indicators or {}
        locked_n = indicators.get('locked_n')
        unit_prices = indicators.get('unit_prices', [])
        if not locked_n or not unit_prices:
            return

        last_unit_price = unit_prices[-1]
        trigger_distance = 0.5 * locked_n

        triggered = False
        if position.direction == 1 and price >= last_unit_price + trigger_distance:
            triggered = True
        elif position.direction == -1 and price <= last_unit_price - trigger_distance:
            triggered = True

        if triggered:
            self.stdout.write(f"[Turtle] 加仓信号: {position.symbol} "
                              f"价格{price:.2f} >= {last_unit_price + trigger_distance:.2f} (0.5N)")
            self._execute_add_on(api, account, position, price, level)

    # ==================== 加仓执行 ====================

    def _execute_add_on(self, api, account, position, price, level):
        """执行加仓: 增加1个单位"""
        indicators = position.indicators or {}
        locked_n = indicators.get('locked_n', 0)
        unit_prices = list(indicators.get('unit_prices', []))

        n_value = locked_n or level['n_value']
        unit_lots = self._turtle_unit_lots(api, position.symbol, account, n_value)
        order_volume = 1 * unit_lots
        new_total = position.contract_total_position + order_volume

        self.stdout.write(f"[Turtle] 加仓 {position.symbol}: +1 Unit × {unit_lots}手 = "
                          f"{order_volume}手 (总{new_total}手)")

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=position.symbol,
            product_code=position.product_code,
            trade_date=timezone.now().date(),
            trade_type='ADD_ON',
            signal_direction=position.direction,
            executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
            contract_target_number=1,
            remark=f"Turtle加仓: 0.5N触发, 价格={price:.2f}",
        )

        target_pos = TargetPosTask(api, position.symbol)
        target_lots = new_total if position.direction == 1 else -new_total
        target_pos.set_target_volume(target_lots)

        result = wait_for_target_position(api, target_pos, position.symbol,
                                          target_lots, 'turtle_add_on')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[Turtle] 加仓失败: {position.symbol}"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

        for _ in range(3):
            api.wait_update()
        quote = api.get_quote(position.symbol)
        fill_price = float(quote.last_price) if quote and quote.last_price else price

        unit_prices.append(fill_price)
        new_units = position.units + 1

        with transaction.atomic():
            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total,
                last_add_price=Decimal(str(fill_price)),
                latest_close_price=Decimal(str(fill_price)),
                # 加仓不更新 cost_price（策略设计原则）
                indicators={
                    'locked_n': locked_n or n_value,
                    'unit_prices': unit_prices,
                    'hard_stop_price': indicators.get('hard_stop_price'),
                },
            )
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status'])

        log_trade('turtle_add_on',
                  f"{position.symbol} 加仓 {order_volume}手 @ {fill_price:.2f}, "
                  f"units={new_units}/{new_total}手",
                  symbol=position.symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[Turtle] ✅ 加仓成功: {position.symbol} +{order_volume}手 @ {fill_price:.2f}"))

    # ==================== 出场执行 ====================

    def _execute_exit(self, api, account, position, reason):
        """执行出场: TargetPosTask → 0 → 记录平仓"""
        symbol = position.symbol
        volume = position.contract_total_position

        self.stdout.write(f"[Turtle] 平仓 {symbol}: {volume}手, 原因: {reason}")

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=symbol, product_code=position.product_code,
            trade_date=timezone.now().date(),
            trade_type='STOP_LOSS',
            signal_direction=-position.direction,
            executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
            remark=reason,
        )

        target_pos = TargetPosTask(api, symbol)
        target_pos.set_target_volume(0)

        result = wait_for_target_position(api, target_pos, symbol, 0, 'turtle_exit')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[Turtle] 平仓失败: {symbol}"))
            # 即使 TargetPosTask 超时，也尝试用 record_and_reset_position 清理
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

        # 等待成交回报
        for _ in range(3):
            api.wait_update()

        # 获取成交信息
        trades = api.get_trades()
        filled_volume = 0
        total_cost = Decimal('0')
        try:
            for trade in reversed(list(trades.values())):
                if (trade.instrument_id == symbol and
                        trade.offset in ('CLOSE', 'CLOSETODAY')):
                    filled_volume += trade.volume
                    total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                    if filled_volume >= volume:
                        break
        except Exception:
            pass

        if filled_volume > 0:
            avg_price = float(total_cost / Decimal(str(filled_volume)))
        else:
            quote = api.get_quote(symbol)
            avg_price = float(quote.last_price) if quote and quote.last_price else 0
            filled_volume = volume

        record_and_reset_position(api, position, signal, filled_volume, avg_price)

        signal.executed_status = 'SUCCESS'
        signal.save(update_fields=['executed_status'])

        log_trade('turtle_exit',
                  f"{symbol} 平仓 {filled_volume}手 @ {avg_price:.2f}, 原因: {reason}",
                  symbol=symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[Turtle] ✅ 平仓成功: {symbol} {filled_volume}手 @ {avg_price:.2f}"))

    # ==================== 移仓 ====================

    def _check_rollover(self, api, account, position):
        """检查是否需要移仓换月"""
        if not position or position.units == 0:
            return

        try:
            contract = FullContractList.objects.filter(
                product_code=position.product_code
            ).first()
        except Exception:
            return

        if not contract or contract.symbol == position.symbol:
            return

        if self._already_signaled_today(account, position.symbol, 'ROLLOVER'):
            return

        self.stdout.write(f"[Turtle] 移仓触发: {position.symbol} → {contract.symbol}")
        self._execute_rollover(api, account, position, contract.symbol)

    def _execute_rollover(self, api, account, old_position, new_symbol):
        """移仓换月: 平旧合约 → 开新合约 → 迁移持仓"""
        old_symbol = old_position.symbol
        volume = old_position.contract_total_position
        direction = old_position.direction
        indicators = dict(old_position.indicators or {})

        self.stdout.write(f"[Turtle] 移仓 {old_symbol} → {new_symbol} {volume}手")

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=old_symbol, product_code=old_position.product_code,
            trade_date=timezone.now().date(),
            trade_type='ROLLOVER',
            signal_direction=direction,
            executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
            remark=f'移仓: {old_symbol} → {new_symbol}',
        )

        # Phase 1: 平旧合约
        self.stdout.write(f"[Turtle] 移仓 Phase 1: 平 {old_symbol}")
        old_target = TargetPosTask(api, old_symbol)
        old_target.set_target_volume(0)
        result = wait_for_target_position(api, old_target, old_symbol, 0,
                                          'turtle_rollover_close')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[Turtle] 移仓平旧合约失败: {old_symbol}"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

        for _ in range(3):
            api.wait_update()

        # 获取旧合约平仓信息
        trades = api.get_trades()
        filled_volume = 0
        total_cost = Decimal('0')
        try:
            for trade in reversed(list(trades.values())):
                if (trade.instrument_id == old_symbol and
                        trade.offset in ('CLOSE', 'CLOSETODAY')):
                    filled_volume += trade.volume
                    total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                    if filled_volume >= volume:
                        break
        except Exception:
            pass

        if filled_volume > 0:
            exit_price = float(total_cost / Decimal(str(filled_volume)))
        else:
            quote = api.get_quote(old_symbol)
            exit_price = float(quote.last_price) if quote and quote.last_price else 0
            filled_volume = volume

        # 记录旧合约平仓
        record_and_reset_position(api, old_position, signal, filled_volume, exit_price)

        # Phase 2: 开新合约
        self.stdout.write(f"[Turtle] 移仓 Phase 2: 开 {new_symbol} {volume}手")
        new_target = TargetPosTask(api, new_symbol)
        target_lots = volume if direction == 1 else -volume
        new_target.set_target_volume(target_lots)
        result = wait_for_target_position(api, new_target, new_symbol, target_lots,
                                          'turtle_rollover_open')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[Turtle] 移仓开新合约失败: {new_symbol}"))
            signal.remark = f'{signal.remark}, 开{new_symbol}失败'
            signal.save(update_fields=['remark'])
            return

        for _ in range(3):
            api.wait_update()
        quote = api.get_quote(new_symbol)
        new_price = float(quote.last_price) if quote and quote.last_price else 0

        # Phase 3: 创建新持仓
        contract = FullContractList.objects.filter(symbol=new_symbol).first()
        new_product_code = contract.product_code if contract else old_position.product_code

        with transaction.atomic():
            # 删除旧持仓（已通过 record_and_reset_position 重置）
            old_position.refresh_from_db()
            if old_position.units == 0:
                old_position.delete()

            PositionState.objects.create(
                account=account, symbol=new_symbol, product_code=new_product_code,
                direction=direction, units=old_position.units,
                contract_total_position=volume,
                last_add_price=Decimal(str(new_price)),
                first_open_price=Decimal(str(new_price)),
                cost_price=Decimal(str(new_price)),
                highest_close=Decimal(str(new_price)),
                lowest_close=Decimal(str(new_price)),
                latest_close_price=Decimal(str(new_price)),
                open_date=timezone.now().date(),
                entry_atr=old_position.entry_atr,
                indicators=indicators,
            )

        signal.executed_status = 'SUCCESS'
        signal.save(update_fields=['executed_status'])

        log_trade('turtle_rollover',
                  f"移仓完成: {old_symbol} → {new_symbol} {volume}手",
                  symbol=new_symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[Turtle] ✅ 移仓完成: {old_symbol} → {new_symbol}"))

    # ==================== 单次检测模式 ====================

    def _handle_once(self, api, account):
        """单次检测: 计算通道 + 检查当前价格 + 不执行"""
        contracts = self._get_active_contracts(account)
        symbols = [c.symbol for c in contracts]
        product_codes = {c.symbol: c.product_code for c in contracts}

        self.stdout.write("[Turtle] 单次检测模式 (只检测,不执行)")
        levels = self._compute_all_levels(api, account, symbols)

        if not levels:
            self.stdout.write(self.style.WARNING("无有效数据"))
            return

        for symbol, level in levels.items():
            try:
                quote = api.get_quote(symbol)
                price = float(quote.last_price) if quote and quote.last_price else 0
            except Exception:
                price = 0

            try:
                pos = PositionState.objects.get(account=account, symbol=symbol, units__gt=0)
                has_pos = f"持仓 {pos.units} Unit {pos.direction == 1 and '多' or '空'}"
            except PositionState.DoesNotExist:
                pos = None
                has_pos = "无持仓"

            entry_signal = ''
            if level['h20'] and price > level['h20']:
                entry_signal = '↑ 多头突破'
            elif level['l20'] and price < level['l20']:
                entry_signal = '↓ 空头突破'

            exit_signal = ''
            if pos:
                if pos.direction == 1 and level['l10'] and price < level['l10']:
                    exit_signal = '↓ 多头出场'
                elif pos.direction == -1 and level['h10'] and price > level['h10']:
                    exit_signal = '↑ 空头出场'

            self.stdout.write(
                f"  {symbol:<22} {has_pos:<18} "
                f"N={level['n_value']:<8.2f} "
                f"20H={level['h20']:<10.2f} 20L={level['l20']:<10.2f} "
                f"当前={price:<10.2f} "
                f"{entry_signal or exit_signal or '—'}")

    # ==================== 强制平仓模式 ====================

    def _handle_exit_only(self, api, account):
        """强制平仓所有持仓"""
        positions = PositionState.objects.filter(account=account, units__gt=0) \
            .exclude(direction=0)

        if not positions:
            self.stdout.write("该账户无持仓")
            return

        self.stdout.write(f"[Turtle] 强制平仓 {positions.count()} 个持仓...")

        for pos in positions:
            self._execute_exit(api, account, pos, "强制平仓")
