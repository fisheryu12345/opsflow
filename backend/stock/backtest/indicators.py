"""
Pure pandas indicator computations for backtesting.
No TqApi dependency — operates on local DataFrames.
"""
import pandas as pd
import numpy as np
from typing import Optional


def calculate_atr(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Average True Range (SMA method).

    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: ATR period (default 20)

    Returns:
        Series of ATR values, aligned with input index.
        First (period-1) values are NaN.
    """
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]),
                               np.abs(low[1:] - close[:-1])))

    atr_values = np.full(len(df), np.nan)
    for i in range(period - 1, len(tr)):
        atr_values[i + 1] = np.mean(tr[i - period + 1:i + 1])

    return pd.Series(atr_values, index=df.index)


def calculate_ma(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Simple Moving Average of close prices."""
    return df['close'].rolling(window=period, min_periods=period).mean()


def calculate_donchian(df: pd.DataFrame, period: int = 20) -> tuple[pd.Series, pd.Series]:
    """Calculate Donchian channel.

    Uses shifted values to avoid lookahead bias:
    - entry_high = max(high[-period-1:-1])  — highest high of prior period bars
    - entry_low  = min(low[-period-1:-1])   — lowest low of prior period bars

    Returns:
        (upper_entry, lower_entry) Series aligned with input.
        Each value at position i uses data up to i-1 (shifted by 1).
    """
    # Shift by 1 to avoid lookahead, then rolling
    entry_high = df['high'].shift(1).rolling(window=period, min_periods=period).max()
    entry_low = df['low'].shift(1).rolling(window=period, min_periods=period).min()
    return entry_high, entry_low


def compute_trend_factor(
    ma_10: float,
    ma_20: float,
    ma_40: float,
    atr: float = None,
    gap_atr_limit: float = 2.0,
    trend_factor_max: float = 0.5,
) -> tuple[float, str]:
    """Compute trend factor and label from MA alignment with ATR normalization.

    Same logic as core/indicators.py calculate_indicators().
    atr 不可用时返回 (0.0, 'choppy').

    Args:
        ma_10: 10-period MA value
        ma_20: 20-period MA value
        ma_40: 40-period MA value
        atr: ATR value (必须)
        gap_atr_limit: ATR-based gap threshold (默认2.0 = 2倍ATR)
        trend_factor_max: Maximum factor value (default 0.5)

    Returns:
        (trend_factor, trend_label)
        factor is [0.0, trend_factor_max], label is one of:
        'strong_bull', 'strong_bear', 'weak_bull', 'weak_bear', 'choppy'
    """
    if not all([ma_10, ma_20, ma_40]):
        return 0.0, 'choppy'

    is_bull = ma_10 > ma_20 > ma_40
    is_bear = ma_10 < ma_20 < ma_40

    if not (is_bull or is_bear) or not (atr and atr > 0):
        return 0.0, 'choppy'

    gap_10_20 = abs(ma_10 - ma_20) / atr
    gap_20_40 = abs(ma_20 - ma_40) / atr
    max_gap = max(gap_10_20, gap_20_40)

    trend_strength = min(max_gap / gap_atr_limit, 1.0)
    trend_factor = round(trend_strength * trend_factor_max, 3)

    LABEL_STRONG = 0.80
    LABEL_WEAK = 0.30

    if trend_strength >= LABEL_STRONG:
        trend_label = 'strong_bull' if is_bull else 'strong_bear'
    elif trend_strength >= LABEL_WEAK:
        trend_label = 'weak_bull' if is_bull else 'weak_bear'
    else:
        trend_label = 'choppy'

    return trend_factor, trend_label


def check_gap_protection(
    open_price: float,
    prev_close: float,
    atr: float,
    threshold: float = 1.5,
) -> bool:
    """Check if price gap at open is within safe range.

    Args:
        open_price: Today's open
        prev_close: Yesterday's close
        atr: Current ATR value
        threshold: Max allowed gap as multiple of ATR

    Returns:
        True if gap is safe (<= threshold), False if protection triggered
    """
    if atr <= 0:
        return False
    gap_ratio = abs(open_price - prev_close) / atr
    return gap_ratio <= threshold


def compute_unit_lots(
    atr: float,
    risk_base: float,
    multiplier: int,
    volume_multiple: int,
) -> int:
    """Compute how many lots per Unit (Turtle position sizing).

    Formula: round(risk_base / (atr * multiplier * volume_multiple)), min 1.

    Args:
        atr: Current ATR value
        risk_base: Base risk amount per unit
        multiplier: Risk multiplier
        volume_multiple: Contract volume multiple

    Returns:
        Number of lots per Unit (minimum 1)
    """
    if atr <= 0:
        return 1
    unit_lots = risk_base / (atr * multiplier * volume_multiple)
    unit_lots = round(unit_lots)
    return max(1, unit_lots)


def compute_add_on_units(
    direction: int,
    current_units: int,
    latest_close: float,
    last_add_price: float,
    first_open_price: float,
    atr: float,
    max_units: int = 3,
) -> int:
    """Compute how many units to add (Turtle pyramiding logic).

    Mirrors check_add_position_signals() in tasks_daily_close.py.

    Args:
        direction: 1=long, -1=short
        current_units: Current position units (1 or 2)
        latest_close: Current close price
        last_add_price: Price of last add
        first_open_price: Price of first unit entry
        atr: Current ATR value
        max_units: Maximum allowed units

    Returns:
        Number of units to add (0 if no add-on triggered)
    """
    if current_units <= 0 or current_units >= max_units:
        return 0

    add_units = 0

    if current_units == 1:
        price_diff = latest_close - last_add_price if direction == 1 else last_add_price - latest_close

        if price_diff > 1.0 * atr:
            add_units = 2  # jump straight to full
        elif price_diff > 0.5 * atr:
            add_units = 1

    elif current_units == 2:
        if direction == 1:
            price_diff = latest_close - first_open_price
        else:
            price_diff = first_open_price - latest_close

        if price_diff > 1.0 * atr:
            add_units = 1

    # Safety: don't exceed max_units
    if current_units + add_units > max_units:
        add_units = max_units - current_units

    return add_units
