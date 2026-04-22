import os
import time
from decimal import Decimal
from tqsdk import TqApi, TqAuth, TargetPosTask
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, DailyStrategySignal,StrategyConfig
from stock.scheduler.calculate_unit_lots import calculate_unit_lots
from stock.scheduler.calculate_atr import calculate_atr, price_gap_protection
from stock.scheduler.send_report import send_report
from stock.utils.log_util import log_trade, log_error
from stock.scheduler.check_min_position_requirement import check_min_position_requirement,execute_two_step_opening

# ==================== 仓位管理配置常量 ====================
POSITION_RISK_BASE_AMOUNT = 4000  # 每个Unit（单位）的固定风险资金基数（元）
POSITION_RISK_MULTIPLIER = 2      # ATR风险倍数系数（止损距离 = N × ATR）
POSITION_MIN_UNITS = 1            # 最小持仓单位数（海龟法则中的"Unit"数量，非手数）
POSITION_MAX_UNITS = 3            # 最大持仓3单位数（如1Unit=4手，最大持仓12手）

def is_trading(api, account,signal):
    ts = api.get_trading_status(signal.symbol)
    if ts.trade_status == 'NOTRADING':
        msg = f"[WARN] {signal.symbol} 不在交易时间"
        print(msg)
        log_trade('is_trading checking', msg)
        return False
    else:
        return True
