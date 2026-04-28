import time
from decimal import Decimal
from django.utils import timezone
from tqsdk import TqApi, TqAuth, TargetPosTask,TqAccount , TqKq,TqSim
from django.db import transaction,close_old_connections
from django.db.models import Q
from stock.models import TradingAccount, PositionState, DailyStrategySignal
from stock.scheduler.calculate_unit_lots import calculate_unit_lots
from stock.scheduler.calculate_atr import calculate_atr, price_gap_protection
from stock.scheduler.send_report import send_open_report
from stock.utils.log_util import log_trade, log_error
from stock.scheduler.check_min_position_requirement import check_min_position_requirement,execute_two_step_opening
from stock.parameter_config import TIMEOUT_SECONDS, POSITION_MAX_UNITS


def wait_for_target_position(api, target_pos, symbol, target_lots, function_name, timeout=TIMEOUT_SECONDS):
    """
    通用持仓目标等待与资源释放函数
    
    :param api: TqApi 实例
    :param target_pos: TargetPosTask 实例
    :param symbol: 合约代码
    :param target_lots: 目标持仓手数
    :param function_name: 调用该函数的名称（用于日志记录）
    :param timeout: 超时时间（秒）
    :return: dict {'success': bool, 'pos': Position object or None}
    """
    start_time = time.time()
    pos_current = None
    
    while time.time() - start_time < timeout:
        api.wait_update()
        
        # 【核心修复】直接检查实际持仓是否达到目标
        pos_current = api.get_position(symbol)
        if pos_current and pos_current.pos == target_lots:
            msg = f"{symbol} 任务完成: 当前持仓 {target_lots} 手"
            print(msg)
            log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
            break
    
    # 【关键一步】：无论成功与否，都尝试 cancel 释放资源
    try:
        target_pos.cancel()
        while not target_pos.is_finished():
            api.wait_update()
    except Exception as e:
        log_error(function_name, f"{symbol} 释放 TargetPosTask 资源时出错: {str(e)}")

    return {'success': pos_current is not None and pos_current.pos == target_lots, 'pos': pos_current}

