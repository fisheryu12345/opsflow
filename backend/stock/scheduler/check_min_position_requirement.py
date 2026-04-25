from stock.utils.log_util import log_trade,log_error
import time
from tqsdk import  TargetPosTask
from stock.parameter_config import TIMEOUT_SECONDS


def check_min_position_requirement(symbol, planned_volume):
    """
    检查交易所最小开仓手数限制，并返回是否需要两步开仓策略
    
    【功能说明】
    当策略计划开仓手数小于交易所规定的该合约最小开仓手数（min_position）时，
    为确保合规并达到目标持仓，应采用"两步开仓法"：
    1. 第一步：先开立等于最小开仓手数（min_position）的仓位
    2. 第二步：立即平仓多余部分，数量为 min_position - 计划开仓手数
    3. 结果：最终持仓等于原计划开仓手数，同时符合交易所规则
    
    【适用场景】
    - 首次开仓（execute_entry_order）
    - 加仓操作（execute_addon_order）
    - 移仓换月的新合约开仓（execute_rollover_order Phase 2）
    
    :param symbol: 合约代码（如 "SHFE.rb2610"）
    :param planned_volume: 计划开仓手数（正整数）
    :return: dict {
        'need_adjustment': bool,          # 是否需要两步开仓调整
        'min_position': int,              # 交易所最小开仓手数
        'original_volume': int,           # 原始计划开仓手数
        'adjusted_volume': int,           # 调整后第一步需要开的手数
        'excess_to_close': int            # 第二步需要平仓的多余手数
    }
    """
    result = {
        'need_adjustment': False,
        'min_position': planned_volume,
        'original_volume': planned_volume,
        'adjusted_volume': planned_volume,
        'excess_to_close': 0
    }
    
    try:
        from stock.models import FullContractList
        # 提取品种代码（如 "SHFE.rb2610" -> "rb"）
        product_code = symbol.split('.')[-1][:2] if '.' in symbol else symbol[:2]
        
        contract_info = FullContractList.objects.filter(
            product_code=product_code,
            is_active=True
        ).first()
        
        if contract_info and contract_info.min_position > 1:
            min_pos = contract_info.min_position
            result['min_position'] = min_pos
            
            if planned_volume < min_pos:
                print(f"[INFO] {symbol} 检测到最小开仓限制: {min_pos}手")
                print(f"[WARN] {symbol} 计划开仓{planned_volume}手 < 最小限制{min_pos}手，将采用两步开仓策略")
                print(f"[INFO] 第1步：先开{min_pos}手满足交易所要求")
                print(f"[INFO] 第2步：再平{min_pos - planned_volume}手达到目标{planned_volume}手")
                
                result['need_adjustment'] = True
                result['original_volume'] = planned_volume
                result['adjusted_volume'] = min_pos
                result['excess_to_close'] = min_pos - planned_volume
            else:
                print(f"[INFO] {symbol} 计划开仓{planned_volume}手 >= 最小限制{min_pos}手，直接开仓")
        else:
            print(f"[INFO] {symbol} 无最小开仓限制或限制为1手，直接开仓")
            
    except Exception as e:
        print(f"[WARN] {symbol} 检查最小开仓限制失败: {str(e)}，继续正常开仓流程")
        import traceback
        traceback.print_exc()
    
    return result


def execute_two_step_opening(api, symbol, direction, adjusted_volume, excess_to_close, target_volume, function_name, account=None, signal=None):
    """
    执行两步开仓策略（应对交易所最小开仓限制）
    
    【功能说明】
    当计划开仓手数小于交易所规定的最小开仓手数时，采用两步开仓法：
    1. 第一步：开立等于最小开仓手数的仓位
    2. 第二步：立即平仓多余部分，达到目标持仓
    
    :param api: TqApi实例
    :param symbol: 合约代码
    :param direction: 持仓方向 (1:多头, -1:空头)
    :param adjusted_volume: 第一步需要开立的手数（等于min_position）
    :param excess_to_close: 第二步需要平仓的多余手数
    :param target_volume: 最终目标持仓手数
    :param function_name: 调用函数名称（用于日志记录）
    :param account: TradingAccount实例（可选，用于日志关联）
    :param signal: DailyStrategySignal实例（可选，用于日志关联和状态更新）
    :return: dict {
        'success': bool,              # 是否成功
        'actual_filled': int,         # 实际成交手数
        'avg_price': float or None    # 成交价格
    }
    """
    result = {
        'success': False,
        'actual_filled': 0,
        'avg_price': None
    }
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, symbol)
    
    try:
        # ========== 第1步：开立等于最小开仓手数的仓位 ==========
        if direction == 1:
            step1_target = adjusted_volume  # 多头
        else:
            step1_target = -adjusted_volume  # 空头
        
        msg = f"{symbol} 第1步：设置目标持仓 {step1_target}手 (最小开仓{adjusted_volume}手)"
        print(msg)
        log_trade(function_name, msg,symbol=symbol,log_level='INFO')
        
        target_pos.set_target_volume(step1_target)
        # 等待第1步成交
        start_time = time.time()
        step1_completed = False
        while time.time() - start_time < TIMEOUT_SECONDS:
            api.wait_update(deadline=time.time() + 1)
            if target_pos.is_finished():
                msg = f"{symbol} 第1步完成: 已开{step1_target}手"
                print(msg)
                log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
                step1_completed = True
                break
        if not step1_completed:
            msg = f"[ERROR] {symbol} 第1步开仓超时或失败"
            print(msg)
            log_error(function_name, msg)
            return result
        
        # ========== 第2步：立即平仓多余部分 ==========
        if direction == 1:
            step2_target = adjusted_volume - excess_to_close
        else:
            step2_target = -(adjusted_volume - excess_to_close)
        
        msg = f"{symbol} 第2步：平仓{excess_to_close}手，目标持仓 {step2_target}手"
        print(msg)
        log_trade(function_name, msg,symbol=symbol,log_level='INFO')
        
        target_pos.set_target_volume(step2_target)
        
        # 等待第2步成交
        start_time = time.time()
        step2_completed = False
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            api.wait_update(deadline=time.time() + 1)
            if target_pos.is_finished():
                msg = f"{symbol} 第2步完成: 最终持仓{step2_target}手"
                print(msg)
                log_trade(function_name, msg,symbol=symbol,log_level='SUCCESS')
                step2_completed = True
                break
        if not step2_completed:
            msg = f"[ERROR] {symbol} 第2步平仓超时或失败"
            print(msg)
            log_error(function_name, msg)
            return result
        
        # 获取最终成交结果
        pos_after = api.get_position(symbol)
        if pos_after is None:
            msg = f"[ERROR] {symbol} 无法获取持仓信息"
            print(msg)
            log_error(function_name, msg)
            return result
        
        # 获取成交价格,简化处理
        quote = api.get_quote(symbol)
        avg_price = float(quote.last_price) if quote and quote.last_price else None
        
        # # 验证实际成交手数
        if direction == 1:
            actual_final_filled = pos_after.volume_long
        else:
            actual_final_filled = pos_after.volume_short     
        # 成功返回
        result['success'] = True
        result['actual_filled'] = actual_final_filled
        result['avg_price'] = avg_price
        
        msg = f"两步开仓成功: {actual_final_filled}手 @ {avg_price:.2f}"
        print(msg)
        log_trade(function_name, msg,symbol=symbol,log_level='SUCCESS')
        return result
        
    except Exception as e:
        msg = f"[ERROR] {symbol} 两步开仓失败: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        log_error(function_name, f"{msg}\n{traceback.format_exc()}")
        return result
    finally:
        try:
            del target_pos
        except:
            pass