"""
Position sizing — Turtle system Unit-to-contract conversion.
"""
import traceback
from stock.core.config_loader import get_config


def calculate_unit_lots(api, symbol, atr=None):
    """
    计算1个海龟Unit对应的实际手数

    计算公式：1个Unit的手数 = POSITION_RISK_BASE_AMOUNT / (ATR × POSITION_RISK_MULTIPLIER × 合约乘数)

    :param api: TqApi实例
    :param symbol: 合约代码（如 "SHFE.rb2610"）
    :param atr: 预计算的ATR值（避免重复计算），为None时内部计算
    :return: 1个Unit对应的实际手数（整数）
    """
    try:
        contract = api.get_quote(symbol)
        if not contract or not contract.volume_multiple:
            return 1

        volume_multiple = contract.volume_multiple

        if atr is None:
            from stock.core.atr import calculate_atr
            atr_20 = calculate_atr(api, symbol, period=20)
        else:
            atr_20 = atr

        if atr_20 is None or atr_20 <= 0:
            return 1

        unit_lots = get_config('POSITION_RISK_BASE_AMOUNT') / (atr_20 * get_config('POSITION_RISK_MULTIPLIER') * volume_multiple)
        unit_lots = round(unit_lots)
        unit_lots = max(1, unit_lots)

        return unit_lots

    except Exception as e:
        return 1
