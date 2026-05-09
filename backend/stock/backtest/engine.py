"""
Main backtest simulation loop — day-by-day close → open cycle.
"""
import os
import sys
import pandas as pd

from stock.backtest.config import BacktestConfig
from stock.backtest.broker import BacktestAccount
from stock.backtest.strategy import run_close_step, execute_signals_at_open
from stock.backtest.data_loader import build_daily_timeline


class BacktestEngine:
    """Day-by-day simulation engine.

    For each day T:
      1. Open step — execute signals from previous close at T's open
      2. Close step — generate new signals from T's close data
      3. MTM — record equity snapshot at T's close
    """

    def __init__(
        self,
        config: BacktestConfig,
        timeline: pd.DataFrame,
        verbose: bool = True,
    ):
        self.config = config
        self.timeline = timeline
        self.verbose = verbose
        self.lookback_bars = max(config.atr_period, config.entry_period, max(config.ma_periods)) + 5

        # Pre-validate
        if len(timeline) < self.lookback_bars + 2:
            raise ValueError(
                f"Timeline too short: {len(timeline)} rows, "
                f"need at least {self.lookback_bars + 2}"
            )

        # Init account
        self.account = BacktestAccount(
            initial_capital=config.initial_capital,
            volume_multiple=config.volume_multiple,
            price_tick=config.price_tick,
        )

        self.signals_log: list[dict] = []

    def run(self) -> dict:
        """Execute the full backtest loop.

        Returns:
            {
                'account': BacktestAccount (with trades + equity_curve),
                'config': BacktestConfig,
                'signals_log': list of signal dicts,
            }
        """
        tl = self.timeline
        lookback = self.lookback_bars
        total_days = len(tl) - lookback - 1  # -1 because last day has no tomorrow
        pending_signals: list = []

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  回测开始: {tl.iloc[lookback]['datetime']}")
            print(f"           -> {tl.iloc[-2]['datetime']}")
            print(f"  初始权益: {self.config.initial_capital:,.0f} RMB")
            print(f"  交易日数: {total_days}")
            print(f"{'='*60}\n")

        for i in range(lookback, len(tl) - 1):
            today = tl.iloc[i]
            tomorrow = tl.iloc[i + 1]

            # ── Open step: execute yesterday's signals at today's open ──
            if pending_signals:
                # Signals were generated on prev_day's close. Execute at today's open.
                prev_close = tl.iloc[i - 1]['close'] if i > lookback else today['close']
                executed = execute_signals_at_open(
                    account=self.account,
                    signals=pending_signals,
                    today_row=today,
                    prev_close=prev_close,
                    config=self.config,
                )
                if executed and self.verbose:
                    for t in executed:
                        print(f"  [EXEC] {t.date} {t.trade_type:12s} {t.symbol:6s} "
                              f"{t.volume:2d}手 @{t.price:7.2f} PnL={t.pnl:+.0f}")
                pending_signals = []

            # ── Close step: generate signals from today's data ──
            window = tl.iloc[:i + 1]
            signals = run_close_step(
                position=self.account.position,
                today_row=today,
                klines_window=window,
                config=self.config,
                is_rollover_date=bool(today.get('is_rollover_date', False)),
                active_contract=str(today.get('active_contract', '')),
                rollover_gap=float(today.get('rollover_gap', 0.0)),
            )

            # Log signals
            for s in signals:
                self.signals_log.append({
                    'date': str(today['datetime'])[:10],
                    'type': s.type,
                    'direction': s.direction,
                    'volume': s.volume,
                    'units': s.units,
                    'symbol': s.symbol,
                    'remark': s.remark,
                })
                if self.verbose:
                    print(f"  [SIGNAL] {str(today['datetime'])[:10]} {s.type:12s} "
                          f"{'LONG' if s.direction==1 else 'SHORT' if s.direction==-1 else '':5s}"
                          f" ref={s.price_ref:.2f} {s.remark}")

            pending_signals = signals

            # ── 移仓跳空调整：消除连续合约跳空的虚假 PnL ──
            rollover_gap = float(today.get('rollover_gap', 0.0))
            if rollover_gap != 0 and self.account.position.is_open:
                pos = self.account.position
                old_cost = pos.cost_price
                # 将所有价格参考平移至新合约的价格水平
                pos.cost_price += rollover_gap
                if pos.first_open_price is not None:
                    pos.first_open_price += rollover_gap
                if pos.last_add_price is not None:
                    pos.last_add_price += rollover_gap
                if self.verbose:
                    print(f"  [ROLLGAP] 移仓跳空调整 cost: {old_cost:.2f} -> "
                          f"{pos.cost_price:.2f} (gap={rollover_gap:+.2f})")

            # ── MTM at today's close ──
            self.account.update_mtm(float(today['close']), str(today['datetime'])[:10])

        # Final close-out: execute any remaining pending signals on last bar
        if pending_signals:
            last_row = tl.iloc[-1]
            executed = execute_signals_at_open(
                account=self.account,
                signals=pending_signals,
                today_row=last_row,
                prev_close=tl.iloc[-2]['close'],
                config=self.config,
            )
            if executed and self.verbose:
                for t in executed:
                    print(f"  [EXEC-FINAL] {t.date} {t.trade_type:12s} {t.symbol:6s} "
                          f"{t.volume:2d}手 @{t.price:7.2f} PnL={t.pnl:+.0f}")
            # MTM after final execution
            self.account.update_mtm(float(last_row['close']), str(last_row['datetime'])[:10])

        # Close any remaining open position on last day
        if self.account.position.is_open:
            last_row = tl.iloc[-1]
            trade = self.account.execute_exit(
                float(last_row['close']), str(last_row['datetime'])[:10], 'FORCE_CLOSE'
            )
            self.account.update_mtm(float(last_row['close']), str(last_row['datetime'])[:10])
            if trade and self.verbose:
                print(f"  [FORCE-CLOSE] {trade.date} 平仓剩余仓位 PnL={trade.pnl:.0f}")

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  回测完成")
            print(f"  最终权益: {self.account.total_equity:,.2f} RMB")
            print(f"  总交易笔数: {len(self.account.trades)}")
            print(f"{'='*60}\n")

        return {
            'account': self.account,
            'config': self.config,
            'signals_log': pd.DataFrame(self.signals_log) if self.signals_log else pd.DataFrame(),
        }
