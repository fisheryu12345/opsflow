"""
Compare ATR periods 14, 20, 26 — trend_factor distribution and cross-product uniformity.

Generates an HTML report with distribution comparison, uniformity analysis, and
product-level stats.

Usage:
    python manage.py compare_atr_periods
    python manage.py compare_atr_periods --output /path/to/report.html
"""
import os
import numpy as np
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import connection
from stock.core.indicators import compute_trend_factor_from_backtest

GAP_ATR_LIMIT = 2.0
TREND_FACTOR_MAX = 0.5
ATR_PERIODS = [14, 20, 26]
ACCOUNT_NAME = '510976'

DEFAULT_OUTPUT_DIR = r"C:\Users\dell\.claude\skills\parameter-scanner-workspace\iteration-1\eval-1\without_skill\outputs"


def compute_atr_sma(high, low, close, period):
    """Compute ATR as SMA of True Range over N periods."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(close)
    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_close),
                               np.abs(low - prev_close)))
    atr = np.full(n, np.nan)
    for i in range(period - 1, n):
        atr[i] = np.mean(tr[i - period + 1:i + 1])
    return atr


class Command(BaseCommand):
    help = 'Compare ATR periods 14, 20, 26 for trend_factor distribution'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output HTML file path')

    def handle(self, *args, **options):
        output_path = options.get('output')
        if not output_path:
            os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(
                DEFAULT_OUTPUT_DIR,
                f"parameter_scan_ATR_PERIOD_{datetime.now().strftime('%Y%m%d')}.html"
            )

        self.stdout.write("Fetching active products...")
        with connection.cursor() as cur:
            cur.execute("""
                SELECT acc.product_code
                FROM stock_accountcontractconfig acc
                JOIN stock_tradingaccount ta ON acc.account_id = ta.id
                WHERE ta.name = %s AND acc.is_active = 1
            """, [ACCOUNT_NAME])
            codes = sorted([r[0] for r in cur.fetchall()])

        self.stdout.write(f"Found {len(codes)} active products: {', '.join(codes)}")

        # Fetch kline data for all products
        all_records = []
        for code in codes:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT date, open, high, low, close, ma_10, ma_20, ma_40
                    FROM stock_klinedata
                    WHERE product_code = %s
                    ORDER BY date
                """, [code])
                rows = cur.fetchall()

            if len(rows) < 30:
                self.stdout.write(f"  {code}: only {len(rows)} rows, skipping")
                continue

            dates = [r[0] for r in rows]
            opens = [float(r[1]) for r in rows]
            highs = [float(r[2]) for r in rows]
            lows = [float(r[3]) for r in rows]
            closes = [float(r[4]) for r in rows]
            ma10_vals = [float(r[5]) if r[5] is not None else None for r in rows]
            ma20_vals = [float(r[6]) if r[6] is not None else None for r in rows]
            ma40_vals = [float(r[7]) if r[7] is not None else None for r in rows]

            # Compute ATR for each period from raw OHLC
            atr_result = {}
            for p in ATR_PERIODS:
                atr_result[p] = compute_atr_sma(highs, lows, closes, p)

            max_period = max(ATR_PERIODS)
            for i in range(max_period - 1, len(rows)):
                ma10 = ma10_vals[i]
                ma20 = ma20_vals[i]
                ma40 = ma40_vals[i]
                if ma10 is None or ma20 is None or ma40 is None:
                    continue

                row_data = {
                    'product': code,
                    'date': str(dates[i]),
                    'close': closes[i],
                }

                valid_row = True
                for p in ATR_PERIODS:
                    atr_val = atr_result[p][i]
                    if np.isnan(atr_val):
                        valid_row = False
                        break
                    tf, label = compute_trend_factor_from_backtest(
                        ma10, ma20, ma40, atr=atr_val,
                        gap_atr_limit=GAP_ATR_LIMIT,
                        trend_factor_max=TREND_FACTOR_MAX
                    )
                    row_data[f'atr_{p}'] = atr_val
                    row_data[f'tf_{p}'] = tf
                    row_data[f'label_{p}'] = label

                if valid_row:
                    row_data['ma10'] = ma10
                    row_data['ma20'] = ma20
                    row_data['ma40'] = ma40
                    all_records.append(row_data)

        total = len(all_records)
        self.stdout.write(f"Total data points: {total}")
        if total == 0:
            self.stdout.write(self.style.ERROR("No data available. Aborting."))
            return

        # ========== ANALYSIS ==========
        labels = ['strong_bull', 'weak_bull', 'choppy', 'weak_bear', 'strong_bear']
        buckets = [(0, 0, '=0'), (0, 0.1, '0-0.1'), (0.1, 0.2, '0.1-0.2'),
                   (0.2, 0.3, '0.2-0.3'), (0.3, 0.4, '0.3-0.4'), (0.4, 0.5, '0.4-0.5')]

        def bucket_count(records, tf_key, lo, hi):
            if lo == 0 and hi == 0:
                return sum(1 for r in records if r[tf_key] == 0)
            return sum(1 for r in records if lo <= r[tf_key] < hi)

        def period_stats(records, tf_key):
            vals = [r[tf_key] for r in records]
            pos_vals = [v for v in vals if v > 0]
            return {
                'n': len(vals), 'n_pos': len(pos_vals),
                'pct_pos': len(pos_vals) / len(vals) * 100 if vals else 0,
                'mean_all': float(np.mean(vals)) if vals else 0,
                'mean_pos': float(np.mean(pos_vals)) if pos_vals else 0,
                'median_pos': float(np.median(pos_vals)) if pos_vals else 0,
                'std_pos': float(np.std(pos_vals)) if len(pos_vals) > 1 else 0,
                'p50': float(np.percentile(pos_vals, 50)) if pos_vals else 0,
                'p75': float(np.percentile(pos_vals, 75)) if pos_vals else 0,
                'p90': float(np.percentile(pos_vals, 90)) if pos_vals else 0,
                'p95': float(np.percentile(pos_vals, 95)) if pos_vals else 0,
                'p99': float(np.percentile(pos_vals, 99)) if pos_vals else 0,
            }

        def label_dist(records, label_key):
            dist = {l: 0 for l in labels}
            for r in records:
                lbl = r[label_key]
                if lbl in dist:
                    dist[lbl] += 1
            return dist

        def product_stats(records, tf_key, label_key):
            prod_data = {}
            for r in records:
                p = r['product']
                if p not in prod_data:
                    prod_data[p] = {'vals': [], 'pos_vals': [], 'labels': []}
                prod_data[p]['vals'].append(r[tf_key])
                if r[tf_key] > 0:
                    prod_data[p]['pos_vals'].append(r[tf_key])
                prod_data[p]['labels'].append(r[label_key])

            stats = []
            for p, d in sorted(prod_data.items()):
                n = len(d['vals'])
                pv = d['pos_vals']
                ls = d['labels']
                if n == 0:
                    continue
                stats.append({
                    'product': p, 'n': n,
                    'mean_tf': float(np.mean(pv)) if pv else 0,
                    'median_tf': float(np.median(pv)) if pv else 0,
                    'std_tf': float(np.std(pv)) if len(pv) > 1 else 0,
                    'saturation': sum(1 for v in pv if v >= 0.45) / n * 100,
                    'pct_strong': sum(1 for l in ls if l.startswith('strong')) / n * 100,
                    'pct_weak': sum(1 for l in ls if l.startswith('weak')) / n * 100,
                    'pct_choppy': sum(1 for l in ls if l == 'choppy') / n * 100,
                })
            return stats

        def uniformity(prod_stats_list):
            means = [p['mean_tf'] for p in prod_stats_list if p['mean_tf'] > 0]
            if not means:
                return {}
            return {
                'mean': float(np.mean(means)),
                'std': float(np.std(means)),
                'cv': float(np.std(means) / np.mean(means)) if np.mean(means) > 0 else 0,
                'min': float(min(means)),
                'max': float(max(means)),
                'range': float(max(means) - min(means)),
                'max_dev_pct': float(max(abs(m / np.mean(means) - 1) for m in means) * 100),
            }

        def confusion_matrix(records, label_a, label_b):
            cm = {o: {n: 0 for n in labels} for o in labels}
            for r in records:
                cm[r[label_a]][r[label_b]] += 1
            return cm

        # Compute all stats
        period_stats_dict = {}
        bucket_data = {}
        label_dist_data = {}
        prod_stats_data = {}
        uniformity_data = {}
        mean_atr_per_product = {}
        rank_data = {}

        for p in ATR_PERIODS:
            tf_key = f'tf_{p}'
            label_key = f'label_{p}'

            period_stats_dict[p] = period_stats(all_records, tf_key)

            bucket_data[p] = []
            for lo, hi, name in buckets:
                bc = bucket_count(all_records, tf_key, lo, hi)
                bucket_data[p].append((name, bc, bc / total * 100))

            label_dist_data[p] = label_dist(all_records, label_key)

            ps = product_stats(all_records, tf_key, label_key)
            prod_stats_data[p] = ps

            uniformity_data[p] = uniformity(ps)

            # Mean ATR per product
            mean_atr_per_product[p] = {}
            for r in all_records:
                prod = r['product']
                atr = r[f'atr_{p}']
                if prod not in mean_atr_per_product[p]:
                    mean_atr_per_product[p][prod] = []
                mean_atr_per_product[p][prod].append(atr)
            for prod in mean_atr_per_product[p]:
                mean_atr_per_product[p][prod] = float(np.mean(mean_atr_per_product[p][prod]))

            # Ranking
            sorted_ps = sorted(ps, key=lambda x: x['mean_tf'], reverse=True)
            rank_data[p] = {item['product']: idx + 1 for idx, item in enumerate(sorted_ps)}

        # Agreement
        agreement_14_20 = sum(1 for r in all_records if r['label_14'] == r['label_20'])
        agreement_14_26 = sum(1 for r in all_records if r['label_14'] == r['label_26'])
        agreement_20_26 = sum(1 for r in all_records if r['label_20'] == r['label_26'])
        all_three_agree = sum(1 for r in all_records if r['label_14'] == r['label_20'] == r['label_26'])

        # TF difference stats
        tf_diff_stats = {}
        for p1, p2 in [(14, 20), (14, 26), (20, 26)]:
            diffs = [abs(r[f'tf_{p1}'] - r[f'tf_{p2}']) for r in all_records]
            tf_diff_stats[f'{p1}_vs_{p2}'] = {
                'mean_diff': float(np.mean(diffs)),
                'max_diff': float(max(diffs)),
                'std_diff': float(np.std(diffs)),
                'pct_identical': sum(1 for d in diffs if d == 0) / len(diffs) * 100,
                'pct_small_diff': sum(1 for d in diffs if d < 0.05) / len(diffs) * 100,
            }

        # Rank correlation
        def rank_correlation(rank_a, rank_b):
            common = set(rank_a.keys()) & set(rank_b.keys())
            if len(common) < 2:
                return 0
            ranks_a = [rank_a[c] for c in common]
            ranks_b = [rank_b[c] for c in common]
            n = len(common)
            d_sq = sum((ra - rb) ** 2 for ra, rb in zip(ranks_a, ranks_b))
            return 1 - 6 * d_sq / (n * (n ** 2 - 1))

        # ========== GENERATE HTML ==========
        def fmt(val, decimals=4):
            if isinstance(val, float):
                return f'{val:.{decimals}f}'
            return str(val)

        def fmt_pct(val):
            return f'{val:.1f}%'

        def bar(val, max_val, color='#4CAF50'):
            pct = val / max_val * 100 if max_val > 0 else 0
            return (f'<div style="width:200px;background:#eee;border-radius:3px;overflow:hidden">'
                    f'<div style="width:{pct:.1f}%;background:{color};height:18px;text-align:center;'
                    f'color:white;font-size:11px;line-height:18px">{fmt(val)}</div></div>')

        def html_table(headers, rows):
            h = '<thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead>'
            b = '<tbody>'
            for row in rows:
                b += '<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>'
            b += '</tbody>'
            return f'<table>{h}{b}</table>'

        all_products = sorted(set(ps['product'] for ps in prod_stats_data[ATR_PERIODS[0]]))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ATR Period Comparison — trend_factor Analysis</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f7fa; color: #333; }}
