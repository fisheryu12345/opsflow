"""
Pre-market order execution — APScheduler entry point.
Orchestrates signal processing for STOP_LOSS, ENTRY, ROLLOVER, and ADD_ON.
"""
import traceback
import time
from django_redis import get_redis_connection
from django.db import close_old_connections
from datetime import datetime
from stock.models import TradingAccount, StrategyConfig
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade, log_error
from stock.infrastructure.report_sender import send_open_report
from stock.infrastructure.tqapi import create_tqapi, safe_close_api, ensure_api_connected
from stock.infrastructure.order_signals import process_signals_by_type
from stock.utils.redis_lock import redis_lock, LockAcquisitionError


def job_daily_open_process():
    """
    每日开盘处理函数（APScheduler 入口）。
    处理顺序：STOP_LOSS → ENTRY → ROLLOVER → ADD_ON
    """
    current_date = datetime.now().date()
    close_old_connections()

    accounts = TradingAccount.objects.filter(is_active=True)
    is_first_account = True

    for account in accounts:
        api = None
        try:
            # 判断是否独立运行策略（TURTLE/HVOB 自管信号，开盘任务不干预）
            is_independent_strategy = False
            try:
                is_independent_strategy = account.strategyconfig.strategy_type in ('TURTLE', 'HVOB')
            except StrategyConfig.DoesNotExist:
                pass
            if is_independent_strategy:
                print(f"[INFO] {account.name} 独立策略跳过开盘信号处理")
                continue

            api = create_tqapi(account)
            # 等待数据到达，确保 get_position/get_account 能读到有效值
            api.wait_update(deadline=time.time() + 10)

            # 第一个账户的 API 连接复用做交易日检查，避免单独创建连接
            if is_first_account:
                is_first_account = False
                if skip_if_not_trade_day(api=api):
                    return  # finally 块会处理 safe_close_api
            redis = get_redis_connection('default')
            lock_key = f'lock:open:{account.id}'
            with redis_lock(redis, lock_key):
                try:
                    result = process_signals_by_type(api, account, 'STOP_LOSS')
                    print(f"[INFO] 平仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                    api, reconnected = ensure_api_connected(api, account)
                    if reconnected:
                        print(f"[INFO] 平仓处理后API重连成功")
                    result = process_signals_by_type(api, account, 'ENTRY')
                    print(f"[INFO] 开仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                    api, reconnected = ensure_api_connected(api, account)
                    if reconnected:
                        print(f"[INFO] 开仓处理后API重连成功")
                    result = process_signals_by_type(api, account, 'ROLLOVER')
                    print(f"[INFO] 移仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔, 跳过{result['skipped']}笔")

                    api, reconnected = ensure_api_connected(api, account)
                    if reconnected:
                        print(f"[INFO] 移仓处理后API重连成功")
                    result = process_signals_by_type(api, account, 'ADD_ON')
                    print(f"[INFO] 加仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")

                    send_open_report(account, current_date)

                except Exception as e:
                    error_msg = f"处理账户 {account.username}(id={account.id}) 时发生错误: {str(e)}"
                    print(f"[ERROR] {error_msg}")
                    traceback.print_exc()
                    log_error(
                        function_name='job_daily_open_process',
                        error_message=f"{error_msg}\n{traceback.format_exc()}",
                        account=account,
                        notify=True,
                    )
        except LockAcquisitionError:
            print(f"[INFO] 账户 {account.username} 正在处理中, 跳过")
            log_trade('job_daily_open_process', f"账户 {account.username} 正在处理中, 跳过",
                      symbol=None, log_level='INFO', account=account)
        finally:
            safe_close_api(api)
