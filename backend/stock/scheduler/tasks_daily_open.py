import time
from tqsdk import TqApi, TqAuth
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, TradeExecution, RolloverLog,DailyStrategySignal

def price_gap_proection(api, symbol, target_price, gap_threshold):
    """
    价格跳空保护函数
    :param api: TqApi实例
    :param symbol: 合约代码
    :param target_price: 目标价格
    :param gap_threshold: 跳空价格差阈值
    :return: 是否需要进行价格跳空保护
    """
    # 获取当前合约的最新价格
    quote = api.get_quote(symbol)
    latest_price = quote.last_price
    
    # 计算价格差
    price_gap = abs(latest_price - target_price)
    
    # 判断是否需要进行价格跳空保护
    if price_gap > gap_threshold:
        print(f"⚠️ 价格跳空保护触发: {symbol} 最新价={latest_price}, 目标价={target_price}, 跳空差={price_gap}")
        return True  # 需要进行价格跳空保护
    else:
        return False  # 不需要进行价格跳空保护  
def execute_entry_order(api, account, signal):
    """
    执行开仓操作的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例
    :return: 是否成功执行开仓操作
    """
    # 获取当前合约信息
    contract = api.get_instrument(signal.symbol)
    
    # 创建开仓指令
    order_price = signal.price  # 可以根据策略信号中的价格来设置开仓价格
    order_volume = signal.volume  # 可以根据策略信号中的数量来设置开仓数量
    order_direction = 'BUY' if signal.direction == 1 else 'SELL'  # 根据策略信号中的方向设置开仓指令的方向
    order_id = api.insert_order(
        symbol=signal.symbol,
        direction=order_direction,
        offset='OPEN',
        volume=order_volume,
        limit_price=order_price
    ) 
    print(f"✅ 开仓指令已发送: {signal.symbol} OrderID={order_id}, 价格={order_price}")
    with transaction.atomic():
        # 记录开仓交易执行日志
        TradeExecution.objects.create(
            account=account,
            symbol=signal.symbol,
            direction=order_direction,
            volume=order_volume,
            price=order_price,
            trade_time=timezone.now(),
            order_id=order_id,
            trade_type='ENTRY'
        )
        
        # 创建持仓状态记录
        PositionState.objects.create(
            account=account,
            symbol=signal.symbol,
            direction=signal.direction,
            units=order_volume,
            open_price=order_price,

        )

def execute_exit_order(api, position, signal):
    """
    执行平仓操作的函数
    :param api: TqApi实例
    :param position: PositionState实例
    :param signal: DailyStrategySignal实例
    :return: 是否成功执行平仓操作
    """
    # 获取当前持仓的合约信息
    contract = api.get_instrument(position.symbol)
    
    # 创建平仓指令
    order_price = signal.price  # 可以根据策略信号中的价格来设置平仓价格
    order_volume = position.volume  # 平掉当前持仓的全部数量
    order_direction = 'SELL' if position.direction == 1 else 'BUY'  # 根据持仓方向设置平仓指令的方向
    order_id = api.insert_order(
        symbol=position.symbol,
        direction=order_direction,
        offset='CLOSE',
        volume=order_volume,
        limit_price=order_price
    )
    print(f"✅ 平仓指令已发送: {position.symbol} OrderID={order_id}, 价格={order_price}")
    with transaction.atomic():
        # 记录平仓交易执行日志
        TradeExecution.objects.create(
            account=position.account,
            symbol=position.symbol,
            direction=order_direction,
            volume=order_volume,
            price=order_price,
            trade_time=timezone.now(),
            order_id=order_id,
            trade_type='EXIT'
        )
        
        # 更新持仓状态为已平仓
        PositionState.objects.filter(id=position.id).update(units=0)  # 更新持仓状态为已平仓
