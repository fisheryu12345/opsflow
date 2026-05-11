"""
TqApi lifecycle management — centralized API creation and teardown.
"""
from tqsdk import TqApi, TqAuth, TqKq, TqAccount
from stock.core.config_loader import get_config
from stock.models import StrategyConfig


def create_tqapi(account=None):
    """创建 TqApi 连接。

    Args:
        account: TradingAccount 实例或 ID，用于查询策略配置中的运行模式。
                 为 None 时默认使用模拟盘 TqKq。
    """
    if account is not None:
        try:
            acct_id = account.id if hasattr(account, 'id') else account
            config = StrategyConfig.objects.get(account_id=acct_id)
            if not config.is_simulation:
                return TqApi(
                    TqAccount(config.future_broker, config.future_account, config.future_password),
                    auth=TqAuth(config.tqapi_account, config.tqapi_password)
                )
        except StrategyConfig.DoesNotExist:
            pass
    return TqApi(TqKq(), auth=TqAuth(get_config('TQAPI_ACCOUNT'), get_config('TQAPI_PASSWORD')))


def safe_close_api(api):
    """安全关闭 TqApi 连接。"""
    if api:
        try:
            api.close()
            print("[INFO] TqApi连接已关闭")
        except Exception:
            pass


def is_api_connected(api) -> bool:
    """检查 TqApi 连接是否仍然有效。

    通过一次轻量级调用来验证连接状态。
    返回 True 表示连接正常，False 表示已断开。
    """
    if api is None:
        return False
    try:
        _ = api.get_account()
        return True
    except Exception:
        return False


def ensure_api_connected(api, account=None):
    """确保 API 连接有效，断开时尝试重连。

    Args:
        account: 关联的 TradingAccount 实例，用于重连时创建对应模式的连接。

    Returns:
        (api, reconnected): 新的 api 实例和是否重连的标志
    """
    if is_api_connected(api):
        return api, False
    print("[WARN] TqApi连接已断开，正在重连...")
    safe_close_api(api)
    return create_tqapi(account), True
