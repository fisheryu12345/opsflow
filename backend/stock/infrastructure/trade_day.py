"""
Trade day check using TqSDK trading calendar API.
"""
from datetime import date, timedelta, datetime
from typing import Optional
from stock.utils.log_util import log_error, log_trade


def _fallback_is_trade_day(check_date: date) -> bool:
    """API 失败时的回退方案：按周一到周五判断（无法覆盖法定节假日）。"""
    is_weekday = check_date.weekday() < 5  # 0=Mon ... 4=Fri
    log_trade('is_trade_day', f"API 不可用，回退到星期判断: {check_date} weekday={check_date.weekday()} → {'交易日' if is_weekday else '非交易日'}", symbol='N/A', log_level='WARNING')
    return is_weekday


def is_trade_day(check_date: Optional[date] = None, api=None) -> bool:
    """
    检查指定日期是否为交易日。

    优先通过 TqSDK 交易日历 API 判断；API 失败时回退到星期判断。

    :param check_date: 要检查的日期，默认为今天
    :param api: TqApi实例。如果提供则复用，否则临时创建并关闭
    :return: True=交易日，False=非交易日
    """
    if check_date is None:
        check_date = date.today()

    year = check_date.year
    api_created = False

    try:
        if api is None:
            from stock.infrastructure.tqapi import create_tqapi
            api = create_tqapi()
            api_created = True

        calendar = api.get_trading_calendar(
            start_dt=date(year, 1, 1),
            end_dt=date(year, 12, 31)
        )

        check_datetime = datetime.combine(check_date, datetime.min.time())
        today_record = calendar[calendar['date'] == check_datetime]

        if today_record.empty:
            log_trade('is_trade_day', f"日期 {check_date} 不在交易日历中，回退到星期判断", symbol='N/A', log_level='WARNING')
            return _fallback_is_trade_day(check_date)

        is_trading = today_record['trading'].iloc[0]
        return is_trading

    except Exception as e:
        log_error(
            function_name='is_trade_day',
            error_message=f"检查交易日失败 ({e})，回退到星期判断"
        )
        return _fallback_is_trade_day(check_date)
    finally:
        if api_created and api:
            api.close()


def skip_if_not_trade_day(api=None) -> bool:
    """
    便捷函数：检查今天是否为交易日。

    :return: True=应该跳过（非交易日），False=继续执行（交易日）
    """
    today = date.today()

    if not is_trade_day(today, api):
        # 补充判断：若为周末则 API 回退判断结果明确，否则可能是 API 异常
        if today.weekday() >= 5:
            detail = f"今日({today})为周末"
        else:
            detail = f"今日({today})为工作日但 API 判定为非交易日（需检查TqSDK连接/鉴权）"
        log_trade('skip_if_not_trade_day', f"{detail}，跳过任务", symbol='N/A', log_level='INFO')
        return True

    # log_trade('skip_if_not_trade_day', f"今日({today})为交易日，继续执行任务", symbol='N/A', log_level='INFO')
    return False
