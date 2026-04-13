import os
import time
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, TradeExecution, RolloverLog,DailyStrategySignal

# ==================== 仓位管理配置常量 ====================
POSITION_RISK_BASE_AMOUNT = 4000  # 每个Unit（单位）的固定风险资金基数（元）
POSITION_RISK_MULTIPLIER = 2      # ATR风险倍数系数（止损距离 = N × ATR）
POSITION_MIN_UNITS = 1            # 最小持仓单位数（海龟法则中的"Unit"数量，非手数）
POSITION_MAX_UNITS = 3            # 最大持仓3单位数（如1Unit=4手，最大持仓12手）

def calculate_unit_lots(api, symbol):
    """
    计算1个海龟Unit对应的实际手数
    
    计算公式：1个Unit的手数 = POSITION_RISK_BASE_AMOUNT / (ATR × POSITION_RISK_MULTIPLIER × 合约乘数)
    
    示例（RB2610）：
    - POSITION_RISK_BASE_AMOUNT = 4000元
    - ATR(20) = 50元/吨
    - POSITION_RISK_MULTIPLIER = 2（止损距离为2倍ATR）
    - 合约乘数 = 10吨/手
    - 1个Unit的手数 = 4000 / (50 × 2 × 10) = 4手
    
    含义：持有4手螺纹钢，如果价格反向波动2个ATR（100元/吨）触发止损，
    亏损金额 = 4手 × 10吨/手 × 100元/吨 = 4000元（即预设的风险基数）
    
    :param api: TqApi实例
    :param symbol: 合约代码（如 "SHFE.rb2610"）
    :return: 1个Unit对应的实际手数（整数）
    """
    try:
        # 获取合约信息
        contract = api.get_instrument(symbol)
        if not contract or not contract.volume_multiple:
            return 1  # 默认返回1手
        
        contracts_per_unit = contract.volume_multiple  # 合约乘数（如螺纹钢10吨/手）
        
        # 获取K线数据计算20日ATR
        klines = api.get_kline_serial(symbol, duration_seconds=86400, data_length=25)
        
        if klines is None or len(klines) < 21:
            # 数据不足，使用默认值
            return 1
        
        # 计算TR（真实波幅）
        high = klines['high']
        low = klines['low']
        close = klines['close']
        
        # 计算TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr_list = []
        for i in range(1, len(klines)):
            hl = high.iloc[i] - low.iloc[i]
            hpc = abs(high.iloc[i] - close.iloc[i-1])
            lpc = abs(low.iloc[i] - close.iloc[i-1])
            tr = max(hl, hpc, lpc)
            tr_list.append(tr)
        
        if len(tr_list) < 20:
            return 1  # 数据不足
        
        # 计算20日ATR（取最近20个TR的平均值）
        atr_20 = sum(tr_list[-20:]) / 20
        
        # 防止除零错误
        if atr_20 <= 0:
            return 1
        
        # 【核心公式】计算1个Unit对应的手数
        # 公式含义：固定风险资金 / (单手止损金额)
        # 单手止损金额 = ATR × 风险倍数 × 合约乘数
        #              = 50元/吨 × 2 × 10吨/手 = 1000元/手
        unit_lots = POSITION_RISK_BASE_AMOUNT / (atr_20 * POSITION_RISK_MULTIPLIER * contracts_per_unit)
        
        # 向下取整，确保风险可控
        unit_lots = int(unit_lots)
        
        # 至少1手
        unit_lots = max(1, unit_lots)
        
        return unit_lots
        
    except Exception as e:
        # 异常情况下返回默认值
        return 1

def price_gap_proection(api, symbol, direction, gap_threshold_percent=1.5):
    """
    价格跳空保护函数（支持期货多空双向交易）
    :param api: TqApi实例
    :param symbol: 合约代码
    :param direction: 交易方向，1表示做多，-1表示做空
    :param gap_threshold_percent: 跳空阈值百分比，默认1.5%
    :return: True表示可以交易（无危险跳空），False表示存在危险跳空应禁止交易
    """
    # 获取当前合约的行情
    quote = api.get_quote(symbol)
    latest_price = quote.last_price
    pre_close = quote.pre_close  # 昨日收盘价
    
    # 检查数据有效性
    if latest_price is None or pre_close is None or pre_close == 0:
        return False  # 数据无效，禁止交易
    
    # 计算跳空幅度（相对于昨日收盘价）
    gap_percent = ((latest_price - pre_close) / pre_close) * 100
    
    # 根据交易方向判断是否存在危险跳空
    if direction == 1:
        # 做多：警惕向上跳空超过阈值（追高风险）
        if gap_percent > gap_threshold_percent:
            return False  # 向上跳空过大，禁止做多
        else:
            return True  # 可以正常做多
    elif direction == -1:
        # 做空：警惕向下跳空超过阈值（追空风险）
        if gap_percent < -gap_threshold_percent:
            return False  # 向下跳空过大，禁止做空
        else:
            return True  # 可以正常做空
    else:
        return False  # 无效的交易方向


