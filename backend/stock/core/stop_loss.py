"""
Stop-loss computation — pure functions for dynamic stop-loss and break-even protection.
"""
from decimal import Decimal
from typing import Optional


def compute_stop_loss(
    direction: int,
    highest_close: Optional[Decimal],
    lowest_close: Optional[Decimal],
    atr_value: Decimal,
    factor: Decimal,
    tick: Decimal,
) -> Optional[Decimal]:
    """
    计算动态止损价。

    多头止损 = highest_close - 2*(1+factor)*ATR，并按 tick 向下取整
    空头止损 = lowest_close + 2*(1+factor)*ATR，并按 tick 向上取整

    :returns 止损价（Decimal），如果数据不足返回 None
    """
    stop_distance = Decimal('2') * (Decimal('1') + factor) * atr_value

    if direction == 1:
        if highest_close is None:
            return None
        raw_stop = highest_close - stop_distance
        # 按 tick 向下取整
        stop_loss = (raw_stop / tick).quantize(Decimal('1'), rounding='ROUND_FLOOR') * tick
    elif direction == -1:
        if lowest_close is None:
            return None
        raw_stop = lowest_close + stop_distance
        # 按 tick 向上取整
        stop_loss = (raw_stop / tick).quantize(Decimal('1'), rounding='ROUND_CEILING') * tick
    else:
        return None

    return stop_loss


def check_protect_cost_condition(
    direction: int,
    latest_close_price: Optional[Decimal],
    cost_price: Optional[Decimal],
    atr_value: Decimal,
    protect_cost_enabled: bool,
    protect_cost_ratio: float,
) -> tuple:
    """
    检查保本条件是否满足。

    :returns (protect_cost_enabled, protect_price)
        protect_cost_enabled: 是否启用保本
        protect_price: 保本价（启用后才有意义）
    """
    protect_price = None
    if cost_price:
        if direction == 1:
            protect_price = cost_price
        elif direction == -1:
            protect_price = cost_price

    # 仅在未启用且数据齐全时判断是否应启用
    if not protect_cost_enabled and cost_price and latest_close_price is not None:
        if direction == 1:
            profit_diff = latest_close_price - cost_price
            if profit_diff > Decimal(str(protect_cost_ratio)) * atr_value:
                protect_cost_enabled = True
        elif direction == -1:
            profit_diff = cost_price - latest_close_price
            if profit_diff > Decimal(str(protect_cost_ratio)) * atr_value:
                protect_cost_enabled = True

    return protect_cost_enabled, protect_price


def apply_protect_price(dynamic_stop_loss: Decimal, protect_price: Optional[Decimal], direction: int) -> Decimal:
    """
    保本兜底：确保止损价不劣于保本价。
    """
    if protect_price is None:
        return dynamic_stop_loss

    if direction == 1 and dynamic_stop_loss < protect_price:
        return protect_price
    elif direction == -1 and dynamic_stop_loss > protect_price:
        return protect_price

    return dynamic_stop_loss
