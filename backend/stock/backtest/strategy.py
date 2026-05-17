"""
Strategy logic for backtesting — mirrors live system's close/open cycle.

close_step:  after market close → generate signals (STOP_LOSS, ENTRY, ADD_ON, ROLLOVER)
open_step:   at market open → execute pending signals in priority order
"""
import pandas as pd
from typing import Optional
from dataclasses import dataclass, field
from decimal import Decimal

from stock.backtest.indicators import (
    calculate_atr, calculate_ma, calculate_donchian,
    compute_trend_factor, check_gap_protection,
    compute_unit_lots, compute_add_on_units,
)
from stock.backtest.broker import BacktestAccount, PositionState
from stock.backtest.config import BacktestConfig


# ── Signal model ──

@dataclass
class Signal:
    type: str          # ENTRY, STOP_LOSS, ADD_ON, ROLLOVER
    direction: int     # 1=long, -1=short
    volume: int        # lots to trade
    units: int         # units involved
    price_ref: float   # reference price (close that triggered)
    symbol: str        # contract code (for rollover target)
    remark: str = ''


# ── Helpers ──

def _compute_stop(direction: int, highest: Optional[float], lowest: Optional[float],
                  atr: float, factor: float, tick: float) -> Optional[float]:
    """Compute dynamic stop loss price (mirrors core.stop_loss.compute_stop_loss)."""
    stop_distance = 2.0 * (1.0 + factor) * atr

    if direction == 1:
        if highest is None:
            return None
        raw = highest - stop_distance
        # Round down to tick
        return round(raw // tick * tick, 2)
    elif direction == -1:
        if lowest is None:
            return None
        raw = lowest + stop_distance
        # Round up to tick
        return round((raw // tick + (1 if raw % tick > 1e-10 else 0)) * tick, 2)
    return None


def _check_protect(direction: int, close: float, cost: float, atr: float,
                   ratio: float, tick: float) -> tuple[bool, Optional[float]]:
    """Check if protect-cost should activate (mirrors core.stop_loss.check_protect_cost_condition)."""
    if direction == 1:
        profit = close - cost
        protect_price = cost + 2 * tick  # 2 ticks above cost
    else:
        profit = cost - close
        protect_price = cost - 2 * tick  # 2 ticks below cost

    if profit > ratio * atr:
        return True, protect_price
    return False, None


# ── Close step ──

def run_close_step(
    position: PositionState,
    today_row,
    klines_window,
    config: BacktestConfig,
    is_rollover_date: bool = False,
    active_contract: str = '',
    rollover_gap: float = 0.0,
) -> list[Signal]:
    """Execute the close-of-day logic.

    Returns a list of Signal objects to be executed at next day's open.
    Max one signal per type (priority: STOP_LOSS > ENTRY > ROLLOVER > ADD_ON).

    Args:
        rollover_gap: 主力连续合约跳空幅度。非零时跳过止损检测，
                      避免移仓换月虚假跳空触发止损。
    """
    signals: list[Signal] = []
    today_close = float(today_row['close'])

    # ── 1. Compute indicators ──
    atr_series = calculate_atr(klines_window, config.atr_period)
    ma_10_series = calculate_ma(klines_window, 10)
    ma_20_series = calculate_ma(klines_window, 20)
    ma_40_series = calculate_ma(klines_window, 40)
    donchian_high, donchian_low = calculate_donchian(klines_window, config.entry_period)

    atr_val = float(atr_series.iloc[-1]) if pd.notna(atr_series.iloc[-1]) else 0.0
    ma_10 = float(ma_10_series.iloc[-1]) if pd.notna(ma_10_series.iloc[-1]) else 0.0
    ma_20 = float(ma_20_series.iloc[-1]) if pd.notna(ma_20_series.iloc[-1]) else 0.0
    ma_40 = float(ma_40_series.iloc[-1]) if pd.notna(ma_40_series.iloc[-1]) else 0.0

    trend_factor, trend_label = compute_trend_factor(
        ma_10, ma_20, ma_40,
        atr=atr_val,
        gap_atr_limit=config.gap_atr_limit,
        trend_factor_max=config.trend_factor_max,
    )

    # Save latest indicators to position
    position.atr_value = atr_val
    position.trend_factor = trend_factor
    position.trend_label = trend_label

    if atr_val <= 0:
        return signals  # not enough data

    # ── 2. If position is open ──
    if position.is_open:
        # 2a. Update trailing high/low
        if position.direction == 1:
            if position.highest_close is None or today_close > position.highest_close:
                position.highest_close = today_close
        elif position.direction == -1:
            if position.lowest_close is None or today_close < position.lowest_close:
                position.lowest_close = today_close

        position.latest_close_price = today_close

        # 2b. Compute dynamic stop loss
        stop_loss = _compute_stop(
            position.direction,
            position.highest_close,
            position.lowest_close,
            atr_val,
            trend_factor,
            config.price_tick,
        )

        # 2c. Check protect-cost condition
        if position.cost_price is not None:
            protect_enabled, protect_price = _check_protect(
                position.direction, today_close, position.cost_price,
                atr_val, config.protect_cost_ratio, config.price_tick,
            )
            if protect_enabled:
                position.protect_cost_enabled = True
                # Apply protect: stop loss should not be worse than protect price
                if stop_loss is not None and protect_price is not None:
                    if position.direction == 1:
                        stop_loss = max(stop_loss, protect_price)
                    else:
                        stop_loss = min(stop_loss, protect_price)

        position.stop_loss_price = stop_loss

        # 2d. STOP_LOSS: check if stop triggered (跳过移仓跳空日)
        if stop_loss is not None and rollover_gap == 0:
            triggered = False
            if position.direction == 1 and today_close <= stop_loss:
                triggered = True
            elif position.direction == -1 and today_close >= stop_loss:
                triggered = True

            if triggered:
                signals.append(Signal(
                    type='STOP_LOSS',
                    direction=position.direction,
                    volume=position.contract_target_number,
                    units=position.units,
                    price_ref=today_close,
                    symbol=position.symbol,
                    remark=f'止损触发 close={today_close} stop={stop_loss}',
                ))
                return signals  # STOP_LOSS has highest priority

        # 2e. ADD_ON: check pyramiding add
        if position.units < config.max_units and position.cost_price is not None:
            add_units = compute_add_on_units(
                direction=position.direction,
                current_units=position.units,
                latest_close=today_close,
                last_add_price=position.last_add_price,
                first_open_price=position.first_open_price,
                atr=atr_val,
                max_units=config.max_units,
            )
            if add_units > 0:
                # Calculate volume for add-on
                unit_lots = compute_unit_lots(
                    atr_val, config.risk_base_amount,
                    config.risk_multiplier, config.volume_multiple,
                )
                add_volume = add_units * unit_lots
                signals.append(Signal(
                    type='ADD_ON',
                    direction=position.direction,
                    volume=add_volume,
                    units=add_units,
                    price_ref=today_close,
                    symbol=position.symbol,
                    remark=f'加仓 {add_units}U@{today_close} trend={trend_label}',
                ))

        # 2f. ROLLOVER
        if is_rollover_date and active_contract and active_contract != position.active_contract:
            signals.append(Signal(
                type='ROLLOVER',
                direction=position.direction,
                volume=position.contract_target_number,
                units=position.units,
                price_ref=today_close,
                symbol=active_contract,
                remark=f'移仓 {position.active_contract}->{active_contract}',
            ))

    # ── 3. If flat — check ENTRY (breakout + MA filter) ──
    else:
        entry_high = float(donchian_high.iloc[-1]) if pd.notna(donchian_high.iloc[-1]) else 0.0
        entry_low = float(donchian_low.iloc[-1]) if pd.notna(donchian_low.iloc[-1]) else 0.0

        is_bull_breakout = entry_high > 0 and today_close > entry_high
        is_bear_breakout = entry_low > 0 and today_close < entry_low

        if is_bull_breakout or is_bear_breakout:
            # MA filter: trend must not be 'choppy'
            direction = 1 if is_bull_breakout else -1

            if trend_label not in ('choppy',):
                # Also check alignment: bull breakout needs bull trend, bear breakout needs bear trend
                trend_is_aligned = (
                    (direction == 1 and 'bull' in trend_label) or
                    (direction == -1 and 'bear' in trend_label)
                )

                if trend_is_aligned:
                    unit_lots = compute_unit_lots(
                        atr_val, config.risk_base_amount,
                        config.risk_multiplier, config.volume_multiple,
                    )
                    entry_volume = 1 * unit_lots  # 1st unit
                    signals.append(Signal(
                        type='ENTRY',
                        direction=direction,
                        volume=entry_volume,
                        units=1,
                        price_ref=today_close,
                        symbol=active_contract or '',
                        remark=f'突破开仓 {"LONG" if direction==1 else "SHORT"} '
                               f'close={today_close} upper={entry_high} lower={entry_low} '
                               f'trend={trend_label} factor={trend_factor}',
                    ))

    return signals


# ── Open step ──

def execute_signals_at_open(
    account: BacktestAccount,
    signals: list[Signal],
    today_row,
    prev_close: float,
    config: BacktestConfig,
) -> list:
    """Execute pending signals at market open.

    Priority order: STOP_LOSS → ENTRY → ROLLOVER → ADD_ON

    Args:
        account: BacktestAccount instance
        signals: List of Signal objects from run_close_step
        today_row: Today's K-line (open/high/low/close)
        prev_close: Yesterday's close price
        config: BacktestConfig

    Returns:
        List of executed TradeRecord objects
    """
    open_price = float(today_row['open'])
    date = str(today_row['datetime'])[:10]
    executed_trades = []

    # Sort: STOP_LOSS first, then ENTRY, ROLLOVER, ADD_ON
    priority = {'STOP_LOSS': 0, 'ENTRY': 1, 'ROLLOVER': 2, 'ADD_ON': 3}
    signals_sorted = sorted(signals, key=lambda s: priority.get(s.type, 99))

    for signal in signals_sorted:
        if signal.type == 'STOP_LOSS':
            if account.position.is_open:
                trade = account.execute_exit(open_price, date, trade_type='STOP_LOSS')
                if trade:
                    executed_trades.append(trade)

        elif signal.type == 'ENTRY':
            if account.position.is_open:
                continue  # already have position

            # Gap protection
            atr = account.position.atr_value or 0.0
            if atr > 0 and not check_gap_protection(
                open_price, prev_close, atr, config.gap_protection_ratio,
            ):
                print(f"  [GAP] 跳空保护: open={open_price} prev_close={prev_close} "
                      f"atr={atr:.2f}, 跳过开仓")
                continue

            # Slippage
            if signal.direction == 1:
                fill_price = open_price + config.slippage * config.price_tick
            else:
                fill_price = open_price - config.slippage * config.price_tick
            fill_price = max(fill_price, config.price_tick)

            trade = account.execute_entry(
                direction=signal.direction,
                price=fill_price,
                volume=signal.volume,
                units=signal.units,
                date=date,
                symbol=signal.symbol,
            )
            if trade:
                executed_trades.append(trade)

        elif signal.type == 'ROLLOVER':
            if not account.position.is_open:
                continue
            if signal.symbol == account.position.active_contract:
                continue  # already on this contract

            # Rollover: close at open, open at same open
            close_price = open_price
            new_open_price = open_price
            # Slippage on both legs
            close_price -= config.slippage * config.price_tick
            new_open_price += config.slippage * config.price_tick

            try:
                exit_trade, entry_trade = account.execute_rollover(
                    new_symbol=signal.symbol,
                    close_price=close_price,
                    open_price=new_open_price,
                    volume=signal.volume,
                    date=date,
                )
                executed_trades.append(exit_trade)
                executed_trades.append(entry_trade)
            except ValueError:
                pass

        elif signal.type == 'ADD_ON':
            if not account.position.is_open:
                continue
            if signal.direction != account.position.direction:
                continue

            # Slippage
            if signal.direction == 1:
                fill_price = open_price + config.slippage * config.price_tick
            else:
                fill_price = open_price - config.slippage * config.price_tick
            fill_price = max(fill_price, config.price_tick)

            # Re-check add-on condition at open price
            if account.position.units >= config.max_units:
                continue

            trade = account.execute_add_on(
                price=fill_price,
                volume=signal.volume,
                add_units=signal.units,
                date=date,
            )
            if trade:
                executed_trades.append(trade)

    return executed_trades
