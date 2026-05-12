"""
MA10 斜率排名策略 — 自定义管理命令

每日收盘计算全品种 MA10 斜率排名，取前 5 做多 / 后 5 做空。
不加仓、不移仓。作为对比系统独立运行，不改动任何实盘代码。

用法:
    python manage.py run_ma10_slope --mode monitor     # 实时监控（主模式）
    python manage.py run_ma10_slope --mode once         # 单次排名 + 信号生成
    python manage.py run_ma10_slope --mode exit_only    # 强制平仓
"""
import time
import traceback
import signal
from decimal import Decimal
from datetime import datetime

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
    TradingAccount, PositionState, DailyStrategySignal, FullContractList,
)
from stock.utils.log_util import log_trade, log_error
from stock.core.ma_slope import (
    DEFAULTS, rank_by_ma10_slope, get_ma10_slope_for_symbol,
)
from stock.core.atr import calculate_atr


FSM = 'run_ma10_slope'
ACCOUNT_NAME = '510988'


class RestartSignal(Exception):
    """定时重启信号 — 用于关闭旧连接并重新建立"""
    pass


class Command(BaseCommand):
    help = 'MA10斜率排名策略 — 全品种排名择优，取前5做多/后5做空'

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str,
                            choices=['monitor', 'once', 'exit_only'],
                            default='monitor',
                            help='运行模式: monitor=实时监控, once=单次检测, exit_only=强制平仓')

    # ==================== 入口 ====================

    def handle(self, *args, **options):
        account = self._get_account()
        mode = options['mode']

        if mode == 'once':
            # once 模式不需要 TqApi 连接，直接从数据库读取 KlineData
            self._handle_once(account)
            self.stdout.write(self.style.SUCCESS("[MA10] once 模式完成"))
            return

        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)

            self.stdout.write(f"[MA10] 启动 {mode} 模式 | 账户: {account.name}")

            if mode == 'monitor':
                while True:
                    try:
                        self._handle_monitor(api, account)
                        break
                    except RestartSignal:
                        self.stdout.write("[MA10] ⏰ 定时重启连接...")
                        safe_close_api(api)
                        time.sleep(35)
                        api = create_tqapi(account)
                        api.wait_update(deadline=time.time() + 15)
                        self.stdout.write("[MA10] 连接已重建，继续监控")
            elif mode == 'exit_only':
                self._handle_exit_only(api, account)

            self.stdout.write(self.style.SUCCESS(f"[MA10] {mode} 模式完成"))
        except KeyboardInterrupt:
            self.stdout.write("\n[MA10] 用户中断")
        except Exception as e:
            log_error(FSM, f"命令执行失败: {traceback.format_exc()}", account=account, notify=True)
            raise CommandError(str(e))
        finally:
            safe_close_api(api)

    def _get_account(self):
        try:
            return TradingAccount.objects.get(name=ACCOUNT_NAME, is_active=True)
        except TradingAccount.DoesNotExist:
            raise CommandError(f"MA10账户 '{ACCOUNT_NAME}' 不存在或已停用")

    def _already_signaled_today(self, account, symbol, trade_type):
        """检查今日是否已生成过该类型的有效信号"""
        return DailyStrategySignal.objects.filter(
            account=account, symbol=symbol,
            trade_type=trade_type,
            trade_date=timezone.now().date(),
        ).exclude(executed_status='FAILED').exists()

    # ==================== 仓位计算 ====================

    def _calc_unit_lots(self, api, symbol, account, atr_value):
        """
        仓位计算（与海龟相同，但不考虑加仓）：
        每品种手数 = floor(权益 × risk_per_trade_pct / (atr_stop_multiplier × ATR × 合约乘数))
        """
        account.refresh_from_db()
        equity = float(account.current_equity or Decimal('1000000'))

        try:
            quote = api.get_quote(symbol)
            volume_multiple = int(quote.volume_multiple) if quote and quote.volume_multiple else 10
        except Exception:
            # 尝试从入参获取
            from stock.models import FullContractList
            contract = FullContractList.objects.filter(symbol=symbol).first()
            volume_multiple = contract.volume_multiple if contract else 10

        if atr_value is None or atr_value <= 0:
            return 1

        stop_mult = float(DEFAULTS['ATR_STOP_MULTIPLIER'])
        risk_pct = float(DEFAULTS['RISK_PER_TRADE_PCT'])
        risk_amount = equity * risk_pct / 100.0
        unit_value = stop_mult * atr_value * volume_multiple

        if unit_value <= 0:
            return 1

        return max(1, int(risk_amount / unit_value))

    @staticmethod
    def _calc_hard_stop(direction, entry_price, atr_value):
        """硬止损价 = 入场价 ± atr_stop_multiplier × ATR"""
        stop_mult = float(DEFAULTS['ATR_STOP_MULTIPLIER'])
        if direction == 1:
            return entry_price - stop_mult * atr_value
        else:
            return entry_price + stop_mult * atr_value

    # ==================== 信号生成（收盘后执行） ====================

    def _compute_rankings(self, account):
        """计算全品种 MA10 斜率排名，返回 (long_candidates, short_candidates, all_ranked)"""
        return rank_by_ma10_slope(account)

    def _generate_entry_signals(self, api, account):
        """
        收盘后执行：计算排名 → 为候选品种生成 PENDING ENTRY 信号。
        只在 monitor 模式下的收盘时段执行。
        """
        long_cands, short_cands, all_ranked = self._compute_rankings(account)

        if not all_ranked:
            self.stdout.write(self.style.WARNING("[MA10] 无有效的排名数据"))
            return

        self.stdout.write(f"[MA10] 排名总品种数: {len(all_ranked)}")
        self.stdout.write(f"  多头候选: {len(long_cands)}, 空头候选: {len(short_cands)}")
        for c in long_cands:
            self.stdout.write(f"    LONG #{c['rank']}: {c['symbol']} slope={c['slope_pct']:+.4f}%")
        for c in short_cands:
            self.stdout.write(f"    SHORT #{c['rank']}: {c['symbol']} slope={c['slope_pct']:+.4f}%")

        # 检查现有持仓数量
        existing_longs = PositionState.objects.filter(
            account=account, direction=1, units__gt=0
        ).count()
        existing_shorts = PositionState.objects.filter(
            account=account, direction=-1, units__gt=0
        ).count()

        max_side = DEFAULTS['MAX_POSITIONS_PER_SIDE']

        # 生成多头 PENDING 信号
        for cand in long_cands:
            if existing_longs >= max_side:
                self.stdout.write(f"  [SKIP] 多头已达上限 {max_side}, 跳过 {cand['symbol']}")
                break

            if self._already_signaled_today(account, cand['symbol'], 'ENTRY'):
                self.stdout.write(f"  [SKIP] {cand['symbol']} 今日已有 ENTRY 信号")
                continue

            # 检查是否已有同向持仓
            existing_pos = PositionState.objects.filter(
                account=account, symbol=cand['symbol'], units__gt=0
            ).first()
            if existing_pos and existing_pos.direction == 1:
                self.stdout.write(f"  [SKIP] {cand['symbol']} 已持有多头")
                continue

            DailyStrategySignal.objects.create(
                account=account, symbol=cand['symbol'],
                product_code=cand['product_code'],
                trade_date=timezone.now().date(),
                trade_type='ENTRY',
                signal_direction=1,
                executed_status='PENDING',
                donchian_upper=Decimal(str(cand['slope_pct'])).quantize(Decimal('0.0001')),
                contract_target_number=1,
                remark=f"MA10排名多头 #{cand['rank']} slope={cand['slope_pct']:+.4f}%",
            )
            existing_longs += 1
            self.stdout.write(f"  ✅ 生成多头 PENDING: {cand['symbol']} (rank #{cand['rank']})")

        # 生成空头 PENDING 信号
        for cand in short_cands:
            if existing_shorts >= max_side:
                self.stdout.write(f"  [SKIP] 空头已达上限 {max_side}, 跳过 {cand['symbol']}")
                break

            if self._already_signaled_today(account, cand['symbol'], 'ENTRY'):
                self.stdout.write(f"  [SKIP] {cand['symbol']} 今日已有 ENTRY 信号")
                continue

            existing_pos = PositionState.objects.filter(
                account=account, symbol=cand['symbol'], units__gt=0
            ).first()
            if existing_pos and existing_pos.direction == -1:
                self.stdout.write(f"  [SKIP] {cand['symbol']} 已持有空头")
                continue

            DailyStrategySignal.objects.create(
                account=account, symbol=cand['symbol'],
                product_code=cand['product_code'],
                trade_date=timezone.now().date(),
                trade_type='ENTRY',
                signal_direction=-1,
                executed_status='PENDING',
                donchian_lower=Decimal(str(cand['slope_pct'])).quantize(Decimal('0.0001')),
                contract_target_number=1,
                remark=f"MA10排名空头 #{cand['rank']} slope={cand['slope_pct']:+.4f}%",
            )
            existing_shorts += 1
            self.stdout.write(f"  ✅ 生成空头 PENDING: {cand['symbol']} (rank #{cand['rank']})")

    # ==================== 离场检查（收盘后执行） ====================

    def _check_exit_conditions(self, api, account):
        """
        收盘后检查现有持仓是否触发离场条件：
        1. 排名退化 (rank > exit_threshold_rank)
        2. 趋势反转 (slope 方向与持仓方向相反)
        此方法仅在 monitor 模式的收盘时段调用。
        """
        positions = PositionState.objects.filter(account=account, units__gt=0).exclude(direction=0)
        if not positions:
            return

        # 获取全品种排名（用于排名退化检查）
        _, _, all_ranked = self._compute_rankings(account)
        rank_map = {r['symbol']: r['rank'] for r in all_ranked}
        slope_map = {r['symbol']: r['slope_pct'] for r in all_ranked}
        exit_rank = DEFAULTS['EXIT_THRESHOLD_RANK']
        total_products = len(all_ranked)

        for pos in positions:
            symbol = pos.symbol
            rank = rank_map.get(symbol, total_products + 1)
            slope = slope_map.get(symbol, 0)
            triggered = False
            reason = ''

            # 条件 A：排名退化
            if pos.direction == 1 and rank > exit_rank:
                triggered = True
                reason = f"排名退化: rank={rank} > exit_threshold={exit_rank}"
            elif pos.direction == -1 and rank > (total_products - exit_rank + 1):
                triggered = True
                reason = f"排名退化: rank={rank} > exit_threshold={total_products - exit_rank + 1}"

            # 条件 B：趋势反转
            if not triggered:
                if pos.direction == 1 and slope < 0:
                    triggered = True
                    reason = f"趋势反转: slope={slope:+.4f}% (多头持仓)"
                elif pos.direction == -1 and slope > 0:
                    triggered = True
                    reason = f"趋势反转: slope={slope:+.4f}% (空头持仓)"

            if triggered:
                self.stdout.write(f"[MA10] 离场信号: {symbol} - {reason}")
                self._create_exit_signal(api, account, pos, reason)

    def _create_exit_signal(self, api, account, position, reason):
        """创建 STOP_LOSS 信号并执行平仓"""
        if self._already_signaled_today(account, position.symbol, 'STOP_LOSS'):
            return

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=position.symbol,
            product_code=position.product_code,
            trade_date=timezone.now().date(),
            trade_type='STOP_LOSS',
            signal_direction=-position.direction,
            executed_status='PENDING',
            remark=f"MA10排名离场: {reason}",
        )
        log_trade('ma10_exit_signal',
                  f"{position.symbol} 生成平仓信号: {reason}",
                  symbol=position.symbol, log_level='INFO', account=account)

    # ==================== PENDING 信号执行（开盘执行） ====================

    def _execute_pending_signals(self, api, account):
        """
        开盘执行 PENDING 信号：
        1. 先执行 STOP_LOSS 平仓
        2. 再执行 ENTRY 开仓
        """
        self.stdout.write("[MA10] 执行 PENDING 信号...")

        # 1. 平仓
        exit_signals = DailyStrategySignal.objects.filter(
            account=account, trade_type='STOP_LOSS',
            executed_status='PENDING'
        )
        for signal in exit_signals:
            self._execute_exit(api, account, signal)

        # 2. 开仓
        entry_signals = DailyStrategySignal.objects.filter(
            account=account, trade_type='ENTRY',
            executed_status='PENDING'
        )
        for signal in entry_signals:
            self._execute_entry(api, account, signal)

        self.stdout.write(self.style.SUCCESS("[MA10] PENDING 信号执行完毕"))

    # ==================== 入场执行 ====================

    def _execute_entry(self, api, account, signal):
        """执行入场: 计算仓位 → TargetPosTask → 记录持仓"""
        symbol = signal.symbol
        direction = signal.signal_direction

        # 获取 ATR
        atr_value = calculate_atr(api, symbol, period=20)
        if atr_value is None:
            self.stdout.write(self.style.ERROR(f"[MA10] 计算 {symbol} ATR 失败，跳过"))
            signal.executed_status = 'FAILED'
            signal.remark = f'{signal.remark or ""}, ATR计算失败'
            signal.save(update_fields=['executed_status', 'remark'])
            return

        # 计算手数
        unit_lots = self._calc_unit_lots(api, symbol, account, atr_value)

        # 获取当前报价用于跳空保护
        quote = api.get_quote(symbol)
        if quote and quote.last_price:
            from stock.core.atr import price_gap_protection
            if not price_gap_protection(api, symbol, direction, atr=atr_value):
                self.stdout.write(self.style.WARNING(f"[MA10] {symbol} 跳空过大，跳过入场"))
                signal.executed_status = 'FAILED'
                signal.remark = f'{signal.remark or ""}, 跳空保护拦截'
                signal.save(update_fields=['executed_status', 'remark'])
                return

        order_volume = unit_lots
        target_lots = order_volume if direction == 1 else -order_volume

        self.stdout.write(f"[MA10] 入场 {symbol}: {'多' if direction == 1 else '空'} "
                          f"{order_volume}手, ATR={atr_value:.2f}")

        signal.executed_status = 'EXECUTING'
        signal.save(update_fields=['executed_status'])

        target_pos = TargetPosTask(api, symbol)
        target_pos.set_target_volume(target_lots)

        result = wait_for_target_position(api, target_pos, symbol,
                                          target_lots, 'ma10_entry')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[MA10] 入场失败: {symbol}"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

        for _ in range(3):
            api.wait_update()
        quote = api.get_quote(symbol)
        fill_price = float(quote.last_price) if quote and quote.last_price else 0
        hard_stop = self._calc_hard_stop(direction, fill_price, atr_value)

        # 获取斜率值存入 indicators
        slope_val = get_ma10_slope_for_symbol(symbol)

        with transaction.atomic():
            PositionState.objects.update_or_create(
                account=account, symbol=symbol,
                defaults={
                    'product_code': signal.product_code,
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
                    'entry_atr': Decimal(str(atr_value)),
                    'entry_trend_factor': Decimal(str(slope_val)).quantize(Decimal('0.0001')) if slope_val else None,
                    'entry_trend_label': 'up' if (slope_val or 0) > 0 else 'down',
                    'indicators': {
                        'entry_slope_pct': slope_val,
                        'hard_stop_price': hard_stop,
                    },
                }
            )
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status'])

        log_trade('ma10_entry',
                  f"{symbol} {'多' if direction == 1 else '空'} {order_volume}手 @ {fill_price:.2f}, "
                  f"ATR={atr_value:.2f}, hard_stop={hard_stop:.2f}",
                  symbol=symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[MA10] ✅ 入场成功: {symbol} {order_volume}手 @ {fill_price:.2f}"))

    # ==================== 出场执行 ====================

    def _execute_exit(self, api, account, signal):
        """执行平仓: TargetPosTask → 0 → 记录平仓"""
        symbol = signal.symbol

        try:
            position = PositionState.objects.get(
                account=account, symbol=symbol, units__gt=0
            )
        except PositionState.DoesNotExist:
            self.stdout.write(f"[MA10] {symbol} 无持仓，跳过平仓")
            signal.executed_status = 'FAILED'
            signal.remark = '无持仓'
            signal.save(update_fields=['executed_status', 'remark'])
            return

        volume = position.contract_total_position
        self.stdout.write(f"[MA10] 平仓 {symbol}: {volume}手, 原因: {signal.remark}")

        signal.executed_status = 'EXECUTING'
        signal.save(update_fields=['executed_status'])

        target_pos = TargetPosTask(api, symbol)
        target_pos.set_target_volume(0)

        result = wait_for_target_position(api, target_pos, symbol, 0, 'ma10_exit')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"[MA10] 平仓失败: {symbol}"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            return

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

        log_trade('ma10_exit',
                  f"{symbol} 平仓 {filled_volume}手 @ {avg_price:.2f}, 原因: {signal.remark}",
                  symbol=symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(
            f"[MA10] ✅ 平仓成功: {symbol} {filled_volume}手 @ {avg_price:.2f}"))

    # ==================== 盘中硬止损检查 ====================

    def _check_hard_stop(self, api, account, position, price):
        """盘中实时检查硬止损"""
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
            reason = f"硬止损: 价格{price:.2f} <= 止损价{hard_stop:.2f}"
        elif position.direction == -1 and price >= hard_stop:
            triggered = True
            reason = f"硬止损: 价格{price:.2f} >= 止损价{hard_stop:.2f}"

        if triggered:
            self.stdout.write(f"[MA10] 硬止损: {position.symbol} - {reason}")
            # 直接执行平仓
            signal = DailyStrategySignal.objects.create(
                account=account, symbol=position.symbol,
                product_code=position.product_code,
                trade_date=timezone.now().date(),
                trade_type='STOP_LOSS',
                signal_direction=-position.direction,
                executed_status='PENDING',
                remark=reason,
            )
            self._execute_exit(api, account, signal)

    # ==================== 实时监控主循环 ====================

    def _handle_monitor(self, api, account):
        """
        实时监控主循环：
        - 9:01-9:02 → 执行 PENDING 信号（开/平）
        - 15:00-15:05 → 计算排名 + 生成信号 + 检查离场
        - 盘中的每次报价更新 → 检查硬止损
        - 8:55 / 20:55 → 定时重启
        """
        self.stdout.write("[MA10] 开始实时监控 (Ctrl+C 退出)...")

        # 注册信号处理，优雅退出
        running = True
        orig_handler = signal.getsignal(signal.SIGINT)

        def _signal_handler(sig, frame):
            nonlocal running
            running = False
            self.stdout.write("\n[MA10] 正在退出...")

        signal.signal(signal.SIGINT, _signal_handler)

        # 记录上次执行时段，防止重复触发
        last_action_key = None
        last_restart_key = None

        try:
            while running:
                api.wait_update()

                now = datetime.now()

                # === 定时重启检查 ===
                restart_key = now.strftime('%Y-%m-%d-%H') if now.hour in (8, 20) else None
                if restart_key and restart_key != last_restart_key and now.minute == 55:
                    last_restart_key = restart_key
                    self.stdout.write(f"[MA10] 触法定时重启 ({now.strftime('%H:%M')})")
                    raise RestartSignal()

                # === 开盘执行 PENDING 信号 (9:01-9:02) ===
                if now.hour == 9 and now.minute in (1, 2):
                    action_key = now.strftime('%Y-%m-%d') + '-open'
                    if action_key != last_action_key:
                        last_action_key = action_key
                        self._execute_pending_signals(api, account)

                # === 收盘处理 (15:00-15:05) ===
                if now.hour == 15 and now.minute < 5:
                    action_key = now.strftime('%Y-%m-%d') + '-close'
                    if action_key != last_action_key:
                        last_action_key = action_key
                        self.stdout.write("[MA10] 收盘处理: 检查离场 + 生成排名信号...")
                        self._check_exit_conditions(api, account)
                        self._generate_entry_signals(api, account)

                # === 盘中硬止损检查 ===
                for position in PositionState.objects.filter(
                    account=account, units__gt=0
                ).exclude(direction=0):
                    try:
                        quote = api.get_quote(position.symbol)
                        if quote and quote.last_price is not None:
                            self._check_hard_stop(api, account, position,
                                                  float(quote.last_price))
                    except Exception:
                        pass

        finally:
            signal.signal(signal.SIGINT, orig_handler)

    # ==================== 单次检测模式 ====================

    def _handle_once(self, account):
        """单次检测: 计算排名 + 检查现有持仓 + 输出信息（不执行）"""
        self.stdout.readline = lambda: None  # prevent error
        self.stdout.write("[MA10] 单次检测模式 (只检测, 不执行)")

        long_cands, short_cands, all_ranked = self._compute_rankings(account)

        if not all_ranked:
            self.stdout.write(self.style.WARNING("无有效的排名数据"))
            return

        # 输出排名
        self.stdout.write(f"\n=== 全品种排名 ({len(all_ranked)} 个) ===")
        self.stdout.write(f"{'排名':<6} {'品种':<20} {'slope%':<12} {'方向':<8}")
        self.stdout.write("-" * 50)
        for r in all_ranked:
            direction = ''
            if r in long_cands:
                direction = '↑ LONG'
            elif r in short_cands:
                direction = '↓ SHORT'
            self.stdout.write(f"#{r['rank']:<4} {r['symbol']:<20} {r['slope_pct']:+.4f}%   {direction}")

        # 输出现有持仓
        positions = PositionState.objects.filter(account=account, units__gt=0).exclude(direction=0)
        if positions:
            self.stdout.write(f"\n=== 现有持仓 ({positions.count()} 个) ===")
            for pos in positions:
                slope = get_ma10_slope_for_symbol(pos.symbol)
                self.stdout.write(
                    f"  {pos.symbol:<20} "
                    f"{'多' if pos.direction == 1 else '空':<6} "
                    f"{pos.contract_total_position}手, "
                    f"slope={slope:+.4f}%" if slope is not None else f"slope=--"
                )

        self.stdout.write(self.style.SUCCESS(f"[MA10] 单次检测完成"))

    # ==================== 强制平仓模式 ====================

    def _handle_exit_only(self, api, account):
        """强制平仓所有持仓"""
        positions = PositionState.objects.filter(account=account, units__gt=0).exclude(direction=0)

        if not positions:
            self.stdout.write("该账户无持仓")
            return

        self.stdout.write(f"[MA10] 强制平仓 {positions.count()} 个持仓...")

        for pos in positions:
            if self._already_signaled_today(account, pos.symbol, 'STOP_LOSS'):
                continue

            signal = DailyStrategySignal.objects.create(
                account=account, symbol=pos.symbol,
                product_code=pos.product_code,
                trade_date=timezone.now().date(),
                trade_type='STOP_LOSS',
                signal_direction=-pos.direction,
                executed_status='PENDING',
                remark="MA10强制平仓",
            )
            self._execute_exit(api, account, signal)
