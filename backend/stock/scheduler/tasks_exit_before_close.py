"""
Pre-close stop-loss execution — APScheduler entry point.
Per-account API connections to support real account mode.
"""
import time
from django.db import close_old_connections
from django_redis import get_redis_connection
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade, log_error
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.stop_loss_executor import check_and_execute_stop_loss
from stock.models import TradingAccount, StrategyConfig


def execute_exit_before_close():
    """
    在收盘前执行平仓操作（APScheduler 入口）。
    遍历所有活跃账户，为每个账户创建对应的 TqApi 连接（模拟/实盘），
    检查该账户持仓的止损条件并执行平仓。
    """
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:exit_before_close'):
            close_old_connections()
            log_trade('execute_exit_before_close', "开始执行收盘前平仓任务", symbol='N/A', log_level='INFO')

            accounts = TradingAccount.objects.filter(is_active=True)
            if not accounts.exists():
                print("[WARN] 未找到活跃账户，跳过收盘前平仓任务")
                return

            # 用第一个账户检查交易日
            first_api = create_tqapi(accounts.first())
            try:
                if skip_if_not_trade_day(api=first_api):
                    return
            finally:
                safe_close_api(first_api)

            for account in accounts:
                api = None
                try:
                    log_trade('execute_exit_before_close', f"开始执行账户 {account.name} 的收盘前止损检查",symbol='N/A',log_level='INFO',account=account.name)
                    api = create_tqapi(account)
                    api.wait_update(deadline=time.time() + 10)
                    check_and_execute_stop_loss(api, account=account)
                    print(f"[INFO] ✅ {account.name} 收盘前止损检查完成")
                except Exception as e:
                    log_error('execute_exit_before_close',
                              f"账户 {account.name} 止损检查失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
                finally:
                    safe_close_api(api)

    except LockAcquisitionError:
        print("[INFO] 收盘前平仓任务正在执行中，跳过本次调度")
    except Exception as e:
        log_error('execute_exit_before_close', f"收盘前平仓任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