def execute_addon_order(api, account, signal, max_retries=5, retry_interval=10):
    """
    执行加仓操作的函数（从信号表获取加仓指令 + 使用对手价 + 重试机制 + 持仓表更新）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例（trade_type='ADD_ON'）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行加仓操作
    """
    # 【验证信号类型】
    if signal.trade_type != 'ADD_ON':
        return False
    
    # 获取当前持仓状态
    position = PositionState.objects.filter(
        account=account,
        symbol=signal.symbol,
        units__gt=0
    ).first()
    
    if not position:
        return False  # 无持仓，无法加仓
    
    # 【从信号备注中解析加仓单位数】
    # remark格式: "加仓信号: 多头 价格差=60.00, ATR=50.00, 建议加仓2单位 (当前1→3)"
    try:
        import re
        match = re.search(r'建议加仓(\d+)单位', signal.remark or '')
        if not match:
            return False  # 无法解析加仓单位数
        
        add_units_from_signal = int(match.group(1))
        
        if add_units_from_signal <= 0:
            return False  # 加仓单位数无效
        
    except Exception as e:
        return False  # 解析失败
    
    # 获取合约信息
    try:
        contract = api.get_instrument(signal.symbol)
        contracts_per_unit = contract.volume_multiple if contract and contract.volume_multiple else 1
    except:
        contracts_per_unit = 1
    
    # 计算实际下单手数 = 加仓单位数 × 合约乘数
    order_volume = add_units_from_signal * contracts_per_unit
    order_direction = 'BUY' if signal.direction == 1 else 'SELL'
    
    filled_total_lots = 0  # 累计已成交手数
    total_cost = Decimal('0')  # 累计成交金额
    last_order_id = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # 计算本次需要下单的手数
            remaining_volume = order_volume - filled_total_lots
            
            if remaining_volume <= 0:
                break  # 已全部成交
            
            # 获取最新行情并使用对手价
            quote = api.get_quote(signal.symbol)
            
            if order_direction == 'BUY':
                order_price = quote.ask_price1 if quote.ask_price1 else quote.last_price
            else:
                order_price = quote.bid_price1 if quote.bid_price1 else quote.last_price
            
            # 行情可用性检查
            if order_price is None:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                else:
                    return False
            
            # 发送加仓指令
            order_id = api.insert_order(
                symbol=signal.symbol,
                direction=order_direction,
                offset='ADDON',
                volume=remaining_volume,  # ← 剩余手数
                limit_price=order_price
            )
            last_order_id = order_id
            
            # 监控订单状态
            start_time = time.time()
            while time.time() - start_time < retry_interval:
                api.wait_update(deadline=time.time() + 0.5)
                order = api.get_order(order_id)
                
                if order.status == 'FINISHED':
                    break
                elif order.status in ['CANCELLED', 'ERROR']:
                    return False
                elif order.status == 'PARTIAL_FILLED':
                    pass
            
            # 处理订单结果
            order = api.get_order(order_id)
            
            if order.status == 'FINISHED':
                current_filled = order.volume_orign - order.volume_left
                actual_filled = min(current_filled, remaining_volume)
                
                # 数据有效性验证
                if actual_filled <= 0 or order.average_price is None:
                    return False
                
                filled_total_lots += actual_filled
                total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                
                # 检查是否全部完成
                if filled_total_lots >= order_volume:
                    avg_price = total_cost / Decimal(str(filled_total_lots))
                    
                    # 计算加仓的单位数（向下取整）
                    added_units = filled_total_lots // contracts_per_unit
                    
                    with transaction.atomic():
                        # 记录加仓交易执行日志
                        TradeExecution.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            direction=order_direction,
                            volume=filled_total_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=order_id,
                            trade_type='ADD_ON',
                            signal=signal  # 关联到原始信号
                        )
                        
                        # 【更新持仓表】
                        new_units = position.units + added_units  # ← 累加单位数
                        new_total_lots = position.contract_total_position + filled_total_lots  # ← 累加总手数
                        
                        # 检查是否超过最大持仓限制
                        if new_units > POSITION_MAX_UNITS:
                            return False
                        
                        # 【核心计算】加权平均成本价
                        # 公式：新成本价 = (旧持仓总成本 + 新开仓总成本) / 新持仓总手数
                        old_total_cost = Decimal(str(position.contract_total_position)) * position.contract_price_avg
                        new_add_cost = total_cost  # 本次加仓的总成本
                        combined_total_cost = old_total_cost + new_add_cost
                        
                        new_avg_price = combined_total_cost / Decimal(str(new_total_lots))
                        
                        PositionState.objects.filter(id=position.id).update(
                            units=new_units,  # ← 更新单位数
                            contract_total_position=new_total_lots,  # ← 更新总手数
                            last_add_price=avg_price,  # 更新上次加仓价为本次加权均价
                            contract_price_avg=new_avg_price,  # ← 更新加权平均成本价
                            latest_close_price=avg_price  # 同时更新最新收盘价
                        )
                    
                    return True
                else:
                    # FINISHED但累计量不足，说明有逻辑错误
                    return False
            
            elif order.status == 'PARTIAL_FILLED':
                current_filled = order.volume_orign - order.volume_left
                actual_filled = min(current_filled, remaining_volume)
                
                # 数据有效性验证
                if actual_filled > 0 and order.average_price is not None:
                    filled_total_lots += actual_filled
                    total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                
                # 撤销剩余部分，准备下一轮重试
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                last_order_id = None
                
                # 检查是否已累计全部成交
                if filled_total_lots >= order_volume:
                    avg_price = total_cost / Decimal(str(filled_total_lots))
                    
                    # 计算加仓的单位数
                    added_units = filled_total_lots // contracts_per_unit
                    
                    with transaction.atomic():
                        TradeExecution.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            direction=order_direction,
                            volume=filled_total_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=order_id,
                            trade_type='ADD_ON',
                            signal=signal  # 关联到原始信号
                        )
                        
                        # 【更新持仓表】
                        new_units = position.units + added_units
                        new_total_lots = position.contract_total_position + filled_total_lots
                        
                        if new_units > POSITION_MAX_UNITS:
                            return False
                        
                        # 【核心计算】加权平均成本价
                        old_total_cost = Decimal(str(position.contract_total_position)) * position.contract_price_avg
                        new_add_cost = total_cost
                        combined_total_cost = old_total_cost + new_add_cost
                        
                        new_avg_price = combined_total_cost / Decimal(str(new_total_lots))
                        
                        PositionState.objects.filter(id=position.id).update(
                            units=new_units,
                            contract_total_position=new_total_lots,
                            last_add_price=avg_price,
                            contract_price_avg=new_avg_price,  # ← 更新加权平均成本价
                            latest_close_price=avg_price
                        )
                    
                    return True
                else:
                    # 继续重试剩余量
                    if attempt >= max_retries:
                        return False
                    continue
            else:
                # 未成交，撤单后重试
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                last_order_id = None
                
                if attempt >= max_retries:
                    return False
                    
        except Exception as e:
            if last_order_id:
                try:
                    api.cancel_order(last_order_id)
                    api.wait_update(deadline=time.time() + 1)
                except:
                    pass
                finally:
                    last_order_id = None
            
            if attempt >= max_retries:
                return False
    
    return False


