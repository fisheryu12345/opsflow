from stock.parameter_config import POSITION_RISK_BASE_AMOUNT, POSITION_RISK_MULTIPLIER

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
        contract = api.get_quote(symbol)
        if not contract or not contract.volume_multiple:
            print(123123)
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
        unit_lots = POSITION_RISK_BASE_AMOUNT / (atr_20 * POSITION_RISK_MULTIPLIER * contracts_per_unit)
        
        # 向下取整，确保风险可控
        unit_lots = int(unit_lots)
        
        # 至少1手
        unit_lots = max(1, unit_lots)
        
        return unit_lots
        
    except Exception as e:
        return 1