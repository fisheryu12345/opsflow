"""
TqApi lifecycle management — centralized API creation and teardown.
"""
from tqsdk import TqApi, TqAuth, TqKq
from stock.core.config_loader import get_config


def create_tqapi():
    """创建 TqApi 连接（使用模拟交易环境）。"""
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


def ensure_api_connected(api):
    """确保 API 连接有效，断开时尝试重连。

    Returns:
        (api, reconnected): 新的 api 实例和是否重连的标志
    """
    if is_api_connected(api):
        return api, False
    print("[WARN] TqApi连接已断开，正在重连...")
    safe_close_api(api)
    return create_tqapi(), True
