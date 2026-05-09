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
