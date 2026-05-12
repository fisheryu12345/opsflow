"""
Daily position reconciliation — APScheduler entry point.
Compares DB PositionState vs TqSDK actual positions and emails discrepancies.
Runs at 15:35 (after daily close calculation).
"""
from django.db import close_old_connections
from django_redis import get_redis_connection
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.utils.log_util import log_trade, log_error
from stock.infrastructure.position_reconciliation import reconcile_all_accounts
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.infrastructure.tqapi import create_tqapi, safe_close_api


def job_daily_reconciliation():
    """
    每日持仓校验任务（15:35 执行）。
    对比 DB 与 TqSDK 持仓，差异通过邮件通知用户手动处理。
    """
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:daily_reconciliation'):
            close_old_connections()
            log_trade('job_daily_reconciliation', "开始执行持仓校验任务",
                      symbol='N/A', log_level='INFO')

            from stock.models import TradingAccount
            first_account = TradingAccount.objects.filter(is_active=True).first()
            if not first_account:
                print("[INFO] 无活跃账户，跳过持仓校验")
                return

            api = create_tqapi(first_account)
            try:
                if skip_if_not_trade_day(api=api):
                    return
            finally:
                safe_close_api(api)

            reconcile_all_accounts()
            log_trade('job_daily_reconciliation', "持仓校验任务完成",
                      symbol='N/A', log_level='INFO')

    except LockAcquisitionError:
        print("[INFO] 持仓校验任务正在执行中，跳过本次调度")
    except Exception as e:
        log_error('job_daily_reconciliation', f"持仓校验任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
