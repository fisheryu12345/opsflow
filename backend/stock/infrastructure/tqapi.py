"""
TqApi lifecycle management — centralized API creation and teardown.
"""
from tqsdk import TqApi, TqAuth, TqKq, TqAccount
from stock.core.config_loader import get_config
from stock.models import StrategyConfig, TradingAccount


def _get_default_auth():
    """获取默认 TqSDK 认证凭据。

    优先使用全局 env 配置 (TQAPI_ACCOUNT/TQAPI_PASSWORD)；
    未配置时尝试第一个活跃账户的 StrategyConfig 凭据作为降级。
    """
    tqapi_account = get_config('TQAPI_ACCOUNT')
    tqapi_password = get_config('TQAPI_PASSWORD')
    if tqapi_account and tqapi_password:
        return tqapi_account, tqapi_password
    try:
        acct = TradingAccount.objects.filter(is_active=True).first()
        if acct:
            cfg = StrategyConfig.objects.get(account=acct)
            if cfg.tqapi_account and cfg.tqapi_password:
                return cfg.tqapi_account, cfg.tqapi_password
    except (StrategyConfig.DoesNotExist, Exception):
        pass
    return tqapi_account, tqapi_password


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
            # 模拟账户：用自己的天勤账号创建独立的 TqKq 连接
            return TqApi(
                TqKq(),
                auth=TqAuth(config.tqapi_account, config.tqapi_password)
            )
        except StrategyConfig.DoesNotExist:
            pass
    tqapi_account, tqapi_password = _get_default_auth()
    return TqApi(TqKq(), auth=TqAuth(tqapi_account, tqapi_password))


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

    通过 wait_update 执行一次非阻塞 I/O 来验证连接状态。
    TqSDK 的 get_account() 返回懒加载代理不进行网络 I/O，
    而 wait_update 会驱动事件循环，连接已断开时可能抛出异常。

    注意：非交易时段无新数据时 wait_update 只超时返回 False，
    此时连接正常只是无数据更新，仍返回 True。
    """
    if api is None:
        return False
    try:
        # 给 TqSDK 机会处理连接事件和异常
        api.wait_update(deadline=time.time() + 0.5)
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