h1 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 8px; }}
h2 {{ color: #283593; margin-top: 30px; border-bottom: 1px solid #c5cae9; padding-bottom: 4px; }}
h3 {{ color: #3949ab; margin-top: 20px; }}
table {{ border-collapse: collapse; margin: 10px 0 20px 0; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #303f9f; color: white; padding: 8px 12px; text-align: center; }}
td {{ padding: 6px 12px; border: 1px solid #ddd; text-align: center; }}
tr:nth-child(even) {{ background: #f8f9ff; }}
tr:hover {{ background: #e8eaf6; }}
.summary-card {{ display: inline-block; background: white; border-radius: 8px; padding: 16px 24px; margin: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-width: 200px; }}
.summary-card .label {{ font-size: 12px; color: #666; }}
.summary-card .value {{ font-size: 24px; font-weight: bold; color: #1a237e; }}
.flex {{ display: flex; flex-wrap: wrap; }}
.note {{ background: #e3f2fd; border-left: 4px solid #1976d2; padding: 12px 16px; margin: 16px 0; border-radius: 4px; }}
</style>
</head>
<body>

<h1>ATR Period Comparison: trend_factor Distribution and Cross-Product Uniformity</h1>

<div class="note">
    <strong>Parameters:</strong> GAP_ATR_LIMIT = {GAP_ATR_LIMIT}, TREND_FACTOR_MAX = {TREND_FACTOR_MAX}<br>
    <strong>Data:</strong> {total} data points across {len(codes)} active products (account {ACCOUNT_NAME})<br>
    <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>

<div class="flex">
    <div class="summary-card">
        <div class="label">Total Data Points</div>
        <div class="value">{total}</div>
    </div>
    <div class="summary-card">
        <div class="label">Active Products</div>
        <div class="value">{len(codes)}</div>
    </div>
    <div class="summary-card">
        <div class="label">ATR Periods</div>
        <div class="value">{', '.join(str(p) for p in ATR_PERIODS)}</div>
    </div>
</div>

<h2>1. Trend Factor Distribution Comparison</h2>

<h3>1.1 Bucket Distribution</h3>
"""
        headers = ['Bucket']
        for p in ATR_PERIODS:
            headers += [f'ATR{p} Count', f'ATR{p} %']
        rows = []
        for bi, (lo, hi, name) in enumerate(buckets):
            row = [name]
            for p in ATR_PERIODS:
                _, bc, bp = bucket_data[p][bi]
                row += [str(bc), fmt_pct(bp)]
            rows.append(tuple(row))
        html += html_table(headers, rows)

        # Bar visualization
        html += '<h3>1.2 Distribution Visualization (% of total)</h3><table>'
        html += '<tr><th>Bucket</th>'
        for p in ATR_PERIODS:
            html += f'<th>ATR{p}</th>'
        html += '</tr>'
        for bi, (lo, hi, name) in enumerate(buckets):
            html += f'<tr><td><strong>{name}</strong></td>'
            for p in ATR_PERIODS:
                _, bc, bp = bucket_data[p][bi]
                color = '#FF9800' if name == '=0' else '#4CAF50'
                html += f'<td>{bar(bp, 100, color)}</td>'
            html += '</tr>'
        html += '</table>'

        # Statistics
        html += '<h3>1.3 Key Statistics</h3>'
        headers = ['Metric']
        for p in ATR_PERIODS:
            headers += [f'ATR{p}']
        rows = [
            ('Sample size', *(str(period_stats_dict[p]['n']) for p in ATR_PERIODS)),
            ('Non-zero count', *(str(period_stats_dict[p]['n_pos']) for p in ATR_PERIODS)),
            ('Non-zero %', *(fmt_pct(period_stats_dict[p]['pct_pos']) for p in ATR_PERIODS)),
            ('Mean (all)', *(fmt(period_stats_dict[p]['mean_all']) for p in ATR_PERIODS)),
            ('Mean (pos. only)', *(fmt(period_stats_dict[p]['mean_pos']) for p in ATR_PERIODS)),
            ('Median (pos. only)', *(fmt(period_stats_dict[p]['median_pos']) for p in ATR_PERIODS)),
            ('Std (pos. only)', *(fmt(period_stats_dict[p]['std_pos']) for p in ATR_PERIODS)),
        ]
        html += html_table(headers, rows)

        # Quantiles
        html += '<h3>1.4 Quantiles (positive trend_factor)</h3>'
        quantile_labels = [('P50 (Median)', 'p50'), ('P75', 'p75'), ('P90', 'p90'), ('P95', 'p95'), ('P99', 'p99')]
        rows = []
        for ql, qk in quantile_labels:
            row = [ql]
            for p in ATR_PERIODS:
                row.append(fmt(period_stats_dict[p][qk]))
            rows.append(tuple(row))
        html += html_table(['Metric'] + [f'ATR{p}' for p in ATR_PERIODS], rows)

        # Label distribution
        html += '<h3>1.5 Label Distribution</h3>'
        headers = ['Label']
        for p in ATR_PERIODS:
            headers += [f'ATR{p} Count', f'ATR{p} %']
        rows = []
        for lbl in labels:
            row = [lbl]
            for p in ATR_PERIODS:
                cnt = label_dist_data[p][lbl]
                row += [str(cnt), fmt_pct(cnt / total * 100)]
            rows.append(tuple(row))
        html += html_table(headers, rows)

        html += '<h3>1.6 Sentiment Summary</h3>'
        headers = ['Sentiment']
        for p in ATR_PERIODS:
            headers += [f'ATR{p} %']
        rows = []
        for senti, key_lbl in [('Strong (bull+bear)', 'strong'), ('Weak (bull+bear)', 'weak'), ('Choppy', 'choppy')]:
            row = [senti]
            for p in ATR_PERIODS:
                if key_lbl == 'choppy':
                    s = label_dist_data[p]['choppy']
                else:
                    s = sum(cnt for lbl, cnt in label_dist_data[p].items() if lbl.startswith(key_lbl))
                row.append(fmt_pct(s / total * 100))
            rows.append(tuple(row))
        html += html_table(headers, rows)

        # ===== SECTION 2: AGREEMENT =====
        html += '<h2>2. Label Agreement Between ATR Periods</h2>'
        headers = ['Comparison', 'Agreement Count', 'Agreement %']
        rows = [
            ('ATR14 vs ATR20', str(agreement_14_20), fmt_pct(agreement_14_20 / total * 100)),
            ('ATR14 vs ATR26', str(agreement_14_26), fmt_pct(agreement_14_26 / total * 100)),
            ('ATR20 vs ATR26', str(agreement_20_26), fmt_pct(agreement_20_26 / total * 100)),
            ('All three agree', str(all_three_agree), fmt_pct(all_three_agree / total * 100)),
        ]
        html += html_table(headers, rows)

        # Confusion matrices
        cm_14_20 = confusion_matrix(all_records, 'label_14', 'label_20')
        html += '<h3>2.1 Confusion Matrix: ATR14 (rows) vs ATR20 (cols)</h3>'
        headers = ['ATR14 \\ ATR20'] + labels
        rows = [[o] + [str(cm_14_20[o][n]) for n in labels] for o in labels]
        html += html_table(headers, rows)

        cm_14_26 = confusion_matrix(all_records, 'label_14', 'label_26')
        html += '<h3>2.2 Confusion Matrix: ATR14 (rows) vs ATR26 (cols)</h3>'
        rows = [[o] + [str(cm_14_26[o][n]) for n in labels] for o in labels]
        html += html_table(headers, rows)

        cm_20_26 = confusion_matrix(all_records, 'label_20', 'label_26')
        html += '<h3>2.3 Confusion Matrix: ATR20 (rows) vs ATR26 (cols)</h3>'
        rows = [[o] + [str(cm_20_26[o][n]) for n in labels] for o in labels]
        html += html_table(headers, rows)

        html += '<h3>2.4 Trend Factor Difference Statistics</h3>'
        headers = ['Comparison', 'Mean |diff|', 'Max |diff|', 'Std |diff|', '% Identical', '% |diff| < 0.05']
        rows = []
        for pair_label, pair_key in [('ATR14 vs ATR20', '14_vs_20'), ('ATR14 vs ATR26', '14_vs_26'), ('ATR20 vs ATR26', '20_vs_26')]:
            d = tf_diff_stats[pair_key]
            rows.append((pair_label, fmt(d['mean_diff']), fmt(d['max_diff']), fmt(d['std_diff']),
                         fmt_pct(d['pct_identical']), fmt_pct(d['pct_small_diff'])))
        html += html_table(headers, rows)

        # ===== SECTION 3: PRODUCT-LEVEL =====
        html += '<h2>3. Product-Level Statistics</h2>'
        for idx, p in enumerate(ATR_PERIODS):
            html += f'<h3>3.{idx + 1} ATR{p} — Product Details</h3>'
            headers = ['Product', 'N', 'Mean TF', 'Median TF', 'Std TF', 'Saturation (>=0.45)',
                       '% Strong', '% Weak', '% Choppy']
            rows = []
            for ps in prod_stats_data[p]:
                rows.append((ps['product'], str(ps['n']), fmt(ps['mean_tf']), fmt(ps['median_tf']),
                             fmt(ps['std_tf']), fmt_pct(ps['saturation']),
                             fmt_pct(ps['pct_strong']), fmt_pct(ps['pct_weak']), fmt_pct(ps['pct_choppy'])))
            html += html_table(headers, rows)

        # ===== SECTION 4: UNIFORMITY =====
        html += '<h2>4. Cross-Product Uniformity Analysis</h2>'
        headers = ['Metric']
        for p in ATR_PERIODS:
            headers += [f'ATR{p}']
        rows = [
            ('Mean of product means', *(fmt(uniformity_data[p].get('mean', 0)) for p in ATR_PERIODS)),
            ('Std of product means', *(fmt(uniformity_data[p].get('std', 0)) for p in ATR_PERIODS)),
            ('CV (std/mean)', *(fmt(uniformity_data[p].get('cv', 0)) for p in ATR_PERIODS)),
            ('Min product mean', *(fmt(uniformity_data[p].get('min', 0)) for p in ATR_PERIODS)),
            ('Max product mean', *(fmt(uniformity_data[p].get('max', 0)) for p in ATR_PERIODS)),
            ('Range (max-min)', *(fmt(uniformity_data[p].get('range', 0)) for p in ATR_PERIODS)),
            ('Max deviation from mean', *(fmt_pct(uniformity_data[p].get('max_dev_pct', 0)) for p in ATR_PERIODS)),
        ]
        html += html_table(headers, rows)

        # Product ranking
        html += '<h3>4.1 Product Ranking by Mean TF</h3>'
        headers = ['Product']
        for p in ATR_PERIODS:
            headers += [f'ATR{p} Mean', f'ATR{p} Rank']
        rows = []
        for prod in all_products:
            row = [prod]
            for p in ATR_PERIODS:
                match = [x for x in prod_stats_data[p] if x['product'] == prod]
                if match:
                    row += [fmt(match[0]['mean_tf']), str(rank_data[p].get(prod, '-'))]
                else:
                    row += ['-', '-']
            rows.append(tuple(row))
        html += html_table(headers, rows)

        # Rank stability
        html += '<h3>4.2 Rank Stability (Spearman Correlation)</h3>'
        headers = ['Comparison', 'Spearman Rho']
        rows = [
            ('ATR14 vs ATR20', fmt(rank_correlation(rank_data[14], rank_data[20]), 4)),
            ('ATR14 vs ATR26', fmt(rank_correlation(rank_data[14], rank_data[26]), 4)),
            ('ATR20 vs ATR26', fmt(rank_correlation(rank_data[20], rank_data[26]), 4)),
        ]
        html += html_table(headers, rows)

        # Raw ATR comparison
        html += '<h3>4.3 Raw ATR Cross-Product (mean ATR per product)</h3>'
        headers = ['Product']
        for p in ATR_PERIODS:
            headers += [f'Mean ATR{p}']
        rows = []
        for prod in sorted(mean_atr_per_product[ATR_PERIODS[0]].keys()):
            row = [prod]
            for p in ATR_PERIODS:
                row.append(fmt(mean_atr_per_product[p].get(prod, 0), 2))
            rows.append(tuple(row))
        html += html_table(headers, rows)

        html += '<h3>4.4 ATR Cross-Product Uniformity</h3>'
        headers = ['Metric']
        for p in ATR_PERIODS:
            headers += [f'ATR{p}']
        rows = []
        for metric, fn in [('Mean across products', np.mean), ('Std across products', np.std),
                           ('CV', lambda x: np.std(x) / np.mean(x) if np.mean(x) > 0 else 0),
                           ('Min', np.min), ('Max', np.max)]:
            vals = [list(mean_atr_per_product[p].values()) for p in ATR_PERIODS]
            row = [metric]
            for j, p in enumerate(ATR_PERIODS):
                row.append(fmt(float(fn(vals[j])), 2))
            rows.append(tuple(row))
        html += html_table(headers, rows)

        # ===== SECTION 5: STOP-LOSS IMPACT =====
        html += '<h2>5. Stop-Loss Impact (stop = 2 * (1 + tf) * ATR)</h2>'
        headers = ['Product']
        for p in ATR_PERIODS:
            headers += [f'ATR{p} Mean Stop']
        headers += ['Mean ATR20']
        rows = []
        for prod in all_products:
            prod_records = [r for r in all_records if r['product'] == prod]
            if not prod_records:
                continue
            row = [prod]
            for p in ATR_PERIODS:
                stops = [2 * (1 + r[f'tf_{p}']) * r[f'atr_{p}'] for r in prod_records]
                row.append(fmt(float(np.mean(stops)), 1))
            row.append(fmt(float(np.mean([r['atr_20'] for r in prod_records])), 1))
            rows.append(tuple(row))
        html += html_table(headers, rows)

        html += '<h3>5.1 Overall Average Stop Distance</h3>'
        rows = []
        for p in ATR_PERIODS:
            all_stops = [2 * (1 + r[f'tf_{p}']) * r[f'atr_{p}'] for r in all_records]
            rows.append((f'ATR{p}', fmt(float(np.mean(all_stops)), 1)))
        html += html_table(['ATR Period', 'Mean Stop Distance'], rows)

        # ===== SECTION 6: KEY FINDINGS =====
        html += '<h2>6. Key Findings</h2><ul>'

        best_mean = max(ATR_PERIODS, key=lambda p: period_stats_dict[p]['mean_pos'])
        html += f'<li>Highest mean trend_factor (positive): ATR{best_mean} ({fmt(period_stats_dict[best_mean]["mean_pos"])})</li>'

        lowest_mean = min(ATR_PERIODS, key=lambda p: period_stats_dict[p]['mean_pos'])
        html += f'<li>Lowest mean trend_factor (positive): ATR{lowest_mean} ({fmt(period_stats_dict[lowest_mean]["mean_pos"])})</li>'

        best_uniform = min(ATR_PERIODS, key=lambda p: uniformity_data[p].get('cv', 999))
        html += f'<li>Best cross-product uniformity (lowest CV): ATR{best_uniform} (CV={fmt(uniformity_data[best_uniform].get("cv", 0))})</li>'

        worst_uniform = max(ATR_PERIODS, key=lambda p: uniformity_data[p].get('cv', 0))
        html += f'<li>Worst cross-product uniformity (highest CV): ATR{worst_uniform} (CV={fmt(uniformity_data[worst_uniform].get("cv", 0))})</li>'

        html += f'<li>Label agreement (all three periods): {all_three_agree}/{total} ({fmt_pct(all_three_agree / total * 100)})</li>'

        for p in ATR_PERIODS:
            strong_cnt = label_dist_data[p]['strong_bull'] + label_dist_data[p]['strong_bear']
            html += f'<li>ATR{p} strong label rate: {fmt_pct(strong_cnt / total * 100)}</li>'

        for p in ATR_PERIODS:
            html += f'<li>ATR{p} choppy rate: {fmt_pct(label_dist_data[p]["choppy"] / total * 100)}</li>'

        html += '</ul>'

        # ===== SECTION 7: SENTIMENT =====
        html += '<h2>7. Period-by-Period Sentiment Breakdown</h2>'
        for p in ATR_PERIODS:
            html += f'<h3>ATR{p}</h3>'
            headers = ['Category', 'Count', 'Percentage']
            rows = []
            for lbl in labels:
                rows.append((lbl, str(label_dist_data[p][lbl]), fmt_pct(label_dist_data[p][lbl] / total * 100)))
            html += html_table(headers, rows)

        html += '\n</body>\n</html>'

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        self.stdout.write(self.style.SUCCESS(f"Report saved to: {output_path}"))
        self.stdout.write(f"File size: {os.path.getsize(output_path):,} bytes")
