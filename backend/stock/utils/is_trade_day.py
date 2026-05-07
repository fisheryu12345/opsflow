"""
交易日检查工具模块

提供判断指定日期是否为交易日的功能。
"""
from datetime import date, timedelta
from typing import Optional
import logging

from stock.utils.log_util import log_error, log_trade



def is_trade_day(check_date: Optional[date] = None, api=None) -> bool:
    """
    检查指定日期是否为交易日
    
    使用 TqSDK 的交易日历 API 查询。
    
    参数：
    check_date: 要检查的日期，默认为今天
    api: TqApi实例。如果提供则复用，否则临时创建并关闭
    
    返回：
    bool: True=交易日，False=非交易日
    """
    if check_date is None:
        check_date = date.today()
    
    year = check_date.year
    api_created = False
    
    try:
        # 如果没有传入 api，临时创建一个
        if api is None:
            from tqsdk import TqApi, TqAuth, TqKq
            api = TqApi(TqKq(), auth=TqAuth("yupei1986", "yupei1986"))
            api_created = True
        
        # 获取全年交易日历（避免边界问题）
        from datetime import datetime
        calendar = api.get_trading_calendar(
            start_dt=date(year, 1, 1),
            end_dt=date(year, 12, 31)
        )
        
        # 【关键修复】将 check_date 转换为 datetime 对象，以匹配 DataFrame 的 datetime64[ns] 类型
        check_datetime = datetime.combine(check_date, datetime.min.time())
        
        # 在日历中查找指定日期
        today_record = calendar[calendar['date'] == check_datetime]
        
        if today_record.empty:
            log_trade('is_trade_day', f"日期 {check_date} 不在交易日历中", symbol='N/A', log_level='WARNING')
            return False
        
        is_trading = today_record['trading'].iloc[0]
        
        if is_trading:
            log_trade('is_trade_day', f"{check_date} 是交易日", symbol='N/A', log_level='INFO')
        else:
            log_trade('is_trade_day', f"{check_date} 不是交易日", symbol='N/A', log_level='INFO')
        
        return is_trading
        
    except Exception as e:
        log_error(f"[ERROR] 检查交易日失败: {e}")
        return False  # 【修复】异常时应返回 False，而非 True
    finally:
        # 如果是临时创建的 api，使用后关闭
        if api_created and api:
            api.close()


def skip_if_not_trade_day(api=None) -> bool:
    """
    便捷函数：检查今天是否为交易日，如果不是则打印日志
    
    适用于定时任务开头的快速检查。
    
    参数：
    api: TqApi实例（可选）
    
    返回：
    bool: True=应该跳过（非交易日），False=继续执行（交易日）
    
    示例：
    >>> def job_daily_task():
    ...     if skip_if_not_trade_day():
    ...         return  # 非交易日，直接返回
    ...     # 继续执行任务逻辑
    """
    from stock.utils.log_util import log_trade
    
    today = date.today()
    
    if not is_trade_day(today, api):
        msg = f"今日({today})为非交易日，跳过任务"
        print(f"[INFO] {msg}")
        log_trade('skip_if_not_trade_day', msg, symbol='N/A', log_level='INFO')
        return True  # 应该跳过
    
    print(f"[INFO] 今日({today})为交易日，继续执行任务")
    log_trade('skip_if_not_trade_day', f"今日({today})为交易日，继续执行任务", symbol='N/A', log_level='INFO')
    return False  # 不应该跳过


