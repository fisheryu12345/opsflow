"""
Performance reporting — trade log, equity curve, metrics.
"""
import os
import math
import numpy as np
import pandas as pd

from stock.backtest.config import BacktestConfig
from stock.backtest.broker import BacktestAccount


def generate_report(results: dict, config: BacktestConfig) -> dict:
    """Generate full performance report from backtest results.

    Args:
        results: Output of BacktestEngine.run()
        config: BacktestConfig

    Returns:
        {
            'metrics': dict of performance metrics,
            'trade_log': DataFrame,
            'equity_curve': DataFrame,
            'monthly_returns': DataFrame,
            'summary_text': formatted summary,
        }
    """
    account: BacktestAccount = results['account']
    trades = account.trades
    equity = account.equity_curve

    # ── 1. Trade log ──
    trade_log = pd.DataFrame([t.to_dict() for t in trades]) if trades else pd.DataFrame()

    # ── 2. Equity curve ──
    eq_records = [
        {
            'date': e.date,
            'total_equity': e.total_equity,
            'cash': e.cash,
            'unrealized_pnl': e.unrealized_pnl,
            'position_lots': e.position_lots,
            'position_direction': e.position_direction,
            'close_price': e.close_price,
        }
        for e in equity
    ]
    equity_df = pd.DataFrame(eq_records)
    if not equity_df.empty:
        equity_df['daily_return'] = equity_df['total_equity'].pct_change()
        equity_df['cumulative_return'] = equity_df['total_equity'] / config.initial_capital - 1.0

    # ── 3. Performance metrics ──
    metrics = _calc_metrics(equity_df, trade_log, config)

    # ── 4. Monthly returns ──
    monthly_df = _calc_monthly_returns(equity_df)

    # ── 5. Summary text ──
    summary = _format_summary(metrics)

    return {
        'metrics': metrics,
        'trade_log': trade_log,
        'equity_curve': equity_df,
        'monthly_returns': monthly_df,
        'summary_text': summary,
    }


def _calc_metrics(equity_df: pd.DataFrame, trade_log: pd.DataFrame, config: BacktestConfig) -> dict:
    """Calculate all performance metrics."""
    initial = config.initial_capital
    if equity_df.empty:
        return {'error': 'No equity data'}

    final_equity = equity_df['total_equity'].iloc[-1]
    total_return = (final_equity - initial) / initial

    # Number of trading days
    n_days = len(equity_df)
    years = n_days / 252 if n_days > 0 else 1

    # CAGR
    if years > 0 and initial > 0:
        cagr = (final_equity / initial) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    # Max drawdown
    max_dd, max_dd_pct = _calc_max_drawdown(equity_df['total_equity'].values)

    # Daily return stats
    daily_returns = equity_df['daily_return'].dropna()
    if len(daily_returns) > 0:
        annualized_return = cagr
        annualized_vol = daily_returns.std() * math.sqrt(252)
        sharpe = (annualized_return - 0.02) / annualized_vol if annualized_vol > 0 else 0.0
        # Sortino
        downside = daily_returns[daily_returns < 0]
        downside_vol = downside.std() * math.sqrt(252) if len(downside) > 0 else 0.0
        sortino = (annualized_return - 0.02) / downside_vol if downside_vol > 0 else 0.0
    else:
        annualized_vol = 0.0
        sharpe = 0.0
        sortino = 0.0

    # Trade stats
    if not trade_log.empty:
        # Only count actual trades (EXIT, STOP_LOSS, FORCE_CLOSE, ROLLOVER_EXIT have PnL)
        pnl_trades = trade_log[trade_log['trade_type'].isin(['STOP_LOSS', 'ROLLOVER_EXIT', 'FORCE_CLOSE'])]
        # Also count ROLLOVER_EXIT (has PnL)
        closed_trades = trade_log[trade_log['pnl'] != 0].copy()
        total_closed = len(closed_trades)
        winning = closed_trades[closed_trades['pnl'] > 0]
        losing = closed_trades[closed_trades['pnl'] < 0]
        win_count = len(winning)
        loss_count = len(losing)
        win_rate = win_count / total_closed if total_closed > 0 else 0.0
        avg_win = winning['pnl'].mean() if win_count > 0 else 0.0
        avg_loss = losing['pnl'].mean() if loss_count > 0 else 0.0
        wl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        gross_profit = winning['pnl'].sum() if win_count > 0 else 0.0
        gross_loss = abs(losing['pnl'].sum()) if loss_count > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        total_pnl = closed_trades['pnl'].sum()
    else:
        total_closed = 0
        win_count = 0
        loss_count = 0
        win_rate = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        wl_ratio = 0.0
        profit_factor = 0.0
        total_pnl = 0.0

    # Calmar ratio
    calmar = cagr / abs(max_dd_pct) if max_dd_pct != 0 else 0.0

    # Max consecutive wins/losses
    max_consec_win, max_consec_loss = _calc_consecutive(closed_trades['pnl']) if total_closed > 0 else (0, 0)

    start_date = equity_df['date'].iloc[0] if not equity_df.empty else ''
    end_date = equity_df['date'].iloc[-1] if not equity_df.empty else ''

    return {
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': n_days,
        'years': round(years, 2),
        'initial_capital': initial,
        'final_equity': round(final_equity, 2),
        'total_return_pct': round(total_return * 100, 2),
        'cagr_pct': round(cagr * 100, 2),
        'annualized_vol_pct': round(annualized_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 3),
        'sortino_ratio': round(sortino, 3),
        'calmar_ratio': round(calmar, 3),
        'max_drawdown_pct': round(max_dd_pct * 100, 2),
        'max_drawdown': round(max_dd, 2),
        'total_trades': total_closed,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate_pct': round(win_rate * 100, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'wl_ratio': round(wl_ratio, 2),
        'profit_factor': round(profit_factor, 2),
        'total_pnl': round(total_pnl, 2),
        'max_consec_wins': max_consec_win,
        'max_consec_losses': max_consec_loss,
    }


