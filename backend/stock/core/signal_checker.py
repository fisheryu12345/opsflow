"""
Signal deduplication utility.
"""
from stock.models import DailyStrategySignal
from stock.utils.log_util import log_trade


def check_duplicate_pending_signal(account, symbol: str, trade_type: str) -> bool:
    """
    检查 (account, symbol, trade_type) 是否已有未执行的信号。
    如果有重复信号，记录日志并返回 True（表示应跳过）。
    """
    last_signal = DailyStrategySignal.objects.filter(
        account=account,
        symbol=symbol,
        trade_type=trade_type,
        executed_status='PENDING'
    ).order_by('-trade_date').first()

    if last_signal:
        log_trade(
            'signal_checker.is_duplicate',
            f"[SKIP] 跳过重复 {trade_type} 信号 {symbol}: "
            f"存在未执行的信号（{last_signal.trade_date}）",
            symbol=symbol, log_level='INFO'
        )
        return True
    return False