def execute_rollover_order(api, position, signal):
    """
    执行移仓操作的函数
    :param api: TqApi实例
    :param position: PositionState实例
    :param signal: DailyStrategySignal实例
    :return: 是否成功执行移仓操作
    """
    # 获取当前持仓的合约信息
    contract = api.get_instrument(position.symbol)
    
    # 创建移仓指令（先平掉当前持仓，再开新的持仓）
    exit_order_price = signal.price  # 可以根据策略信号中的价格来设置平仓价格
    entry_order_price = signal.price  # 可以根据策略信号中的价格来设置开仓价格
    order_volume = position.volume  # 移仓数量与当前持仓数量相同
    
    # 先平掉当前持仓
    exit_order_direction = 'SELL' if position.direction == 1 else 'BUY'
    exit_order_id = api.insert_order(
        symbol=position.symbol,
        direction=exit_order_direction,
        offset='CLOSE',
        volume=order_volume,
        limit_price=exit_order_price
    )
    
    # 再开新的持仓
    entry_order_direction = 'BUY' if position.direction == 1 else 'SELL'
    entry_order_id = api.insert_order(
        symbol=signal.symbol,
        direction=entry_order_direction,
        offset='OPEN',
        volume=order_volume,
        limit_price=entry_order_price
    )
    
    print(f"✅ 移仓指令已发送: {position.symbol} ExitOrderID={exit_order_id}, EntryOrderID={entry_order_id}, 价格={entry_order_price}")
    
    with transaction.atomic():
        # 记录平仓交易执行日志
        TradeExecution.objects.create(
            account=position.account,
            symbol=position.symbol,
            direction=exit_order_direction,
            volume=order_volume,
            price=exit_order_price,
            trade_time=timezone.now(),
            order_id=exit_order_id,
            trade_type='ROLLOVER_EXIT'
        )
        
        # 记录开仓交易执行日志
        TradeExecution.objects.create(
            account=position.account,
            symbol=signal.symbol,
            direction=entry_order_direction,
            volume=order_volume,
            price=entry_order_price,
            trade_time=timezone.now(),
            order_id=entry_order_id,
            trade_type='ROLLOVER_ENTRY'
        )   
        # 更新持仓状态为已平仓
        # PositionState.objects.filter(id=position.id).update(units=0)  # 更新持仓状态为已平仓
def process_exit_signals(api, account, current_date):
    """
    处理平仓信号的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return:
    """
    # 查询所有持仓状态为持仓中的记录
    open_positions = PositionState.objects.filter(account=account, status='open')
    
    for position in open_positions:
        # 检查是否存在平仓信号
        exit_signals = DailyStrategySignal.objects.filter(
            Q(symbol=position.symbol) & 
            Q(trade_type='STOP_LOSS') & 
            Q(date=current_date)
        )
        
        for signal in exit_signals:
            # 执行平仓操作
            success = execute_exit_order(api, position, signal) 
def process_entry_signals(api, account, current_date):
    """
    处理开仓信号的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return:
    """
    # 查询所有开仓信号
    entry_signals = DailyStrategySignal.objects.filter(
        Q(trade_type='ENTRY') & 
        Q(date=current_date)
    )
    
    for signal in entry_signals:
        # 执行开仓操作
        success = execute_entry_order(api, account, signal) 

def process_rollover_signals(api, account, current_date):
    """
    处理移仓信号的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return:
    """
    # 查询所有移仓信号
    rollover_signals = DailyStrategySignal.objects.filter(
        Q(trade_type='ROLLOVER') & 
        Q(date=current_date)
    )
    
    for signal in rollover_signals:
        # 执行移仓操作
        success = execute_rollover_order(api, account, signal)

def job_daily_open_process():
    api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
    account = TradingAccount.objects.get(account_id="1")
    # 获取当前日期
    current_date = timezone.now().date()
    
    #处理平仓信号
    process_exit_signals(api, account, current_date)
    #处理开仓信号
    process_entry_signals(api, account, current_date)
    #处理移仓信号
    process_rollover_signals(api, account, current_date)
