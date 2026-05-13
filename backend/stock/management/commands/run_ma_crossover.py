"""
双均线MA10/20交叉交易系统 — 自定义管理命令

收盘MA10穿越MA20判断，下一开盘执行。
单品种单次开仓，无加仓减仓，仓位=2%资金/(2×ATR×合约乘数)。
定时在 8:55 和 20:55 重启连接以避免服务端断开。

用法:
    python manage.py run_ma_crossover --mode full
    python manage.py run_ma_crossover --mode signal
    python manage.py run_ma_crossover --mode execute
    python manage.py run_ma_crossover --mode exit_all
"""
import time
import traceback
import numpy as np
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
    TradingAccount, PositionState, DailyStrategySignal,
    FullContractList, AccountContractConfig,
)
from stock.utils.log_util import log_trade, log_error
from stock.core.atr import calculate_atr

FSM = 'run_ma_crossover'
MA_ACCOUNT_NAME = '510978'  # 双均线对比测试专用账户


class RestartSignal(Exception):
    """定时重启信号 — 在 8:55 和 20:55 触发，关闭旧连接并重新建立"""
    pass


class Command(BaseCommand):
    help = '双均线MA10/20交叉交易系统 — 收盘判断，次开盘执行'

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str,
                            choices=['signal', 'execute', 'full', 'exit_all'],
                            default='full',
                            help='运行模式: signal=仅检测, execute=仅执行, full=检测+执行, exit_all=强制平仓')

    # ==================== 入口 ====================

    def handle(self, *args, **options):
        mode = options['mode']
        account = self._get_account(MA_ACCOUNT_NAME)

        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)
            self.stdout.write(f"[MA交叉] 启动 {mode} 模式 | 账户: {account.name}")

            while True:
                try:
                    if mode == 'signal':
                        self._handle_signal(api, account)
                    elif mode == 'execute':
                        self._handle_execute(api, account)
                    elif mode == 'full':
                        self._handle_full(api, account)
                    elif mode == 'exit_all':
                        self._handle_exit_all(api, account)
                    break  # 正常完成，退出循环
                except RestartSignal:
                    self.stdout.write("[MA] ⏰ 定时重启连接...")
                    safe_close_api(api)
                    time.sleep(35)
                    api = create_tqapi(account)
                    api.wait_update(deadline=time.time() + 15)

        except Exception as e:
            log_error(f'{FSM}.handle', f'运行异常: {traceback.format_exc()}',
                      account=account, notify=True)
            raise
        finally:
            safe_close_api(api)

    # ==================== 工具方法 ====================

    def _get_account(self, name):
        try:
            return TradingAccount.objects.get(name=name, is_active=True)
        except TradingAccount.DoesNotExist:
            raise CommandError(f"账户不存在或未激活: {name}")

    def _get_active_contracts(self, account):
        """获取账户活跃的交易品种对应的主力合约列表。"""
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

    def _get_volume_multiple(self, symbol):
        try:
            return FullContractList.objects.get(symbol=symbol).volume_multiple
        except FullContractList.DoesNotExist:
            return 10

    def _parse_remark_field(self, remark):
        """从 remark 字段解析 MA10/MA20 值。"""
        result = {}
        if not remark:
            return result
        for part in remark.split(', '):
            if '=' in part:
                key, val = part.split('=', 1)
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
        return result

    def _check_restart_time(self):
        """
        检查是否需要定时重启。
        在 8:55-8:59 和 20:55-20:59 区间触发 RestartSignal。
        """
        now = datetime.now()
        if now.hour in (8, 20) and now.minute == 55:
            self.stdout.write(f"[MA] 到达定时重启时间 ({now.strftime('%H:%M')})")
            raise RestartSignal()

    # ==================== MA交叉检测 ====================

    def _compute_ma_cross(self, api, symbol):
        """
        检测 MA10/20 金叉/死叉。

        使用 TqSDK 日 K 线数据，始终取倒数第二根完成的 K 线作为"最新收盘"，
        避免盘中运行时最后 1 根未完成 K 线的影响。

        Returns:
            dict with keys (direction, ma10, ma20, atr) or None
        """
        klines = api.get_kline_serial(symbol, duration_seconds=86400, data_length=30)
        api.wait_update(deadline=time.time() + 5)

        if klines is None or len(klines) < 22:
            return None

        closes = klines['close'].values

        # 取已完成 K 线：排除最后 1 根（可能为当日未完成 K 线）
        # [-11:-1] = 最近 10 个收盘价（不含当前未完成根）
        # [-21:-1] = 最近 20 个收盘价（不含当前未完成根）
        # [-12:-2] = 上推 1 日的 10 个收盘价
        # [-22:-2] = 上推 1 日的 20 个收盘价
        ma10_curr = float(np.mean(closes[-11:-1]))
        ma20_curr = float(np.mean(closes[-21:-1]))
        ma10_prev = float(np.mean(closes[-12:-2]))
        ma20_prev = float(np.mean(closes[-22:-2]))

        if ma10_prev <= ma20_prev and ma10_curr > ma20_curr:
            direction = 1  # 金叉，做多
        elif ma10_prev >= ma20_prev and ma10_curr < ma20_curr:
            direction = -1  # 死叉，做空
        else:
            return None

        atr = calculate_atr(api, symbol)

        return {
            'direction': direction,
            'ma10': ma10_curr,
            'ma20': ma20_curr,
            'atr': atr,
        }

    # ==================== 仓位计算 ====================

    def _calc_position_size(self, account, symbol, atr_value):
        """
        仓位计算公式：floor(current_equity × 2% / (2 × ATR × 合约乘数))
        """
        equity = float(account.current_equity or 1_000_000)
        vol_mult = self._get_volume_multiple(symbol)

        if not atr_value or atr_value <= 0:
            return 1

        risk_amount = equity * 0.02                    # 2% 资金
        risk_per_lot = 2.0 * atr_value * vol_mult       # 2 × ATR × 乘数

        if risk_per_lot <= 0:
            return 1

        return max(1, int(risk_amount / risk_per_lot))

    # ==================== 移仓检查 ====================

    def _check_rollover(self, api, account):
        """检查所有持仓的合约是否需要移仓（主力合约变更）。"""
        positions = PositionState.objects.filter(
            account=account, units__gt=0
        )
        for position in positions:
            contract = FullContractList.objects.filter(
                product_code=position.product_code
            ).first()
            if not contract or contract.symbol == position.symbol:
                continue

            main_symbol = contract.symbol
            self.stdout.write(f"[MA] {position.symbol} -> {main_symbol}: 检测到主力合约变更，执行移仓")

            # 旧合约平仓
            self._close_position(
                api, account, position,
                f"移仓平仓: {position.symbol}->{main_symbol}"
            )

            # 新合约开同向仓
            atr = calculate_atr(api, main_symbol)
            if not atr or atr <= 0:
                log_trade(f'{FSM}._check_rollover',
                          f'{main_symbol} ATR计算失败，移仓开仓跳过',
                          symbol=main_symbol, log_level='WARNING', account=account)
                continue

            lots = self._calc_position_size(account, main_symbol, atr)

            rollover_signal = DailyStrategySignal.objects.create(
                account=account,
                symbol=main_symbol,
                product_code=position.product_code,
                trade_date=timezone.now().date(),
                trade_type='ROLLOVER',
                signal_direction=position.direction,
                executed_status='EXECUTING',
                trend_factor=Decimal('0'), trend_label='unknown',
                contract_target_number=lots,
                remark=f"移仓开仓: {position.symbol}->{main_symbol}",
            )

            target_lots = lots if position.direction == 1 else -lots
            target_pos = TargetPosTask(api, main_symbol)
            target_pos.set_target_volume(target_lots)

            result = wait_for_target_position(
                api, target_pos, main_symbol, target_lots,
                f'{FSM}._check_rollover'
            )

            if not result['success']:
                log_trade(f'{FSM}._check_rollover',
                          f'{main_symbol} 移仓开仓超时',
                          symbol=main_symbol, log_level='ERROR', account=account)
                rollover_signal.executed_status = 'FAILED'
                rollover_signal.save(update_fields=['executed_status'])
                continue

            api.wait_update()
            pos_after = api.get_position(main_symbol)
            quote = api.get_quote(main_symbol)

            if position.direction == 1:
                fill_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else float(quote.last_price)
                actual_filled = int(pos_after.volume_long) if pos_after else lots
            else:
                fill_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else float(quote.last_price)
                actual_filled = int(pos_after.volume_short) if pos_after else lots

            with transaction.atomic():
                PositionState.objects.create(
                    account=account,
                    symbol=main_symbol,
                    product_code=position.product_code,
                    direction=position.direction,
                    units=1,
                    contract_total_position=actual_filled,
                    last_add_price=Decimal(str(fill_price)),
                    first_open_price=Decimal(str(fill_price)),
                    cost_price=Decimal(str(fill_price)),
                    highest_close=Decimal(str(fill_price)),
                    lowest_close=Decimal(str(fill_price)),
                    latest_close_price=Decimal(str(fill_price)),
                    open_date=timezone.now().date(),
                    entry_atr=Decimal(str(atr)),
                    entry_trend_label='MA_CROSSOVER',
                    indicators={
                        'entry_atr': atr,
                        'rollover_from': position.symbol,
                    },
                )
                rollover_signal.executed_status = 'SUCCESS'
                rollover_signal.save(update_fields=['executed_status'])

            log_trade(f'{FSM}._check_rollover',
                      f'移仓完成: {position.symbol}->{main_symbol}, {actual_filled}手 @ {fill_price:.2f}',
                      symbol=main_symbol, log_level='SUCCESS', account=account)
            self.stdout.write(self.style.SUCCESS(
                f"[MA] 移仓完成: {position.symbol} -> {main_symbol}, {actual_filled}手 @ {fill_price:.2f}"
            ))

    # ==================== 模式分派 ====================

    def _handle_signal(self, api, account):
        """仅检测MA交叉，写入PENDING信号，不执行。"""
        self._check_restart_time()
        contracts = self._get_active_contracts(account)
        if not contracts:
            self.stdout.write(self.style.WARNING("[MA] 无活跃合约配置"))
            return

        signal_count = 0
        for contract in contracts:
            cross = self._compute_ma_cross(api, contract.symbol)
            if cross is None:
                continue

            # 检查现有持仓方向
            position = PositionState.objects.filter(
                account=account, symbol=contract.symbol
            ).first()
            if position and position.units > 0 and position.direction == cross['direction']:
                self.stdout.write(f"[MA] {contract.symbol}: 方向不变，跳过")
                continue

            # 检查今日是否已有信号（唯一约束保护）
            today_signal = DailyStrategySignal.objects.filter(
                account=account, symbol=contract.symbol,
                trade_date=timezone.now().date()
            ).first()
            if today_signal:
                self.stdout.write(f"[MA] {contract.symbol}: 今日信号已存在 ({today_signal.executed_status})，跳过")
                continue

            # 写入 PENDING 信号
            cross_text = 'GOLDEN' if cross['direction'] == 1 else 'DEATH'
            DailyStrategySignal.objects.create(
                account=account,
                symbol=contract.symbol,
                product_code=contract.product_code,
                trade_date=timezone.now().date(),
                trade_type='ENTRY',
                signal_direction=cross['direction'],
                
                trend_factor=Decimal('0'), trend_label='unknown',
                contract_target_number=0,
                remark=f"MA10={cross['ma10']:.2f}, MA20={cross['ma20']:.2f}, Cross={cross_text}",
            )
            log_trade(f'{FSM}._handle_signal',
                      f'{contract.symbol} MA{cross_text}交叉: '
                      f'MA10={cross["ma10"]:.2f}, MA20={cross["ma20"]:.2f}',
                      symbol=contract.symbol, log_level='INFO', account=account)
            signal_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"[MA] 信号模式完成: 检测到 {signal_count} 个交叉信号")
        )

    def _handle_execute(self, api, account):
        """执行待处理的 PENDING 信号。"""
        self._check_restart_time()
        # 检查移仓
        self._check_rollover(api, account)

        signals = DailyStrategySignal.objects.filter(
            account=account,
            trade_type='ENTRY',
            executed_status='PENDING',
        ).order_by('trade_date')

        if not signals.exists():
            self.stdout.write("[MA] 无待执行信号")
            return

        for signal in signals:
            self._check_restart_time()
            cross_info = self._parse_remark_field(signal.remark)
            self._execute_signal(api, account, signal, cross_info)

    def _handle_full(self, api, account):
        """检测MA交叉 + 立即执行。"""
        self._check_restart_time()
        # 先检查移仓
        self._check_rollover(api, account)

        contracts = self._get_active_contracts(account)
        if not contracts:
            self.stdout.write(self.style.WARNING("[MA] 无活跃合约配置"))
            return

        executed_count = 0
        for contract in contracts:
            self._check_restart_time()
            cross = self._compute_ma_cross(api, contract.symbol)
            if cross is None:
                continue

            # 检查现有持仓方向
            position = PositionState.objects.filter(
                account=account, symbol=contract.symbol
            ).first()
            if position and position.units > 0 and position.direction == cross['direction']:
                self.stdout.write(f"[MA] {contract.symbol}: 方向不变，跳过")
                continue

            # 检查今日是否已有信号（唯一约束保护）
            today_signal = DailyStrategySignal.objects.filter(
                account=account, symbol=contract.symbol,
                trade_date=timezone.now().date()
            ).first()
            if today_signal:
                self.stdout.write(f"[MA] {contract.symbol}: 今日信号已存在 ({today_signal.executed_status})，跳过")
                continue

            # 创建信号并执行
            cross_text = 'GOLDEN' if cross['direction'] == 1 else 'DEATH'
            signal = DailyStrategySignal.objects.create(
                account=account,
                symbol=contract.symbol,
                product_code=contract.product_code,
                trade_date=timezone.now().date(),
                trade_type='ENTRY',
                signal_direction=cross['direction'],
                executed_status='PENDING',
            trend_factor=Decimal('0'), trend_label='unknown',
                contract_target_number=0,
                remark=f"MA10={cross['ma10']:.2f}, MA20={cross['ma20']:.2f}, Cross={cross_text}",
            )

            self._execute_signal(api, account, signal, cross)
            executed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"[MA] 全模式完成: {executed_count} 个信号已处理")
        )

    def _handle_exit_all(self, api, account):
        """强制平仓该账户所有持仓。"""
        positions = PositionState.objects.filter(
            account=account, units__gt=0
        )
        if not positions.exists():
            self.stdout.write("[MA] 无持仓需平仓")
            return

        for position in positions:
            self._close_position(api, account, position, "MA策略强制平仓")

        self.stdout.write(
            self.style.SUCCESS(f"[MA] 已平仓 {positions.count()} 个持仓")
        )

    # ==================== 执行核心 ====================

    def _execute_signal(self, api, account, signal, cross_info=None):
        """
        执行 MA 交叉信号。

        Args:
            cross_info: 可选，直接传入交叉数据 {ma10, ma20, atr}
                        未传时从 signal.remark 解析
        """
        try:
            direction_text = 'LONG' if signal.signal_direction == 1 else 'SHORT'
            self.stdout.write(f"[MA] 执行信号: {signal.symbol} {direction_text}")

            # --- 检查现有持仓 ---
            position = PositionState.objects.filter(
                account=account, symbol=signal.symbol, units__gt=0
            ).first()

            if position and position.direction == signal.signal_direction:
                self.stdout.write(f"[MA] {signal.symbol}: 方向不变，跳过执行")
                signal.executed_status = 'CANCELLED'
                signal.save(update_fields=['executed_status'])
                return

            # --- 反向持仓 -> 先平仓 ---
            if position and position.direction == -signal.signal_direction:
                self.stdout.write(f"[MA] {signal.symbol}: 反方向持仓，先平仓")
                self._close_position(
                    api, account, position,
                    f"MA交叉反向: {signal.remark}"
                )
                position = None

            # --- 获取交叉数据 ---
            if cross_info is None:
                cross_info = self._parse_remark_field(signal.remark)

            ma10_val = cross_info.get('ma10', 0)
            ma20_val = cross_info.get('ma20', 0)
            atr_value = cross_info.get('atr') or calculate_atr(api, signal.symbol)

            if not atr_value or atr_value <= 0:
                log_trade(f'{FSM}._execute_signal',
                          f'{signal.symbol} ATR计算失败，无法开仓',
                          symbol=signal.symbol, log_level='WARNING', account=account)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status'])
                return

            # --- 计算仓位 ---
            lots = self._calc_position_size(account, signal.symbol, atr_value)

            signal.executed_status = 'EXECUTING'
            signal.contract_target_number = lots
            signal.save(update_fields=['executed_status', 'contract_target_number'])

            # --- 执行开仓 ---
            target_lots = lots if signal.signal_direction == 1 else -lots
            target_pos = TargetPosTask(api, signal.symbol)
            target_pos.set_target_volume(target_lots)

            result = wait_for_target_position(
                api, target_pos, signal.symbol, target_lots,
                f'{FSM}._execute_signal'
            )

            if not result['success']:
                log_trade(f'{FSM}._execute_signal',
                          f'{signal.symbol} 开仓超时: 目标{target_lots}手',
                          symbol=signal.symbol, log_level='ERROR', account=account)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status'])
                return

            # --- 获取成交信息 ---
            api.wait_update()
            pos_after = api.get_position(signal.symbol)
            quote = api.get_quote(signal.symbol)

            if signal.signal_direction == 1:
                fill_price = float(
                    pos_after.open_price_long
                ) if pos_after and pos_after.open_price_long else float(quote.last_price)
                actual_filled = int(pos_after.volume_long) if pos_after else lots
            else:
                fill_price = float(
                    pos_after.open_price_short
                ) if pos_after and pos_after.open_price_short else float(quote.last_price)
                actual_filled = int(pos_after.volume_short) if pos_after else lots

            # --- 更新持仓状态 ---
            with transaction.atomic():
                PositionState.objects.update_or_create(
                    account=account,
                    symbol=signal.symbol,
                    defaults={
                        'product_code': signal.product_code,
                        'direction': signal.signal_direction,
                        'units': 1,
                        'contract_total_position': actual_filled,
                        'last_add_price': Decimal(str(fill_price)),
                        'first_open_price': Decimal(str(fill_price)),
                        'cost_price': Decimal(str(fill_price)),
                        'highest_close': Decimal(str(fill_price)),
                        'lowest_close': Decimal(str(fill_price)),
                        'latest_close_price': Decimal(str(fill_price)),
                        'open_date': timezone.now().date(),
                        'entry_atr': Decimal(str(atr_value)),
                        'entry_trend_factor': None,
                        'entry_trend_label': 'MA_CROSSOVER',
                        'indicators': {
                            'ma_10': ma10_val,
                            'ma_20': ma20_val,
                            'entry_atr': atr_value,
                        },
                    }
                )
                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status'])

            log_trade(f'{FSM}._execute_signal',
                      f'{signal.symbol} 开仓成功: {actual_filled}手 @ {fill_price:.2f}, {direction_text}',
                      symbol=signal.symbol, log_level='SUCCESS', account=account)
            self.stdout.write(self.style.SUCCESS(
                f"[MA] {signal.symbol} 开仓成功: {actual_filled}手 @ {fill_price:.2f} {direction_text}"
            ))

        except Exception as e:
            log_error(f'{FSM}._execute_signal',
                      f'{signal.symbol} 执行失败: {traceback.format_exc()}',
                      account=account)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            self.stdout.write(self.style.ERROR(
                f"[MA] {signal.symbol} 执行失败: {str(e)}"
            ))

    # ==================== 平仓 ====================

    def _close_position(self, api, account, position, reason):
        """平仓并记录。"""
        try:
            # 创建平仓信号
            signal = DailyStrategySignal.objects.create(
                account=account,
                symbol=position.symbol,
                product_code=position.product_code,
                trade_date=timezone.now().date(),
                trade_type='STOP_LOSS',
                signal_direction=-position.direction,
                executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
                remark=reason,
            )

            # TargetPosTask 平仓
            target_pos = TargetPosTask(api, position.symbol)
            target_pos.set_target_volume(0)

            result = wait_for_target_position(
                api, target_pos, position.symbol, 0,
                f'{FSM}._close_position'
            )

            if not result['success']:
                log_trade(f'{FSM}._close_position',
                          f'{position.symbol} 平仓可能未完全成交',
                          symbol=position.symbol, log_level='WARNING', account=account)

            # 获取成交价
            api.wait_update()
            quote = api.get_quote(position.symbol)
            fill_price = float(quote.last_price) if quote and quote.last_price else 0
            closed_volume = position.contract_total_position or 0

            # 复用现有平仓记录逻辑
            record_and_reset_position(api, position, signal, closed_volume, fill_price)

            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status'])

            log_trade(f'{FSM}._close_position',
                      f'{position.symbol} 平仓成功: {closed_volume}手 @ {fill_price:.2f}, 原因: {reason}',
                      symbol=position.symbol, log_level='SUCCESS', account=account)
            self.stdout.write(self.style.SUCCESS(
                f"[MA] {position.symbol} 平仓成功: {closed_volume}手 @ {fill_price:.2f}"
            ))

        except Exception as e:
            log_error(f'{FSM}._close_position',
                      f'{position.symbol} 平仓失败: {traceback.format_exc()}',
                      account=account)
            self.stdout.write(self.style.ERROR(
                f"[MA] {position.symbol} 平仓失败: {str(e)}"
            ))
