"""
多品种投资组合回测 —— 下载 → 逐品种运行 → 聚合 → 报告。

流程：
  1. download_all_products()     使用 TqSDK 批量下载所有品种主力连续 K 线
  2. run_portfolio_backtest()    逐品种运行回测，聚合权益曲线
  3. generate_portfolio_report() 生成多品种组合报告

组合逻辑：
  - 各品种独立运行，每品种分配 full initial_capital
  - 仓位计算 (compute_unit_lots) 不依赖总资本，各品种 PnL 可加
  - 组合权益 = sum(各品种权益曲线)；组合指标基于加总曲线计算
"""
import os
import sys
import time
import math
import json
import glob as glob_mod
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from stock.backtest.product_data import PRODUCTS, get_product, tqsdk_symbol
from stock.backtest.config import BacktestConfig
from stock.backtest.data_loader import load_daily_data, build_daily_timeline, DATA_DIR
from stock.backtest.engine import BacktestEngine
from stock.backtest.reporter import generate_report, save_report


# ═══════════════════════════════════════════════════════════════
#  1. 批量数据下载
# ═══════════════════════════════════════════════════════════════

def download_all_products(products: list[str] = None, overwrite: bool = False):
    """使用 TqSDK 批量下载所有品种的主力连续 K 线数据。

    Args:
        products: 品种代码列表；None = 全部定义品种
        overwrite: 是否覆盖已有文件
    """
    if products is None:
        products = [p.code for p in PRODUCTS]

    # 检查哪些需要下载
    to_download = []
    for code in products:
        files = sorted(glob_mod.glob(os.path.join(DATA_DIR, f"{code}_main_daily_*.csv")))
        if files and not overwrite:
            print(f"  [SKIP] {code}: 已存在 {os.path.basename(files[-1])}")
        else:
            to_download.append(code)

    if not to_download:
        print("[INFO] 所有品种数据已存在，跳过下载")
        return

    print(f"\n[INFO] 需下载 {len(to_download)} 个品种: {', '.join(to_download)}")
    print("[INFO] 正在连接 TqSDK ...")

    # Windows GBK 终端兼容
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    from tqsdk import TqApi, TqAuth

    api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
    try:
        symbols = {code: tqsdk_symbol(code) for code in to_download}

        print(f"[INFO] 批量订阅 {len(symbols)} 个合约（data_length=3000）...")
        kline_refs = {}
        for code, sym in symbols.items():
            kline_refs[code] = api.get_kline_serial(sym, duration_seconds=86400, data_length=3000)

        print("[INFO] 等待数据加载（约 60 秒）...")
        for _ in range(12):
            api.wait_update(deadline=time.time() + 10)
            ready = sum(1 for v in kline_refs.values() if len(v) > 0)
            if ready == len(kline_refs):
                print(f"  [OK] 全部就绪 ({ready}/{len(kline_refs)})")
                break
            if _ % 3 == 2:
                print(f"  ... {ready}/{len(kline_refs)} 就绪")

        time.sleep(1)
        api.wait_update(deadline=time.time() + 5)

        # 逐个保存
        for code in to_download:
            raw = kline_refs[code]
            if len(raw) == 0:
                print(f"  [WARN] {code}: 无数据返回")
                continue

            df = _clean_kline(raw.copy())
            if len(df) == 0:
                print(f"  [WARN] {code}: 清洗后无有效数据")
                continue

            s = df['datetime'].iloc[0].strftime('%Y%m%d')
            e = df['datetime'].iloc[-1].strftime('%Y%m%d')
            fname = f"{code}_main_daily_{s}_{e}.csv"
            fpath = os.path.join(DATA_DIR, fname)
            df.to_csv(fpath, index=False, encoding='utf-8-sig', float_format='%.2f')
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  [OK] {fname}  ({len(df)}条, {size_kb:.1f}KB)")

    finally:
        api.close()


def _clean_kline(df: pd.DataFrame) -> pd.DataFrame:
    """清洗 K 线数据：时间戳转换、去空、排序去重。"""
    keep = [c for c in ['datetime', 'open', 'high', 'low', 'close', 'volume', 'open_oi']
            if c in df.columns]
    df = df[keep].copy()

    ts = pd.to_numeric(df['datetime'], errors='coerce')
    df['datetime'] = pd.to_datetime(ts, unit='ns', utc=True, errors='coerce'
                                     ).dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
    df = df.dropna(subset=['datetime'])
    df = df[df['datetime'].dt.year >= 2010]
    df = df.sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
    for c in ['open', 'high', 'low', 'close']:
        if c in df.columns:
            df[c] = df[c].round(2)
    return df