def _calc_max_drawdown(equity: np.ndarray) -> tuple[float, float]:
    """Calculate maximum drawdown and its percentage.

    Returns:
        (max_drawdown_value, max_drawdown_pct)
    """
    if len(equity) == 0:
        return 0.0, 0.0

    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd_idx = np.argmax(drawdown)
    max_dd = float(drawdown[max_dd_idx])

    # Percentage: drawdown divided by peak at the drawdown start
    if max_dd_idx > 0 and peak[max_dd_idx] > 0:
        max_dd_pct = max_dd / peak[max_dd_idx]
    else:
        max_dd_pct = 0.0

    return max_dd, max_dd_pct


def _calc_consecutive(pnl_series: pd.Series) -> tuple[int, int]:
    """Calculate max consecutive wins and losses."""
    if len(pnl_series) == 0:
        return 0, 0

    positive = (pnl_series > 0).astype(int)
    negative = (pnl_series < 0).astype(int)

    # Max consecutive wins
    max_wins = 0
    current = 0
    for v in positive:
        if v:
            current += 1
            max_wins = max(max_wins, current)
        else:
            current = 0

    # Max consecutive losses
    max_losses = 0
    current = 0
    for v in negative:
        if v:
            current += 1
            max_losses = max(max_losses, current)
        else:
            current = 0

    return max_wins, max_losses


