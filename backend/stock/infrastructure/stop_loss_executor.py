"""
Stop-loss execution — position scanning and TargetPosTask-based exit.
"""
import time
import traceback
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, F
from tqsdk import TargetPosTask
from stock.models import TradingAccount, PositionState, DailyStrategySignal, ClosedPositionRecord
from stock.utils.log_util import log_trade, log_error
from stock.infrastructure.order_execution import record_and_reset_position
from stock.core.signal_checker import check_duplicate_pending_signal


def execute_stop_loss_exit(api, position):
    """
    使用 TargetPosTask 执行止损平仓。

    :return: tuple (是否成功, 成交手数, 成交均价)
    """
    try:
        print(f"[INFO] 开始执行止损平仓: {position.symbol} (当前持仓={position.contract_total_position}手)")

        if position.contract_total_position <= 0:
            return True, 0, Decimal('0')

        target_pos = TargetPosTask(api, position.symbol)
        target_pos.set_target_volume(0)

        start_time = time.time()
        while not target_pos.is_finished():
            api.wait_update(deadline=time.time() + 1)
            if time.time() - start_time > 60:
                print(f"⚠️ 止损平仓超时: {position.symbol}")
                return False, 0, Decimal('0')

        trades = api.get_trades()
        filled_volume = 0
        total_cost = Decimal('0')

        for trade in reversed(trades.values()):
            if (trade.instrument_id == position.symbol and
                    trade.offset == 'CLOSE'):
                filled_volume += trade.volume
                total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                if filled_volume >= position.contract_total_position:
                    break

        if filled_volume > 0:
            avg_price = total_cost / Decimal(str(filled_volume))
        else:
            quote = api.get_quote(position.symbol)
            avg_price = Decimal(str(quote.last_price)) if quote.last_price else Decimal('0')
            filled_volume = position.contract_total_position

        print(f"✅ 止损平仓成功: {position.symbol} 成交量={filled_volume}, 均价={avg_price:.2f}")
        return True, filled_volume, avg_price

    except Exception as e:
        error_msg = f"止损平仓异常: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        log_error(
            function_name='execute_stop_loss_exit',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )
        return False, 0, Decimal('0')


def check_and_execute_stop_loss(api):
    """
    检查持仓止损并执行平仓。
    """
    try:
        accounts = TradingAccount.objects.filter(is_active=True)
        if not accounts.exists():
            print("[WARN] 未找到活跃账户，跳过止损检查")
            return

        for account in accounts:
            try:
                _execute_stop_loss_for_account(api, account)
            except Exception as acct_error:
                error_msg = f"处理账户 {account.name} 止损检查失败: {acct_error}"
                print(f"[ERROR] {error_msg}")
                traceback.print_exc()
                log_error(
                    function_name='check_and_execute_stop_loss',
                    error_message=f"{error_msg}\n{traceback.format_exc()}",
                    account=account,
                )
                continue

    except Exception as e:
        error_msg = f"检查并执行止损失败: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        log_error(
            function_name='check_and_execute_stop_loss',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )


def _execute_stop_loss_for_account(api, default_account):
    """
    为单个账户执行止损检查。
    """
    try:
        long_stop_loss = Q(direction=1) & Q(latest_close_price__lt=F('stop_loss_price'))
        short_stop_loss = Q(direction=-1) & Q(latest_close_price__gt=F('stop_loss_price'))

        positions = PositionState.objects.filter(
            account=default_account,
            units__gt=0,
            latest_close_price__isnull=False,
            stop_loss_price__isnull=False
        ).filter(long_stop_loss | short_stop_loss)

        exit_count = 0

        for position in positions:
            try:
                latest_price = float(position.latest_close_price)
                stop_loss = float(position.stop_loss_price)

                if position.direction == 1:
                    remark = f"多头止损触发: 最新价{latest_price:.2f} < 止损价{stop_loss:.2f}"
                else:
                    remark = f"空头止损触发: 最新价{latest_price:.2f} > 止损价{stop_loss:.2f}"

                if check_duplicate_pending_signal(default_account, position.symbol, 'STOP_LOSS'):
                    continue

                DailyStrategySignal.objects.create(
                    account=default_account,
                    symbol=position.symbol,
                    product_code=position.product_code,
                    trade_date=date.today(),
                    trend_factor=Decimal(str(position.indicators.get('trend_factor', 0))) if position.indicators else Decimal('0'),
                    trend_label=position.indicators.get('trend_label', '') if position.indicators else '',
                    donchian_upper=None,
                    donchian_lower=None,
                    is_breakout=False,
                    signal_direction=0,
                    trade_type='STOP_LOSS',
                    remark=remark,
                    executed_status='EXECUTING'
                )

                print(f"[EXIT] 止损信号: {position.symbol} - {remark}")

                success, filled_volume, avg_price = execute_stop_loss_exit(api, position)

                if success and filled_volume > 0:
                    exit_count += 1

                    record_and_reset_position(api, position, None, filled_volume, float(avg_price))

                    DailyStrategySignal.objects.filter(
                        account=default_account,
                        symbol=position.symbol,
                        trade_type='STOP_LOSS',
                        executed_status='EXECUTING'
                    ).update(executed_status='SUCCESS')

                    log_trade('check_and_execute_stop_loss',
                              f"✅ 止损平仓成功: {position.symbol} 成交量={filled_volume}, 均价={avg_price:.2f}",
                              symbol=position.symbol, log_level='SUCCESS')
                else:
                    DailyStrategySignal.objects.filter(
                        account=default_account,
                        symbol=position.symbol,
                        trade_type='STOP_LOSS',
                        executed_status='EXECUTING'
                    ).update(executed_status='FAILED')

                    log_trade('check_and_execute_stop_loss',
                              f"❌ 止损平仓失败: {position.symbol}",
                              symbol=position.symbol, log_level='ERROR')

            except Exception as pos_error:
                error_msg = f"处理 {position.symbol} 止损检查失败: {pos_error}"
                print(f"[ERROR] {error_msg}")
                traceback.print_exc()
                log_error(
                    function_name='_execute_stop_loss_for_account',
                    error_message=f"{error_msg}\n{traceback.format_exc()}",
                    account=default_account,
                )
                continue

        if exit_count > 0:
            print(f"[SUMMARY] 今日共执行 {exit_count} 个止损平仓")
            log_trade('check_and_execute_stop_loss',
                      f"[SUMMARY] 今日共执行 {exit_count} 个止损平仓",
                      symbol='N/A', log_level='SUCCESS')
        else:
            print(f"[INFO] 本次检查未发现触发止损的持仓")

    except Exception as e:
        print(f"[ERROR] 检查并执行止损失败: {e}")
        traceback.print_exc()