def is_trading(api, account,signal):
    ts = api.get_trading_status(signal.symbol)
    if ts.trade_status == 'NOTRADING':
        msg = f"{signal.symbol} 不在交易时间"
        print(msg)
        log_trade('is_trading checking', msg,symbol=signal.symbol,log_level='INFO')
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
    
    # 优化】直接从 signal.contract_target_number 获取加仓单位数
    add_units_from_signal = signal.contract_target_number   
    msg = f"{signal.symbol} 从信号获取加仓单位数: {add_units_from_signal} Unit"
    print(msg)
    log_trade('execute_add_on_order', msg,symbol=signal.symbol, log_level='INFO')
    
    position = PositionState.objects.get(
        account=account,
        symbol=signal.symbol,
    )

    # 【修复P0】在下单前检查是否会超过最大持仓限制
    projected_units = position.units + add_units_from_signal
    if projected_units > POSITION_MAX_UNITS:
        msg = f"{signal.symbol} 加仓后将超限: 当前{position.units} Unit + 加仓 {add_units_from_signal} Unit = {projected_units} Unit > 最大 {POSITION_MAX_UNITS} Unit"
        print(msg)
        log_trade('execute_add_on_order', msg,symbol=signal.symbol,level='WARNING')
        # 更新信号状态为取消（超出限制）
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    
    # 【修复】使用 calculate_unit_lots 计算1个Unit对应的实际手数
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    # 计算实际下单手数 = 加仓单位数 × 1个Unit的手数
    order_volume = add_units_from_signal * unit_lots
    
    msg = f"{signal.symbol} 加仓计划: {add_units_from_signal} Unit × {unit_lots} 手/Unit = {order_volume} 手"
    print(msg)
    log_trade('execute_add_on_order', msg,symbol=signal.symbol, log_level='INFO')
    
    # 【新增】检查交易所最小开仓手数限制
    min_position_check = check_min_position_requirement(signal.symbol, order_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        msg = f"{signal.symbol} 采用两步开仓策略: 先开 {adjusted_volume} 手，再平 {excess_to_close} 手"
        print(msg)
        log_trade('execute_add_on_order', msg,symbol=signal.symbol, log_level='INFO')
    
        
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
            new_units = position.units + add_units_from_signal
            new_total_lots = position.contract_total_position + order_volume
            
            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                last_add_price=Decimal(str(two_step_result['avg_price'])),
                latest_close_price=Decimal(str(two_step_result['avg_price'])),
                last_update_time=timezone.now()  # 【修复】手动更新最后更新时间
            )

        # 更新信号执行状态为成功
        signal.executed_status = 'SUCCESS'
        signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"{signal.symbol} 加仓成功（两步开仓）: +{unit_lots} Unit ({order_volume}手) @ {two_step_result['avg_price']:.2f}, 总持仓:{new_units} Unit"
        print(msg)
        log_trade('execute_add_on_order', msg,symbol=signal.symbol, log_level='SUCCESS')
        return True
    
    else:        
        # 创建目标持仓任务
        target_pos = TargetPosTask(api, signal.symbol)
        try:
            if position.direction == 1:
                target_lots = position.contract_total_position + order_volume
            else:
                target_lots = -(position.contract_total_position + order_volume)
            
            msg = f"{signal.symbol} 设置目标持仓: {target_lots} 手 (当前 {position.contract_total_position} 手 + 加仓 {order_volume} 手)"
            print(msg)
            log_trade('execute_add_on_order', msg,symbol=signal.symbol, log_level='INFO')

            target_pos.set_target_volume(target_lots)
            
            # 【重构】调用通用等待函数
            result = wait_for_target_position(
                api=api, 
                target_pos=target_pos, 
                symbol=signal.symbol, 
                target_lots=target_lots, 
                function_name='execute_add_on_order'
            )
            
            # pos_after = result['pos']
            if not result['success']:
                msg = f"[ERROR] {signal.symbol} 加仓超时或失败"
                print(msg)
                log_error('execute_add_on_order', msg)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False

            # 【简化】直接使用TqSDK实时行情价格作为成交价格
            quote = api.get_quote(signal.symbol)
            avg_price = float(quote.last_price) if quote and quote.last_price else None
        
            with transaction.atomic():   
                new_units = position.units + add_units_from_signal
                new_total_lots = position.contract_total_position + order_volume
                
                PositionState.objects.filter(id=position.id).update(
                    units=new_units,
                    contract_total_position=new_total_lots,
                    last_add_price=Decimal(str(avg_price)),
                    latest_close_price=Decimal(str(avg_price)),
                    last_update_time=timezone.now()  # 【修复】手动更新最后更新时间
                )

            # 【新增】更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
            
            msg = f"{signal.symbol} 加仓成功: +{unit_lots} Unit({order_volume}手) @ {avg_price:.2f}, 总持仓:{new_units} Unit"
            print(msg)
            log_trade('execute_add_on_order', msg, symbol=signal.symbol,log_level='SUCCESS')
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
    
    # 【基于ATR计算1个Unit对应的手数】
    unit_lots = calculate_unit_lots(api, signal.symbol)
    
    # 首次开仓固定为1个Unit
    target_units = 1
    order_volume = target_units * unit_lots
    print(f"[INFO] {signal.symbol} 开仓计划: 1个Unit × {unit_lots}手/Unit = {order_volume}手")
    
    # 【跳空保护检查】
    can_trade = price_gap_protection(api, signal.symbol, signal.signal_direction, gap_threshold_percent)
    if not can_trade:
        msg = f"{signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        log_trade('execute_entry_order', msg,signal=signal.symbol, log_level='WARNING')
        signal.executed_status = 'CANCELLED'
        signal.remark = '跳空保护'
        signal.save(update_fields=['executed_status', 'updated_at','remark'])
        return False
    
    # 【新增】检查交易所最小开仓手数限制
    min_position_check = check_min_position_requirement(signal.symbol, order_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        
        msg = f"{signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_entry_order', msg,symbol=signal.symbol, log_level='INFO')
        
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
                    'last_update_time': timezone.now()  # 【修复】手动更新最后更新时间
                }
            )
            
            # 更新信号执行状态为成功
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        
        msg = f"{signal.symbol} 开仓成功（两步开仓）: 1 Unit({two_step_result['actual_filled']}手) @ {two_step_result['avg_price']:.2f}"
        print(msg)
        log_trade('execute_entry_order', msg,symbol=signal.symbol,log_level='SUCCESS')
        return True
    
    else:
        # 正常开仓流程（无需两步开仓）
        target_pos = TargetPosTask(api, signal.symbol)
        try:
            if signal.signal_direction == 1:
                target_lots = order_volume  # 多头：目标持多单order_volume手
            else:
                target_lots = -order_volume  # 空头：目标持空单order_volume手
            msg = f"{signal.symbol} 设置目标持仓: {target_lots} 手 (开仓{target_units} Unit)"
            print(msg)
            log_trade('execute_entry_order', msg,symbol=signal.symbol, log_level='INFO')
            # 设置目标持仓
            target_pos.set_target_volume(target_lots)
        
            # 【重构】调用通用等待函数
            result = wait_for_target_position(
                api=api, 
                target_pos=target_pos, 
                symbol=signal.symbol, 
                target_lots=target_lots, 
                function_name='execute_entry_order'
            )
            
            pos_after = result['pos']
            if not result['success']:
                msg = f"[ERROR] {signal.symbol} 开仓超时或失败"
                print(msg)
                log_error('execute_entry_order', msg)
                signal.executed_status = 'FAILED'
                signal.remark = '开仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
                return False

            # 获取最终成交结果（复用 pos_current，避免重复请求）
            pos_after = result['pos']
            if pos_after is None:
                # 如果 pos_current 依然是 None，说明可能还没收到任何持仓更新，尝试最后获取一次
                pos_after = api.get_position(signal.symbol)

            if pos_after is None:
                msg = f"[ERROR] {signal.symbol} 获取持仓信息失败"
                print(msg)
                log_error('execute_entry_order', msg, account=account, symbol=signal.symbol, signal=signal)
                # 获取失败，更新信号状态为失败
                signal.executed_status = 'FAILED'
                signal.remark = '获取持仓信息失败'
                signal.save(update_fields=['executed_status', 'updated_at','remark'])
            else:
                if signal.signal_direction == 1:
                    entry_avg_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else None
                    actual_filled = pos_after.volume_long_today
                else:
                    entry_avg_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else None
                    actual_filled = pos_after.volume_short_today
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
                                'highest_close': Decimal(str(entry_avg_price)),
                                'lowest_close': Decimal(str(entry_avg_price)),
                                'latest_close_price': Decimal(str(entry_avg_price)),
                                'last_update_time': timezone.now()
                            }
                        )
                        
                        # 【新增】更新信号执行状态为成功
                        signal.executed_status = 'SUCCESS'
                        signal.save(update_fields=['executed_status', 'updated_at'])
                
                msg = f"{signal.symbol} 开仓成功: 1 Unit({actual_filled}手) @ {entry_avg_price:.2f}"
                print(msg)
                log_trade('execute_entry_order', msg,symbol=signal.symbol, log_level='SUCCESS')
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
    total_volume = position.contract_total_position
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, position.symbol)
    try:
        # 设置目标持仓为0（完全平仓）
        msg = f"{position.symbol} 设置目标持仓: 0手 (平仓{total_volume} 手)"
        print(msg)
        log_trade('execute_exit_order', msg,symbol=position.symbol, log_level='INFO')
        target_pos.set_target_volume(0)
        
        # 【重构】调用通用等待函数
        result = wait_for_target_position(
            api=api, 
            target_pos=target_pos, 
            symbol=position.symbol, 
            target_lots=0, 
            function_name='execute_exit_order'
        )
        
        if not result['success']:
            msg = f"[ERROR] {position.symbol} 平仓超时或失败"
            print(msg)
            log_error('execute_exit_order', msg)
            if signal:
                signal.executed_status = 'FAILED'
                signal.remark = '平仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
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
                stop_loss_price=None,
                last_update_time=timezone.now()  # 【修复】手动更新最后更新时间
            )

        if signal:
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])
        msg = f"{position.symbol} 平仓成功"
        print(msg)
        log_trade('execute_exit_order', msg,symbol=position.symbol, log_level='SUCCESS')
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
    
    # ========== 第1阶段：平仓旧合约 ==========
    msg = f"{position.symbol} 开始平仓旧合约..."
    print(msg)
    log_trade('execute_rollover_order', msg,symbol=position.symbol, log_level='INFO')
          
    # 创建目标持仓任务（旧合约）
    target_pos_old = TargetPosTask(api, position.symbol)
    
    try:
        target_pos_old.set_target_volume(0)
        
        # 【重构】调用通用等待函数处理旧合约平仓
        result = wait_for_target_position(
            api=api, 
            target_pos=target_pos_old, 
            symbol=position.symbol, 
            target_lots=0, 
            function_name='execute_rollover_order'
        )
        
        if not result['success']:
            msg = f"[ERROR] {position.symbol} 移仓操作中，平仓旧合约失败"
            print(msg)
            log_error('execute_rollover_order', msg)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

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
    msg = f"{signal.symbol} 开始开仓新合约..."
    print(msg)
    log_trade('execute_rollover_order', msg,symbol=position.symbol, log_level='INFO')
    
    # 【新增】检查交易所最小开仓手数限制
    target_volume = position.contract_total_position
    min_position_check = check_min_position_requirement(signal.symbol, target_volume)
    
    if min_position_check['need_adjustment']:
        # 需要两步开仓策略
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        
        msg = f"{signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_rollover_order', msg,symbol=position.symbol, log_level='INFO')
        
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
        
        msg = f"{signal.symbol} 换月开仓成功（两步开仓）: {actual_filled}手 @ {entry_avg_price:.2f}"
        print(msg)
        log_trade('execute_rollover_order', msg,symbol=signal.symbol,log_level='INFO')
    
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
            
            msg = f"{signal.symbol} 设置目标持仓: {target_lots}手"
            print(msg)
            log_trade('execute_rollover_order', msg,symbol=signal.symbol,log_level='INFO')
            target_pos_new.set_target_volume(target_lots)
            
            # 【重构】调用通用等待函数处理新合约开仓
            result = wait_for_target_position(
                api=api, 
                target_pos=target_pos_new, 
                symbol=signal.symbol, 
                target_lots=target_lots, 
                function_name='execute_rollover_order'
            )
            
            pos_after = result['pos']
            if not result['success']:
                msg = f"[ERROR] {signal.symbol} 移仓操作中，开仓新合约失败"
                print(msg)
                log_error('execute_rollover_order', msg)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False

            if signal.signal_direction == 1:
                entry_avg_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else None
                actual_filled = pos_after.volume_long_today
            else:
                entry_avg_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else None
                actual_filled = pos_after.volume_short_today
            
            msg = f"{signal.symbol} 换月开仓成功: {actual_filled}手 @ {entry_avg_price:.2f}"
            print(msg)
            log_trade('execute_rollover_order', msg,symbol=signal.symbol,log_level='INFO')
            
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
                    
                    msg = f"{signal.symbol} 基于20日历史数据初始化: highest={historical_high:.2f}, lowest={historical_low:.2f}, ATR={atr_value:.2f}"
                    print(msg)
                    log_trade('execute_rollover_order', msg,symbol=signal.symbol, log_level='INFO')
                else:
                    # 数据不足，使用开仓价作为后备方案
                    msg = f"{signal.symbol} 历史数据不足({len(klines) if klines else 0}根)，使用开仓价初始化"
                    print(msg)
                    log_trade('execute_rollover_order', msg,symbol=signal.symbol, log_level='WARNING')
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
                    'highest_close': init_highest_close,
                    'lowest_close': init_lowest_close,
                    'latest_close_price': Decimal(str(entry_avg_price)),
                    'last_update_time': timezone.now(),  # 【修复】手动更新最后更新时间
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
    signals = DailyStrategySignal.objects.filter(config['query_filter']).filter(executed_status = 'PENDING')
    
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
    from django_redis import get_redis_connection
    current_date = datetime.now().date()
    close_old_connections()
    # 获取交易账户
    accounts = TradingAccount.objects.all()
    for account in accounts:
        # api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
        api = TqApi(TqKq(),auth=TqAuth("yupei1986", "yupei1986"))
        # api = TqApi(TqAccount("Y银河期货_CTP七席", "0210003762", "012613"), auth=TqAuth("yupei1986", "yupei1986"))
        
        redis = get_redis_connection('default')
        lock_key = 'lock:open'
        if redis.set(lock_key, 'true', nx=True, ex=600): 
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
                send_open_report(account, current_date)
            except Exception as e:
                print(f"[ERROR] 处理账户 {account.username} 时发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                # 关闭TqApi连接
                redis.delete(lock_key)
                api.close()
        else:
            print(f"[INFO] 账户 {account.username} 正在处理中, 跳过")
            msg = f"账户 {account.username} 正在处理中, 跳过"
            log_trade('job_daily_open_process', msg, symbol=None,log_level='INFO')