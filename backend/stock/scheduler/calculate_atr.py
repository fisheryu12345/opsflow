from stock.utils.log_util import log_trade
def calculate_atr(api, symbol, period=20):
    """
    计算指定周期的ATR（平均真实波幅）
    
    :param api: TqApi实例
    :param symbol: 合约代码（如 "SHFE.rb2610"）
    :param period: ATR周期，默认20日
    :return: ATR值（float），失败返回None
    """
    try:
        # 获取K线数据（需要period+1根K线来计算period个TR值）
        klines = api.get_kline_serial(symbol, duration_seconds=86400, data_length=period + 5)
        
        if klines is None or len(klines) < period + 1:
            return None
        
        # 提取价格序列
        high = klines['high']
        low = klines['low']
        close = klines['close']
        
        # 计算TR（真实波幅）
        tr_list = []
        for i in range(1, len(klines)):
            hl = high.iloc[i] - low.iloc[i]
            hpc = abs(high.iloc[i] - close.iloc[i-1])
            lpc = abs(low.iloc[i] - close.iloc[i-1])
            tr = max(hl, hpc, lpc)
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None
        
        # 计算ATR（取最近period个TR的平均值）
        atr = sum(tr_list[-period:]) / period
        
        return float(atr) if atr > 0 else None
        
    except Exception as e:
        print(f"[WARN] 计算{symbol}的ATR失败: {str(e)}")
        return None
    
def price_gap_protection(api, symbol, direction, gap_threshold_percent=1.5):
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
            msg = f"存在危险跳空，请勿进行交易！合约：{symbol}，最新价：{latest_price:.2f}，昨日收盘价：{pre_close:.2f}，跳空幅度：{gap_percent:.2f}%"
            print(msg)
            log_trade('execute_entry_order', msg,symbol=symbol, log_level='WARNING')
            return False  # 向上跳空过大，禁止做多
        else:
            return True  # 可以正常做多
    elif direction == -1:
        # 做空：警惕向下跳空超过阈值（追空风险）
        if gap_percent < -gap_threshold_percent:
            msg = f"[WARN]存在危险跳空，请勿进行交易！合约：{symbol}，最新价：{latest_price:.2f}，昨日收盘价：{pre_close:.2f}，跳空幅度：{gap_percent:.2f}%"
            print(msg)
            log_trade('execute_entry_order', msg,symbol=symbol, log_level='WARNING')
            return False  # 向下跳空过大，禁止做空
        else:
            return True  # 可以正常做空
    else:
        return False  # 无效的交易方向