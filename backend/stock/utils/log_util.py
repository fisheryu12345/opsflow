"""
日志工具模块

提供统一的日志记录接口，将系统运行时的错误和业务日志写入数据库。
相比传统的文件日志，数据库日志的优势：
1. 结构化查询：可以按函数名、时间范围、级别快速检索
2. 持久化保存：不受日志文件轮转影响
3. 统计分析：可以统计高频错误、错误趋势
4. 告警集成：可以基于数据库实现自动告警

使用示例：
    from stock.utils.log_util import log_error, log_trade
    
    # 记录错误
    try:
        do_something()
    except Exception as e:
        log_error(
            function_name='my_module.my_function',
            error_message=str(e),
            error_level='ERROR',
            account=my_account,
            symbol='SHFE.rb2610'
        )
    
    # 记录交易日志
    log_trade(
        function_name='my_module.my_function',
        log_message='开仓成功：4手 @ 3820.00',
        log_level='SUCCESS',
        account=my_account,
        symbol='SHFE.rb2610'
    )
"""

import traceback
from typing import Optional
from django.utils import timezone


def log_error(
    function_name: str,
    error_message: str,
):
    """
    记录错误日志到数据库
    
    :param function_name: 发生错误的函数完整路径（如：stock.scheduler.tasks_daily_open.execute_addon_order）
    :param error_message: 错误详情，建议包含完整的Traceback信息
    :param error_level: 错误级别，可选值：CRITICAL/ERROR/WARNING，默认ERROR
    :param account: 关联的交易账户对象（TradingAccount实例），可选
    :param symbol: 关联的合约代码（如：SHFE.rb2610），可选
    
    :return: 创建的ErrorLog对象，失败返回None
    
    使用示例：
        try:
            result = execute_addon_order(api, account, signal)
        except Exception as e:
            log_error(
                function_name='stock.scheduler.tasks_daily_open.execute_addon_order',
                error_message=f"加仓失败: {str(e)}\n{traceback.format_exc()}",
                error_level='ERROR',
                account=account,
                symbol=signal.symbol
            )
    """
    try:
        from stock.models import ErrorLog
        

        
        # 创建错误日志记录
        error_log = ErrorLog.objects.create(
            function_name=function_name,
            error_message=error_message,
        )

        
    except Exception as e:
        # 如果日志记录本身失败，打印到控制台避免静默失败
        print(f"[LOG_ERROR] 写入错误日志失败: {str(e)}")
        print(f"[LOG_ERROR] 原始错误 - 函数: {function_name}, 消息: {error_message}")
        return None


def log_trade(
    function_name: str,
    log_message: str,
    symbol: str = None,
    log_level: str = 'INFO'
):
    """
    记录交易日志到数据库
    
    :param function_name: 生成日志的函数完整路径
    :param log_message: 日志内容，包括关键参数、计算结果、决策原因等
    :param log_level: 日志级别，可选值：DEBUG/INFO/SUCCESS/WARNING，默认INFO
    :param account: 关联的交易账户对象（TradingAccount实例），可选
    :param symbol: 关联的合约代码（如：SHFE.rb2610），可选
    :param signal: 关联的策略信号对象（DailyStrategySignal实例），可选
    
    :return: 创建的TradeLog对象，失败返回None
    
    使用示例：
        # 记录开仓成功
        log_trade(
            function_name='stock.scheduler.tasks_daily_open.execute_entry_order',
            log_message=f"开仓成功: {filled_units}Unit({filled_lots}手) @ {avg_price:.2f}",
            log_level='SUCCESS',
            account=account,
            symbol=signal.symbol,
            signal=signal
        )
        
        # 记录拒绝开仓原因
        log_trade(
            function_name='stock.scheduler.tasks_daily_open.execute_entry_order',
            log_message=f"拒绝开仓: 跳空幅度过大 ({gap_percent:.2f}% > {gap_threshold}%)",
            log_level='WARNING',
            account=account,
            symbol=signal.symbol
        )
    """
    try:
        from stock.models import TradeLog
        
        
        # 创建交易日志记录
        trade_log = TradeLog.objects.create(
            function_name=function_name,
            log_message=log_message,
            symbol=symbol,
            log_level=log_level,

        )
        
        return trade_log
        
    except Exception as e:
        # 如果日志记录本身失败，打印到控制台避免静默失败
        print(f"[LOG_ERROR] 写入交易日志失败: {str(e)}")
        print(f"[LOG_ERROR] 原始日志 - 函数: {function_name}, 消息: {log_message}")
        return None