def execute_add_on_order(api, account, signal):
    """
    执行加仓操作的函数（使用TargetPosTask自动化订单管理）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param signal: DailyStrategySignal实例（trade_type='ADD_ON'）
    :param max_retries: 最大重试次数，默认5次
    :param retry_interval: 重试间隔时间（秒），默认10秒
    :return: 是否成功执行加仓操作
    """
    
    if not is_trading(api, account,signal):
        return False

    if signal and signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        log_trade('execute_add_on_order', msg)
        return False
    
    # 优化】直接从 signal.contract_target_number 获取加仓单位数
    add_units_from_signal = signal.contract_target_number   
    msg = f"[INFO] {signal.symbol} 从信号获取加仓单位数: {add_units_from_signal}Unit"
    print(msg)
    log_trade('execute_add_on_order', msg)
    
    # 【修复P0】使用数据库事务和行级锁防止并发
    with transaction.atomic():
        # 获取当前持仓状态（加锁）
        position = PositionState.objects.select_for_update().filter(
            account=account,
            symbol=signal.symbol,
            # units__gt=0
        ).first()
        
        # 【修复P0】在下单前检查是否会超过最大持仓限制
        projected_units = position.units + add_units_from_signal
        if projected_units > POSITION_MAX_UNITS:
            msg = f"[WARN] {signal.symbol} 加仓后将超限: 当前{position.units}Unit + 加仓{add_units_from_signal}Unit = {projected_units}Unit > 最大{POSITION_MAX_UNITS}Unit"
            print(msg)
            log_trade('execute_add_on_order', msg)
            # 更新信号状态为取消（超出限制）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
    
    # 【修复】使用 calculate_unit_lots 计算1个Unit对应的实际手数
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    # 计算实际下单手数 = 加仓单位数 × 1个Unit的手数
    order_volume = add_units_from_signal * unit_lots
    
    msg = f"[INFO] {signal.symbol} 加仓计划: {add_units_from_signal}Unit × {unit_lots}手/Unit = {order_volume}手"
    print(msg)
    log_trade('execute_add_on_order', msg)
    
    # 【新增】检查交易所最小开仓手数限制
    min_position_check = check_min_position_requirement(signal.symbol, order_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        
        msg = f"[INFO] {signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_add_on_order', msg)
        
        # 记录加仓前的持仓状态
        pos_before = api.get_position(signal.symbol)
        initial_volume_long = pos_before.volume_long if pos_before else 0
        initial_volume_short = pos_before.volume_short if pos_before else 0
        
        # 调用两步开仓函数
        two_step_result = execute_two_step_opening(
            api=api,
            symbol=signal.symbol,
            direction=position.direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=order_volume,
            function_name='execute_add_on_order',
            account=account,
            signal=signal
        )
        
        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 更新数据库
        with transaction.atomic():
            new_units = position.units + unit_lots
            new_total_lots = position.contract_total_position + order_volume
            
            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                last_add_price=Decimal(str(two_step_result['avg_price'])),
                latest_close_price=Decimal(str(two_step_result['avg_price']))
            )
            
            # 更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"[SUCCESS] {signal.symbol} 加仓成功（两步开仓）: +{unit_lots}Unit({order_volume}手) @ {two_step_result['avg_price']:.2f}, 总持仓:{new_units}Unit"
        print(msg)
        log_trade('execute_add_on_order', msg)
        return True
    
    else:
        # 正常加仓流程（无需两步开仓）
        # 【修复P0】记录加仓前的持仓状态（仅用于验证成交量）
        pos_before = api.get_position(signal.symbol)
        initial_volume_long = pos_before.volume_long if pos_before else 0
        initial_volume_short = pos_before.volume_short if pos_before else 0
        
        # 创建目标持仓任务
        target_pos = TargetPosTask(api, signal.symbol)
        
        try:
            # 计算目标持仓量 = 当前持仓 + 加仓手数
            # current_position = api.get_position(signal.symbol)
            if position.direction == 1:
                current_lots = initial_volume_long 
                target_lots = current_lots + order_volume
            else:
                current_lots = initial_volume_short 
                target_lots = -(current_lots + order_volume)
            
            msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (当前{current_lots}手 + 加仓{order_volume}手)"
            print(msg)
            log_trade('execute_add_on_order', msg)
            
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
                    log_trade('execute_add_on_order', msg)
                    break
            
            # 获取最终成交结果
            pos_after = api.get_position(signal.symbol)
            if pos_after is None:
                msg = f"[ERROR] {signal.symbol} 无法获取持仓信息"
                print(msg)
                log_error('execute_add_on_order', msg)
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
            log_trade('execute_add_on_order', msg)
            return True
            
        except Exception as e:
            msg = f"[ERROR] 加仓失败 {signal.symbol}: {str(e)}"
            print(msg)
            import traceback
            traceback.print_exc()
            log_error('execute_add_on_order', f"{msg}\n{traceback.format_exc()}")
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
   
    if not is_trading(api, account,signal):
        return False
    
    if signal and signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        log_trade('execute_entry_order', msg)
        return False
    # 【基于ATR计算1个Unit对应的手数】
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    
    # 首次开仓固定为1个Unit
    target_units = 1
    order_volume = target_units * unit_lots
    print(f"[INFO] {signal.symbol} 开仓计划: 1个Unit × {unit_lots}手/Unit = {order_volume}手")
    # 【修复P0】使用数据库事务和行级锁防止并发
    with transaction.atomic():
        # 【修复P1】检查是否已存在同合约、同方向的持仓
        existing_position = PositionState.objects.select_for_update().filter(
            account=account,
            symbol=signal.symbol,
            direction=signal.signal_direction,
            units__gt=0
        ).first()
        
        if existing_position:
            msg = f"[WARN] {signal.symbol} 已存在{['', '多头', '空头'][signal.signal_direction]}持仓，跳过开仓"
            print(msg)
            log_trade('execute_entry_order', msg)
            # 更新信号状态为取消（已有持仓）
            signal.executed_status = 'CANCELLED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
    # 【跳空保护检查】
    can_trade = price_gap_protection(api, signal.symbol, signal.signal_direction, gap_threshold_percent)
    if not can_trade:
        msg = f"[WARN] {signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        log_trade('execute_entry_order', msg)
        # 更新信号状态为取消（跳空保护）
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    
    # 【新增】检查交易所最小开仓手数限制
    min_position_check = check_min_position_requirement(signal.symbol, order_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        
        msg = f"[INFO] {signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_entry_order', msg)
        
        # 调用两步开仓函数
        two_step_result = execute_two_step_opening(
            api=api,
            symbol=signal.symbol,
            direction=signal.signal_direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=order_volume,
            function_name='execute_entry_order',
            account=account,
            signal=signal
        )
        
        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        # 【修复】使用 update_or_create 避免唯一约束冲突
        with transaction.atomic():
            PositionState.objects.update_or_create(
                account=account,
                symbol=signal.symbol,
                defaults={
                    'product_code': signal.product_code,
                    'direction': signal.signal_direction,
                    'units': 1,
                    'contract_total_position': two_step_result['actual_filled'],
                    'last_add_price': Decimal(str(two_step_result['avg_price'])),
                    'highest_close': Decimal(str(two_step_result['avg_price'])),
                    'lowest_close': Decimal(str(two_step_result['avg_price'])),
                    'latest_close_price': Decimal(str(two_step_result['avg_price'])),
                }
            )
            
            # 更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"[SUCCESS] {signal.symbol} 开仓成功（两步开仓）: 1 Unit({two_step_result['actual_filled']}手) @ {two_step_result['avg_price']:.2f}"
        print(msg)
        log_trade('execute_entry_order', msg)
        return True
    
    else:
        # 正常开仓流程（无需两步开仓）
        # 创建目标持仓任务
        target_pos = TargetPosTask(api, signal.symbol)
        try:
            # 设置目标持仓量（开仓直接设置为目标手数）
            if signal.signal_direction == 1:
                target_lots = order_volume  # 多头：目标持多单order_volume手
            else:
                target_lots = -order_volume  # 空头：目标持空单order_volume手
            
            msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手 (开仓{target_units} Unit)"
            print(msg)
            log_trade('execute_entry_order', msg)
            
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
                if signal.signal_direction == 1:
                    actual_filled = pos_after.volume_long 
                else:
                    actual_filled = pos_after.volume_short
                if actual_filled >= order_volume:
                    msg = f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手"
                    print(msg)
                    log_trade('execute_entry_order', msg)
                    break    

            # 获取最终成交结果
            pos_after = api.get_position(signal.symbol)
            if pos_after is None:
                msg = f"[ERROR] {signal.symbol} 获取持仓信息失败"
                print(msg)
                log_error('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal)
                # 获取失败，更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            else:
                entry_avg_price = float(pos_after.last_price) if pos_after and pos_after.last_price else None
                with transaction.atomic():
                    
                    # 【修复】使用 update_or_create 避免唯一约束冲突
                    with transaction.atomic():
                        PositionState.objects.update_or_create(
                            account=account,
                            symbol=signal.symbol,
                            defaults={
                                'product_code': signal.product_code,
                                'direction': signal.signal_direction,
                                'units': 1,
                                'contract_total_position': actual_filled,
                                'last_add_price': Decimal(str(entry_avg_price)),
                                # contract_price_avg=Decimal(str(entry_avg_price)),
                                'highest_close': Decimal(str(entry_avg_price)),
                                'lowest_close': Decimal(str(entry_avg_price)),
                                'latest_close_price': Decimal(str(entry_avg_price)),
                            }
                        )
                        
                        # 【新增】更新信号执行状态为成功
                        signal.executed_status = 'SUCCESS'
                        signal.save(update_fields=['executed_status', 'updated_at'])
                
                msg = f"[SUCCESS] {signal.symbol} 开仓成功: 1 Unit({actual_filled}手) @ {entry_avg_price:.2f}"
                print(msg)
                log_trade('execute_entry_order', msg)
                return True
            
        except Exception as e:
            msg = f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}"
            print(msg)
            import traceback
            traceback.print_exc()
            log_error('execute_entry_order', f"{msg}\n{traceback.format_exc()}")
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
    
    if not is_trading(api, position.account, signal):
        return False
    # 【新增】过滤已执行的信号，只处理PENDING状态的信号（如果有信号关联）

    
    if signal and signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {position.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        log_trade('execute_exit_order', msg)
        return False
    
    # 【计算需要平仓的总手数】从 contract_total_position 获取
    total_volume = position.contract_total_position
    
    # 【边界检查】如果没有持仓，直接返回成功
    if total_volume <= 0:
        msg = f"[INFO] {position.symbol} 无持仓，无需平仓"
        print(msg)
        log_trade('execute_exit_order', msg)
        return True
        
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, position.symbol)
    
    try:
        # 设置目标持仓为0（完全平仓）
        msg = f"[INFO] {position.symbol} 设置目标持仓: 0手 (平仓{total_volume}手)"
        print(msg)
        log_trade('execute_exit_order', msg)
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
                log_trade('execute_exit_order', msg)
                break
        
        
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
        log_trade('execute_exit_order', msg)
        return True
        
    except Exception as e:
        msg = f"[ERROR] 平仓失败 {position.symbol}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_exit_order', f"{msg}\n{traceback.format_exc()}")
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
    

    if not is_trading(api, position.account, signal):
        return False
    
    if signal and signal.executed_status and signal.executed_status != 'PENDING':
        msg = f"[INFO] {signal.symbol} 信号已执行（状态={signal.executed_status}），跳过"
        print(msg)
        log_trade('execute_rollover_order', msg)
        return False
    
    # 计算移仓数量
    # total_volume = position.contract_total_position
    
    
    # ========== 第1阶段：平仓旧合约 ==========
    msg = f"[INFO] {position.symbol} 开始平仓旧合约..."
    print(msg)
    log_trade('execute_rollover_order', msg)
          
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
                log_trade('execute_rollover_order', msg)
                break                
    except Exception as e:
        msg = f"[ERROR] {position.symbol} 平仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
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
    log_trade('execute_rollover_order', msg)
    
    # 【新增】检查交易所最小开仓手数限制
    target_volume = position.contract_total_position
    min_position_check = check_min_position_requirement(signal.symbol, target_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        
        msg = f"[INFO] {signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_rollover_order', msg)
        
        # 调用两步开仓函数
        two_step_result = execute_two_step_opening(
            api=api,
            symbol=signal.symbol,
            direction=position.direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=target_volume,
            function_name='execute_rollover_order',
            account=position.account,
            signal=signal
        )
        
        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        
        entry_avg_price = two_step_result['avg_price']
        actual_filled = two_step_result['actual_filled']
        
        msg = f"[INFO] {signal.symbol} 换月开仓成功（两步开仓）: {actual_filled}手 @ {entry_avg_price:.2f}"
        print(msg)
        log_trade('execute_rollover_order', msg)
    
    else:
        # 正常开仓流程（无需两步开仓）
        # 创建目标持仓任务（新合约）
        target_pos_new = TargetPosTask(api, signal.symbol)
        
        try:
            # 设置目标持仓量
            if position.direction == 1:
                target_lots = target_volume  # 多头
            else:
                target_lots = -target_volume  # 空头
            
            msg = f"[INFO] {signal.symbol} 设置目标持仓: {target_lots}手"
            print(msg)
            log_trade('execute_rollover_order', msg)
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
                
                if actual_filled >= target_volume:
                    msg = f"[SUCCESS] {signal.symbol} 开仓完成: {actual_filled}手"
                    print(msg)
                    log_trade('execute_rollover_order', msg)
                    break
            
            # 【简化】直接使用TqSDK实时行情价格作为成交价格
            quote = api.get_quote(signal.symbol)
            entry_avg_price = float(quote.last_price) if quote and quote.last_price else None
            
            msg = f"[INFO] {signal.symbol} 换月开仓成功: {actual_filled}手 @ {entry_avg_price:.2f}"
            print(msg)
            log_trade('execute_rollover_order', msg)
            
        except Exception as e:
            msg = f"[ERROR] {signal.symbol} 移仓操作中，开仓失败: {str(e)}"
            print(msg)
            import traceback
            traceback.print_exc()
            log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except:
                pass
            return False
        finally:
            try:
                del target_pos_new
            except:
                pass
    
    # ========== 第3阶段：更新数据库 ==========
    try:
        with transaction.atomic():
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
                    log_trade('execute_rollover_order', msg)
                else:
                    # 数据不足，使用开仓价作为后备方案
                    msg = f"[WARN] {signal.symbol} 历史数据不足({len(klines) if klines else 0}根)，使用开仓价初始化"
                    print(msg)
                    log_trade('execute_rollover_order', msg)
                    init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                    init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                    init_stop_loss = None
            except Exception as e:
                msg = f"[WARN] {signal.symbol} 计算历史数据失败: {str(e)}，使用开仓价初始化"
                print(msg)
                import traceback
                traceback.print_exc()
                log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
                init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                init_stop_loss = None
            
            # 创建新持仓状态记录
            PositionState.objects.update_or_create(
                account=position.account,
                symbol=signal.symbol,
                defaults={
                    'product_code': signal.product_code,
                    'direction': position.direction,
                    'units': position.units,
                    'contract_total_position': actual_filled,
                    'last_add_price': Decimal(str(entry_avg_price)),
                    # contract_price_avg=Decimal(str(entry_avg_price)),
                    'highest_close': init_highest_close,
                    'lowest_close': init_lowest_close,
                    'latest_close_price': Decimal(str(entry_avg_price)),
                    'stop_loss_price': init_stop_loss,
                    'is_rollover_needed': False
                }
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
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
        # 【新增】更新信号执行状态为失败
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except:
            pass
        return False


def process_signals_by_type(api, account, trade_type):
    """
    通用信号处理函数（支持开仓、平仓、移仓、加仓）
    :param api: TqApi实例
    :param account: TradingAccount实例
    :param trade_type: 交易类型 ('ENTRY', 'STOP_LOSS', 'ROLLOVER', 'ADD_ON')
    :return: 处理结果统计
    """
    # 定义不同交易类型的配置
    type_config = {
        'ENTRY': {
            'query_filter': Q(trade_type='ENTRY'),
            'executor': execute_entry_order,
            'executor_args': ['api', 'account', 'signal'],
            'success_msg': lambda signal: f"✅ 开仓成功: {signal.symbol}",
            'fail_msg': lambda signal: f"❌ 开仓失败: {signal.symbol}",
            'need_position': False
        },
        'STOP_LOSS': {
            'query_filter': Q(trade_type='STOP_LOSS'),
            'executor': execute_exit_order,
            'executor_args': ['api', 'position', 'signal'],
            'success_msg': lambda position: f"✅ 平仓成功: {position.symbol}",
            'fail_msg': lambda position: f"❌ 平仓失败: {position.symbol}",
            'need_position': True,
            'position_filter': lambda account: PositionState.objects.filter(account=account, units__gt=0)
        },
        'ROLLOVER': {
            'query_filter': Q(trade_type='ROLLOVER'),
            'executor': execute_rollover_order,
            'executor_args': ['api', 'position', 'signal'],
            'success_msg': lambda position, signal: f"✅ 移仓成功: {position.symbol} -> {signal.symbol}",
            'fail_msg': lambda position, signal: f"❌ 移仓失败: {position.symbol} -> {signal.symbol}",
            'need_position': True,
            'position_filter': lambda account, symbol: PositionState.objects.get(account=account, symbol=symbol, units__gt=0)
        },
        'ADD_ON': {
            'query_filter': Q(trade_type='ADD_ON'),
            'executor': execute_add_on_order,
            'executor_args': ['api', 'account', 'signal'],
            'success_msg': lambda signal: f"✅ 加仓成功: {signal.symbol}",
            'fail_msg': lambda signal: f"❌ 加仓失败: {signal.symbol}",
            'need_position': False
        }
    }
    
    # 获取配置
    config = type_config.get(trade_type)
    if not config:
        print(f"[ERROR] 不支持的交易类型: {trade_type}")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    # 查询信号
    signals = DailyStrategySignal.objects.filter(config['query_filter'])
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    # 根据是否需要持仓记录采用不同的处理逻辑
    if config['need_position']:
        if trade_type == 'STOP_LOSS':
            # 平仓：遍历持仓记录，查找对应的信号
            positions = config['position_filter'](account)
            for position in positions:
                exit_signals = DailyStrategySignal.objects.filter(
                    Q(symbol=position.symbol) & config['query_filter']
                )
                for signal in exit_signals:
                    try:
                        success = config['executor'](api, position, signal)
                        if success:
                            # signal.delete()
                            print(config['success_msg'](position))
                            success_count += 1
                        else:
                            print(config['fail_msg'](position))
                            failed_count += 1
                    except Exception as e:
                        print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                        failed_count += 1
        
        elif trade_type == 'ROLLOVER':
            # 移仓：遍历信号，查找对应的持仓记录
            for signal in signals:
                try:
                    position = config['position_filter'](account, signal.symbol)
                    success = config['executor'](api, position, signal)
                    if success:
                        # signal.delete()
                        print(config['success_msg'](position, signal))
                        success_count += 1
                    else:
                        print(config['fail_msg'](position, signal))
                        failed_count += 1
                except PositionState.DoesNotExist:
                    print(f"⚠️ 移仓信号未找到对应持仓: {signal.symbol}")
                    skipped_count += 1
                except Exception as e:
                    print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                    failed_count += 1
    else:
        # 开仓和加仓：直接遍历信号
        for signal in signals:
            try:
                success = config['executor'](api, account, signal)
                if success:
                    # signal.delete()
                    print(config['success_msg'](signal))
                    success_count += 1
                else:
                    print(config['fail_msg'](signal))
                    failed_count += 1
            except Exception as e:
                print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                failed_count += 1
    
    return {'success': success_count, 'failed': failed_count, 'skipped': skipped_count}


def job_daily_open_process():
    """
    每日开盘处理函数
    """
    from datetime import datetime
    # pause_open_task_job = StrategyConfig.objects.get(name='FT').pause_open_task_job
    # if pause_open_task_job:
    #     print("[INFO] 暂停开仓任务")
    #     return
    # 获取当前日期
    current_date = datetime.now().date()
    # 获取交易账户
    accounts = TradingAccount.objects.all()
    for account in accounts:
        # 初始化TqApi
        api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
        try:
            # 处理平仓信号
            result = process_signals_by_type(api, account, 'STOP_LOSS')
            print(f"[INFO] 平仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")
            
            # 处理开仓信号
            result = process_signals_by_type(api, account, 'ENTRY')
            print(f"[INFO] 开仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")
            
            # 处理移仓信号
            result = process_signals_by_type(api, account, 'ROLLOVER')
            print(f"[INFO] 移仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔, 跳过{result['skipped']}笔")
            
            # 处理加仓信号
            result = process_signals_by_type(api, account, 'ADD_ON')
            print(f"[INFO] 加仓处理完成: 成功{result['success']}笔, 失败{result['failed']}笔")
            
            # 发送交易执行情况报告
            send_report(account, current_date)
        except Exception as e:
            print(f"[ERROR] 处理账户 {account.username} 时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 关闭TqApi连接
            api.close()