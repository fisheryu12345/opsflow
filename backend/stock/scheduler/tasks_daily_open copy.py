import os
import time
from decimal import Decimal
from tqsdk import TqApi, TqAuth, TargetPosTask
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, DailyStrategySignal
from stock.scheduler.calculate_unit_lots import calculate_unit_lots
from stock.scheduler.calculate_atr import calculate_atr, price_gap_protection
from stock.scheduler.send_report import send_report
from stock.utils.log_util import log_trade, log_error

# ==================== 仓位管理配置常量 ====================
POSITION_RISK_BASE_AMOUNT = 4000  # 每个Unit（单位）的固定风险资金基数（元）
POSITION_RISK_MULTIPLIER = 2      # ATR风险倍数系数（止损距离 = N × ATR）
POSITION_MIN_UNITS = 1            # 最小持仓单位数（海龟法则中的"Unit"数量，非手数）
POSITION_MAX_UNITS = 3            # 最大持仓3单位数（如1Unit=4手，最大持仓12手）



def execute_addon_order(api, account, signal):
    """
    执行加仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例（trade_type='ADD_ON'）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行加仓操作
    """
    
    # 优化】直接从 signal.contract_target_number 获取加仓单位数
    add_units_from_signal = signal.contract_target_number   
    print(f"[INFO] {signal.symbol} 从信号获取加仓单位数: {add_units_from_signal}Unit")
    
    # 【修复P0】使用数据库事务和行级锁防止并发
    with transaction.atomic():
        # 获取当前持仓状态（加锁）
        position = PositionState.objects.select_for_update().filter(
            account=account,
            symbol=signal.symbol,
            units__gt=0
        ).first()
        
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
    
    # 【修复P0】记录加仓前的持仓状态（仅用于验证成交量）
    pos_before = api.get_position(signal.symbol)
    initial_volume_long = pos_before.volume_long if pos_before else 0
    initial_volume_short = pos_before.volume_short if pos_before else 0
    
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
        
        msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (当前{current_lots}手 + 加仓{order_volume}手)"
        print(msg)
        log_trade('execute_addon_order', msg, account=account, symbol=signal.symbol, signal=signal)
        
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
                msg = f"[SUCCESS] {signal.symbol} 加仓完成: {actual_added}手"
                print(msg)
                log_trade('execute_addon_order', msg, account=account, symbol=signal.symbol, signal=signal, level='SUCCESS')
                break
        
        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)
        if pos_after is None:
            msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
            print(msg)
            log_error('execute_addon_order', msg, account=account, symbol=signal.symbol, signal=signal)
            # 更新信号状态为失败
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【简化】直接使用TqSDK实时行情价格作为成交价格
        quote = api.get_quote(signal.symbol)
        avg_price = float(quote.last_price) if quote and quote.last_price else None
    
        with transaction.atomic():
            new_units = position.units + unit_lots
            new_total_lots = position.contract_total_position + order_volume
            
            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                last_add_price=Decimal(str(avg_price)),
                latest_close_price=Decimal(str(avg_price))
            )
            
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"[SUCCESS] {signal.symbol} 加仓成功: +{unit_lots}Unit({order_volume}手) @ {avg_price:.2f}, 总持仓:{new_units}Unit"
        print(msg)
        log_trade('execute_addon_order', msg, account=account, symbol=signal.symbol, signal=signal, level='SUCCESS')
        return True
        
    except Exception as e:
        msg = f"[ERROR] 加仓失败 {signal.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_addon_order', f"{msg}\n{traceback.format_exc()}", account=account, symbol=signal.symbol, signal=signal)
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False
    finally:
        try:
            del target_pos
        except:
            pass


