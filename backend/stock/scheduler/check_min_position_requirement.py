
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