def execute_entry_order(api, account, signal, max_retries=5, retry_interval=10, gap_threshold_percent=1.5):
    """
    执行开仓操作的函数（使用对手价 + 跳空保护 + 重试机制）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :param gap_threshold_percent: 跳空阈值百分比，默认1.5%
    :return: 是否成功执行开仓操作
    """
    # 【基于ATR计算1个Unit对应的手数】
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    # 首次开仓固定为1个Unit
    target_units = 1
    order_volume = target_units * unit_lots  # ← 实际下单手数
    
    # 获取合约信息
    try:
        contract = api.get_instrument(signal.symbol)
        contracts_per_unit = contract.volume_multiple if contract and contract.volume_multiple else 1
    except:
        contracts_per_unit = 1
    
    order_direction = 'BUY' if signal.direction == 1 else 'SELL'
    
    # 【持仓重复检查】检查是否已存在同合约、同方向的持仓
    existing_position = PositionState.objects.filter(
        account=account,
        symbol=signal.symbol,
        direction=signal.direction,
        units__gt=0  # 持仓单位数大于0
    ).first()
    
    if existing_position:
        # 已存在持仓，不应重复开仓
        return False
    
    last_order_id = None  # 记录最后一次发送的订单ID，用于异常清理
    
    for attempt in range(1, max_retries + 1):
        try:
            # 【第1步】获取最新行情并确定价格
            quote = api.get_quote(signal.symbol)
            
            # 使用对手价：买单用卖一价，卖单用买一价
            if order_direction == 'BUY':
                order_price = quote.ask_price1 if quote.ask_price1 else quote.last_price
            else:  # SELL
                order_price = quote.bid_price1 if quote.bid_price1 else quote.last_price
            
            # 【行情可用性检查】如果价格为空，跳过本轮重试
            if order_price is None:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                else:
                    return False
            
            # 【第2步】跳空阈值保护检查（仅在第一轮检查）
            if attempt == 1:
                can_trade = price_gap_proection(api, signal.symbol, signal.direction, gap_threshold_percent)
                if not can_trade:
                    # 存在危险跳空，放弃本次交易
                    return False
            
            # 【第3步】发送开仓指令
            order_id = api.insert_order(
                symbol=signal.symbol,
                direction=order_direction,
                offset='OPEN',
                volume=order_volume,  # ← 实际手数（如8手）
                limit_price=order_price
            )
            last_order_id = order_id
            
            # 【第4步】等待并监控订单状态
            start_time = time.time()
            
            while time.time() - start_time < retry_interval:
                # 驱动事件循环以同步订单状态
                api.wait_update(deadline=time.time() + 0.5)
                
                # 获取订单对象
                order = api.get_order(order_id)
                
                # 检查订单终态
                if order.status == 'FINISHED':
                    # 订单全部成交
                    filled_lots = order.volume_orign - order.volume_left  # 实际成交手数
                    avg_price = order.average_price
                    
                    # 【数据有效性验证】确保成交量和价格有效
                    if filled_lots <= 0 or avg_price is None:
                        return False
                    
                    # 计算成交的单位数（向下取整到Unit）
                    filled_units = filled_lots // unit_lots if unit_lots > 0 else 1
                    
                    with transaction.atomic():
                        # 记录开仓交易执行日志
                        TradeExecution.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            direction=order_direction,
                            volume=filled_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=order_id,
                            trade_type='ENTRY'
                        )
                        
                        # 创建持仓状态记录
                        PositionState.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',  # 提取品种代码
                            direction=signal.direction,
                            units=filled_units,  # ← 存储海龟单位数（如1）
                            contract_total_position=filled_lots,  # ← 存储总手数（如8）
                            last_add_price=avg_price,  # 初始化为开仓价
                            contract_price_avg=avg_price,  # ← 首次开仓，成本价 = 开仓价
                            highest_close=avg_price,  # 多头初始最高价
                            lowest_close=avg_price,  # 空头初始最低价
                            latest_close_price=avg_price,  # 初始化为开仓价
                        )
                    
                    return True
                elif order.status in ['CANCELLED', 'ERROR']:
                    # 订单被取消或出错
                    return False
                elif order.status == 'PARTIAL_FILLED':
                    # 部分成交，继续等待直到超时或全部成交
                    pass
            
            # 【第5步】处理超时未完全成交的情况
            order = api.get_order(order_id)
            
            if order.status == 'PARTIAL_FILLED':
                # 部分成交，撤销剩余部分
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                
                # 记录已成交部分
                filled_lots = order.volume_orign - order.volume_left
                if filled_lots > 0:
                    avg_price = order.average_price
                    
                    # 【数据有效性验证】确保价格有效
                    if avg_price is None:
                        return False
                    
                    # 计算成交的单位数
                    filled_units = filled_lots // unit_lots if unit_lots > 0 else 1
                    
                    with transaction.atomic():
                        TradeExecution.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            direction=order_direction,
                            volume=filled_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=order_id,
                            trade_type='ENTRY'
                        )
                        
                        # 创建持仓状态记录（按实际成交量）
                        PositionState.objects.create(
                            account=account,
                            symbol=signal.symbol,
                            product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                            direction=signal.direction,
                            units=filled_units,  # ← 存储单位数
                            contract_total_position=filled_lots,  # ← 存储总手数
                            last_add_price=avg_price,
                            highest_close=avg_price,
                            lowest_close=avg_price,
                            latest_close_price=avg_price,
                        )
                    
                    return True
                else:
                    # 未成交，准备重试
                    if attempt < max_retries:
                        last_order_id = None
                        continue
                    else:
                        return False
            else:
                # 未成交，撤单后重试
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                last_order_id = None
                
                if attempt >= max_retries:
                    return False
                    
        except Exception as e:
            # 异常处理：尝试撤销未完成的订单
            if last_order_id:
                try:
                    api.cancel_order(last_order_id)
                    api.wait_update(deadline=time.time() + 1)
                except:
                    pass
                finally:
                    last_order_id = None
            
            if attempt >= max_retries:
                return False
    
    return False


