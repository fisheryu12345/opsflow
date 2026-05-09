"""
多品种投资组合回测 CLI 入口。

用法：
    # 全流程（下载数据 → 逐品种回测 → 聚合报告）
    python -m stock.backtest.run_portfolio_backtest

    # 仅下载数据
    python -m stock.backtest.run_portfolio_backtest --download-only

    # 跳过下载，直接使用已有数据
    python -m stock.backtest.run_portfolio_backtest --skip-download

    # 指定品种子集
    python -m stock.backtest.run_portfolio_backtest --products rb,hc,MA,SA

    # 指定区间 & 资金
    python -m stock.backtest.run_portfolio_backtest --start 2020 --end 2025 --capital 500000
"""
import os
import sys
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from stock.backtest.portfolio import (
    download_all_products,
    run_portfolio_backtest,
    generate_portfolio_report,
)
from stock.backtest.product_data import PRODUCTS
from stock.backtest.generate_html_report import load_all_data, build_html


def parse_args():
    parser = argparse.ArgumentParser(
        description='多品种投资组合回测 (2019-2026)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--products', '-p', default='',
                        help='品种列表，逗号分隔（默认: 全部品种）')
    parser.add_argument('--start', type=int, default=2019, help='起始年份')
    parser.add_argument('--end', type=int, default=2026, help='结束年份')
    parser.add_argument('--capital', type=float, default=1_000_000,
                        help='每品种初始权益（用于各品种独立回测的资金起点）')
    parser.add_argument('--total-capital', type=float, default=None,
                        help='组合总资金（默认 = capital × 品种数）。'
                             '设定此值 < capital × 品种数 实现共享资金池效果')
    parser.add_argument('--output', '-o', default='',
                        help='输出目录（默认: ./results/portfolio_{start}_{end}）')
    parser.add_argument('--download-only', action='store_true',
                        help='仅下载数据，不运行回测')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过下载，直接使用已有数据回测')
    parser.add_argument('--overwrite-data', action='store_true',
                        help='重新下载已存在的数据文件')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='打印每品种详细交易记录')
    return parser.parse_args()


def main():
    args = parse_args()

    # 品种列表
    if args.products:
        products = [c.strip() for c in args.products.split(',') if c.strip()]
    else:
        products = [p.code for p in PRODUCTS]

    print(f"{'#'*62}")
    print(f"  多品种投资组合回测系统")
    print(f"  品种: {len(products)} 个 | 区间: {args.start}-{args.end}")
    total_cap = args.total_capital or (args.capital * len(products))
    print(f"  每品种初始权益: RMB{args.capital:,.0f}")
    print(f"  组合总资金:     RMB{total_cap:,.0f}{'（共享资金池）' if args.total_capital else ''}")
    print(f"{'#'*62}\n")

    # ── 1. 下载数据（可选）──
    if not args.skip_download:
        print("─" * 40)
        print("  步骤 1/3: 下载主力连续合约数据")
        print("─" * 40)
        download_all_products(products=products, overwrite=args.overwrite_data)
        print()

    if args.download_only:
        print("[INFO] 下载完成。可使用 --skip-download 运行回测。\n")
        return

    # ── 2. 运行投资组合回测 ──
    print("─" * 40)
    print("  步骤 2/3: 运行投资组合回测")
    print("─" * 40)

    results = run_portfolio_backtest(
        products=products,
        start_year=args.start,
        end_year=args.end,
        capital_per_product=args.capital,
        total_capital=args.total_capital,
        verbose=args.verbose,
    )

    if not results.get('product_results'):
        print("\n[ERROR] 无有效回测结果。\n")
        return

    # ── 3. 生成报告 ──
    output_dir = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'results',
        f"portfolio_{args.start}_{args.end}",
    )

    print(f"\n{'─'*40}")
    print(f"  生成组合报告 ...")
    print(f"{'─'*40}")

    report = generate_portfolio_report(results, output_dir)

    # 打印摘要
    print("\n" + report['summary_text'])

    # 打印品种对比表格
    if not report['product_summary'].empty:
        print("\n  品种绩效对比:")
        print("-" * 80)
        print(report['product_summary'].to_string(index=False))

    # ── 4. 生成HTML报告 ──
    print(f"\n{'─'*40}")
    print(f"  步骤 3/3: 生成HTML可视化报告")
    print(f"{'─'*40}")

    try:
        data = load_all_data(output_dir)
        if data['products']:
            html_path = os.path.join(output_dir, 'portfolio_report.html')
            html_content = build_html(data)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            size_mb = os.path.getsize(html_path) / 1024 / 1024
            print(f"  [OK] HTML报告: {html_path} ({size_mb:.1f}MB)")
    except Exception as e:
        print(f"  [WARN] HTML报告生成失败: {e}")

    print(f"\n{'#'*62}")
    print(f"  投资组合回测完成")
    print(f"  报告目录: {output_dir}")
    print(f"{'#'*62}\n")


if __name__ == '__main__':
    main()
