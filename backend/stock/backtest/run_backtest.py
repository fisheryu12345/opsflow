"""
Backtest CLI entry point.

Usage:
    # Run with defaults (rb, 2019-2026)
    python -m stock.backtest.run_backtest

    # Custom run
    python -m stock.backtest.run_backtest --product rb --start 2019 --end 2026 \\
        --capital 1000000 --output ./bt_results
"""
import os
import sys
import argparse
from datetime import datetime

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from stock.backtest.config import BacktestConfig
from stock.backtest.engine import BacktestEngine
from stock.backtest.reporter import generate_report, save_report
from stock.backtest.data_loader import build_daily_timeline


def parse_args():
    parser = argparse.ArgumentParser(
        description='期货趋势跟踪策略回测 (2019-2026)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--product', default='rb', help='品种代码 (默认: rb)')
    parser.add_argument('--start', type=int, default=2019, help='起始年份 (默认: 2019)')
    parser.add_argument('--end', type=int, default=2026, help='结束年份 (默认: 2026)')
    parser.add_argument('--capital', type=float, default=1_000_000, help='初始权益 (默认: 1,000,000)')
    parser.add_argument('--output', '-o', default='', help='输出目录 (默认: ./backtest_results/{product})')
    parser.add_argument('--verbose', '-v', action='store_true', default=True, help='详细输出')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    return parser.parse_args()


def main():
    args = parse_args()

    # Config
    config = BacktestConfig(
        product=args.product,
        start_year=args.start,
        end_year=args.end,
        initial_capital=args.capital,
        output_dir=args.output or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'results',
            f"{args.product}_{args.start}_{args.end}",
        ),
    )

    verbose = args.verbose and not args.quiet

    print(f"\n{'#'*60}")
    print(f"  期货趋势跟踪策略回测系统")
    print(f"  品种: {config.product.upper()} | 区间: {config.start_year}-{config.end_year}")
    print(f"  初始权益: RMB{config.initial_capital:,.0f}")
    print(f"{'#'*60}\n")

    # 1. Load data
    start_date = f"{config.start_year}-01-01"
    end_date = f"{config.end_year}-12-31"
    print("[1/3] 加载数据...")
    timeline = build_daily_timeline(config.product, start=start_date, end=end_date)
    print(f"      交易日: {len(timeline)}")

    # 2. Run engine
    print("[2/3] 运行回测...")
    engine = BacktestEngine(config, timeline, verbose=verbose)
    results = engine.run()

    # 3. Generate report
    print("[3/3] 生成报告...")
    report = generate_report(results, config)

    # Print summary
    print(report['summary_text'])

    # Monthly returns
    if not report['monthly_returns'].empty:
        print("\n  月度收益表 (%):")
        print(report['monthly_returns'].to_string())

    # Save
    print("\n  保存报告...")
    save_report(report, config.output_dir)

    print(f"\n{'#'*60}")
    print(f"  回测完成")
    print(f"{'#'*60}\n")


if __name__ == '__main__':
    main()