# ═══════════════════════════════════════════════════════════════
#  2. 单品种回测
# ═══════════════════════════════════════════════════════════════

def run_product_backtest(code: str, start_year: int = 2019, end_year: int = 2026,
                         capital: float = 1_000_000, verbose: bool = False) -> dict:
    """运行单个品种回测。

    Returns:
        {'product', 'success', 'error', 'config', 'report', 'engine_results'}
    """
    try:
        info = get_product(code)
        config = BacktestConfig(
            product=code,
            start_year=start_year,
            end_year=end_year,
            initial_capital=capital,
            volume_multiple=info.volume_multiple,
            price_tick=info.price_tick,
        )

        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        timeline = build_daily_timeline(code, start=start_date, end=end_date)

        if len(timeline) < 50:
            return {'product': code, 'success': False,
                    'error': f'数据不足: {len(timeline)} 行 < 50'}

        engine = BacktestEngine(config, timeline, verbose=verbose)
        engine_results = engine.run()
        report = generate_report(engine_results, config)

        return {'product': code, 'success': True, 'error': None,
                'config': config, 'report': report,
                'engine_results': engine_results}

    except FileNotFoundError as e:
        return {'product': code, 'success': False, 'error': f'数据文件缺失: {e}'}
    except ValueError as e:
        return {'product': code, 'success': False, 'error': str(e)}
    except Exception as e:
        return {'product': code, 'success': False, 'error': f'{type(e).__name__}: {e}'}


# ═══════════════════════════════════════════════════════════════
#  3. 投资组合回测
# ═══════════════════════════════════════════════════════════════

