import os
import time
from decimal import Decimal
from tqsdk import TqApi, TqAuth, TargetPosTask
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, TradeExecution, RolloverLog, DailyStrategySignal

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
    执行加仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例（trade_type='ADD_ON'）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行加仓操作
    """
    # 【新增】过滤已执行的信号，只处理PENDING状态的信号
    if signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        return False
    
    # 【验证信号类型】
    if signal.trade_type != 'ADD_ON':
        msg = f"[WARN] {signal.symbol} 信号类型错误: {signal.trade_type}，期望ADD_ON"
        print(msg)
        # 更新信号状态为取消（非预期类型）
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    
    # 【优化】直接从 signal.contract_target_number 获取加仓单位数
    add_units_from_signal = signal.contract_target_number
    
    if not add_units_from_signal or add_units_from_signal <= 0:
        msg = f"[ERROR] {signal.symbol} 信号中未设置有效的加仓单位数: contract_target_number={add_units_from_signal}"
        print(msg)
        # 更新信号状态为失败（数据无效）
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
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
            msg = f"[WARN] {signal.symbol} 无持仓，无法加仓"
            print(msg)
            # 更新信号状态为取消（无条件执行）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【修复P0】在下单前检查是否会超过最大持仓限制
        projected_units = position.units + add_units_from_signal
        if projected_units > POSITION_MAX_UNITS:
            msg = f"[WARN] {signal.symbol} 加仓后将超限: 当前{position.units}Unit + 加仓{add_units_from_signal}Unit = {projected_units}Unit > 最大{POSITION_MAX_UNITS}Unit"
            print(msg)
            # 更新信号状态为取消（超出限制）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
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
    
    try:
        # 计算目标持仓量 = 当前持仓 + 加仓手数
        current_position = api.get_position(signal.symbol)
        if position.direction == 1:
            current_lots = current_position.volume_long if current_position else 0
            target_lots = current_lots + order_volume
        else:
            current_lots = current_position.volume_short if current_position else 0
            target_lots = current_lots + order_volume
        
        print(f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (当前{current_lots}手 + 加仓{order_volume}手)")
        
        # 设置目标持仓（TargetPosTask会自动处理下单、撤单、重试）
        target_pos.set_target_volume(target_lots)
        
        # 等待成交（带超时控制）
        timeout_seconds = 120  # 60秒超时
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            
            # 获取最新持仓
            pos_after = api.get_position(signal.symbol)
            if pos_after is None:
                continue
            
            # 检查是否达到目标
            if position.direction == 1:
                actual_added = pos_after.volume_long - initial_volume_long
            else:
                actual_added = pos_after.volume_short - initial_volume_short
            
            if actual_added >= order_volume:
                print(f"[SUCCESS] {signal.symbol} 加仓完成: {actual_added}手")
                break
            
            # 检查是否长时间无进展（流动性问题）
            if time.time() - start_time > timeout_seconds / 2 and actual_added == 0:
                print(f"[WARN] {signal.symbol} 加仓{int(timeout_seconds/2)}秒仍无成交，可能存在流动性问题")
        
        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)
        if pos_after is None:
            msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【修复P0】使用增量计算法计算本次加仓的实际成交量和均价
        if position.direction == 1:
            filled_lots = pos_after.volume_long - initial_volume_long
            if filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 多头持仓未增加"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            # 计算本次加仓的均价 = (新累计成本 - 旧累计成本) / 新增持仓量
            current_cost = Decimal(str(pos_after.open_cost_long))
            added_cost = current_cost - initial_cost_long
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        else:
            filled_lots = pos_after.volume_short - initial_volume_short
            if filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 空头持仓未增加"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after.open_cost_short))
            added_cost = current_cost - initial_cost_short
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        
        # 数据有效性验证
        if avg_price is None or avg_price <= 0:
            msg = f"[ERROR] {signal.symbol} 无法计算有效成交均价: avg_price={avg_price}"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 检查是否部分成交
        if filled_lots < order_volume:
            print(f"[WARN] {signal.symbol} 部分成交: {filled_lots}/{order_volume}手，继续执行")
            # 重新计算实际加仓的单位数（使用unit_lots）
            add_units_from_signal = filled_lots // unit_lots
            if add_units_from_signal == 0:
                msg = f"[ERROR] {signal.symbol} 成交手数不足以构成1个Unit"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
        
        # 计算加仓的单位数（向下取整，使用unit_lots）
        added_units = filled_lots // unit_lots
        
        if added_units == 0:
            msg = f"[ERROR] {signal.symbol} 加仓单位数为0"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        with transaction.atomic():
            # 【修复P0】再次检查最大持仓限制（双重保险）
            position = PositionState.objects.select_for_update().get(id=position.id)
            new_units = position.units + added_units
            if new_units > POSITION_MAX_UNITS:
                msg = f"[ERROR] {signal.symbol} 加仓后超限（并发保护）: {new_units}Unit > {POSITION_MAX_UNITS}Unit"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
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
            
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        print(f"[SUCCESS] {signal.symbol} 加仓成功: +{added_units}Unit({filled_lots}手) @ {avg_price:.2f}, 总持仓:{new_units}Unit")
        return True
        
    except Exception as e:
        msg = f"[ERROR] 加仓失败 {signal.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_entry_order(api, account, signal, max_retries=5, retry_interval=10, gap_threshold_percent=1.5):
    """
    执行开仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :param gap_threshold_percent: 跳空阈值百分比，默认1.5%
    :return: 是否成功执行开仓操作
    """
    # 【新增】过滤已执行的信号，只处理PENDING状态的信号
    if signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        return False
    
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
            msg = f"[WARN] {signal.symbol} 已存在{['', '多头', '空头'][signal.direction]}持仓，跳过开仓"
            print(msg)
            # 更新信号状态为取消（已有持仓）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
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
        msg = f"[WARN] {signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        # 更新信号状态为取消（跳空保护）
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    
    # 【修复P0】记录开仓前的持仓状态（用于增量计算）
    pos_before = api.get_position(signal.symbol)
    initial_volume_long = pos_before.volume_long if pos_before else 0
    initial_volume_short = pos_before.volume_short if pos_before else 0
    initial_cost_long = Decimal(str(pos_before.open_cost_long)) if pos_before else Decimal('0')
    initial_cost_short = Decimal(str(pos_before.open_cost_short)) if pos_before else Decimal('0')
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, signal.symbol)
    
    try:
        # 设置目标持仓量（开仓直接设置为目标手数）
        if signal.direction == 1:
            target_lots = order_volume  # 多头：目标持多单order_volume手
        else:
            target_lots = -order_volume  # 空头：目标持空单order_volume手
        
        print(f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (开仓{target_units}Unit)")
        
        # 设置目标持仓
        target_pos.set_target_volume(target_lots)
        
        # 等待成交（带超时控制）
        timeout_seconds = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            
            # 获取最新持仓
            pos_after = api.get_position(signal.symbol)
            if pos_after is None:
                continue
            
            # 检查是否达到目标
            if signal.direction == 1:
                actual_filled = pos_after.volume_long - initial_volume_long
            else:
                actual_filled = pos_after.volume_short - initial_volume_short
            
            if actual_filled >= order_volume:
                print(f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手")
                break
            
            # 检查是否长时间无进展
            if time.time() - start_time > timeout_seconds / 2 and actual_filled == 0:
                print(f"[WARN] {signal.symbol} 开仓{int(timeout_seconds/2)}秒仍无成交，可能存在流动性问题")
        
        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)
        if pos_after is None:
            msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【修复P0】使用增量计算法计算本次开仓的实际成交量和均价
        if signal.direction == 1:
            filled_lots = pos_after.volume_long - initial_volume_long
            if filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 多头持仓未增加"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            # 计算本次开仓的均价 = (新累计成本 - 旧累计成本) / 新增持仓量
            current_cost = Decimal(str(pos_after.open_cost_long))
            added_cost = current_cost - initial_cost_long
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        else:
            filled_lots = pos_after.volume_short - initial_volume_short
            if filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 空头持仓未增加"
                print(msg)
                # 更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after.open_cost_short))
            added_cost = current_cost - initial_cost_short
            avg_price = float(added_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        
        # 数据有效性验证
        if avg_price is None or avg_price <= 0:
            msg = f"[ERROR] {signal.symbol} 无法计算有效成交均价: avg_price={avg_price}"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 检查是否部分成交
        if filled_lots < order_volume:
            print(f"[WARN] {signal.symbol} 部分成交: {filled_lots}/{order_volume}手，继续执行")
            # 更新实际成交的单位数
            order_volume = filled_lots
        
        # 计算成交的单位数（向下取整）
        filled_units = filled_lots // unit_lots if unit_lots > 0 else 1
        
        if filled_units == 0:
            msg = f"[ERROR] {signal.symbol} 成交手数不足以构成1个Unit"
            print(msg)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
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
            
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        print(f"[SUCCESS] {signal.symbol} 开仓成功: {filled_units}Unit({filled_lots}手) @ {avg_price:.2f}")
        return True
        
    except Exception as e:
        msg = f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_exit_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行平仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param position: PositionState实例
    :param signal: DailyStrategySignal实例
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行平仓操作
    """
    # 【新增】过滤已执行的信号，只处理PENDING状态的信号（如果有信号关联）
    if signal and signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {position.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        return False
    
    # 【计算需要平仓的总手数】从 contract_total_position 获取
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        return True
    
    # 【修复P0】记录平仓前的持仓状态（用于增量计算）
    pos_before = api.get_position(position.symbol)
    initial_volume_long = pos_before.volume_long if pos_before else 0
    initial_volume_short = pos_before.volume_short if pos_before else 0
    initial_cost_long = Decimal(str(pos_before.open_cost_long)) if pos_before else Decimal('0')
    initial_cost_short = Decimal(str(pos_before.open_cost_short)) if pos_before else Decimal('0')
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, position.symbol)
    
    try:
        # 设置目标持仓为0（完全平仓）
        print(f"[INFO] {position.symbol} 设置目标持仓: 0手 (平仓{total_volume}手)")
        target_pos.set_target_volume(0)
        
        # 等待成交（带超时控制）
        timeout_seconds = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            
            # 获取最新持仓
            pos_after = api.get_position(position.symbol)
            if pos_after is None:
                continue
            
            # 检查是否达到目标（持仓归零）
            remaining_lots = 0
            if position.direction == 1:
                remaining_lots = pos_after.volume_long
            else:
                remaining_lots = pos_after.volume_short
            
            if remaining_lots == 0:
                print(f"[SUCCESS] {position.symbol} 平仓完成")
                break
            
            # 检查是否长时间无进展
            if time.time() - start_time > timeout_seconds / 2 and remaining_lots == total_volume:
                print(f"[WARN] {position.symbol} 平仓{int(timeout_seconds/2)}秒仍无成交，可能存在流动性问题")
        
        # 获取最终成交结果
        pos_after = api.get_position(position.symbol)
        if pos_after is None:
            msg = f"[ERROR] {position.symbol} 无法获取持仓信息"
            print(msg)
            # 更新信号状态为失败（如果有信号关联）
            if signal:
                try:
                    signal.executed_status = 'FAILED'
                    signal.save(update_fields=['executed_status', 'updated_at'])
                except:
                    pass
            return False
        
        # 【修复P0】使用增量计算法计算本次平仓的实际成交量和均价
        if position.direction == 1:
            filled_lots = initial_volume_long - pos_after.volume_long
            if filled_lots <= 0:
                msg = f"[ERROR] {position.symbol} 多头持仓未减少"
                print(msg)
                if signal:
                    try:
                        signal.executed_status = 'FAILED'
                        signal.save(update_fields=['executed_status', 'updated_at'])
                    except:
                        pass
                return False
            
            # 计算本次平仓的均价
            current_cost = Decimal(str(pos_after.open_cost_long))
            reduced_cost = initial_cost_long - current_cost
            avg_price = float(reduced_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        else:
            filled_lots = initial_volume_short - pos_after.volume_short
            if filled_lots <= 0:
                msg = f"[ERROR] {position.symbol} 空头持仓未减少"
                print(msg)
                if signal:
                    try:
                        signal.executed_status = 'FAILED'
                        signal.save(update_fields=['executed_status', 'updated_at'])
                    except:
                        pass
                return False
            
            current_cost = Decimal(str(pos_after.open_cost_short))
            reduced_cost = initial_cost_short - current_cost
            avg_price = float(reduced_cost / Decimal(str(filled_lots))) if filled_lots > 0 else None
        
        # 数据有效性验证
        if avg_price is None or avg_price <= 0:
            msg = f"[ERROR] {position.symbol} 无法计算有效成交均价: avg_price={avg_price}"
            print(msg)
            if signal:
                try:
                    signal.executed_status = 'FAILED'
                    signal.save(update_fields=['executed_status', 'updated_at'])
                except:
                    pass
            return False
        
        with transaction.atomic():
            TradeExecution.objects.create(
                account=position.account,
                symbol=position.symbol,
                direction='SELL' if position.direction == 1 else 'BUY',
                volume=filled_lots,
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
            
            # 【新增】更新信号执行状态为成功（如果有信号关联）
            if signal:
                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status', 'updated_at'])
        
        print(f"[SUCCESS] {position.symbol} 平仓成功: {filled_lots}手 @ {avg_price:.2f}")
        return True
        
    except Exception as e:
        msg = f"[ERROR] 平仓失败 {position.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        # 【新增】更新信号执行状态为失败（如果有信号关联）
        if signal:
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except:
                pass
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos
        except:
            pass


def execute_rollover_order(api, position, signal, max_retries=5, retry_interval=10):
    """
    执行移仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param position: PositionState实例（旧合约持仓）
    :param signal: DailyStrategySignal实例（新合约信号）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行移仓操作
    """
    # 【新增】过滤已执行的信号，只处理PENDING状态的信号
    if signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {position.symbol} -> {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        return False
    
    # 计算移仓数量
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        return True
    
    # 创建移仓日志记录（初始状态为PENDING）
    rollover_log = RolloverLog.objects.create(
        account=position.account,
        old_symbol=position.symbol,
        new_symbol=signal.symbol,
        volume=total_volume,
        status='PENDING'
    )
    
    # ========== 第1阶段：平仓旧合约 ==========
    print(f"[INFO] {position.symbol} 开始平仓旧合约...")
    
    # 【修复P0】记录平仓前的持仓状态（用于增量计算）
    pos_before_old = api.get_position(position.symbol)
    initial_volume_long_old = pos_before_old.volume_long if pos_before_old else 0
    initial_volume_short_old = pos_before_old.volume_short if pos_before_old else 0
    initial_cost_long_old = Decimal(str(pos_before_old.open_cost_long)) if pos_before_old else Decimal('0')
    initial_cost_short_old = Decimal(str(pos_before_old.open_cost_short)) if pos_before_old else Decimal('0')
    
    # 创建目标持仓任务（旧合约）
    target_pos_old = TargetPosTask(api, position.symbol)
    
    try:
        # 设置目标持仓为0（完全平仓）
        target_pos_old.set_target_volume(0)
        
        # 等待成交
        timeout_seconds = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            
            # 检查是否达到目标
            pos_after_old = api.get_position(position.symbol)
            if pos_after_old is None:
                continue
            
            remaining_lots = 0
            if position.direction == 1:
                remaining_lots = pos_after_old.volume_long
            else:
                remaining_lots = pos_after_old.volume_short
            
            if remaining_lots == 0:
                print(f"[SUCCESS] {position.symbol} 平仓完成")
                break
        
        # 获取最终成交结果
        pos_after_old = api.get_position(position.symbol)
        if pos_after_old is None:
            msg = f"[ERROR] {position.symbol} 无法获取持仓信息"
            print(msg)
            rollover_log.status = 'FAILED'
            rollover_log.save(update_fields=['status', 'updated_at'])
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 计算平仓成交量和均价
        if position.direction == 1:
            exit_filled_lots = initial_volume_long_old - pos_after_old.volume_long
            if exit_filled_lots <= 0:
                msg = f"[ERROR] {position.symbol} 多头持仓未减少"
                print(msg)
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after_old.open_cost_long))
            reduced_cost = initial_cost_long_old - current_cost
            exit_avg_price = float(reduced_cost / Decimal(str(exit_filled_lots))) if exit_filled_lots > 0 else None
        else:
            exit_filled_lots = initial_volume_short_old - pos_after_old.volume_short
            if exit_filled_lots <= 0:
                msg = f"[ERROR] {position.symbol} 空头持仓未减少"
                print(msg)
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after_old.open_cost_short))
            reduced_cost = initial_cost_short_old - current_cost
            exit_avg_price = float(reduced_cost / Decimal(str(exit_filled_lots))) if exit_filled_lots > 0 else None
        
        # 数据有效性验证
        if exit_avg_price is None or exit_avg_price <= 0:
            msg = f"[ERROR] {position.symbol} 无法计算有效成交均价: avg_price={exit_avg_price}"
            print(msg)
            rollover_log.status = 'FAILED'
            rollover_log.save(update_fields=['status', 'updated_at'])
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        print(f"[INFO] {position.symbol} 平仓成功: {exit_filled_lots}手 @ {exit_avg_price:.2f}")
        
    except Exception as e:
        msg = f"[ERROR] {position.symbol} 平仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        rollover_log.status = 'FAILED'
        rollover_log.save(update_fields=['status', 'updated_at'])
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos_old
        except:
            pass
    
    # ========== 第2阶段：开仓新合约 ==========
    print(f"[INFO] {signal.symbol} 开始开仓新合约...")
    
    # 【修复P0】记录开仓前的持仓状态（用于增量计算）
    pos_before_new = api.get_position(signal.symbol)
    initial_volume_long_new = pos_before_new.volume_long if pos_before_new else 0
    initial_volume_short_new = pos_before_new.volume_short if pos_before_new else 0
    initial_cost_long_new = Decimal(str(pos_before_new.open_cost_long)) if pos_before_new else Decimal('0')
    initial_cost_short_new = Decimal(str(pos_before_new.open_cost_short)) if pos_before_new else Decimal('0')
    
    # 创建目标持仓任务（新合约）
    target_pos_new = TargetPosTask(api, signal.symbol)
    
    try:
        # 设置目标持仓量
        if position.direction == 1:
            target_lots = exit_filled_lots  # 多头
        else:
            target_lots = -exit_filled_lots  # 空头
        
        print(f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手")
        target_pos_new.set_target_volume(target_lots)
        
        # 等待成交
        timeout_seconds = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            
            # 检查是否达到目标
            pos_after_new = api.get_position(signal.symbol)
            if pos_after_new is None:
                continue
            
            actual_filled = 0
            if position.direction == 1:
                actual_filled = pos_after_new.volume_long - initial_volume_long_new
            else:
                actual_filled = pos_after_new.volume_short - initial_volume_short_new
            
            if actual_filled >= exit_filled_lots:
                print(f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手")
                break
        
        # 获取最终成交结果
        pos_after_new = api.get_position(signal.symbol)
        if pos_after_new is None:
            msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
            print(msg)
            rollover_log.status = 'FAILED'
            rollover_log.save(update_fields=['status', 'updated_at'])
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 计算开仓成交量和均价
        if position.direction == 1:
            entry_filled_lots = pos_after_new.volume_long - initial_volume_long_new
            if entry_filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 多头持仓未增加"
                print(msg)
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after_new.open_cost_long))
            added_cost = current_cost - initial_cost_long_new
            entry_avg_price = float(added_cost / Decimal(str(entry_filled_lots))) if entry_filled_lots > 0 else None
        else:
            entry_filled_lots = pos_after_new.volume_short - initial_volume_short_new
            if entry_filled_lots <= 0:
                msg = f"[ERROR] {signal.symbol} 空头持仓未增加"
                print(msg)
                rollover_log.status = 'FAILED'
                rollover_log.save(update_fields=['status', 'updated_at'])
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False
            
            current_cost = Decimal(str(pos_after_new.open_cost_short))
            added_cost = current_cost - initial_cost_short_new
            entry_avg_price = float(added_cost / Decimal(str(entry_filled_lots))) if entry_filled_lots > 0 else None
        
        # 数据有效性验证
        if entry_avg_price is None or entry_avg_price <= 0:
            msg = f"[ERROR] {signal.symbol} 无法计算有效成交均价: avg_price={entry_avg_price}"
            print(msg)
            rollover_log.status = 'FAILED'
            rollover_log.save(update_fields=['status', 'updated_at'])
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        print(f"[INFO] {signal.symbol} 开仓成功: {entry_filled_lots}手 @ {entry_avg_price:.2f}")
        
        # ========== 第3阶段：更新数据库 ==========
        with transaction.atomic():
            # 记录平仓交易执行日志
            TradeExecution.objects.create(
                account=position.account,
                symbol=position.symbol,
                direction='SELL' if position.direction == 1 else 'BUY',
                volume=exit_filled_lots,
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
                volume=entry_filled_lots,
                price=Decimal(str(entry_avg_price)),
                trade_time=timezone.now(),
                order_id='',
                trade_type='ROLLOVER_ENTRY'
            )
            
            # 【关键】计算移仓盈亏
            rollover_pnl = (Decimal(str(exit_avg_price)) - position.contract_price_avg) * Decimal(str(exit_filled_lots))
            if position.direction == -1:  # 空头持仓，盈亏反向
                rollover_pnl = -rollover_pnl
            
            # 更新旧持仓状态为已平仓（清空所有字段）
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
            
            # 获取新合约的合约乘数
            try:
                contract = api.get_instrument(signal.symbol)
                contracts_per_unit = contract.volume_multiple if contract and contract.volume_multiple else 1
            except:
                contracts_per_unit = 1
            
            # 计算新持仓的单位数
            entry_units = entry_filled_lots // contracts_per_unit
            
            # 创建新持仓状态记录
            PositionState.objects.create(
                account=position.account,
                symbol=signal.symbol,
                product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                direction=position.direction,
                units=entry_units,
                contract_total_position=entry_filled_lots,
                last_add_price=Decimal(str(entry_avg_price)),
                contract_price_avg=Decimal(str(entry_avg_price)),
                highest_close=Decimal(str(entry_avg_price)),
                lowest_close=Decimal(str(entry_avg_price)),
                latest_close_price=Decimal(str(entry_avg_price)),
                is_rollover_needed=False
            )
            
            # 更新移仓日志为成功
            rollover_log.status = 'COMPLETED'
            rollover_log.exit_price = Decimal(str(exit_avg_price))
            rollover_log.entry_price = Decimal(str(entry_avg_price))
            rollover_log.rollover_pnl = rollover_pnl
            rollover_log.remark = f"移仓完成: {position.symbol} → {signal.symbol}, 盈亏={float(rollover_pnl):.2f}元"
            rollover_log.save()
            
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        print(f"[SUCCESS] 移仓成功: {position.symbol} → {signal.symbol}, 盈亏={float(rollover_pnl):.2f}元")
        return True
        
    except Exception as e:
        msg = f"[ERROR] {signal.symbol} 开仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        rollover_log.status = 'FAILED'
        rollover_log.save(update_fields=['status', 'updated_at'])
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False
    finally:
        # 清理TargetPosTask
        try:
            del target_pos_new
        except:
            pass


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
