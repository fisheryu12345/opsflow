"""
Pre-market order execution — APScheduler entry point.
Orchestrates signal processing for STOP_LOSS, ENTRY, ROLLOVER, and ADD_ON.
"""
import traceback
from django_redis import get_redis_connection
from django.db import close_old_connections
from datetime import datetime
from stock.models import TradingAccount
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade
from stock.infrastructure.report_sender import send_open_report
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.order_signals import process_signals_by_type


def job_daily_open_process():
    """
    每日开盘处理函数（APScheduler 入口）。
    处理顺序：STOP_LOSS → ENTRY → ROLLOVER → ADD_ON
    """
    current_date = datetime.now().date()
    close_old_connections()

    accounts = TradingAccount.objects.all()
    for account in accounts:
        api = create_tqapi()
        if skip_if_not_trade_day(api=api):
            safe_close_api(api)
            return

        redis = get_redis_connection('default')
        lock_key = 'lock:open'
        if redis.set(lock_key, 'true', nx=True, ex=600):
            try:
                result = process_signals_by_type(api, account, 'STOP_LOSS')
                print(f"[INFO] 平仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                result = process_signals_by_type(api, account, 'ENTRY')
                print(f"[INFO] 开仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                result = process_signals_by_type(api, account, 'ROLLOVER')
                print(f"[INFO] 移仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔, 跳过{result['skipped']}笔")

                result = process_signals_by_type(api, account, 'ADD_ON')
                print(f"[INFO] 加仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                send_open_report(account, current_date)

            except Exception as e:
                print(f"[ERROR] 处理账户 {account.username} 时发生错误: {str(e)}")
                traceback.print_exc()
            finally:
                redis.delete(lock_key)
                safe_close_api(api)
        else:
            print(f"[INFO] 账户 {account.username} 正在处理中, 跳过")
            log_trade('job_daily_open_process', f"账户 {account.username} 正在处理中, 跳过",
                      symbol=None, log_level='INFO')
