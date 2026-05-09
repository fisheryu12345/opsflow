"""
In-memory account and position tracking for backtesting.
No Django/ORM dependency — pure dataclasses.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PositionState:
    """Tracks a single open position."""
    direction: int = 0              # 1=long, -1=short, 0=flat
    units: int = 0                  # current units (0-3)
    contract_target_number: int = 0  # total lots held

    # Price tracking
    cost_price: Optional[float] = None        # weighted average entry price
    last_add_price: Optional[float] = None     # last unit's entry price
    first_open_price: Optional[float] = None   # first unit entry price
    latest_close_price: Optional[float] = None

    # Stop loss
    stop_loss_price: Optional[float] = None
    protect_cost_enabled: bool = False

    # Trailing high/low (from position open date)
    highest_close: Optional[float] = None
    lowest_close: Optional[float] = None

    # Indicators snapshot
    atr_value: Optional[float] = None
    trend_factor: float = 0.0
    trend_label: str = 'choppy'

    # Contract identity
    symbol: str = ''
    active_contract: str = ''

    @property
    def is_open(self) -> bool:
        return self.units > 0 and self.direction != 0


@dataclass
class TradeRecord:
    """A single executed trade."""
    date: str                # trade date
    symbol: str              # contract code
    trade_type: str          # ENTRY, EXIT, ADD_ON, ROLLOVER_EXIT, ROLLOVER_ENTRY
    direction: int           # 1=long, -1=short
    volume: int              # lots traded
    price: float             # execution price
    pnl: float = 0.0         # realized PnL (0 for entry)
    units_before: int = 0
    units_after: int = 0
    remark: str = ''

    def to_dict(self) -> dict:
        return {
            'date': self.date,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'direction': 'LONG' if self.direction == 1 else 'SHORT',
            'volume': self.volume,
            'price': round(self.price, 2),
            'pnl': round(self.pnl, 2),
            'units_before': self.units_before,
            'units_after': self.units_after,
            'remark': self.remark,
        }


@dataclass
class EquitySnapshot:
    """Daily equity snapshot."""
    date: str
    total_equity: float
    cash: float
    unrealized_pnl: float
    position_lots: int = 0
    position_direction: int = 0
    close_price: float = 0.0


class BacktestAccount:
    """In-memory trading account for futures backtesting.

    Cash tracks realized PnL only (futures margin is not deducted).
    Total equity = cash + unrealized PnL of open positions.
    """

    def __init__(self, initial_capital: float, volume_multiple: int, price_tick: float):
        self.initial_capital = initial_capital
        self.volume_multiple = volume_multiple
        self.price_tick = price_tick

        # Cash = initial capital + all realized PnL (never debited for margin)
        self.cash = initial_capital

        self.position = PositionState()
        self.trades: list[TradeRecord] = []
        self.equity_curve: list[EquitySnapshot] = []

        self._cumulative_realized_pnl = 0.0

    # ── Position queries ──

    @property
    def total_equity(self) -> float:
        if not self.equity_curve:
            return self.initial_capital
        return self.equity_curve[-1].total_equity

    def unrealized_pnl_at_price(self, price: float) -> float:
        """Calculate unrealized PnL at a given price."""
        if not self.position.is_open:
            return 0.0
        lots = self.position.contract_target_number
        direction = self.position.direction
        return direction * (price - self.position.cost_price) * lots * self.volume_multiple

    # ── Trade execution ──

    def execute_entry(self, direction: int, price: float, volume: int,
                      units: int, date: str, symbol: str = '') -> TradeRecord:
        """Open a new position (1st unit entry)."""
        self.position.direction = direction
        self.position.units = units
        self.position.contract_target_number = volume
        self.position.cost_price = price
        self.position.last_add_price = price
        self.position.first_open_price = price
        self.position.latest_close_price = price
        self.position.highest_close = price if direction == 1 else None
        self.position.lowest_close = price if direction == -1 else None
        self.position.stop_loss_price = None
        self.position.protect_cost_enabled = False

        if symbol:
            self.position.symbol = symbol
            self.position.active_contract = symbol

        trade = TradeRecord(
            date=date, symbol=self.position.symbol, trade_type='ENTRY',
            direction=direction, volume=volume, price=price, pnl=0.0,
            units_before=0, units_after=units,
            remark=f'开仓 {"LONG" if direction==1 else "SHORT"} {units}U@{price} vol={volume}'
        )
        self.trades.append(trade)
        return trade

    def execute_add_on(self, price: float, volume: int, add_units: int,
                       date: str) -> Optional[TradeRecord]:
        """Add units to an existing position."""
        if not self.position.is_open:
            return None

        old_units = self.position.units
        old_lots = self.position.contract_target_number
        new_lots = old_lots + volume

        # Weighted average cost
        old_cost = self.position.cost_price * old_lots
        new_cost = price * volume
        avg_price = (old_cost + new_cost) / new_lots if new_lots > 0 else price

        self.position.units = old_units + add_units
        self.position.contract_target_number = new_lots
        self.position.cost_price = avg_price
        self.position.last_add_price = price
        self.position.latest_close_price = price

        trade = TradeRecord(
            date=date, symbol=self.position.symbol, trade_type='ADD_ON',
            direction=self.position.direction, volume=volume, price=price, pnl=0.0,
            units_before=old_units, units_after=self.position.units,
            remark=f'加仓 +{add_units}U@{price} vol={volume}'
        )
        self.trades.append(trade)
        return trade

    def execute_exit(self, price: float, date: str,
                     trade_type: str = 'STOP_LOSS') -> Optional[TradeRecord]:
        """Fully exit the current position. Returns trade with realized PnL."""
        if not self.position.is_open:
            return None

        volume = self.position.contract_target_number
        direction = self.position.direction

        # Realized PnL
        pnl = direction * (price - self.position.cost_price) * volume * self.volume_multiple

        self.cash += pnl  # futures: cash collects realized PnL
        self._cumulative_realized_pnl += pnl

        old_units = self.position.units
        old_direction = self.position.direction
        old_symbol = self.position.symbol

        trade = TradeRecord(
            date=date, symbol=old_symbol, trade_type=trade_type,
            direction=old_direction, volume=volume, price=price, pnl=pnl,
            units_before=old_units, units_after=0,
            remark=f'平仓 {trade_type} {"LONG" if old_direction==1 else "SHORT"} '
                   f'{old_units}U PnL={pnl:.2f}'
        )
        self.trades.append(trade)

        # Reset position (keep symbol/contract for tracking)
        self.position = PositionState(
            symbol=old_symbol,
            active_contract=self.position.active_contract,
        )
        return trade

    def execute_rollover(self, new_symbol: str, close_price: float,
                         open_price: float, volume: int, date: str) -> tuple[TradeRecord, TradeRecord]:
        """Rollover: close old contract, open new contract.

        Returns:
            (exit_trade, entry_trade)
        """
        if not self.position.is_open:
            raise ValueError("Cannot rollover without an open position")

        direction = self.position.direction
        old_symbol = self.position.symbol
        old_units = self.position.units
        cost_price = self.position.cost_price

        # Realized PnL from closing old contract
        pnl = direction * (close_price - cost_price) * volume * self.volume_multiple
        self.cash += pnl
        self._cumulative_realized_pnl += pnl

        exit_trade = TradeRecord(
            date=date, symbol=old_symbol, trade_type='ROLLOVER_EXIT',
            direction=direction, volume=volume, price=close_price, pnl=pnl,
            units_before=old_units, units_after=0,
            remark=f'移仓平仓 {old_symbol}->{new_symbol} PnL={pnl:.2f}'
        )

        # Open new contract (same direction, units)
        self.position.symbol = new_symbol
        self.position.active_contract = new_symbol
        self.position.contract_target_number = volume
        self.position.cost_price = open_price
        self.position.last_add_price = open_price
        self.position.latest_close_price = open_price
        self.position.stop_loss_price = None
        self.position.protect_cost_enabled = False

        if direction == 1:
            self.position.highest_close = open_price
        else:
            self.position.lowest_close = open_price

        entry_trade = TradeRecord(
            date=date, symbol=new_symbol, trade_type='ROLLOVER_ENTRY',
            direction=direction, volume=volume, price=open_price, pnl=0.0,
            units_before=0, units_after=old_units,
            remark=f'移仓开仓 {old_symbol}->{new_symbol} {old_units}U@{open_price}'
        )

        self.trades.append(exit_trade)
        self.trades.append(entry_trade)
        return exit_trade, entry_trade

    # ── MTM / Equity tracking ──

    def update_mtm(self, close_price: float, date: str):
        """Record daily MTM snapshot at close."""
        if self.position.is_open:
            unrealized = self.unrealized_pnl_at_price(close_price)
            lots = self.position.contract_target_number
            total_equity = self.cash + unrealized
        else:
            unrealized = 0.0
            lots = 0
            total_equity = self.cash

        snapshot = EquitySnapshot(
            date=date,
            total_equity=round(total_equity, 2),
            cash=round(self.cash, 2),
            unrealized_pnl=round(unrealized, 2),
            position_lots=lots,
            position_direction=self.position.direction,
            close_price=close_price,
        )
        self.equity_curve.append(snapshot)
