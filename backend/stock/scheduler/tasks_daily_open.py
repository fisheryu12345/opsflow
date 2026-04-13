import os
import time
from decimal import Decimal
from tqsdk import TqApi, TqAuth, TargetPosTask
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
    执行加仓操作的函数（使用TargetPosTask简化订单管理）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例（trade_type='ADD_ON'）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行加仓操作
    """
    # 【验证信号类型】
    if signal.trade_type != 'ADD_ON':
        print(f"[WARN] 信号类型错误: {signal.trade_type}，期望ADD_ON")
        return False
    
    # 【优化】直接从 signal.contract_target_number 获取加仓单位数
    add_units_from_signal = signal.contract_target_number
    
    if not add_units_from_signal or add_units_from_signal <= 0:
        print(f"[ERROR] 信号中未设置有效的加仓单位数: contract_target_number={add_units_from_signal}")
        return False
    
    print(f"[INFO] {signal.symbol} 从信号获取加仓单位数: {add_units_from_signal}Unit")
    
    # 【修复P0】使用数据库事务和行级锁防止并发
    with transaction.atomic():
        # 获取当前持仓状态（加锁）
        position = PositionState.objects.select_for_update().filter(
            account=account,
            symbol=signal.symbol,
            units__gt=0
        ).first()
        
        if not position:
            print(f"[WARN] {signal.symbol} 无持仓，无法加仓")
            return False
        
        # 【修复P0】在下单前检查是否会超过最大持仓限制
        projected_units = position.units + add_units_from_signal
        if projected_units > POSITION_MAX_UNITS:
            print(f"[WARN] {signal.symbol} 加仓后将超限: 当前{position.units}Unit + 加仓{add_units_from_signal}Unit = {projected_units}Unit > 最大{POSITION_MAX_UNITS}Unit")
            return False
    
    # 【修复】使用 calculate_unit_lots 计算1个Unit对应的实际手数
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    # 计算实际下单手数 = 加仓单位数 × 1个Unit的手数
    order_volume = add_units_from_signal * unit_lots
    
    print(f"[INFO] {signal.symbol} 加仓计划: {add_units_from_signal}Unit × {unit_lots}手/Unit = {order_volume}手")
    
    # 【修复P0】记录加仓前的持仓状态（用于增量计算）
    pos_before = api.get_position(signal.symbol)
    initial_volume_long = pos_before.volume_long if pos_before else 0
    initial_volume_short = pos_before.volume_short if pos_before else 0
    initial_cost_long = Decimal(str(pos_before.open_cost_long)) if pos_before else Decimal('0')
    initial_cost_short = Decimal(str(pos_before.open_cost_short)) if pos_before else Decimal('0')
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, signal.symbol)
    
    # 计算目标持仓量（考虑方向）
    current_position = position.contract_total_position
    if position.direction == 1:  # 多头
        target_volume = current_position + order_volume
    else:  # 空头
        target_volume = -(current_position + order_volume)
    
    try:
        # 设置目标持仓量（TqSDK会自动处理下单、撤单、部分成交等）
        target_pos.set_target_volume(target_volume)
        
        # 【修复P1】优化等待逻辑，增加进度监控和超时控制
        timeout_seconds = 30  # 加仓超时30秒
        start_time = time.time()
        last_logged_volume = -1
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 0.5)
            
            pos_obj = api.get_position(signal.symbol)
            if pos_obj is None:
                continue
            
            current_volume = pos_obj.volume_long if position.direction == 1 else pos_obj.volume_short
            actual_added = current_volume - current_position
            
            # 只在成交量变化时打印日志
            if actual_added != last_logged_volume:
                print(f"   [INFO] {signal.symbol} 加仓进度: {actual_added}/{order_volume}手")
                last_logged_volume = actual_added
            
            # 达到目标成交量
            if actual_added >= order_volume:
                print(f"   [SUCCESS] {signal.symbol} 加仓完成: {actual_added}手")
                break
            
            # 检查是否长时间无进展（流动性问题）
            if time.time() - start_time > timeout_seconds / 2 and actual_added == 0:
                print(f"[WARN] {signal.symbol} 加仓{int(timeout_seconds/2)}秒仍无成交，可能存在流动性问题")
        
        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)
        if pos_after is None:
            print(f"[ERROR] {signal.symbol} 无法获取持仓信息")
            return False
        
        # 【修复P0】使用增量计算法计算本次加仓的实际成交量和均价
        if position.direction == 1:
            filled_lots = pos_after.volume_long - initial_volume_long
            if filled_lots <= 0:
                print(f"[ERROR] {signal.symbol} 多头持仓未增加")
                return False
            
            # 计算本次加仓的均价 = (新累计成本 - 旧累计成本) / 新增持仓量
            current_cost = Decimal(str(pos_after.open_cost_long))
            added_cost = current_cost - initial_cost_long
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        else:
            filled_lots = pos_after.volume_short - initial_volume_short
            if filled_lots <= 0:
                print(f"[ERROR] {signal.symbol} 空头持仓未增加")
                return False
            
            current_cost = Decimal(str(pos_after.open_cost_short))
            added_cost = current_cost - initial_cost_short
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        
        # 数据有效性验证
        if avg_price is None or avg_price <= 0:
            print(f"[ERROR] {signal.symbol} 无法计算有效成交均价: avg_price={avg_price}")
            return False
        
        # 检查是否部分成交
        if filled_lots < order_volume:
            print(f"[WARN] {signal.symbol} 部分成交: {filled_lots}/{order_volume}手，继续执行")
            # 重新计算实际加仓的单位数（使用unit_lots）
            add_units_from_signal = filled_lots // unit_lots
            if add_units_from_signal == 0:
                print(f"[ERROR] {signal.symbol} 成交手数不足以构成1个Unit")
                return False
        
        # 计算加仓的单位数（向下取整，使用unit_lots）
        added_units = filled_lots // unit_lots
        
        if added_units == 0:
            print(f"[ERROR] {signal.symbol} 加仓单位数为0")
            return False
        
        with transaction.atomic():
            # 【修复P0】再次检查最大持仓限制（双重保险）
            position = PositionState.objects.select_for_update().get(id=position.id)
            new_units = position.units + added_units
            if new_units > POSITION_MAX_UNITS:
                print(f"[ERROR] {signal.symbol} 加仓后超限（并发保护）: {new_units}Unit > {POSITION_MAX_UNITS}Unit")
                return False
            
            new_total_lots = position.contract_total_position + filled_lots
            
            # 记录加仓交易执行日志
            TradeExecution.objects.create(
                account=account,
                symbol=signal.symbol,
                direction='BUY' if position.direction == 1 else 'SELL',
                volume=filled_lots,
                price=Decimal(str(avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type='ADD_ON',
                signal=signal
            )
            
            # 【核心计算】加权平均成本价
            old_total_cost = Decimal(str(position.contract_total_position)) * position.contract_price_avg
            new_add_cost = Decimal(str(avg_price)) * Decimal(str(filled_lots))
            combined_total_cost = old_total_cost + new_add_cost
            
            new_avg_price = combined_total_cost / Decimal(str(new_total_lots))
            
            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                last_add_price=Decimal(str(avg_price)),
                contract_price_avg=new_avg_price,
                latest_close_price=Decimal(str(avg_price))
            )
        
        print(f"[SUCCESS] {signal.symbol} 加仓成功: +{added_units}Unit({filled_lots}手) @ {avg_price:.2f}, 总持仓:{new_units}Unit")
        return True
        
    except Exception as e:
        print(f"[ERROR] 加仓失败 {signal.symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_entry_order(api, account, signal, max_retries=5, retry_interval=10, gap_threshold_percent=1.5):
    """
    执行开仓操作的函数（使用TargetPosTask简化订单管理）
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
    order_volume = target_units * unit_lots
    
    # 【修复P0】使用数据库事务和行级锁防止并发
    with transaction.atomic():
        # 【修复P1】检查是否已存在同合约、同方向的持仓
        existing_position = PositionState.objects.select_for_update().filter(
            account=account,
            symbol=signal.symbol,
            direction=signal.direction,
            units__gt=0
        ).first()
        
        if existing_position:
            print(f"[WARN] {signal.symbol} 已存在{['', '多头', '空头'][signal.direction]}持仓，跳过开仓")
            return False
        
        # 【修复P1】检查是否有反向持仓（避免同时对冲）
        # opposite_position = PositionState.objects.select_for_update().filter(
        #     account=account,
        #     symbol=signal.symbol,
        #     direction=-signal.direction,
        #     units__gt=0
        # ).first()
        
        # if opposite_position:
        #     print(f"[WARN] {signal.symbol} 存在反向持仓，需先平仓后再开仓")
        #     return False
    
    # 【跳空保护检查】
    can_trade = price_gap_proection(api, signal.symbol, signal.direction, gap_threshold_percent)
    if not can_trade:
        print(f"[WARN] {signal.symbol} 跳空幅度过大，禁止开仓")
        return False
    
    # 【修复P0】记录开仓前的持仓状态（用于增量计算）
    pos_before = api.get_position(signal.symbol)
    initial_volume_long = pos_before.volume_long if pos_before else 0
    initial_volume_short = pos_before.volume_short if pos_before else 0
    initial_cost_long = Decimal(str(pos_before.open_cost_long)) if pos_before else Decimal('0')
    initial_cost_short = Decimal(str(pos_before.open_cost_short)) if pos_before else Decimal('0')
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, signal.symbol)
    
    # 设置目标持仓量（考虑方向）
    target_volume = order_volume if signal.direction == 1 else -order_volume
    
    try:
        # 设置目标持仓量
        target_pos.set_target_volume(target_volume)
        
        # 【修复P1】优化等待逻辑，增加进度监控和超时控制
        timeout_seconds = 30  # 开仓超时30秒
        start_time = time.time()
        last_logged_volume = -1
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 0.5)
            
            pos_obj = api.get_position(signal.symbol)
            if pos_obj is None:
                continue
            
            current_volume = pos_obj.volume_long if signal.direction == 1 else pos_obj.volume_short
            
            # 只在成交量变化时打印日志
            if current_volume != last_logged_volume:
                print(f"   [INFO] {signal.symbol} 开仓进度: {current_volume}/{order_volume}手")
                last_logged_volume = current_volume
            
            # 达到目标成交量
            if current_volume >= order_volume:
                print(f"   [SUCCESS] {signal.symbol} 开仓完成: {current_volume}手")
                break
            
            # 检查是否长时间无进展（流动性问题）
            if time.time() - start_time > timeout_seconds / 2 and current_volume == 0:
                print(f"[WARN] {signal.symbol} 开仓{int(timeout_seconds/2)}秒仍无成交，可能存在流动性问题")
        
        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)
        if pos_after is None:
            print(f"[ERROR] {signal.symbol} 无法获取持仓信息")
            return False
        
        # 【修复P0】使用增量计算法计算本次开仓的实际成交量和均价
        if signal.direction == 1:
            filled_lots = pos_after.volume_long - initial_volume_long
            if filled_lots <= 0:
                print(f"[ERROR] {signal.symbol} 多头持仓未增加")
                return False
            
            # 计算本次开仓的均价 = (新累计成本 - 旧累计成本) / 新增持仓量
            current_cost = Decimal(str(pos_after.open_cost_long))
            added_cost = current_cost - initial_cost_long
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        else:
            filled_lots = pos_after.volume_short - initial_volume_short
            if filled_lots <= 0:
                print(f"[ERROR] {signal.symbol} 空头持仓未增加")
                return False
            
            current_cost = Decimal(str(pos_after.open_cost_short))
            added_cost = current_cost - initial_cost_short
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        
        # 数据有效性验证
        if avg_price is None or avg_price <= 0:
            print(f"[ERROR] {signal.symbol} 无法计算有效成交均价: avg_price={avg_price}")
            return False
        
        # 检查是否部分成交
        if filled_lots < order_volume:
            print(f"[WARN] {signal.symbol} 部分成交: {filled_lots}/{order_volume}手，继续执行")
            # 更新实际成交的单位数
            order_volume = filled_lots
        
        # 计算成交的单位数（向下取整）
        filled_units = filled_lots // unit_lots if unit_lots > 0 else 1
        
        if filled_units == 0:
            print(f"[ERROR] {signal.symbol} 成交手数不足以构成1个Unit")
            return False
        
        with transaction.atomic():
            # 记录开仓交易执行日志
            TradeExecution.objects.create(
                account=account,
                symbol=signal.symbol,
                direction='BUY' if signal.direction == 1 else 'SELL',
                volume=filled_lots,
                price=Decimal(str(avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type='ENTRY'
            )
            
            # 创建持仓状态记录
            PositionState.objects.create(
                account=account,
                symbol=signal.symbol,
                product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                direction=signal.direction,
                units=filled_units,
                contract_total_position=filled_lots,
                last_add_price=Decimal(str(avg_price)),
                contract_price_avg=Decimal(str(avg_price)),
                highest_close=Decimal(str(avg_price)),
                lowest_close=Decimal(str(avg_price)),
                latest_close_price=Decimal(str(avg_price)),
            )
        
        print(f"[SUCCESS] {signal.symbol} 开仓成功: {filled_units}Unit({filled_lots}手) @ {avg_price:.2f}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_exit_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行平仓操作的函数（使用TargetPosTask简化订单管理）
    :param api: TqApi实例
    :param position: PositionState实例
    :param signal: DailyStrategySignal实例
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行平仓操作
    """
    # 获取需要平仓的总手数
    total_volume = position.contract_total_position
    
    # 边界检查
    if total_volume <= 0:
        return True
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, position.symbol)
    
    try:
        # 设置目标持仓为0（全部平仓）
        target_pos.set_target_volume(0)
        
        # 等待成交完成
        start_time = time.time()
        while time.time() - start_time < retry_interval * max_retries:
            api.wait_update(deadline=time.time() + 0.5)
            
            # 检查是否已平仓
            pos_obj = api.get_position(position.symbol)
            if pos_obj is not None:
                if pos_obj.volume_long == 0 and pos_obj.volume_short == 0:
                    break
        
        # 获取最终成交结果
        pos_obj = api.get_position(position.symbol)
        if pos_obj is None:
            return False
        
        # 计算平仓均价（需要从历史成交记录估算）
        # 由于TargetPosTask不直接提供平仓均价，这里使用当前市价作为近似
        quote = api.get_quote(position.symbol)
        avg_price = quote.last_price
        
        if avg_price is None:
            return False
        
        with transaction.atomic():
            TradeExecution.objects.create(
                account=position.account,
                symbol=position.symbol,
                direction='SELL' if position.direction == 1 else 'BUY',
                volume=total_volume,
                price=Decimal(str(avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type=signal.trade_type if signal else 'EXIT',
                signal=signal
            )
            
            # 清空持仓状态
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
        
    except Exception as e:
        print(f"[ERROR] 平仓失败 {position.symbol}: {str(e)}")
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_rollover_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行移仓操作的函数（使用TargetPosTask简化订单管理）
    :param api: TqApi实例
    :param position: PositionState实例（旧合约持仓）
    :param signal: DailyStrategySignal实例（新合约信号）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行移仓操作
    """
    # 计算移仓数量
    total_volume = position.contract_total_position
    
    # 边界检查
    if total_volume <= 0:
        return True
    
    # 创建移仓日志记录
    rollover_log = RolloverLog.objects.create(
        account=position.account,
        old_symbol=position.symbol,
        new_symbol=signal.symbol,
        volume=total_volume,
        status='PENDING'
    )
    
    exit_avg_price = None
    entry_avg_price = None
    
    try:
        # ========== 第1阶段：平仓旧合约 ==========
        target_pos_old = TargetPosTask(api, position.symbol)
        
        try:
            # 设置目标持仓为0（全部平仓）
            target_pos_old.set_target_volume(0)
            
            # 等待成交完成
            start_time = time.time()
            while time.time() - start_time < retry_interval * max_retries:
                api.wait_update(deadline=time.time() + 0.5)
                
                pos_obj = api.get_position(position.symbol)
                if pos_obj is not None:
                    if pos_obj.volume_long == 0 and pos_obj.volume_short == 0:
                        break
            
            # 获取平仓均价
            quote = api.get_quote(position.symbol)
            exit_avg_price = quote.last_price
            
            if exit_avg_price is None:
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                return False
                
        finally:
            try:
                del target_pos_old
            except:
                pass
        
        # ========== 第2阶段：开仓新合约 ==========
        target_pos_new = TargetPosTask(api, signal.symbol)
        
        try:
            # 设置目标持仓量（考虑方向）
            target_volume = total_volume if position.direction == 1 else -total_volume
            target_pos_new.set_target_volume(target_volume)
            
            # 等待成交完成
            start_time = time.time()
            while time.time() - start_time < retry_interval * max_retries:
                api.wait_update(deadline=time.time() + 0.5)
                
                pos_obj = api.get_position(signal.symbol)
                if pos_obj is not None:
                    if position.direction == 1:
                        if pos_obj.volume_long >= total_volume:
                            break
                    else:
                        if pos_obj.volume_short >= total_volume:
                            break
            
            # 获取开仓均价
            pos_obj = api.get_position(signal.symbol)
            if pos_obj is None:
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                return False
            
            if position.direction == 1:
                entry_avg_price = pos_obj.open_cost_long / pos_obj.volume_long if pos_obj.volume_long > 0 else None
            else:
                entry_avg_price = pos_obj.open_cost_short / pos_obj.volume_short if pos_obj.volume_short > 0 else None
            
            if entry_avg_price is None:
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                return False
                
        finally:
            try:
                del target_pos_new
            except:
                pass
        
        # ========== 更新数据库 ==========
        with transaction.atomic():
            # 记录平仓交易执行日志
            TradeExecution.objects.create(
                account=position.account,
                symbol=position.symbol,
                direction='SELL' if position.direction == 1 else 'BUY',
                volume=total_volume,
                price=Decimal(str(exit_avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type='ROLLOVER_EXIT'
            )
            
            # 记录开仓交易执行日志
            TradeExecution.objects.create(
                account=position.account,
                symbol=signal.symbol,
                direction='BUY' if position.direction == 1 else 'SELL',
                volume=total_volume,
                price=Decimal(str(entry_avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type='ROLLOVER_ENTRY'
            )
            
            # 计算移仓盈亏
            rollover_pnl = (Decimal(str(exit_avg_price)) - position.contract_price_avg) * Decimal(str(total_volume))
            if position.direction == -1:
                rollover_pnl = -rollover_pnl
            
            # 获取新合约的合约乘数
            try:
                contract = api.get_instrument(signal.symbol)
                contracts_per_unit = contract.volume_multiple if contract and contract.volume_multiple else 1
            except:
                contracts_per_unit = 1
            
            # 计算新持仓的单位数
            entry_units = total_volume // contracts_per_unit
            
            # 更新旧持仓状态为已平仓
            PositionState.objects.filter(id=position.id).update(
                units=0,
                contract_total_position=0,
                direction=0,
                last_add_price=None,
                contract_price_avg=None,
                highest_close=None,
                lowest_close=None,
                stop_loss_price=None,
                latest_close_price=None,
                is_rollover_needed=False
            )
            
            # 创建新持仓状态记录
            PositionState.objects.create(
                account=position.account,
                symbol=signal.symbol,
                product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                direction=position.direction,
                units=entry_units,
                contract_total_position=total_volume,
                last_add_price=Decimal(str(entry_avg_price)),
                contract_price_avg=Decimal(str(entry_avg_price)),
                highest_close=Decimal(str(entry_avg_price)),
                lowest_close=Decimal(str(entry_avg_price)),
                latest_close_price=Decimal(str(entry_avg_price)),
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
                exit_price=Decimal(str(exit_avg_price)),
                entry_price=Decimal(str(entry_avg_price)),
                rollover_pnl=rollover_pnl,
                rollover_time=timezone.now(),
                status='COMPLETED',
                remark=f"移仓完成: {position.symbol} → {signal.symbol}, 盈亏={float(rollover_pnl):.2f}元"
            )
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 移仓失败 {position.symbol} -> {signal.symbol}: {str(e)}")
        try:
            rollover_log.status = 'FAILED'
            rollover_log.save(update_fields=['status', 'updated_at'])
        except:
            pass