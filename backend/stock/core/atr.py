"""
ATR computation and price gap protection — pure domain logic.
"""
import traceback
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


def price_gap_protection(api, symbol, direction, gap_threshold_atr_multiplier=1.5):
    """
    价格跳空保护函数（支持期货多空双向交易）

    逻辑区分多空方向：
    - 多头入场 (direction=1)：仅跳空高开（最新价 >> 前收盘）危险 — 买入价过高
    - 空头入场 (direction=-1)：仅跳空低开（最新价 << 前收盘）危险 — 卖出价过低
    反向跳空（多头遇到低开、空头遇到高开）视为有利，不拦截。

    :param api: TqApi实例
    :param symbol: 合约代码
    :param direction: 交易方向，1表示做多，-1表示做空
    :param gap_threshold_atr_multiplier: 跳空阈值（ATR倍数），默认1.5倍ATR（与GAP_PROTECTION_RATIO一致）
    :return: True表示可以交易（无危险跳空），False表示存在危险跳空应禁止交易
    """
    atr = calculate_atr(api, symbol)
    quote = api.get_quote(symbol)
    latest_price = quote.last_price
    pre_close = quote.pre_close

    if latest_price is None or pre_close is None or pre_close == 0:
        return False
    if atr is None or atr <= 0:
        return False

    if direction == 1:
        # 多头：检查跳空高开（最新价显著高于前收盘）
        gap_up = (latest_price - pre_close) / atr
        if gap_up > gap_threshold_atr_multiplier:
            log_trade('execute_entry_order',
                      f"[跳空保护] 多头开仓被拦截：{symbol} 跳空高开 {gap_up:.2f}倍ATR"
                      f"（最新价={latest_price:.2f}, 前收盘={pre_close:.2f}），"
                      f"阈值={gap_threshold_atr_multiplier}倍ATR",
                      symbol=symbol, log_level='WARNING')
            return False
        return True
    elif direction == -1:
        # 空头：检查跳空低开（最新价显著低于前收盘）
        gap_down = (pre_close - latest_price) / atr
        if gap_down > gap_threshold_atr_multiplier:
            log_trade('execute_entry_order',
                      f"[跳空保护] 空头开仓被拦截：{symbol} 跳空低开 {gap_down:.2f}倍ATR"
                      f"（最新价={latest_price:.2f}, 前收盘={pre_close:.2f}），"
                      f"阈值={gap_threshold_atr_multiplier}倍ATR",
                      symbol=symbol, log_level='WARNING')
            return False
        return True
    else:
        return False