def _calc_monthly_returns(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly return table from equity curve."""
    if equity_df.empty:
        return pd.DataFrame()

    df = equity_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    # Monthly equity (last day of each month)
    monthly = df.groupby(['year', 'month'])['total_equity'].last().reset_index()
    monthly['monthly_return'] = monthly.groupby('year')['total_equity'].pct_change()
    monthly['monthly_return'] = monthly['monthly_return'].fillna(0)

    # Pivot for display
    pivot = monthly.pivot_table(
        index='year', columns='month', values='monthly_return',
        aggfunc='last',
    )
    pivot = pivot * 100  # to percentage
    pivot = pivot.round(2)

    # Add annual return column
    annual = df.groupby('year')['total_equity'].last()
    annual_return = annual.pct_change()
    pivot['年化'] = (annual_return * 100).round(2)

    # Column names
    pivot.columns = [f'{m}月' for m in pivot.columns[:-1]] + ['年化']

    return pivot


def _format_summary(metrics: dict) -> str:
    """Format metrics into a readable summary."""
    if 'error' in metrics:
        return f"[ERROR] {metrics['error']}"

    lines = [
        "=" * 60,
        "  策略回测绩效报告",
        "=" * 60,
        f"  回测区间: {metrics['start_date']} → {metrics['end_date']}",
        f"  交易天数: {metrics['trading_days']} 天 ({metrics['years']} 年)",
        "",
        "── 收益指标 ──",
        f"  初始权益: RMB{metrics['initial_capital']:>10,.2f}",
        f"  最终权益: RMB{metrics['final_equity']:>10,.2f}",
        f"  总收益率: {metrics['total_return_pct']:>7.2f}%",
        f"  年化收益率 (CAGR): {metrics['cagr_pct']:>7.2f}%",
        f"  年化波动率: {metrics['annualized_vol_pct']:>7.2f}%",
        "",
        "── 风险指标 ──",
        f"  夏普比率: {metrics['sharpe_ratio']:>8.3f}",
        f"  索提诺比率: {metrics['sortino_ratio']:>7.3f}",
        f"  卡玛比率: {metrics['calmar_ratio']:>8.3f}",
        f"  最大回撤: {metrics['max_drawdown_pct']:>7.2f}% (RMB{metrics['max_drawdown']:>8,.0f})",
        "",
        "── 交易统计 ──",
        f"  总交易笔数: {metrics['total_trades']}",
        f"  盈利笔数: {metrics['win_count']}",
        f"  亏损笔数: {metrics['loss_count']}",
        f"  胜率: {metrics['win_rate_pct']:>5.2f}%",
        f"  平均盈利: RMB{metrics['avg_win']:>8,.2f}",
        f"  平均亏损: RMB{metrics['avg_loss']:>8,.2f}",
        f"  盈亏比: {metrics['wl_ratio']:>5.2f}",
        f"  利润因子: {metrics['profit_factor']:>5.2f}",
        f"  总盈亏: RMB{metrics['total_pnl']:>8,.2f}",
        f"  最大连续盈利: {metrics['max_consec_wins']} 笔",
        f"  最大连续亏损: {metrics['max_consec_losses']} 笔",
        "=" * 60,
    ]
    return '\n'.join(lines)


def save_report(report: dict, output_dir: str):
    """Save report files to disk."""
    os.makedirs(output_dir, exist_ok=True)

    # Metrics JSON
    import json
    metrics_path = os.path.join(output_dir, 'metrics.json')
    # Convert numpy types
    clean = {}
    for k, v in report['metrics'].items():
        if isinstance(v, (np.integer,)):
            clean[k] = int(v)
        elif isinstance(v, (np.floating,)):
            clean[k] = float(v)
        else:
            clean[k] = v
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {metrics_path}")

    # Trade log CSV
    if not report['trade_log'].empty:
        trade_path = os.path.join(output_dir, 'trade_log.csv')
        report['trade_log'].to_csv(trade_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] {trade_path}")

    # Equity curve CSV
    if not report['equity_curve'].empty:
        eq_path = os.path.join(output_dir, 'equity_curve.csv')
        cols = ['date', 'total_equity', 'cash', 'unrealized_pnl',
                'daily_return', 'cumulative_return', 'position_lots']
        available = [c for c in cols if c in report['equity_curve'].columns]
        report['equity_curve'][available].to_csv(eq_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] {eq_path}")

    # Monthly returns CSV
    if not report['monthly_returns'].empty:
        monthly_path = os.path.join(output_dir, 'monthly_returns.csv')
        report['monthly_returns'].to_csv(monthly_path, encoding='utf-8-sig')
        print(f"  [OK] {monthly_path}")

    # Summary text
    summary_path = os.path.join(output_dir, 'summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(report['summary_text'])
    print(f"  [OK] {summary_path}")

    print(f"\n  报告保存至: {output_dir}")