def execute_exit_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行平仓操作的函数（使用当前市价 + 重试机制，确保全部成交）
    :param api: TqApi实例
    :param position: PositionState实例
    :param signal: DailyStrategySignal实例
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行平仓操作（全部成交）
    """
    # 【计算需要平仓的总手数】从 contract_total_position 获取
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        return True
    
    order_direction = 'SELL' if position.direction == 1 else 'BUY'
    
    filled_total_lots = 0  # 累计已成交手数
    total_cost = Decimal('0')  # 累计成交金额（用于计算加权均价）
    last_order_id = None  # 记录最后一次发送的订单ID，用于异常清理
    successful_order_id = None  # 记录成功成交的订单ID
    
    for attempt in range(1, max_retries + 1):
        try:
            # 计算本次需要下单的手数（总量 - 已成交）
            remaining_volume = total_volume - filled_total_lots
            
            if remaining_volume <= 0:
                # 已全部成交，退出循环进行数据库记录
                break
            
            # 【第1步】获取最新行情并确定价格
            quote = api.get_quote(position.symbol)
            
            # 使用对手价：卖单用买一价，买单用卖一价
            if order_direction == 'SELL':
                order_price = quote.bid_price1 if quote.bid_price1 else quote.last_price
            else:  # BUY
                order_price = quote.ask_price1 if quote.ask_price1 else quote.last_price
            
            # 【行情可用性检查】如果价格为空，跳过本轮重试
            if order_price is None:
                if attempt < max_retries:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    return False
            
            # 【第2步】发送交易指令
            order_id = api.insert_order(
                symbol=position.symbol,
                direction=order_direction,
                offset='CLOSE',
                volume=remaining_volume,  # ← 剩余手数
                limit_price=order_price
            )
            last_order_id = order_id
            
            # 【第3步】等待并监控订单状态
            start_time = time.time()
            
            while time.time() - start_time < retry_interval:
                # 驱动事件循环以同步订单状态
                api.wait_update(deadline=time.time() + 0.5)
                
                # 获取订单对象
                order = api.get_order(order_id)
                
                # 检查订单终态
                if order.status == 'FINISHED':
                    successful_order_id = order_id  # 记录成功订单ID
                    break
                elif order.status in ['CANCELLED', 'ERROR']:
                    # 订单被取消或出错，直接返回失败
                    return False
                elif order.status == 'PARTIAL_FILLED':
                    # 部分成交，继续等待直到超时或全部成交
                    pass
            
            # 【第4步】根据最终状态处理
            order = api.get_order(order_id)
            
            if order.status == 'FINISHED':
                # 本笔订单全部成交，累加成交量和成本
                current_filled = order.volume_orign - order.volume_left
                actual_filled = min(current_filled, remaining_volume)
                
                # 【数据有效性验证】确保成交量和价格有效
                if actual_filled <= 0 or order.average_price is None:
                    return False
                
                filled_total_lots += actual_filled
                total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                
                # 检查是否全部完成
                if filled_total_lots >= total_volume:
                    # 计算加权平均价格
                    avg_price = total_cost / Decimal(str(filled_total_lots))
                    
                    with transaction.atomic():
                        TradeExecution.objects.create(
                            account=position.account,
                            symbol=position.symbol,
                            direction=-1 if position.direction == 1 else 1,  # 平仓方向与持仓相反
                            volume=filled_total_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=successful_order_id or order_id,
                            trade_type=signal.trade_type if signal else 'EXIT',
                            signal=signal
                        )
                        
                        # 【清空持仓状态】
                        PositionState.objects.filter(id=position.id).update(
                            units=0,  # ← 单位数归零
                            contract_total_position=0,  # ← 总手数归零
                            direction=0,
                            last_add_price=None,
                            highest_close=None,
                            lowest_close=None,
                            stop_loss_price=None
                        )
                    
                    return True
                else:
                    # FINISHED但累计量不足，说明有逻辑错误
                    return False
            
            elif order.status == 'PARTIAL_FILLED':
                # 部分成交且超时，累加成交量
                current_filled = order.volume_orign - order.volume_left
                actual_filled = min(current_filled, remaining_volume)
                
                # 【数据有效性验证】
                if actual_filled > 0 and order.average_price is not None:
                    filled_total_lots += actual_filled
                    total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                
                # 撤销剩余未成交部分，准备下一轮重试
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                last_order_id = None
                
                # 检查是否已累计全部成交
                if filled_total_lots >= total_volume:
                    avg_price = total_cost / Decimal(str(filled_total_lots))
                    
                    with transaction.atomic():
                        TradeExecution.objects.create(
                            account=position.account,
                            symbol=position.symbol,
                            direction=-1 if position.direction == 1 else 1,
                            volume=filled_total_lots,  # ← 存储实际手数
                            price=avg_price,
                            trade_time=timezone.now(),
                            order_id=order_id,
                            trade_type=signal.trade_type if signal else 'EXIT',
                            signal=signal
                        )
                        
                        # 【清空持仓状态】
                        PositionState.objects.filter(id=position.id).update(
                            units=0,
                            contract_total_position=0,
                            direction=0,
                            last_add_price=None,
                            highest_close=None,
                            lowest_close=None,
                            stop_loss_price=None
                        )
                    
                    return True
                else:
                    # 继续重试剩余量
                    if attempt >= max_retries:
                        return False
                    continue
            else:
                # 未成交（NEW/SUBMITTED等状态超时），撤单后重试
                api.cancel_order(order_id)
                api.wait_update(deadline=time.time() + 1)
                last_order_id = None
                
                if attempt >= max_retries:
                    return False
                    
        except Exception as e:
            # 异常处理：尝试撤销未完成的订单
            if last_order_id:
                try:
                    api.cancel_order(last_order_id)
                    api.wait_update(deadline=time.time() + 1)
                except:
                    pass
                finally:
                    last_order_id = None
            
            if attempt >= max_retries:
                return False
    
    return False


def execute_rollover_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行移仓操作的函数（使用对手价 + 重试机制）
    :param api: TqApi实例
    :param position: PositionState实例（旧合约持仓）
    :param signal: DailyStrategySignal实例（新合约信号）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行移仓操作
    """
    # 计算移仓数量
    total_volume = position.units * position.contracts_per_unit
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        return True
    
    # 确定交易方向
    exit_order_direction = 'SELL' if position.direction == 1 else 'BUY'  # 平仓方向
    entry_order_direction = 'BUY' if position.direction == 1 else 'SELL'  # 开仓方向（与平仓相反）
    
    exit_filled_volume = 0  # 平仓累计成交量
    entry_filled_volume = 0  # 开仓累计成交量
    exit_total_cost = Decimal('0')  # 平仓累计成交金额
    entry_total_cost = Decimal('0')  # 开仓累计成交金额
    
    last_exit_order_id = None  # 记录平仓订单ID
    last_entry_order_id = None  # 记录开仓订单ID
    exit_completed = False  # 标记平仓是否已完成
    
    # 创建移仓日志记录（初始状态为PENDING）
    rollover_log = RolloverLog.objects.create(
        account=position.account,
        old_symbol=position.symbol,
        new_symbol=signal.symbol,
        volume=total_volume,
        status='PENDING'
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            # ========== 第1阶段：平仓旧合约（仅当未完成时执行）==========
            if not exit_completed and exit_filled_volume < total_volume:
                exit_remaining_volume = total_volume - exit_filled_volume
                
                # 获取旧合约行情并使用对手价
                exit_quote = api.get_quote(position.symbol)
                if exit_order_direction == 'SELL':
                    exit_order_price = exit_quote.bid_price1 if exit_quote.bid_price1 else exit_quote.last_price
                else:  # BUY
                    exit_order_price = exit_quote.ask_price1 if exit_quote.ask_price1 else exit_quote.last_price
                
                # 行情可用性检查
                if exit_order_price is None:
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    else:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                
                # 发送平仓指令
                exit_order_id = api.insert_order(
                    symbol=position.symbol,
                    direction=exit_order_direction,
                    offset='CLOSE',
                    volume=exit_remaining_volume,
                    limit_price=exit_order_price
                )
                last_exit_order_id = exit_order_id
                
                # 监控平仓订单状态
                start_time = time.time()
                while time.time() - start_time < retry_interval:
                    api.wait_update(deadline=time.time() + 0.5)
                    order = api.get_order(exit_order_id)
                    
                    if order.status == 'FINISHED':
                        break
                    elif order.status in ['CANCELLED', 'ERROR']:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    elif order.status == 'PARTIAL_FILLED':
                        pass
                
                # 处理平仓订单结果
                order = api.get_order(exit_order_id)
                
                if order.status == 'FINISHED':
                    current_filled = order.volume_orign - order.volume_left
                    actual_filled = min(current_filled, exit_remaining_volume)
                    
                    # 【数据有效性验证】
                    if actual_filled <= 0 or order.average_price is None:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    
                    exit_filled_volume += actual_filled
                    exit_total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                    
                    # 检查是否全部完成
                    if exit_filled_volume >= total_volume:
                        exit_completed = True
                elif order.status == 'PARTIAL_FILLED':
                    current_filled = order.volume_orign - order.volume_left
                    actual_filled = min(current_filled, exit_remaining_volume)
                    
                    # 【数据有效性验证】
                    if actual_filled > 0 and order.average_price is not None:
                        exit_filled_volume += actual_filled
                        exit_total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                    
                    # 撤销剩余部分
                    api.cancel_order(exit_order_id)
                    api.wait_update(deadline=time.time() + 1)
                    last_exit_order_id = None
                    
                    if exit_filled_volume < total_volume:
                        if attempt < max_retries:
                            continue
                        else:
                            # 更新日志状态为失败
                            rollover_log.status = 'FAILED'
                            rollover_log.save(update_fields=['status', 'updated_at'])
                            return False
                    else:
                        exit_completed = True
                else:
                    # 未成交，撤单后重试
                    api.cancel_order(exit_order_id)
                    api.wait_update(deadline=time.time() + 1)
                    last_exit_order_id = None
                    
                    if attempt >= max_retries:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    continue
            
            # ========== 第2阶段：开仓新合约（仅当平仓完成后执行）==========
            if exit_completed and entry_filled_volume < total_volume:
                entry_remaining_volume = total_volume - entry_filled_volume
                
                # 获取新合约行情并使用对手价
                entry_quote = api.get_quote(signal.symbol)
                if entry_order_direction == 'BUY':
                    entry_order_price = entry_quote.ask_price1 if entry_quote.ask_price1 else entry_quote.last_price
                else:  # SELL
                    entry_order_price = entry_quote.bid_price1 if entry_quote.bid_price1 else entry_quote.last_price
                
                # 行情可用性检查
                if entry_order_price is None:
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    else:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                
                # 发送开仓指令
                entry_order_id = api.insert_order(
                    symbol=signal.symbol,
                    direction=entry_order_direction,
                    offset='OPEN',
                    volume=entry_remaining_volume,
                    limit_price=entry_order_price
                )
                last_entry_order_id = entry_order_id
                
                # 监控开仓订单状态
                start_time = time.time()
                while time.time() - start_time < retry_interval:
                    api.wait_update(deadline=time.time() + 0.5)
                    order = api.get_order(entry_order_id)
                    
                    if order.status == 'FINISHED':
                        break
                    elif order.status in ['CANCELLED', 'ERROR']:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    elif order.status == 'PARTIAL_FILLED':
                        pass
                
                # 处理开仓订单结果
                order = api.get_order(entry_order_id)
                
                if order.status == 'FINISHED':
                    current_filled = order.volume_orign - order.volume_left
                    actual_filled = min(current_filled, entry_remaining_volume)
                    
                    # 【数据有效性验证】
                    if actual_filled <= 0 or order.average_price is None:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    
                    entry_filled_volume += actual_filled
                    entry_total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                elif order.status == 'PARTIAL_FILLED':
                    current_filled = order.volume_orign - order.volume_left
                    actual_filled = min(current_filled, entry_remaining_volume)
                    
                    # 【数据有效性验证】
                    if actual_filled > 0 and order.average_price is not None:
                        entry_filled_volume += actual_filled
                        entry_total_cost += Decimal(str(order.average_price)) * Decimal(str(actual_filled))
                    
                    # 撤销剩余部分
                    api.cancel_order(entry_order_id)
                    api.wait_update(deadline=time.time() + 1)
                    last_entry_order_id = None
                    
                    if entry_filled_volume < total_volume:
                        if attempt < max_retries:
                            continue
                        else:
                            # 更新日志状态为失败
                            rollover_log.status = 'FAILED'
                            rollover_log.save(update_fields=['status', 'updated_at'])
                            return False
                else:
                    # 未成交，撤单后重试
                    api.cancel_order(entry_order_id)
                    api.wait_update(deadline=time.time() + 1)
                    last_entry_order_id = None
                    
                    if attempt >= max_retries:
                        # 更新日志状态为失败
                        rollover_log.status = 'FAILED'
                        rollover_log.save(update_fields=['status', 'updated_at'])
                        return False
                    continue
            
            # ========== 检查是否全部完成 ==========
            if exit_completed and entry_filled_volume >= total_volume:
                # 计算加权平均价格
                exit_avg_price = exit_total_cost / Decimal(str(exit_filled_volume))
                entry_avg_price = entry_total_cost / Decimal(str(entry_filled_volume))
                
                with transaction.atomic():
                    # 记录平仓交易执行日志
                    TradeExecution.objects.create(
                        account=position.account,
                        symbol=position.symbol,
                        direction=exit_order_direction,
                        volume=exit_filled_volume,
                        price=exit_avg_price,
                        trade_time=timezone.now(),
                        order_id=last_exit_order_id,
                        trade_type='ROLLOVER_EXIT'
                    )
                    
                    # 记录开仓交易执行日志
                    TradeExecution.objects.create(
                        account=position.account,
                        symbol=signal.symbol,
                        direction=entry_order_direction,
                        volume=entry_filled_volume,
                        price=entry_avg_price,
                        trade_time=timezone.now(),
                        order_id=last_entry_order_id,
                        trade_type='ROLLOVER_ENTRY'
                    )
                    
                    # 【关键】计算移仓盈亏
                    rollover_pnl = (exit_avg_price - position.contract_price_avg) * Decimal(str(exit_filled_volume))
                    if position.direction == -1:  # 空头持仓，盈亏反向
                        rollover_pnl = -rollover_pnl
                    
                    # 更新旧持仓状态为已平仓（清空所有字段）
                    PositionState.objects.filter(id=position.id).update(
                        units=0,
                        contract_total_position=0,
                        direction=0,
                        last_add_price=None,
                        contract_price_avg=None,  # ← 清空成本价
                        highest_close=None,
                        lowest_close=None,
                        stop_loss_price=None,
                        latest_close_price=None,
                        is_rollover_needed=False
                    )
                    
                    # 获取新合约的合约乘数
                    try:
                        contract = api.get_instrument(signal.symbol)
                        contracts_per_unit = contract.volume_multiple if contract and contract.volume_multiple else 1
                    except:
                        contracts_per_unit = 1
                    
                    # 计算新持仓的单位数
                    entry_units = entry_filled_volume // contracts_per_unit
                    
                    # 创建新持仓状态记录
                    PositionState.objects.create(
                        account=position.account,
                        symbol=signal.symbol,
                        product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                        direction=position.direction,
                        units=entry_units,  # ← 存储海龟单位数
                        contract_total_position=entry_filled_volume,  # ← 存储实际手数
                        last_add_price=entry_avg_price,
                        contract_price_avg=entry_avg_price,  # ← 新合约成本价 = 开仓价
                        highest_close=entry_avg_price,
                        lowest_close=entry_avg_price,
                        latest_close_price=entry_avg_price,
                        is_rollover_needed=False
                    )
                    
                    # 记录移仓日志
                    RolloverLog.objects.create(
                        account=position.account,
                        old_symbol=position.symbol,
                        new_symbol=signal.symbol,
                        old_units=position.units,
                        new_units=entry_units,
                        old_avg_price=position.contract_price_avg,
                        exit_price=exit_avg_price,
                        entry_price=entry_avg_price,
                        rollover_pnl=rollover_pnl,
                        rollover_time=timezone.now(),
                        status='COMPLETED',
                        remark=f"移仓完成: {position.symbol} → {signal.symbol}, 盈亏={float(rollover_pnl):.2f}元"
                    )
                
                return True
            else:
                # 未完成，继续重试
                if attempt < max_retries:
                    continue
                else:
                    # 更新日志状态为失败
                    rollover_log.status = 'FAILED'
                    rollover_log.save(update_fields=['status', 'updated_at'])
                    return False
                    
        except Exception as e:
            # 异常处理：尝试撤销未完成的订单
            if last_exit_order_id:
                try:
                    api.cancel_order(last_exit_order_id)
                    api.wait_update(deadline=time.time() + 1)
                except:
                    pass
                finally:
                    last_exit_order_id = None
            
            if last_entry_order_id:
                try:
                    api.cancel_order(last_entry_order_id)
                    api.wait_update(deadline=time.time() + 1)
                except:
                    pass
                finally:
                    last_entry_order_id = None
            
            # 更新日志状态为失败
            try:
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
            except:
                pass
            
            if attempt >= max_retries:
                return False
    
    return False


def process_exit_signals(api, account, current_date):
    """
    处理平仓信号的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return:
    """
    # 查询所有持仓状态为持仓中的记录（units > 0 表示有持仓）
    open_positions = PositionState.objects.filter(account=account, units__gt=0)
    
    for position in open_positions:
        # 检查是否存在平仓信号
        exit_signals = DailyStrategySignal.objects.filter(
            Q(symbol=position.symbol) & 
            Q(trade_type='STOP_LOSS')        
        )
        for signal in exit_signals:
            # 执行平仓操作
            success = execute_exit_order(api, position, signal)
            if success:
                # 删除平仓信号
                signal.delete()
                print(f"✅ 平仓成功: {position.symbol}")
            else:
                print(f"❌ 平仓失败: {position.symbol}")    
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
        Q(trade_type='ENTRY')     )
    
    for signal in entry_signals:
        # 执行开仓操作
        success = execute_entry_order(api, account, signal) 
        if success:
            # 删除开仓信号
            signal.delete()
            print(f"✅ 开仓成功: {signal.symbol}")
        else:
            print(f"❌ 开仓失败: {signal.symbol}")
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
        Q(trade_type='ROLLOVER') 
    )
    
    for signal in rollover_signals:
        # 【修复】查找对应的持仓记录
        try:
            position = PositionState.objects.get(account=account, symbol=signal.symbol, units__gt=0)
            # 执行移仓操作
            success = execute_rollover_order(api, position, signal)
            if success:
                # 删除移仓信号
                signal.delete()
                print(f"✅ 移仓成功: {position.symbol} -> {signal.symbol}")
            else:
                print(f"❌ 移仓失败: {position.symbol} -> {signal.symbol}")
        except PositionState.DoesNotExist:
            print(f"⚠️ 移仓信号未找到对应持仓: {signal.symbol}")
