"""
HVOB-MBI APScheduler 定时任务
"""
import time
from django.db import close_old_connections
from stock.infrastructure.tqapi import create_tqapi, safe_close_api


def hvob_mbi_trading_task():
    """
    HVOB-MBI 日内突破交易任务。
    遍历所有启用配置的账户，依次启动交易引擎。
    引擎完成后自动退出（~14:55 强制平仓后）。
    """
    close_old_connections()

    from django.apps import apps
    HvobMbiConfig = apps.get_model('hvob_mbi', 'HvobMbiConfig')
    configs = list(HvobMbiConfig.objects.filter(is_active=True).select_related('account'))

    if not configs:
        print("[HVOB] 未找到启用中的策略配置，跳过")
        return

    for cfg in configs:
        account = cfg.account
        print(f"[HVOB] 启动引擎 | 账户: {account.name}")

        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)

            from hvob_mbi.trading_engine import HvobTradingEngine
            engine = HvobTradingEngine(api, account)
            engine.run()
            print(f"[HVOB] 引擎正常结束 | 账户: {account.name}")
        except Exception as e:
            print(f"[HVOB] 账户 {account.name} 运行失败: {e}")
        finally:
            safe_close_api(api)
            close_old_connections()