def execute_entry_order(api, account, signal, gap_threshold_percent=1.5):
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
            log_trade('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal, level='WARNING')
            # 更新信号状态为取消（已有持仓）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        

    # 【跳空保护检查】
    can_trade = price_gap_protection(api, signal.symbol, signal.direction, gap_threshold_percent)
    if not can_trade:
        msg = f"[WARN] {signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        log_trade('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal, level='WARNING')
        # 更新信号状态为取消（跳空保护）
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, signal.symbol)
    try:
        # 设置目标持仓量（开仓直接设置为目标手数）
        if signal.direction == 1:
            target_lots = order_volume  # 多头：目标持多单order_volume手
        else:
            target_lots = -order_volume  # 空头：目标持空单order_volume手
        
        msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (开仓{target_units}Unit)"
        print(msg)
        log_trade('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal)
        
        # 设置目标持仓
        target_pos.set_target_volume(target_lots)
        
        # 等待成交（带超时控制）
        timeout_seconds = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            api.wait_update(deadline=time.time() + 1)
            pos_after = api.get_position(signal.symbol)
            if pos_after is None:
                continue
            # 检查是否达到目标
            if signal.direction == 1:
                actual_filled = pos_after.volume_long 
            else:
                actual_filled = pos_after.volume_short
            if actual_filled >= order_volume:
                msg = f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手"
                print(msg)
                log_trade('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal, level='SUCCESS')
                break    

        # 获取最终成交结果
        pos_after = api.get_position(signal.symbol)          
        entry_avg_price = float(pos_after.last_price) if pos_after and pos_after.last_price else None
    
        with transaction.atomic():
            
            # 创建持仓状态记录
            PositionState.objects.create(
                account=account,
                symbol=signal.symbol,
                product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                direction=signal.direction,
                units=1,
                contract_total_position=actual_filled,
                last_add_price=Decimal(str(entry_avg_price)),
                contract_price_avg=Decimal(str(entry_avg_price)),
                highest_close=Decimal(str(entry_avg_price)),
                lowest_close=Decimal(str(entry_avg_price)),
                latest_close_price=Decimal(str(entry_avg_price)),
            )
            
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"[SUCCESS] {signal.symbol} 开仓成功: 1 Unit({actual_filled}手) @ {entry_avg_price:.2f}"
        print(msg)
        log_trade('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal, level='SUCCESS')
        return True
        
    except Exception as e:
        msg = f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_entry_order', f"{msg}\n{traceback.format_exc()}", account=account, symbol=signal.symbol, signal=signal)
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


def execute_exit_order(api, position, signal):
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
        log_trade('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal)
        return False
    
    # 【计算需要平仓的总手数】从 contract_total_position 获取
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        msg = f"[INFO] {position.symbol} 无持仓，无需平仓"
        print(msg)
        log_trade('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal)
        return True
        
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, position.symbol)
    
    try:
        # 设置目标持仓为0（完全平仓）
        msg = f"[INFO] {position.symbol} 设置目标持仓: 0手 (平仓{total_volume}手)"
        print(msg)
        log_trade('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal)
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
                msg = f"[SUCCESS] {position.symbol} 平仓完成"
                print(msg)
                log_trade('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal, level='SUCCESS')
                break
        
        # 【修复P0】获取最终成交结果并验证持仓是否真的归零
        pos_after = api.get_position(position.symbol)
        if pos_after is None:
            msg = f"[ERROR] {position.symbol} 无法获取持仓信息"
            print(msg)
            log_error('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal)
            # 更新信号状态为失败（如果有信号关联）
            if signal:
                try:
                    signal.executed_status = 'FAILED'
                    signal.save(update_fields=['executed_status', 'updated_at'])
                except:
                    pass
            return False
        
        # 【关键检查】验证实际剩余持仓
        remaining_lots = 0
        if position.direction == 1:
            remaining_lots = pos_after.volume_long
        else:
            remaining_lots = pos_after.volume_short
        
        if remaining_lots > 0:
            msg = f"[ERROR] {position.symbol} 平仓未完全成功！计划平仓{total_volume}手，剩余{remaining_lots}手"
            print(msg)
            log_error('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal)
            if signal:
                try:
                    signal.executed_status = 'FAILED'
                    signal.save(update_fields=['executed_status', 'updated_at'])
                except:
                    pass
            return False
        
        with transaction.atomic():
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
        
        msg = f"[SUCCESS] {position.symbol} 平仓成功"
        print(msg)
        log_trade('execute_exit_order', msg, account=position.account, symbol=position.symbol, signal=signal, level='SUCCESS')
        return True
        
    except Exception as e:
        msg = f"[ERROR] 平仓失败 {position.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_exit_order', f"{msg}\n{traceback.format_exc()}", account=position.account, symbol=position.symbol, signal=signal)
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


def execute_rollover_order(api, position, signal):
    """
    执行移仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param position: PositionState实例（旧合约持仓）
    :param signal: DailyStrategySignal实例（新合约信号）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行移仓操作
    """
    
    # 计算移仓数量
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        msg = f"[INFO] {position.symbol} 无持仓，无需移仓"
        print(msg)
        log_trade('execute_rollover_order', msg, account=position.account, symbol=position.symbol, signal=signal)
        return True
    
    # ========== 第1阶段：平仓旧合约 ==========
    msg = f"[INFO] {position.symbol} 开始平仓旧合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, account=position.account, symbol=position.symbol, signal=signal)
          
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
                msg = f"[SUCCESS] {position.symbol} 平仓完成"
                print(msg)
                log_trade('execute_rollover_order', msg, account=position.account, symbol=position.symbol, signal=signal, level='SUCCESS')
                break
        
        # 【修复P0】获取最终成交结果并验证持仓是否真的归零
        pos_after_old = api.get_position(position.symbol)
        if pos_after_old is None:
            msg = f"[ERROR] {position.symbol} 无法获取持仓信息"
            print(msg)
            log_error('execute_rollover_order', msg, account=position.account, symbol=position.symbol, signal=signal)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【关键检查】验证实际剩余持仓
        remaining_lots = 0
        if position.direction == 1:
            remaining_lots = pos_after_old.volume_long
        else:
            remaining_lots = pos_after_old.volume_short
        
        if remaining_lots > 0:
            msg = f"[ERROR] {position.symbol} 平仓未完全成功！计划平仓{total_volume}手，剩余{remaining_lots}手"
            print(msg)
            log_error('execute_rollover_order', msg, account=position.account, symbol=position.symbol, signal=signal)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
                
    except Exception as e:
        msg = f"[ERROR] {position.symbol} 平仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", account=position.account, symbol=position.symbol, signal=signal)
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    finally:
        try:
            del target_pos_old
        except:
            pass
    
    # ========== 第2阶段：开仓新合约 ==========
    msg = f"[INFO] {signal.symbol} 开始开仓新合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
    
    # 创建目标持仓任务（新合约）
    target_pos_new = TargetPosTask(api, signal.symbol)
    
    try:
        # 设置目标持仓量
        if position.direction == 1:
            target_lots = position.contract_total_position  # 多头
        else:
            target_lots = -position.contract_total_position  # 空头
        
        msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手"
        print(msg)
        log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
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
                actual_filled = pos_after_new.volume_long
            else:
                actual_filled = pos_after_new.volume_short
            
            if actual_filled >= position.contract_total_position:
                msg = f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手"
                print(msg)
                log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal, level='SUCCESS')
                break
        
        # 【修复P0】获取最终成交结果并验证持仓
        pos_after_new = api.get_position(signal.symbol)
        if pos_after_new is None:
            msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
            print(msg)
            log_error('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【简化】计算实际开仓成交量
        if position.direction == 1:
            entry_filled_lots = pos_after_new.volume_long
        else:
            entry_filled_lots = pos_after_new.volume_short
        
        if entry_filled_lots <= 0:
            msg = f"[ERROR] {signal.symbol} 持仓未增加"
            print(msg)
            log_error('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【简化】直接使用TqSDK实时行情价格作为成交价格
        quote = api.get_quote(signal.symbol)
        entry_avg_price = float(quote.last_price) if quote and quote.last_price else None
        
        if entry_avg_price is None or entry_avg_price <= 0:
            msg = f"[WARN] {signal.symbol} 无法获取有效市场价格，使用0作为均价"
            print(msg)
            log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal, level='WARNING')
            entry_avg_price = 0.0
        
        msg = f"[INFO] {signal.symbol} 开仓成功: {entry_filled_lots}手 @ {entry_avg_price:.2f}"
        print(msg)
        log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
        
        # ========== 第3阶段：更新数据库 ==========
        with transaction.atomic():
            # 【修复】移仓后直接沿用旧合约的Unit值，不重新计算
            entry_units = position.units
            
            # 【修复】基于过去20日历史数据初始化 highest_close、lowest_close 和 stop_loss_price
            try:
                # 获取新合约过去20日的K线数据
                klines = api.get_kline_serial(signal.symbol, duration_seconds=86400, data_length=25)
                
                if klines is not None and len(klines) >= 20:
                    # 计算过去20日的最高收盘价和最低收盘价
                    historical_high = float(klines['close'].rolling(window=20).max().iloc[-1])
                    historical_low = float(klines['close'].rolling(window=20).min().iloc[-1])
                    
                    # 计算ATR用于止损价
                    atr_value = calculate_atr(api, signal.symbol, period=20)
                    
                    # 根据持仓方向设置初始值
                    if position.direction == 1:  # 多头
                        init_highest_close = Decimal(str(historical_high))
                        init_lowest_close = None  # 多头不需要最低价
                        # 止损价 = 最高收盘价 - 2 * ATR
                        init_stop_loss = init_highest_close - Decimal('2') * Decimal(str(atr_value)) if atr_value else None
                    else:  # 空头
                        init_highest_close = None  # 空头不需要最高价
                        init_lowest_close = Decimal(str(historical_low))
                        # 止损价 = 最低收盘价 + 2 * ATR
                        init_stop_loss = init_lowest_close + Decimal('2') * Decimal(str(atr_value)) if atr_value else None
                    
                    msg = f"[INFO] {signal.symbol} 基于20日历史数据初始化: highest={historical_high:.2f}, lowest={historical_low:.2f}, ATR={atr_value:.2f}"
                    print(msg)
                    log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal)
                else:
                    # 数据不足，使用开仓价作为后备方案
                    msg = f"[WARN] {signal.symbol} 历史数据不足({len(klines) if klines else 0}根)，使用开仓价初始化"
                    print(msg)
                    log_trade('execute_rollover_order', msg, account=position.account, symbol=signal.symbol, signal=signal, level='WARNING')
                    init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                    init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                    init_stop_loss = None
            except Exception as e:
                msg = f"[WARN] {signal.symbol} 计算历史数据失败: {str(e)}，使用开仓价初始化"
                print(msg)
                import traceback
                traceback.print_exc()
                log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", account=position.account, symbol=signal.symbol, signal=signal)
                init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                init_stop_loss = None
            
            # 创建新持仓状态记录
            PositionState.objects.create(
                account=position.account,
                symbol=signal.symbol,
                product_code=signal.symbol.split('.')[-1][:2] if '.' in signal.symbol else '',
                direction=position.direction,
                units=position.units,
                contract_total_position=entry_filled_lots,
                last_add_price=Decimal(str(entry_avg_price)),
                contract_price_avg=Decimal(str(entry_avg_price)),
                highest_close=init_highest_close,
                lowest_close=init_lowest_close,
                latest_close_price=Decimal(str(entry_avg_price)),
                stop_loss_price=init_stop_loss,
                is_rollover_needed=False
            )
            # 更新旧持仓状态为已平仓（删除整个合约记录）
            PositionState.objects.filter(id=position.id).delete()
            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        return True
        
    except Exception as e:
        msg = f"[ERROR] {signal.symbol} 移仓操作中，开仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", account=position.account, symbol=signal.symbol, signal=signal)
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False
    
def process_exit_signals(api, account):
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
def process_entry_signals(api, account):
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
def process_rollover_signals(api, account): 
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
def process_addon_signals(api, account):
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