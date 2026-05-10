"""
Pre-close stop-loss execution — APScheduler entry point.
"""
from django.db import close_old_connections
from django_redis import get_redis_connection
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade, log_error
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.stop_loss_executor import check_and_execute_stop_loss


def execute_exit_before_close():
    """
    在收盘前执行平仓操作（APScheduler 入口）。
    检查所有持仓的止损条件并执行平仓。
    """
    api = None
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:exit_before_close'):
            close_old_connections()
            log_trade('execute_exit_before_close', "开始执行收盘前平仓任务", symbol='N/A', log_level='INFO')

            api = create_tqapi()
            if skip_if_not_trade_day(api=api):
                return

            check_and_execute_stop_loss(api)
            print("[INFO] ✅ 收盘前平仓任务完成")

    except LockAcquisitionError:
        print("[INFO] 收盘前平仓任务正在执行中，跳过本次调度")
    except Exception as e:
        log_error('execute_exit_before_close', f"收盘前平仓任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        safe_close_api(api)