def process_addon_signals(api, account, current_date):
    """
    处理加仓信号的函数
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return:
    """
    # 查询所有加仓信号
    addon_signals = DailyStrategySignal.objects.filter(
        Q(trade_type='ADDON'))
    
    for signal in addon_signals:
        # 执行加仓操作
        success = execute_addon_order(api, account, signal)
        if success:
            # 删除加仓信号
            signal.delete()
            print(f"✅ 加仓成功: {signal.symbol}")
        else:
            print(f"❌ 加仓失败: {signal.symbol}")


def send_report(account, current_date):
    """
    发送今日交易执行情况报告（加仓、移仓、平仓）
    
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return: 是否发送成功
    """
    from stock.utils.send_mail import send_email
    from django.template.loader import render_to_string
    from django.utils import timezone
    
    try:
        # 查询今天的交易执行记录
        today_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
        
        today_trades = TradeExecution.objects.filter(
            account=account,
            trade_time__gte=today_start,
            trade_time__lte=today_end
        ).order_by('trade_time')
        
        # 分类统计
        addon_trades = today_trades.filter(trade_type='ADD_ON')
        rollover_exit_trades = today_trades.filter(trade_type='ROLLOVER_EXIT')
        rollover_entry_trades = today_trades.filter(trade_type='ROLLOVER_ENTRY')
        stop_loss_trades = today_trades.filter(trade_type='STOP_LOSS')
        close_signal_trades = today_trades.filter(trade_type='CLOSE_SIGNAL')
        
        # 计算统计数据
        total_trades = (len(addon_trades) + len(rollover_exit_trades) + 
                       len(rollover_entry_trades) + len(stop_loss_trades) + 
                       len(close_signal_trades))
        
        # 使用Django Template渲染HTML
        context = {
            'current_date': current_date,
            'total_trades': total_trades,
            'addon_count': len(addon_trades),
            'rollover_count': len(rollover_exit_trades),
            'stop_loss_count': len(stop_loss_trades),
            'close_signal_count': len(close_signal_trades),
            'addon_trades': addon_trades,
            'rollover_exit_trades': rollover_exit_trades,
            'rollover_entry_trades': rollover_entry_trades,
            'stop_loss_trades': stop_loss_trades,
            'close_signal_trades': close_signal_trades,
        }
        
        html_content = render_to_string('trade_execution_report.html', context)
        
        # 发送邮件
        subject = f"【量化交易日报】{current_date} 交易执行情况"
        receiver_email = os.getenv('EMAIL_RECEIVER', '312711936@qq.com')
        
        # 异步发送邮件
        send_email(
            subject=subject,
            body=html_content,
            receiver_email=receiver_email,
            is_html=True
        )
        
        print(f"[INFO] 交易报告已发送至: {receiver_email}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 发送交易报告失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def job_daily_open_process():
    """
    每日开盘处理函数
    """
    from datetime import datetime

    # 获取当前日期
    current_date = datetime.now().date()

    # 获取交易账户
    accounts = TradingAccount.objects.all()

    for account in accounts:
        # 初始化TqApi
        api = TqApi(TqAuth('yupei1986', 'yupei1986'))

        try:
            # 处理平仓信号
            process_exit_signals(api, account, current_date)

            # 处理开仓信号
            process_entry_signals(api, account, current_date)

            # 处理移仓信号
            process_rollover_signals(api, account, current_date)

            # 处理加仓信号
            process_addon_signals(api, account, current_date)

            # 发送交易执行情况报告
            send_report(account, current_date)

        except Exception as e:
            print(f"[ERROR] 处理账户 {account.username} 时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # 关闭TqApi连接
            api.close()