def run_portfolio_backtest(products: list[str] = None,
                           start_year: int = 2019, end_year: int = 2026,
                           capital_per_product: float = 1_000_000,
                           total_capital: float = None,
                           verbose: bool = False) -> dict:
    """运行多品种投资组合回测。

    各品种独立运行（full capital_per_product），组合权益 = 各品种 PnL 加总 + total_capital。
    当 total_capital < capital_per_product × 品种数时，实现"共享资金池"效果。

    Args:
        total_capital: 组合总初始权益。默认 = capital_per_product × 品种数。

    Returns:
        {'product_results', 'portfolio_equity', 'portfolio_metrics',
         'product_summary', 'total_capital', 'num_products'}
    """
    if products is None:
        products = [p.code for p in PRODUCTS]

    print(f"\n{'='*60}")
    print(f"  投资组合回测: {len(products)} 个品种")
    print(f"  区间: {start_year}-{end_year}")
    print(f"  每品种初始权益: RMB{capital_per_product:,.0f}")
    if total_capital is not None:
        print(f"  组合总资金:     RMB{total_capital:,.0f}（共享资金池）")
    print(f"{'='*60}")

    product_results = {}
    for i, code in enumerate(products, 1):
        info = get_product(code)
        print(f"\n[{i}/{len(products)}] {code:4s} ({info.name}) ...", end=' ')
        result = run_product_backtest(code, start_year, end_year,
                                      capital_per_product, verbose)
        product_results[code] = result

        if result['success']:
            m = result['report']['metrics']
            print(f"Return: {m['total_return_pct']:>6.1f}%  "
                  f"CAGR: {m['cagr_pct']:>5.1f}%  "
                  f"MaxDD: {m['max_drawdown_pct']:>4.1f}%  "
                  f"Sharpe: {m['sharpe_ratio']:>.2f}  "
                  f"Trades: {m['total_trades']}")
        else:
            print(f"FAILED: {result['error']}")

    # ── 聚合 ──
    print(f"\n{'='*60}")
    print(f"  聚合投资组合权益曲线 ...")

    num_success = len([r for r in product_results.values() if r['success']])
    if total_capital is None:
        total_capital = num_success * capital_per_product

    portfolio_equity = _aggregate_equity_curves(
        product_results, capital_per_product, total_capital,
    )

    if portfolio_equity.empty:
        print("[ERROR] 无有效数据生成组合曲线")
        return {'product_results': product_results}

    portfolio_metrics = _compute_portfolio_metrics(portfolio_equity, total_capital)
    product_summary = _build_product_summary(product_results)

    print(f"  组合总初始权益: RMB{total_capital:,.0f}")
    print(f"  组合最终权益:   RMB{portfolio_metrics.get('final_equity', 0):,.0f}")
    print(f"  组合总收益率:   {portfolio_metrics.get('total_return_pct', 0):.2f}%")
    print(f"  组合年化收益率: {portfolio_metrics.get('cagr_pct', 0):.2f}%")
    print(f"  组合最大回撤:   {portfolio_metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"  组合夏普比率:   {portfolio_metrics.get('sharpe_ratio', 0):.3f}")

    return {
        'product_results': product_results,
        'portfolio_equity': portfolio_equity,
        'portfolio_metrics': portfolio_metrics,
        'product_summary': product_summary,
        'total_capital': total_capital,
        'num_products': len(products),
        'start_year': start_year,
        'end_year': end_year,
    }


def _aggregate_equity_curves(product_results: dict,
                              capital_per_product: float,
                              total_capital: float = None) -> pd.DataFrame:
    """聚合各品种权益曲线为组合曲线。

    策略：
      - 对每个成功品种，取出 total_equity 序列（以 date 为索引）
      - 外连接合并，前向填充缺失值
      - 在产品上市前/回测开始前，填 capital_per_product
      - 组合权益 = 各品种权益加总 - 各品种占用资本 + total_capital

    当 total_capital 与 capital_per_product × 品种数不同时，
    实现"所有品种共享同一资金池"的效果。
    """
    all_series = {}

    for code, result in product_results.items():
        if not result['success']:
            continue
        eq = result['report']['equity_curve']
        if eq.empty:
            continue
        s = eq.set_index('date')['total_equity'].copy()
        s = s[~s.index.duplicated(keep='last')]  # 防重复日期
        all_series[code] = s

    if not all_series:
        return pd.DataFrame()

    num_products = len(all_series)
    if total_capital is None:
        total_capital = num_products * capital_per_product

    # 构建完整日期范围
    all_dates = sorted(set.union(*[set(s.index) for s in all_series.values()]))
    combined = pd.DataFrame(index=pd.Index(all_dates, name='date'))

    for code, s in all_series.items():
        combined[code] = s

    # 前向填充，再回填上市前空白为 capital_per_product
    combined = combined.sort_index()
    combined = combined.ffill().fillna(capital_per_product)

    # 组合总权益 = sum(各品种权益) - num_products * capital_per_product + total_capital
    # 即：各品种 PnL 之和 + total_capital
    product_columns = list(all_series.keys())
    combined['total_equity'] = combined[product_columns].sum(axis=1)
    combined['total_equity'] = combined['total_equity'] - num_products * capital_per_product + total_capital
    combined['daily_return'] = combined['total_equity'].pct_change().fillna(0.0)

    return combined


# ═══════════════════════════════════════════════════════════════
#  4. 组合指标计算
# ═══════════════════════════════════════════════════════════════

def _compute_portfolio_metrics(equity_df: pd.DataFrame,
                                total_capital: float) -> dict:
    """计算组合层面的绩效指标（与 reporter._calc_metrics 同逻辑）。"""
    if equity_df.empty:
        return {'error': 'No equity data'}

    equity = equity_df['total_equity'].values
    final_equity = float(equity[-1])
    total_return = (final_equity - total_capital) / total_capital

    n_days = len(equity_df)
    years = n_days / 252 if n_days > 0 else 1

    # CAGR
    if years > 0 and total_capital > 0:
        cagr = (final_equity / total_capital) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    # 最大回撤
    max_dd, max_dd_pct = _max_drawdown(equity)

    # 日收益统计
    daily_returns = equity_df['daily_return'].dropna()
    if len(daily_returns) > 0:
        annualized_vol = daily_returns.std() * math.sqrt(252)
        sharpe = (cagr - 0.02) / annualized_vol if annualized_vol > 0 else 0.0
        downside = daily_returns[daily_returns < 0]
        downside_vol = downside.std() * math.sqrt(252) if len(downside) > 0 else 0.0
        sortino = (cagr - 0.02) / downside_vol if downside_vol > 0 else 0.0
    else:
        annualized_vol = 0.0
        sharpe = 0.0
        sortino = 0.0

    calmar = cagr / abs(max_dd_pct) if max_dd_pct != 0 else 0.0

    return {
        'start_date': str(equity_df.index[0]),
        'end_date': str(equity_df.index[-1]),
        'trading_days': n_days,
        'years': round(years, 2),
        'total_capital': total_capital,
        'final_equity': round(final_equity, 2),
        'total_return_pct': round(total_return * 100, 2),
        'cagr_pct': round(cagr * 100, 2),
        'annualized_vol_pct': round(annualized_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 3),
        'sortino_ratio': round(sortino, 3),
        'calmar_ratio': round(calmar, 3),
        'max_drawdown_pct': round(max_dd_pct * 100, 2),
        'max_drawdown': round(max_dd, 2),
    }


def _max_drawdown(equity: np.ndarray) -> tuple[float, float]:
    """计算最大回撤（金额 & 百分比）。"""
    if len(equity) == 0:
        return 0.0, 0.0
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd_idx = int(np.argmax(drawdown))
    max_dd = float(drawdown[max_dd_idx])
    if max_dd_idx > 0 and peak[max_dd_idx] > 0:
        max_dd_pct = max_dd / peak[max_dd_idx]
    else:
        max_dd_pct = 0.0
    return max_dd, max_dd_pct


def _build_product_summary(product_results: dict) -> pd.DataFrame:
    """构建品种间对比表。"""
    rows = []
    for code, result in product_results.items():
        info = get_product(code)
        if result['success']:
            m = result['report']['metrics']
            rows.append({
                '品种': code,
                '名称': info.name,
                '交易所': info.exchange,
                '总收益率%': m['total_return_pct'],
                '年化收益率%': m['cagr_pct'],
                '最大回撤%': m['max_drawdown_pct'],
                '夏普比率': m['sharpe_ratio'],
                '索提诺比率': m['sortino_ratio'],
                '卡玛比率': m['calmar_ratio'],
                '总交易': m['total_trades'],
                '胜率%': m['win_rate_pct'],
                '利润因子': m['profit_factor'],
                '总盈亏': m['total_pnl'],
            })
        else:
            rows.append({
                '品种': code, '名称': info.name, '交易所': info.exchange,
                '总收益率%': None, '年化收益率%': None, '最大回撤%': None,
                '夏普比率': None, '索提诺比率': None, '卡玛比率': None,
                '总交易': 0, '胜率%': None, '利润因子': None, '总盈亏': None,
            })

    return pd.DataFrame(rows).sort_values('品种').reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
#  5. 组合报告生成
# ═══════════════════════════════════════════════════════════════

def generate_portfolio_report(portfolio_results: dict, output_dir: str) -> dict:
    """生成并保存投资组合回测报告。"""
    os.makedirs(output_dir, exist_ok=True)

    metrics = portfolio_results.get('portfolio_metrics', {})
    product_summary = portfolio_results.get('product_summary', pd.DataFrame())
    portfolio_equity = portfolio_results.get('portfolio_equity', pd.DataFrame())
    product_results = portfolio_results.get('product_results', {})

    # ── 组合绩效正文 ──
    if metrics and 'error' not in metrics:
        total_cap = portfolio_results.get('total_capital', 0)
        num_prods = portfolio_results.get('num_products', 1)
        cap_per = total_cap / max(num_prods, 1)

        lines = [
            "=" * 62,
            "  投资组合回测绩效报告",
            "=" * 62,
            f"  回测区间: {metrics['start_date']} → {metrics['end_date']}",
            f"  交易天数: {metrics['trading_days']} 天 ({metrics['years']} 年)",
            f"  品种数量: {portfolio_results.get('num_products', '?')}",
            f"  成功回测: {len(product_summary[product_summary['总收益率%'].notna()])} 个",
            "",
            "── 组合构建说明 ──",
            f"  总资金 RMB {total_cap:,.0f}，各品种共享同一资金池。",
            f"  品种间独立运行，PnL 可加。",
            f"  仓位计算基于固定风险参数，不依赖总资金。",
            "",
            "── 收益指标 ──",
            f"  初始权益: RMB{metrics['total_capital']:>12,.2f}",
            f"  最终权益: RMB{metrics['final_equity']:>12,.2f}",
            f"  总收益率: {metrics['total_return_pct']:>8.2f}%",
            f"  年化收益率 (CAGR): {metrics['cagr_pct']:>8.2f}%",
            f"  年化波动率: {metrics['annualized_vol_pct']:>8.2f}%",
            "",
            "── 风险指标 ──",
            f"  夏普比率: {metrics['sharpe_ratio']:>9.3f}",
            f"  索提诺比率: {metrics['sortino_ratio']:>8.3f}",
            f"  卡玛比率: {metrics['calmar_ratio']:>9.3f}",
            f"  最大回撤: {metrics['max_drawdown_pct']:>8.2f}% "
            f"(RMB{metrics['max_drawdown']:>10,.0f})",
            "",
        ]

        # 品种排名
        valid = product_summary[product_summary['总收益率%'].notna()].copy()
        if not valid.empty:
            valid = valid.sort_values('总收益率%', ascending=False)
            lines.append("── 品种收益排名 ──")
            for i, (_, row) in enumerate(valid.iterrows(), 1):
                lines.append(
                    f"  {i:2d}. {row['品种']:4s} ({row['名称']:6s})  "
                    f"收益: {row['总收益率%']:>6.1f}%  "
                    f"年化: {row['年化收益率%']:>5.1f}%  "
                    f"回撤: {row['最大回撤%']:>5.1f}%  "
                    f"夏普: {row['夏普比率']:>5.2f}  "
                    f"交易: {row['总交易']} 笔"
                )

            winners = valid[valid['总盈亏'].notna() & (valid['总盈亏'] > 0)]
            losers = valid[valid['总盈亏'].notna() & (valid['总盈亏'] <= 0)]
            lines.append("")
            lines.append(f"── 盈利品种: {len(winners)} / {len(valid)} ──")
            total_pnl = valid['总盈亏'].sum()
            lines.append(f"  投资组合总盈亏: RMB{total_pnl:,.2f}")

            # 排序统计
            top3 = valid.head(3)
            bottom3 = valid.tail(3)
            lines.append("")
            lines.append("── 最佳/最差品种 ──")
            for _, row in top3.iterrows():
                lines.append(f"  + {row['品种']:4s} ({row['名称']:6s})  "
                             f"收益: {row['总收益率%']:>6.1f}%  "
                             f"利润因子: {row['利润因子']:>5.2f}")
            for _, row in bottom3.iterrows():
                lines.append(f"  - {row['品种']:4s} ({row['名称']:6s})  "
                             f"收益: {row['总收益率%']:>6.1f}%  "
                             f"利润因子: {row['利润因子']:>5.2f}")

        lines.extend(["=" * 62, ""])
        summary_text = '\n'.join(lines)
    else:
        summary_text = "[ERROR] 无有效投资组合数据\n"

    # 写入文件
    summary_path = os.path.join(output_dir, 'portfolio_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print(f"  [OK] {summary_path}")

    # ── 组合权益曲线 ──
    if not portfolio_equity.empty:
        eq_path = os.path.join(output_dir, 'portfolio_equity_curve.csv')
        cols = ['total_equity', 'daily_return']
        eq_out = portfolio_equity[cols].copy()
        eq_out.to_csv(eq_path, encoding='utf-8-sig')
        print(f"  [OK] {eq_path}")

    # ── 组合指标 JSON ──
    if metrics and 'error' not in metrics:
        clean = {}
        for k, v in metrics.items():
            if isinstance(v, (np.integer,)):
                clean[k] = int(v)
            elif isinstance(v, (np.floating,)):
                clean[k] = float(v)
            else:
                clean[k] = v
        metrics_path = os.path.join(output_dir, 'portfolio_metrics.json')
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {metrics_path}")

    # ── 品种对比 CSV ──
    if not product_summary.empty:
        comp_path = os.path.join(output_dir, 'product_comparison.csv')
        product_summary.to_csv(comp_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] {comp_path}")

    # ── 各品种明细 ──
    products_dir = os.path.join(output_dir, 'products')
    saved_count = 0
    for code, result in product_results.items():
        if result['success']:
            product_dir = os.path.join(products_dir, code)
            save_report(result['report'], product_dir)
            saved_count += 1
    print(f"  [OK] 已保存 {saved_count} 个品种明细至 {products_dir}")

    print(f"\n  投资组合报告保存至: {output_dir}")

    return {
        'summary_text': summary_text,
        'portfolio_equity': portfolio_equity,
        'metrics': metrics,
        'product_summary': product_summary,
    }
