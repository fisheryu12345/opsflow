"""
reset_accounts — 账户重置管理命令

将 平仓 → 清理活动状态 → 重置权益 → 清空绩效指标（可选）→ 激活实盘（可选）
串联为一个原子操作，避免手动执行多个步骤。

用法:
    python manage.py reset_accounts --account=1,5,6,10
    python manage.py reset_accounts --all
    python manage.py reset_accounts --account=1,5,6,10 --skip-exit
    python manage.py reset_accounts --account=1,5,6,10 --initial-balance=502000
"""
import time
import traceback
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.order_execution import (
    wait_for_target_position,
    record_and_reset_position,
)
from stock.models import (
    TradingAccount, PositionState, DailyStrategySignal,
    AccountPerformanceSummary, DailyEquitySnapshot,
    RollingPerformanceMetrics, SymbolDailyPnl, StrategyConfig,
    TradeLog, ErrorLog, ClosedPositionRecord, SlippageRecord,
)
from stock.utils.log_util import log_trade, log_error
from hvob_mbi.models import HvobMbiDailyState, HvobMbiWatchlistItem


FSM = 'reset_accounts'


class Command(BaseCommand):
    help = '重置账户：平仓 → 清理全部数据（信号/日志/持仓/绩效）→ 重置权益 → 可选激活实盘'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=str, help='账户ID列表，逗号分隔，如: 1,5,6,10')
        parser.add_argument('--all', action='store_true', help='重置所有活跃账户')
        parser.add_argument('--skip-exit', action='store_true',
                            help='跳过 TqSDK 平仓（直接清理 DB），收盘后无行情时使用')
        parser.add_argument('--activate-live', action='store_true',
                            help='重置后将 Acc 1 (V2) 切换为实盘模式 (is_simulation=False)')
        parser.add_argument('--initial-balance', type=float, default=None,
                            help='重置初始权益（默认保留原有 initial_balance）')

    def handle(self, *args, **options):
        # ── 1. 解析目标账户 ──
        account_ids = self._resolve_accounts(options)
        if not account_ids:
            raise CommandError('未指定账户。使用 --account=1,5,6,10 或 --all')

        accounts = list(TradingAccount.objects.filter(id__in=account_ids, is_active=True))
        self.stdout.write(f"[reset_accounts] 目标账户: {[a.name for a in accounts]}")
        self.stdout.write(f"  --skip-exit={options['skip_exit']}, "
                          f"--activate-live={options['activate_live']}, "
                          f"--initial-balance={options.get('initial_balance')}")

        # ── 2. 平仓（除非 --skip-exit）──
        if not options['skip_exit']:
            self._close_all_positions(accounts)
        else:
            self.stdout.write(self.style.WARNING("[reset_accounts] 跳过 TqSDK 平仓，直接清理 DB"))

        # ── 3. 清理所有状态 + 重置权益 ──
        self._cleanup_db(account_ids, options.get('initial_balance'))

        # ── 4. 可选：激活 V2 实盘 ──
        if options['activate_live']:
            self._activate_live()

        # ── 6. 验证 ──
        self._verify(account_ids)

        self.stdout.write(self.style.SUCCESS("[reset_accounts] ✅ 所有步骤完成"))

    # ==================== 账户解析 ====================

    def _resolve_accounts(self, options):
        if options['all']:
            return list(TradingAccount.objects.filter(
                is_active=True
            ).values_list('id', flat=True))
        elif options['account']:
            return [int(aid.strip()) for aid in options['account'].split(',')]
        return []

    # ==================== 平仓（TqSDK） ====================

    def _close_all_positions(self, accounts):
        """遍历账户，逐个平仓。各账户串行执行避免 API 冲突。"""
        for account in accounts:
            close_old_connections()
            positions = PositionState.objects.filter(
                account=account, units__gt=0
            ).exclude(direction=0)

            if not positions.exists():
                self.stdout.write(f"  Acc {account.id} ({account.name}): 无持仓，跳过")
                continue

            self.stdout.write(f"  Acc {account.id} ({account.name}): "
                              f"平仓 {positions.count()} 个持仓...")

            api = None
            try:
                api = create_tqapi(account)
                api.wait_update(deadline=time.time() + 10)

                for pos in positions:
                    close_old_connections()
                    self._execute_exit(api, account, pos)

            except Exception as e:
                log_error(FSM, f"Acc {account.id} 平仓失败: {traceback.format_exc()}",
                          account=account, notify=True)
                self.stdout.write(self.style.ERROR(
                    f"  Acc {account.id} 平仓异常: {e}"))
            finally:
                safe_close_api(api)

    def _execute_exit(self, api, account, position):
        """执行单个持仓平仓：TargetPosTask → 0 → 记录平仓"""
        symbol = position.symbol
        volume = position.contract_total_position

        self.stdout.write(f"    平仓 {symbol}: {volume}手")

        signal = DailyStrategySignal.objects.create(
            account=account, symbol=symbol, product_code=position.product_code,
            trade_date=timezone.now().date(),
            trade_type='STOP_LOSS',
            signal_direction=-position.direction,
            executed_status='EXECUTING',
            trend_factor=Decimal('0'), trend_label='unknown',
            remark='[RESET] 实盘重置强制平仓',
        )

        from tqsdk import TargetPosTask
        target_pos = TargetPosTask(api, symbol, support_open_min_volume=True)
        target_pos.set_target_volume(0)

        result = wait_for_target_position(api, target_pos, symbol, 0, 'reset_exit')

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"    {symbol} 平仓超时，强制清理 DB"))
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status'])
            # 强制删除 PositionState
            PositionState.objects.filter(id=position.id).delete()
            return

        # 获取成交信息
        trades = api.get_trade()
        deadline = time.time() + 3
        while time.time() < deadline:
            api.wait_update(deadline=min(time.time() + 0.5, deadline))

        filled_volume = 0
        total_cost = Decimal('0')
        try:
            sorted_trades = sorted(
                trades.values(), key=lambda t: getattr(t, 'trade_date_time', 0) or 0)
            for trade in sorted_trades:
                if trade.instrument_id == symbol and \
                   trade.offset in ('CLOSE', 'CLOSETODAY'):
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
            api.wait_update()
            avg_price = float(quote.last_price) if quote and quote.last_price else 0
            filled_volume = volume

        record_and_reset_position(api, position, signal, filled_volume, avg_price)

        signal.executed_status = 'SUCCESS'
        signal.save(update_fields=['executed_status'])

        log_trade('reset_exit',
                  f"{symbol} 平仓 {filled_volume}手 @ {avg_price:.2f} [RESET]",
                  symbol=symbol, log_level='SUCCESS', account=account)
        self.stdout.write(self.style.SUCCESS(f"    ✅ {symbol} 平仓完成"))

    # ==================== DB 清理 ====================

    def _cleanup_db(self, account_ids, initial_balance=None):
        """清理活动状态 + 重置账户权益/手续费"""
        self.stdout.write("[reset_accounts] 清理活动状态...")

        # 3a. 清除所有 DailyStrategySignal（含 PENDING、已执行、已取消）
        deleted_signals, _ = DailyStrategySignal.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {deleted_signals} 条 DailyStrategySignal 记录")

        # 3b. 清除所有 PositionState（含幽灵记录）
        deleted, _ = PositionState.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {deleted} 条 PositionState 记录")

        # 3c. 清除 HVOB 运行状态
        h_deleted, _ = HvobMbiDailyState.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {h_deleted} 条 HVOB 运行状态")

        # 3d. 清除 HVOB 观察池
        w_deleted, _ = HvobMbiWatchlistItem.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {w_deleted} 条 HVOB 观察池")

        # 3e. 清除 TradeLog
        t_deleted, _ = TradeLog.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {t_deleted} 条 TradeLog 记录")

        # 3f. 清除 ErrorLog
        e_deleted, _ = ErrorLog.objects.filter(
            account_id__in=account_ids
        ).delete()
        self.stdout.write(f"  删除 {e_deleted} 条 ErrorLog 记录")

        # 3g. 清空绩效指标（权益快照、滚动指标、品种日盈亏、账户绩效汇总）
        DailyEquitySnapshot.objects.filter(account_id__in=account_ids).delete()
        RollingPerformanceMetrics.objects.filter(account_id__in=account_ids).delete()
        SymbolDailyPnl.objects.filter(account_id__in=account_ids).delete()
        AccountPerformanceSummary.objects.filter(account_id__in=account_ids).delete()
        self.stdout.write("  清空绩效指标（DailyEquitySnapshot / RollingPerformanceMetrics / SymbolDailyPnl / AccountPerformanceSummary）")

        # 3h. 清空历史已平仓记录 + 滑点记录
        ClosedPositionRecord.objects.filter(account_id__in=account_ids).delete()
        SlippageRecord.objects.filter(account_id__in=account_ids).delete()
        self.stdout.write("  清空历史记录（ClosedPositionRecord / SlippageRecord）")

        # 3i. 重置账户权益和手续费（可选同时修改初始权益）
        for acct in TradingAccount.objects.filter(id__in=account_ids):
            if initial_balance is not None:
                acct.initial_balance = Decimal(str(initial_balance))
            acct.current_equity = acct.initial_balance
            acct.total_commission = Decimal('0')
            acct.save()
        if initial_balance is not None:
            self.stdout.write(f"  设置 initial_balance = {initial_balance}, "
                              f"重置 {len(account_ids)} 个账户权益 = {initial_balance}, 手续费 = 0")
        else:
            self.stdout.write(f"  重置 {len(account_ids)} 个账户权益 = initial_balance, 手续费 = 0")

    # ==================== 激活实盘（V2） ====================

    def _activate_live(self):
        try:
            cfg = StrategyConfig.objects.get(account_id=1)
            if cfg.is_simulation:
                cfg.is_simulation = False
                cfg.save()
                self.stdout.write(
                    self.style.SUCCESS("  Acc 1 (V2) 已切换为实盘模式 (is_simulation=False)"))
            else:
                self.stdout.write("  Acc 1 (V2) 已经是实盘模式，无需修改")
        except StrategyConfig.DoesNotExist:
            self.stdout.write(self.style.WARNING("  Acc 1 无 StrategyConfig，跳过激活"))

    # ==================== 验证 ====================

    def _verify(self, account_ids):
        self.stdout.write("\n[reset_accounts] 验证清理结果:")
        for aid in account_ids:
            cnt = PositionState.objects.filter(account_id=aid).count()
            self.stdout.write(f"  Acc {aid}: PositionState={cnt}")

        cnt = DailyStrategySignal.objects.filter(
            account_id__in=account_ids, executed_status='PENDING'
        ).count()
        self.stdout.write(f"  PENDING 信号: {cnt}")

        for acct in TradingAccount.objects.filter(id__in=account_ids):
            self.stdout.write(
                f"  Acc {acct.id} ({acct.name}): "
                f"equity={acct.current_equity}, commission={acct.total_commission}")
