"""
Clear all positions for specified accounts via TqSDK TargetPosTask.
Usage: python manage.py clear_all_positions
"""
import time
from decimal import Decimal
from django.db import close_old_connections
from django.core.management.base import BaseCommand
from stock.models import TradingAccount, PositionState, DailyStrategySignal
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from tqsdk import TargetPosTask

ACCOUNT_NAMES = ['510976', '510977', '510988']
TIMEOUT = 60


class Command(BaseCommand):
    help = 'Clear all positions for 510976, 510977, 510988 via TargetPosTask'

    def handle(self, *args, **options):
        close_old_connections()
        accounts = TradingAccount.objects.filter(name__in=ACCOUNT_NAMES)

        for account in accounts:
            api = None
            try:
                positions = PositionState.objects.filter(account=account, units__gt=0)
                if not positions.exists():
                    self.stdout.write(f"[SKIP] {account.name}: no positions")
                    continue

                self.stdout.write(f"\n[开始] {account.name}: {positions.count()} positions")
                api = create_tqapi(account)
                api.wait_update(deadline=time.time() + 10)

                symbols = [p.symbol for p in positions if p.contract_total_position > 0]
                for p in positions:
                    self.stdout.write(f"  {p.symbol} dir={p.direction} units={p.units} lots={p.contract_total_position}")

                if not symbols:
                    continue

                # 为每个品种创建独立的 TargetPosTask
                self.stdout.write(f"  [下单] 逐品种设置目标持仓=0...")
                tasks = {}
                for sym in symbols:
                    task = TargetPosTask(api, sym)
                    task.set_target_volume(0)
                    tasks[sym] = task

                # 等待持仓归零
                start = time.time()
                all_done = False
                while time.time() - start < TIMEOUT:
                    remaining = TIMEOUT - (time.time() - start)
                    if remaining <= 0:
                        break
                    api.wait_update(deadline=time.time() + min(1, remaining))
                    all_done = all(
                        api.get_position(s).pos == 0 for s in symbols
                    )
                    if all_done:
                        break

                # 释放所有 TargetPosTask
                for sym, task in tasks.items():
                    try:
                        task.cancel()
                        while not task.is_finished():
                            api.wait_update(deadline=time.time() + 1)
                    except Exception:
                        pass

                # 等待成交回报到达
                trade_wait = time.time()
                while time.time() - trade_wait < TIMEOUT:
                    api.wait_update(deadline=time.time() + 0.5)

                # 更新 DB
                for pos in positions:
                    try:
                        tq_pos = api.get_position(pos.symbol)
                        remaining_lots = tq_pos.pos if tq_pos else 0
                    except Exception:
                        remaining_lots = 0

                    if remaining_lots == 0:
                        PositionState.objects.filter(id=pos.id).update(
                            units=0, direction=0, contract_total_position=0,
                            stop_loss_price=None, highest_close=None, lowest_close=None,
                            cost_price=None, protect_cost_enabled=False,
                            is_rollover_needed=False, indicators={},
                            latest_close_price=None, first_open_price=None,
                            entry_atr=None, entry_trend_factor=None,
                            entry_trend_label=None,
                        )
                        self.stdout.write(f"  [DB] {pos.symbol} 已清空")
                    else:
                        self.stdout.write(f"  [WARN] {pos.symbol} 仍有 {remaining_lots} 手")

                # 取消 PENDING 信号
                cancelled = DailyStrategySignal.objects.filter(
                    account=account, executed_status='PENDING'
                ).update(executed_status='CANCELLED', remark='手工清仓取消')
                if cancelled:
                    self.stdout.write(f"  [信号] 取消 {cancelled} 条 PENDING 信号")

                self.stdout.write(f"[完成] {account.name}")

            except Exception as e:
                self.stderr.write(f"[错误] {account.name}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                safe_close_api(api)
