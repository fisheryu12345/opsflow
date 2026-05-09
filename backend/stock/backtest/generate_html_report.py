"""
Generate self-contained HTML backtest report with embedded ECharts charts.

Usage:
    python -m stock.backtest.generate_html_report
    python -m stock.backtest.generate_html_report --results-dir results/portfolio_2019_2026
"""
import os
import sys
import json
import argparse
import csv
import numpy as np
from datetime import datetime

from stock.backtest.product_data import PRODUCTS

PRODUCT_MAP = {p.code: p for p in PRODUCTS}


def compute_drawdown(equity_values: list[float]) -> list[float]:
    """Compute drawdown percentage from equity array (running peak → trough)."""
    peak = -float('inf')
    result = []
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100 if peak > 0 else 0.0
        result.append(round(dd, 2))
    return result


def read_csv_columnar(filepath: str, *columns: str) -> dict:
    """Read a CSV and extract specified columns as lists.
    Returns {col_name: [values...]}.
    """
    result = {c: [] for c in columns}
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for c in columns:
                val = row.get(c, '')
                try:
                    result[c].append(float(val))
                except (ValueError, TypeError):
                    result[c].append(val)
    return result


def read_csv_rows(filepath: str) -> list[dict]:
    """Read a CSV into a list of dicts."""
    rows = []
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def reshape_monthly_returns(filepath: str) -> dict:
    """Read monthly returns CSV and reshape to heatmap format.
    Returns {years: [...], months: [...], values: [[y_idx, m_idx, val], ...]}
    """
    rows = read_csv_rows(filepath)
    if not rows:
        return {'years': [], 'months': [], 'values': []}

    months = ['1月', '2月', '3月', '4月', '5月', '6月',
              '7月', '8月', '9月', '10月', '11月', '12月']
    years = []
    values = []

    for row in rows:
        try:
            year = int(row.get('year', 0))
        except (ValueError, TypeError):
            continue
        years.append(year)

    years = sorted(set(years))
    year_to_idx = {y: i for i, y in enumerate(years)}

    for row in rows:
        try:
            year = int(row.get('year', 0))
        except (ValueError, TypeError):
            continue
        for mi, mname in enumerate(months):
            raw = row.get(mname, '')
            if raw == '' or raw is None:
                continue
            try:
                val = float(raw)
            except (ValueError, TypeError):
                continue
            if not (np.isnan(val) or np.isinf(val)):
                values.append([year_to_idx[year], mi, round(val, 2)])

    return {'years': years, 'months': months, 'values': values}


def load_all_data(results_dir: str) -> dict:
    """Load all result files from the results directory."""
    # ── Portfolio level ──
    portfolio_metrics = {}
    metrics_path = os.path.join(results_dir, 'portfolio_metrics.json')
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding='utf-8') as f:
            portfolio_metrics = json.load(f)

    portfolio_equity = {'dates': [], 'equity': [], 'daily_returns': [], 'drawdown_pct': []}
    eq_path = os.path.join(results_dir, 'portfolio_equity_curve.csv')
    if os.path.exists(eq_path):
        raw = read_csv_columnar(eq_path, 'date', 'total_equity', 'daily_return')
        portfolio_equity['dates'] = raw.get('date', [])
        portfolio_equity['equity'] = raw.get('total_equity', [])
        portfolio_equity['daily_returns'] = raw.get('daily_return', [])
        portfolio_equity['drawdown_pct'] = compute_drawdown(portfolio_equity['equity'])

    # ── Product comparison ──
    product_comparison = []
    comp_path = os.path.join(results_dir, 'product_comparison.csv')
    if os.path.exists(comp_path):
        product_comparison = read_csv_rows(comp_path)

    # ── Per-product data ──
    products_dir = os.path.join(results_dir, 'products')
    products_data = {}

    if os.path.isdir(products_dir):
        for code in sorted(os.listdir(products_dir)):
            pdir = os.path.join(products_dir, code)
            if not os.path.isdir(pdir):
                continue

            info = PRODUCT_MAP.get(code)
            pdata = {
                'code': code,
                'name': info.name if info else code.upper(),
                'exchange': info.exchange if info else '',
            }

            # metrics.json
            mp = os.path.join(pdir, 'metrics.json')
            if os.path.exists(mp):
                with open(mp, encoding='utf-8') as f:
                    pdata['metrics'] = json.load(f)

            # equity_curve.csv
            pdata['equity_curve'] = {'dates': [], 'equity': [], 'daily_returns': [], 'drawdown_pct': []}
            ep = os.path.join(pdir, 'equity_curve.csv')
            if os.path.exists(ep):
                raw = read_csv_columnar(ep, 'date', 'total_equity', 'daily_return')
                pdata['equity_curve']['dates'] = raw.get('date', [])
                pdata['equity_curve']['equity'] = raw.get('total_equity', [])
                pdata['equity_curve']['daily_returns'] = raw.get('daily_return', [])
                pdata['equity_curve']['drawdown_pct'] = compute_drawdown(pdata['equity_curve']['equity'])

            # monthly_returns.csv
            mp_path = os.path.join(pdir, 'monthly_returns.csv')
            if os.path.exists(mp_path):
                pdata['monthly_returns'] = reshape_monthly_returns(mp_path)
            else:
                pdata['monthly_returns'] = {'years': [], 'months': [], 'values': []}

            # trade_log.csv
            tp = os.path.join(pdir, 'trade_log.csv')
            if os.path.exists(tp):
                pdata['trade_log'] = read_csv_rows(tp)
            else:
                pdata['trade_log'] = []

            products_data[code] = pdata

    return {
        'portfolio_metrics': portfolio_metrics,
        'portfolio_equity': portfolio_equity,
        'product_comparison': product_comparison,
        'products': products_data,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def build_html(data: dict) -> str:
    """Build the complete self-contained HTML report string."""
    json_data = json.dumps(data, ensure_ascii=False, default=str)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>投资组合回测绩效报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
  "Microsoft YaHei", sans-serif; background: #f0f2f5; color: #1f1f1f; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px 16px; }}

/* Header */
.report-header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff; padding: 36px 40px; border-radius: 12px; margin-bottom: 24px; }}
.report-header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
.report-header .subtitle {{ font-size: 14px; opacity: 0.75; }}
.report-header .subtitle span {{ margin-right: 24px; }}

/* Section */
.section {{ background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.section h2 {{ font-size: 18px; font-weight: 600; margin-bottom: 16px;
  padding-bottom: 8px; border-bottom: 2px solid #f0f2f5; color: #1a1a2e; }}

/* Summary Cards */
.card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px; margin-bottom: 0; }}
.metric-card {{ background: #fff; border-radius: 8px; padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;
  border-top: 3px solid #1890ff; transition: transform 0.2s; }}
.metric-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
.metric-card .label {{ font-size: 13px; color: #8c8c8c; margin-bottom: 8px; }}
.metric-card .value {{ font-size: 24px; font-weight: 700; }}
.metric-card .value.positive {{ color: #00a854; }}
.metric-card .value.negative {{ color: #d93025; }}
.metric-card .value.neutral {{ color: #1890ff; }}

/* Card color accents */
.card-green {{ border-top-color: #00a854; }}
.card-red {{ border-top-color: #d93025; }}
.card-blue {{ border-top-color: #1890ff; }}
.card-orange {{ border-top-color: #fa8c16; }}

/* Charts */
.chart-container {{ width: 100%; height: 420px; }}
.chart-container-sm {{ width: 100%; height: 320px; }}

/* Tables */
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
thead {{ background: #fafafa; }}
th, td {{ padding: 10px 12px; text-align: right; border-bottom: 1px solid #f0f0f0;
  white-space: nowrap; }}
th {{ font-weight: 600; color: #595959; cursor: pointer; user-select: none; }}
th:hover {{ color: #1890ff; }}
th:first-child, td:first-child {{ text-align: left; }}
td.positive {{ color: #00a854; font-weight: 600; }}
td.negative {{ color: #d93025; font-weight: 600; }}
tr:hover td {{ background: #f5f7fa; }}
th .sort-arrow {{ margin-left: 4px; font-size: 11px; }}

/* Product details */
.product-section {{ margin-bottom: 16px; border-radius: 8px; overflow: hidden;
  border: 1px solid #e8e8e8; }}
.product-section summary {{ padding: 14px 20px; cursor: pointer;
  font-size: 15px; font-weight: 600; background: #fafafa;
  display: flex; align-items: center; gap: 12px; }}
.product-section summary:hover {{ background: #f0f2f5; }}
.product-section summary::-webkit-details-marker {{ display: none; }}
.product-section .summary-content {{ flex: 1; display: flex; align-items: center; gap: 16px; }}
.product-section .product-tag {{ display: inline-block; padding: 2px 10px;
  border-radius: 4px; font-size: 12px; font-weight: 600; }}
.tag-positive {{ background: #e6f7ec; color: #00a854; }}
.tag-negative {{ background: #fff1f0; color: #d93025; }}
.tag-win {{ background: #e6f7ec; color: #00a854; }}
.tag-loss {{ background: #fff1f0; color: #d93025; }}
.product-section .product-meta {{ font-size: 13px; font-weight: 400; color: #8c8c8c; }}
.product-section .product-content {{ padding: 20px; }}

/* Sub-tabs inside product */
.sub-tabs {{ display: flex; gap: 4px; margin-bottom: 16px; }}
.sub-tab {{ padding: 6px 16px; border-radius: 4px 4px 0 0; cursor: pointer;
  font-size: 13px; color: #595959; background: #f5f5f5; border: 1px solid #e8e8e8;
  border-bottom: none; }}
.sub-tab.active {{ background: #fff; color: #1890ff; font-weight: 600;
  border-bottom: 2px solid #1890ff; }}
.sub-tab:hover {{ color: #1890ff; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

/* Pagination */
.pagination {{ display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 12px; font-size: 13px; }}
.pagination button {{ padding: 4px 12px; border: 1px solid #d9d9d9;
  border-radius: 4px; background: #fff; cursor: pointer; font-size: 13px; }}
.pagination button:hover {{ border-color: #1890ff; color: #1890ff; }}
.pagination button:disabled {{ color: #d9d9d9; cursor: not-allowed;
  border-color: #d9d9d9; }}
.pagination .page-info {{ color: #8c8c8c; }}

/* Mini metric row */
.mini-metrics {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 16px;
  padding: 12px 16px; background: #fafafa; border-radius: 6px; font-size: 13px; }}
.mini-metrics .mm-item {{ }}
.mini-metrics .mm-label {{ color: #8c8c8c; margin-right: 4px; }}
.mini-metrics .mm-value {{ font-weight: 600; }}
.mini-metrics .mm-value.positive {{ color: #00a854; }}
.mini-metrics .mm-value.negative {{ color: #d93025; }}

/* Metrics table inside product */
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px; margin-bottom: 16px; }}
.metrics-grid .mg-item {{ padding: 10px 14px; background: #fafafa;
  border-radius: 6px; display: flex; justify-content: space-between; }}
.metrics-grid .mg-label {{ color: #8c8c8c; font-size: 13px; }}
.metrics-grid .mg-value {{ font-weight: 600; font-size: 13px; }}
.metrics-grid .mg-value.positive {{ color: #00a854; }}
.metrics-grid .mg-value.negative {{ color: #d93025; }}

/* Responsive */
@media (max-width: 768px) {{
  .card-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .report-header {{ padding: 20px; }}
  .report-header h1 {{ font-size: 20px; }}
  .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .chart-container {{ height: 300px; }}
  .mini-metrics {{ gap: 12px; }}
}}

/* Trade type badges */
.badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 11px; font-weight: 600; }}
.badge-entry {{ background: #e6f7ec; color: #00a854; }}
.badge-exit {{ background: #fff1f0; color: #d93025; }}
.badge-addon {{ background: #e6f7ff; color: #1890ff; }}
.badge-rollover {{ background: #fff7e6; color: #fa8c16; }}
.badge-force {{ background: #f5f5f5; color: #8c8c8c; }}
</style>
</head>
<body>
<div class="container" id="app"></div>

<script>
var REPORT_DATA = {json_data};

// ── Utilities ──
function fmtNum(n) {{
  if (n === null || n === undefined || n === '' || isNaN(n)) return '-';
  n = Number(n);
  return n.toLocaleString('zh-CN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
}}
function fmtPct(n) {{
  if (n === null || n === undefined || n === '' || isNaN(n)) return '-';
  n = Number(n);
  return n.toFixed(2) + '%';
}}
function fmtInt(n) {{
  if (n === null || n === undefined || n === '' || isNaN(n)) return '-';
  return Number(n).toLocaleString('zh-CN', {{maximumFractionDigits: 0}});
}}
function cls(val) {{
  if (val === null || val === undefined || val === '' || isNaN(val)) return '';
  return Number(val) >= 0 ? 'positive' : 'negative';
}}
function shortName(code) {{
  var map = {{'rb':'螺纹钢','hc':'热卷','al':'铝','fu':'燃油','ru':'橡胶',
    'sp':'纸浆','MA':'甲醇','TA':'PTA','SA':'纯碱','FG':'玻璃',
    'UR':'尿素','CF':'棉花','RM':'菜粕','AP':'苹果','SR':'白糖',
    'm':'豆粕','p':'棕榈','jd':'鸡蛋','lh':'生猪','si':'工业硅'}};
  return map[code] || code;
}}
function genId() {{ return 'p-' + Math.random().toString(36).substr(2, 9); }}

// ── Render Portfolio Summary Cards ──
function renderCards(data) {{
  var m = data.portfolio_metrics || {{}};
  if (!m.total_capital) return '';
  var totalPnl = m.final_equity - m.total_capital;
  var winners = 0, total = 0;
  (data.product_comparison || []).forEach(function(r) {{
    total++;
    if (r.总盈亏 && parseFloat(r.总盈亏) > 0) winners++;
  }});

  var cards = [
    {{ label: '总收益率', value: fmtPct(m.total_return_pct), cls: cls(m.total_return_pct), cardCls: 'card-green' }},
    {{ label: '年化收益率', value: fmtPct(m.cagr_pct), cls: cls(m.cagr_pct), cardCls: 'card-green' }},
    {{ label: '最大回撤', value: fmtPct(m.max_drawdown_pct), cls: 'negative', cardCls: 'card-red' }},
    {{ label: '夏普比率', value: m.sharpe_ratio !== undefined && m.sharpe_ratio !== null ? m.sharpe_ratio.toFixed(3) : '-', cls: cls(m.sharpe_ratio), cardCls: 'card-blue' }},
    {{ label: '总盈亏', value: (totalPnl >= 0 ? '+' : '') + fmtNum(totalPnl), cls: cls(totalPnl), cardCls: totalPnl >= 0 ? 'card-green' : 'card-red' }},
    {{ label: '盈利品种', value: winners + '/' + total, cls: 'neutral', cardCls: 'card-orange' }},
  ];

  var html = '<div class="card-grid">';
  cards.forEach(function(c) {{
    html += '<div class="metric-card ' + c.cardCls + '">'
      + '<div class="label">' + c.label + '</div>'
      + '<div class="value ' + c.cls + '">' + c.value + '</div>'
      + '</div>';
  }});
  html += '</div>';
  return html;
}}

// ── Render Portfolio Equity Chart (dual-axis) ──
function renderEquityChart(domId, eq) {{
  if (!eq || !eq.dates || eq.dates.length === 0) return;
  var chart = echarts.init(document.getElementById(domId));
  var dates = eq.dates;
  var equity = eq.equity;
  var dret = eq.daily_returns;

  var option = {{
    tooltip: {{
      trigger: 'axis',
      axisPointer: {{ type: 'cross' }},
      formatter: function(params) {{
        var date = params[0].axisValueLabel;
        var eqVal = '-', retVal = '-';
        params.forEach(function(p) {{
          if (p.seriesName === '组合权益') eqVal = fmtNum(p.value);
          if (p.seriesName === '日收益率') retVal = (p.value * 100).toFixed(2) + '%';
        }});
        return '<strong>' + date + '</strong><br/>'
          + '组合权益: ' + eqVal + '<br/>'
          + '日收益率: ' + retVal;
      }}
    }},
    legend: {{ data: ['组合权益', '日收益率'], bottom: 0, left: 'center' }},
    grid: {{ top: 20, bottom: 50, left: 60, right: 70 }},
    dataZoom: [
      {{ type: 'inside', start: 0, end: 100 }},
      {{ type: 'slider', start: 0, end: 100, bottom: 24, height: 20 }}
    ],
    xAxis: {{
      type: 'category', data: dates, boundaryGap: false,
      axisLabel: {{ rotate: 45, fontSize: 11 }},
      axisLine: {{ lineStyle: {{ color: '#e8e8e8' }} }}
    }},
    yAxis: [
      {{ type: 'value', name: '权益 (RMB)', nameTextStyle: {{ fontSize: 12 }},
         splitLine: {{ lineStyle: {{ type: 'dashed', color: '#f0f0f0' }} }},
         axisLabel: {{ formatter: function(v) {{ return v >= 10000 ? (v/10000).toFixed(0) + '万' : v; }} }} }},
      {{ type: 'value', name: '日收益率 %', nameTextStyle: {{ fontSize: 12 }},
         splitLine: {{ show: false }},
         axisLabel: {{ formatter: function(v) {{ return (v * 100).toFixed(1) + '%'; }} }} }}
    ],
    series: [
      {{
        name: '组合权益', type: 'line', data: equity, smooth: true,
        yAxisIndex: 0, symbol: 'none',
        lineStyle: {{ color: '#1890ff', width: 2 }},
        areaStyle: {{
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {{ offset: 0, color: 'rgba(24, 144, 255, 0.2)' }},
            {{ offset: 1, color: 'rgba(24, 144, 255, 0.02)' }}
          ])
        }}
      }},
      {{
        name: '日收益率', type: 'bar', data: dret, yAxisIndex: 1,
        itemStyle: {{
          color: function(params) {{
            return params.value >= 0 ? 'rgba(0, 168, 84, 0.6)' : 'rgba(217, 48, 37, 0.6)';
          }}
        }}
      }}
    ]
  }};
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}}

// ── Render Drawdown Chart ──
function renderDrawdownChart(domId, eq) {{
  if (!eq || !eq.drawdown_pct || eq.drawdown_pct.length === 0) return;
  var chart = echarts.init(document.getElementById(domId));
  var dd = eq.drawdown_pct;
  var dates = eq.dates;

  var option = {{
    tooltip: {{
      trigger: 'axis',
      formatter: function(params) {{
        var p = params[0];
        return '<strong>' + p.axisValueLabel + '</strong><br/>回撤: ' + p.value.toFixed(2) + '%';
      }}
    }},
    grid: {{ top: 20, bottom: 30, left: 60, right: 30 }},
    xAxis: {{ type: 'category', data: dates, boundaryGap: false,
      axisLabel: {{ rotate: 45, fontSize: 11, show: false }} }},
    yAxis: {{ type: 'value', name: '回撤 %', nameTextStyle: {{ fontSize: 12 }},
      min: 'dataMin', max: 2,
      splitLine: {{ lineStyle: {{ type: 'dashed', color: '#f0f0f0' }} }},
      axisLabel: {{ formatter: function(v) {{ return v.toFixed(1) + '%'; }} }} }},
    series: [{{
      type: 'line', data: dd, smooth: true, symbol: 'none',
      lineStyle: {{ color: '#fa8c16', width: 2 }},
      areaStyle: {{
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          {{ offset: 0, color: 'rgba(250, 140, 22, 0.3)' }},
          {{ offset: 1, color: 'rgba(250, 140, 22, 0.02)' }}
        ])
      }},
      markLine: {{
        silent: true,
        data: [{{
          type: 'min', name: '最大回撤',
          label: {{ formatter: '最大回撤: {{c}}%', position: 'insideEndTop', fontSize: 12,
            color: '#d93025' }},
          lineStyle: {{ color: '#d93025', type: 'dashed', width: 2 }}
        }}]
      }}
    }}]
  }};
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}}

// ── Render Portfolio Metrics Table ──
function renderMetricsTable(m) {{
  if (!m || !m.total_capital) return '';
  var totalPnl = m.final_equity - m.total_capital;
  var rows = [
    ['初始权益', fmtNum(m.total_capital), ''],
    ['最终权益', fmtNum(m.final_equity), cls(m.final_equity - m.total_capital)],
    ['总收益率', fmtPct(m.total_return_pct), cls(m.total_return_pct)],
    ['年化收益率 (CAGR)', fmtPct(m.cagr_pct), cls(m.cagr_pct)],
    ['年化波动率', fmtPct(m.annualized_vol_pct), ''],
    ['夏普比率', m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(3) : '-', cls(m.sharpe_ratio)],
    ['索提诺比率', m.sortino_ratio != null ? m.sortino_ratio.toFixed(3) : '-', cls(m.sortino_ratio)],
    ['卡玛比率', m.calmar_ratio != null ? m.calmar_ratio.toFixed(3) : '-', cls(m.calmar_ratio)],
    ['最大回撤', fmtPct(m.max_drawdown_pct), 'negative'],
    ['最大回撤金额', fmtNum(m.max_drawdown), 'negative'],
    ['交易天数', fmtInt(m.trading_days), ''],
    ['总盈亏', (totalPnl >= 0 ? '+' : '') + fmtNum(totalPnl), cls(totalPnl)],
  ];
  var html = '<div class="table-wrap"><table><thead><tr><th>指标</th><th>值</th></tr></thead><tbody>';
  rows.forEach(function(r) {{
    html += '<tr><td>' + r[0] + '</td><td class="' + r[2] + '">' + r[1] + '</td></tr>';
  }});
  html += '</tbody></table></div>';
  return html;
}}

// ── Product Comparison Table ──
function renderComparisonTable(data) {{
  var rows = data.product_comparison || [];
  if (rows.length === 0) return;

  var cols = ['品种', '名称', '总收益率%', '年化收益率%', '最大回撤%', '夏普比率',
    '索提诺比率', '卡玛比率', '总交易', '胜率%', '利润因子', '总盈亏'];

  var sortState = {{ col: null, asc: true }};

  function getVal(row, col) {{
    var v = row[col];
    if (v === undefined || v === null || v === '') return null;
    var n = parseFloat(v);
    return isNaN(n) ? v : n;
  }}

  function render(col, asc) {{
    var sorted = rows.slice();
    if (col) {{
      sorted.sort(function(a, b) {{
        var va = getVal(a, col), vb = getVal(b, col);
        if (va === null && vb === null) return 0;
        if (va === null) return 1;
        if (vb === null) return -1;
        if (typeof va === 'number' && typeof vb === 'number') {{
          return asc ? va - vb : vb - va;
        }}
        return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      }});
    }}

    var html = '<div class="table-wrap"><table class="sortable"><thead><tr>';
    cols.forEach(function(c) {{
      var arrow = (c === col) ? (asc ? ' ▲' : ' ▼') : '';
      html += '<th data-col="' + c + '">' + c + '<span class="sort-arrow">' + arrow + '</span></th>';
    }});
    html += '</tr></thead><tbody>';

    sorted.forEach(function(r) {{
      var code = r['品种'] || '';
      html += '<tr style="cursor:pointer" onclick="scrollToProduct(\\'' + code + '\\')">';
      cols.forEach(function(c) {{
        var val = r[c];
        if (val === undefined || val === null || val === '') val = '-';
        var numVal = parseFloat(val);
        var cname = isNaN(numVal) ? '' : cls(numVal);
        if (c === '总盈亏') {{
          html += '<td class="' + cname + '">' + (numVal > 0 ? '+' : '') + fmtNum(val) + '</td>';
        }} else if (c === '品种') {{
          html += '<td><strong>' + val + '</strong></td>';
        }} else if (c === '名称') {{
          html += '<td style="color:#8c8c8c">' + val + '</td>';
        }} else if (c === '总交易') {{
          html += '<td>' + fmtInt(val) + '</td>';
        }} else {{
          var display = val;
          if (c.indexOf('%') > -1 && !isNaN(numVal)) display = fmtPct(numVal);
          else if (!isNaN(numVal)) display = numVal.toFixed(2);
          html += '<td class="' + cname + '">' + display + '</td>';
        }}
      }});
      html += '</tr>';
    }});
    html += '</tbody></table></div>';
    return html;
  }}

  var container = document.getElementById('comparison-container');
  var initialHtml = render(null, true);

  container.innerHTML = initialHtml;
  // Event delegation on container — single listener, no re-binding issues
  container.addEventListener('click', function(e) {{
    var th = e.target.closest('th');
    if (!th) return;
    var col = th.dataset.col;
    if (!col) return;
    if (sortState.col === col) sortState.asc = !sortState.asc;
    else {{ sortState.col = col; sortState.asc = false; }}
    container.innerHTML = render(sortState.col, sortState.asc);
  }});
}}

function scrollToProduct(code) {{
  var el = document.getElementById('product-' + code);
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

// ── Product Equity Chart ──
function renderProductEquityChart(domId, eq, code) {{
  if (!eq || !eq.dates || eq.dates.length === 0) return;
  var chart = echarts.init(document.getElementById(domId));
  var dates = eq.dates;
  var equity = eq.equity;
  var totalReturn = 0;
  if (REPORT_DATA.products[code] && REPORT_DATA.products[code].metrics) {{
    totalReturn = Number(REPORT_DATA.products[code].metrics.total_return_pct) || 0;
  }}
  var lineColor = totalReturn >= 0 ? '#00a854' : '#d93025';

  var option = {{
    tooltip: {{
      trigger: 'axis',
      formatter: function(params) {{
        var p = params[0];
        return '<strong>' + p.axisValueLabel + '</strong><br/>权益: ' + fmtNum(p.value);
      }}
    }},
    grid: {{ top: 20, bottom: 60, left: 60, right: 30 }},
    dataZoom: [
      {{ type: 'inside', start: 0, end: 100 }},
      {{ type: 'slider', start: 0, end: 100, bottom: 24, height: 20 }}
    ],
    xAxis: {{ type: 'category', data: dates, boundaryGap: false,
      axisLabel: {{ rotate: 45, fontSize: 11, show: dates.length <= 500 }},
      axisLine: {{ lineStyle: {{ color: '#e8e8e8' }} }} }},
    yAxis: {{ type: 'value', name: '权益 (RMB)', nameTextStyle: {{ fontSize: 12 }},
      splitLine: {{ lineStyle: {{ type: 'dashed', color: '#f0f0f0' }} }},
      axisLabel: {{ formatter: function(v) {{ return v >= 10000 ? (v/10000).toFixed(0) + '万' : v; }} }} }},
    series: [{{
      type: 'line', data: equity, smooth: true, symbol: 'none',
      lineStyle: {{ color: lineColor, width: 2 }},
      areaStyle: {{
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          {{ offset: 0, color: lineColor.replace(')', ', 0.15)').replace('rgb', 'rgba') }},
          {{ offset: 1, color: lineColor.replace(')', ', 0.02)').replace('rgb', 'rgba') }}
        ])
      }}
    }}]
  }};
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}}

// ── Product Monthly Returns Heatmap ──
function renderHeatmap(domId, mr) {{
  if (!mr || !mr.years || mr.years.length === 0 || !mr.values || mr.values.length === 0) return;
  var chart = echarts.init(document.getElementById(domId));

  var maxAbs = 0;
  mr.values.forEach(function(v) {{ if (Math.abs(v[2]) > maxAbs) maxAbs = Math.abs(v[2]); }});
  maxAbs = Math.max(maxAbs, 0.1);

  var option = {{
    tooltip: {{
      formatter: function(params) {{
        var y = mr.years[params.value[1]];
        var m = mr.months[params.value[0]];
        return y + ' ' + m + '<br/>收益率: ' + params.value[2].toFixed(2) + '%';
      }}
    }},
    grid: {{ top: 10, bottom: 30, left: 50, right: 80 }},
    xAxis: {{ type: 'category', data: mr.months, position: 'top',
      axisLabel: {{ fontSize: 11 }} }},
    yAxis: {{ type: 'category', data: mr.years.slice().reverse(),
      axisLabel: {{ fontSize: 11 }} }},
    visualMap: {{
      min: -maxAbs, max: maxAbs,
      inRange: {{ color: ['#d93025', '#ffffff', '#00a854'] }},
      calculable: true, orient: 'vertical', right: 0, top: 'center',
      formatter: function(v) {{ return v.toFixed(1) + '%'; }}
    }},
    series: [{{
      type: 'heatmap', data: mr.values,
      label: {{
        show: mr.years.length <= 8 && mr.values.length <= 96,
        formatter: function(p) {{ return p.value[2].toFixed(1); }},
        fontSize: 10
      }},
      emphasis: {{
        itemStyle: {{ shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' }}
      }}
    }}]
  }};
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}}

// ── Product Metrics Grid ──
function renderProductMetrics(metrics) {{
  if (!metrics) return '';
  var items = [
    ['总收益率', fmtPct(metrics.total_return_pct), cls(metrics.total_return_pct)],
    ['年化收益率', fmtPct(metrics.cagr_pct), cls(metrics.cagr_pct)],
    ['年化波动率', fmtPct(metrics.annualized_vol_pct), ''],
    ['夏普比率', metrics.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(3) : '-', cls(metrics.sharpe_ratio)],
    ['索提诺比率', metrics.sortino_ratio != null ? metrics.sortino_ratio.toFixed(3) : '-', cls(metrics.sortino_ratio)],
    ['卡玛比率', metrics.calmar_ratio != null ? metrics.calmar_ratio.toFixed(3) : '-', cls(metrics.calmar_ratio)],
    ['最大回撤', fmtPct(metrics.max_drawdown_pct), 'negative'],
    ['总交易', fmtInt(metrics.total_trades), ''],
    ['胜率', fmtPct(metrics.win_rate_pct), (metrics.win_rate_pct || 0) >= 50 ? 'positive' : 'negative'],
    ['利润因子', metrics.profit_factor != null ? metrics.profit_factor.toFixed(2) : '-', cls((metrics.profit_factor || 0) - 1)],
    ['平均盈利', fmtNum(metrics.avg_win), 'positive'],
    ['平均亏损', fmtNum(metrics.avg_loss), 'negative'],
    ['盈亏比', metrics.wl_ratio != null ? metrics.wl_ratio.toFixed(2) : '-', cls((metrics.wl_ratio || 0) - 1)],
    ['最大连赢', fmtInt(metrics.max_consec_wins), 'positive'],
    ['最大连亏', fmtInt(metrics.max_consec_losses), 'negative'],
    ['总盈亏', (metrics.total_pnl >= 0 ? '+' : '') + fmtNum(metrics.total_pnl), cls(metrics.total_pnl)],
  ];
  var html = '<div class="metrics-grid">';
  items.forEach(function(item) {{
    html += '<div class="mg-item"><span class="mg-label">' + item[0] + '</span>'
      + '<span class="mg-value ' + item[2] + '">' + item[1] + '</span></div>';
  }});
  html += '</div>';
  return html;
}}

// ── Product Trade Log Table (paginated) ──
function renderTradeLogTable(domId, trades, pageSize) {{
  if (!trades || trades.length === 0) {{
    document.getElementById(domId).innerHTML = '<div style="text-align:center;color:#8c8c8c;padding:20px;">无成交记录</div>';
    return;
  }}
  pageSize = pageSize || 20;
  var totalPages = Math.ceil(trades.length / pageSize);
  var currentPage = 0;

  function renderPage() {{
    var start = currentPage * pageSize;
    var end = Math.min(start + pageSize, trades.length);
    var pageData = trades.slice(start, end);

    var html = '<div class="table-wrap"><table><thead><tr>'
      + '<th>日期</th><th>类型</th><th>方向</th><th>手数</th><th>价格</th>'
      + '<th>盈亏</th><th>说明</th></tr></thead><tbody>';
    pageData.forEach(function(t) {{
      var badgeCls = 'badge-entry';
      var type = t.trade_type || '';
      if (type.indexOf('EXIT') > -1 || type === 'STOP_LOSS' || type === 'FORCE_CLOSE') badgeCls = 'badge-exit';
      else if (type.indexOf('ADD') > -1) badgeCls = 'badge-addon';
      else if (type.indexOf('ROLL') > -1) badgeCls = 'badge-rollover';
      else if (type.indexOf('FORCE') > -1) badgeCls = 'badge-force';

      var labelMap = {{'ENTRY':'开仓','STOP_LOSS':'止损','ADD_ON':'加仓',
        'EXIT':'平仓','FORCE_CLOSE':'强平','ROLLOVER_EXIT':'移仓平','ROLLOVER_ENTRY':'移仓开'}};
      var displayType = labelMap[type] || type;

      var dirCls = (t.direction === 'LONG' || t.direction === '1') ? 'positive' : 'negative';
      var dirText = (t.direction === 'LONG' || t.direction === '1') ? '多' : (t.direction === 'SHORT' || t.direction === '-1') ? '空' : t.direction || '';

      var pnl = parseFloat(t.pnl) || 0;
      var pnlCls = pnl > 0 ? 'positive' : (pnl < 0 ? 'negative' : '');

      html += '<tr>'
        + '<td style="text-align:left">' + (t.date || '') + '</td>'
        + '<td><span class="badge ' + badgeCls + '">' + displayType + '</span></td>'
        + '<td class="' + dirCls + '">' + dirText + '</td>'
        + '<td>' + (t.volume || '') + '</td>'
        + '<td>' + (t.price ? fmtNum(t.price) : '') + '</td>'
        + '<td class="' + pnlCls + '">' + (pnl !== 0 ? (pnl > 0 ? '+' : '') + fmtNum(pnl) : '') + '</td>'
        + '<td style="text-align:left;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + (t.remark || '') + '">' + (t.remark || '') + '</td>'
        + '</tr>';
    }});
    html += '</tbody></table></div>';

    // Pagination
    html += '<div class="pagination">'
      + '<button onclick="tradeLogPage(' + (currentPage - 1) + ')" ' + (currentPage <= 0 ? 'disabled' : '') + '>上一页</button>'
      + '<span class="page-info">第 ' + (currentPage + 1) + '/' + totalPages + ' 页 (共 ' + trades.length + ' 笔)</span>'
      + '<button onclick="tradeLogPage(' + (currentPage + 1) + ')" ' + (currentPage >= totalPages - 1 ? 'disabled' : '') + '>下一页</button>'
      + '</div>';

    document.getElementById(domId).innerHTML = html;
    window.__tradeLogState = {{ currentPage: currentPage, totalPages: totalPages, id: domId, trades: trades, pageSize: pageSize }};
  }}

  window.tradeLogPage = function(page) {{
    var state = window.__tradeLogState || {{}};
    if (state.id !== domId) {{
      state = {{ currentPage: 0, totalPages: totalPages, id: domId, trades: trades, pageSize: pageSize }};
    }}
    if (page < 0 || page >= state.totalPages) return;
    state.currentPage = page;
    var start = page * state.pageSize;
    var end = Math.min(start + state.pageSize, state.trades.length);
    var pageData = state.trades.slice(start, end);

    var html = '<div class="table-wrap"><table><thead><tr>'
      + '<th>日期</th><th>类型</th><th>方向</th><th>手数</th><th>价格</th>'
      + '<th>盈亏</th><th>说明</th></tr></thead><tbody>';
    pageData.forEach(function(t) {{
      var badgeCls = 'badge-entry';
      var type = t.trade_type || '';
      if (type.indexOf('EXIT') > -1 || type === 'STOP_LOSS' || type === 'FORCE_CLOSE') badgeCls = 'badge-exit';
      else if (type.indexOf('ADD') > -1) badgeCls = 'badge-addon';
      else if (type.indexOf('ROLL') > -1) badgeCls = 'badge-rollover';
      else if (type.indexOf('FORCE') > -1) badgeCls = 'badge-force';
      var labelMap = {{'ENTRY':'开仓','STOP_LOSS':'止损','ADD_ON':'加仓',
        'EXIT':'平仓','FORCE_CLOSE':'强平','ROLLOVER_EXIT':'移仓平','ROLLOVER_ENTRY':'移仓开'}};
      var displayType = labelMap[type] || type;
      var dirCls = (t.direction === 'LONG' || t.direction === '1') ? 'positive' : 'negative';
      var dirText = (t.direction === 'LONG' || t.direction === '1') ? '多' : (t.direction === 'SHORT' || t.direction === '-1') ? '空' : t.direction || '';
      var pnl = parseFloat(t.pnl) || 0;
      var pnlCls = pnl > 0 ? 'positive' : (pnl < 0 ? 'negative' : '');
      html += '<tr>'
        + '<td style="text-align:left">' + (t.date || '') + '</td>'
        + '<td><span class="badge ' + badgeCls + '">' + displayType + '</span></td>'
        + '<td class="' + dirCls + '">' + dirText + '</td>'
        + '<td>' + (t.volume || '') + '</td>'
        + '<td>' + (t.price ? fmtNum(t.price) : '') + '</td>'
        + '<td class="' + pnlCls + '">' + (pnl !== 0 ? (pnl > 0 ? '+' : '') + fmtNum(pnl) : '') + '</td>'
        + '<td style="text-align:left;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + (t.remark || '') + '">' + (t.remark || '') + '</td>'
        + '</tr>';
    }});
    html += '</tbody></table></div>';

    html += '<div class="pagination">'
      + '<button onclick="tradeLogPage(' + (page - 1) + ')" ' + (page <= 0 ? 'disabled' : '') + '>上一页</button>'
      + '<span class="page-info">第 ' + (page + 1) + '/' + state.totalPages + ' 页 (共 ' + state.trades.length + ' 笔)</span>'
      + '<button onclick="tradeLogPage(' + (page + 1) + ')" ' + (page >= state.totalPages - 1 ? 'disabled' : '') + '>下一页</button>'
      + '</div>';

    document.getElementById(domId).innerHTML = html;
    window.__tradeLogState = {{ currentPage: page, totalPages: state.totalPages, id: domId, trades: state.trades, pageSize: state.pageSize }};
  }};

  renderPage();
}}

// ── Build App ──
function buildApp() {{
  var data = REPORT_DATA;
  var m = data.portfolio_metrics || {{}};
  var html = '';

  // Header
  html += '<div class="report-header">'
    + '<h1>投资组合回测绩效报告</h1>'
    + '<div class="subtitle">'
    + '<span>📅 ' + (m.start_date || '') + ' → ' + (m.end_date || '') + '</span>'
    + '<span>📊 ' + (m.trading_days || '-') + ' 个交易日</span>'
    + '<span>🏷️ ' + Object.keys(data.products).length + ' 个品种</span>'
    + '<span>⏱️ ' + data.generated_at + ' 生成</span>'
    + '</div></div>';

  document.getElementById('app').innerHTML = html;

  // Summary Cards
  var cardsHtml = '<div class="section"><h2>组合概览</h2>' + renderCards(data) + '</div>';
  document.getElementById('app').insertAdjacentHTML('beforeend', cardsHtml);

  // Portfolio Equity Chart
  var eqId = 'chart-portfolio-equity';
  document.getElementById('app').insertAdjacentHTML('beforeend',
    '<div class="section"><h2>组合权益曲线</h2><div id="' + eqId + '" class="chart-container"></div></div>');
  renderEquityChart(eqId, data.portfolio_equity);

  // Portfolio Drawdown Chart
  var ddId = 'chart-portfolio-drawdown';
  document.getElementById('app').insertAdjacentHTML('beforeend',
    '<div class="section"><h2>组合回撤曲线</h2><div id="' + ddId + '" class="chart-container"></div></div>');
  renderDrawdownChart(ddId, data.portfolio_equity);

  // Portfolio Metrics Table
  document.getElementById('app').insertAdjacentHTML('beforeend',
    '<div class="section"><h2>组合绩效指标</h2>' + renderMetricsTable(m) + '</div>');

  // Product Comparison
  document.getElementById('app').insertAdjacentHTML('beforeend',
    '<div class="section"><h2>品种绩效对比</h2><div id="comparison-container"></div></div>');
  renderComparisonTable(data);

  // Product Details
  var pdHtml = '<div class="section"><h2>品种明细</h2>';
  var productCodes = Object.keys(data.products).sort();
  productCodes.forEach(function(code) {{
    var p = data.products[code];
    if (!p) return;
    var metrics = p.metrics || {{}};
    var totalReturn = metrics.total_return_pct || 0;
    var tagCls = totalReturn >= 0 ? 'tag-positive' : 'tag-negative';
    var tagText = totalReturn >= 0 ? '盈利' : '亏损';
    var eqChartId = 'chart-eq-' + code;
    var hmChartId = 'chart-hm-' + code;
    var tradeLogId = 'trades-' + code;

    pdHtml += '<details class="product-section" id="product-' + code + '">'
      + '<summary><span class="product-tag ' + tagCls + '">' + tagText + '</span>'
      + '<span class="summary-content">'
      + '<strong>' + code + '</strong>'
      + '<span class="product-meta">' + (p.name || '') + ' | ' + (p.exchange || '') + '</span>'
      + '<span class="product-meta">收益率: ' + fmtPct(totalReturn) + '</span>'
      + '<span class="product-meta">交易: ' + fmtInt(metrics.total_trades) + ' 笔</span>'
      + '<span class="product-meta">回撤: ' + fmtPct(metrics.max_drawdown_pct) + '</span>'
      + '</span></summary>'
      + '<div class="product-content">';

    // Mini metrics bar
    pdHtml += '<div class="mini-metrics">'
      + '<span class="mm-item"><span class="mm-label">年化</span><span class="mm-value ' + cls(metrics.cagr_pct) + '">' + fmtPct(metrics.cagr_pct) + '</span></span>'
      + '<span class="mm-item"><span class="mm-label">夏普</span><span class="mm-value ' + cls(metrics.sharpe_ratio) + '">' + (metrics.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(3) : '-') + '</span></span>'
      + '<span class="mm-item"><span class="mm-label">胜率</span><span class="mm-value ' + ((metrics.win_rate_pct || 0) >= 50 ? 'positive' : 'negative') + '">' + fmtPct(metrics.win_rate_pct) + '</span></span>'
      + '<span class="mm-item"><span class="mm-label">利润因子</span><span class="mm-value ' + cls((metrics.profit_factor || 0) - 1) + '">' + (metrics.profit_factor != null ? metrics.profit_factor.toFixed(2) : '-') + '</span></span>'
      + '<span class="mm-item"><span class="mm-label">总盈亏</span><span class="mm-value ' + cls(metrics.total_pnl) + '">' + (metrics.total_pnl >= 0 ? '+' : '') + fmtNum(metrics.total_pnl) + '</span></span>'
      + '</div>';

    // Tabs
    var tabId_eq = 'tab-eq-' + code;
    var tabId_metrics = 'tab-metrics-' + code;
    var tabId_heatmap = 'tab-heatmap-' + code;
    var tabId_trades = 'tab-trades-' + code;

    pdHtml += '<div class="sub-tabs">'
      + '<div class="sub-tab active" onclick="switchTab(\\'' + code + '\\',\\'eq\\')">权益曲线</div>'
      + '<div class="sub-tab" onclick="switchTab(\\'' + code + '\\',\\'metrics\\')">绩效指标</div>'
      + '<div class="sub-tab" onclick="switchTab(\\'' + code + '\\',\\'heatmap\\')">月度收益</div>'
      + '<div class="sub-tab" onclick="switchTab(\\'' + code + '\\',\\'trades\\')">成交记录</div>'
      + '</div>';

    // Tab contents
    pdHtml += '<div id="' + tabId_eq + '" class="tab-content active"><div id="' + eqChartId + '" class="chart-container-sm"></div></div>';
    pdHtml += '<div id="' + tabId_metrics + '" class="tab-content"><div>' + renderProductMetrics(metrics) + '</div></div>';
    pdHtml += '<div id="' + tabId_heatmap + '" class="tab-content"><div id="' + hmChartId + '" class="chart-container-sm"></div></div>';
    pdHtml += '<div id="' + tabId_trades + '" class="tab-content"><div id="' + tradeLogId + '"></div></div>';

    pdHtml += '</div></details>';
  }});
  pdHtml += '</div>';
  document.getElementById('app').insertAdjacentHTML('beforeend', pdHtml);

  // Render per-product charts
  productCodes.forEach(function(code) {{
    var p = data.products[code];
    if (!p) return;
    setTimeout(function() {{
      renderProductEquityChart('chart-eq-' + code, p.equity_curve, code);
      renderHeatmap('chart-hm-' + code, p.monthly_returns);
      renderTradeLogTable('trades-' + code, p.trade_log, 20);
    }}, 10);
  }});
}}

// ── Tab switching ──
function switchTab(code, tab) {{
  var parent = document.getElementById('product-' + code);
  if (!parent) return;
  var tabs = parent.querySelectorAll('.sub-tab');
  var contents = parent.querySelectorAll('.tab-content');
  var contentMap = {{}};
  tabs.forEach(function(t, i) {{
    t.classList.remove('active');
  }});
  contents.forEach(function(c) {{
    c.classList.remove('active');
  }});
  tabs.forEach(function(t) {{
    var onclick = t.getAttribute('onclick') || '';
    if (onclick.indexOf("'" + tab + "'") > -1) t.classList.add('active');
  }});
  var map = {{ eq: 'tab-eq-' + code, metrics: 'tab-metrics-' + code, heatmap: 'tab-heatmap-' + code, trades: 'tab-trades-' + code }};
  var target = document.getElementById(map[tab]);
  if (target) target.classList.add('active');

  // Resize charts after tab becomes visible
  setTimeout(function() {{
    if (tab === 'eq') {{
      var ch = echarts.getInstanceByDom(document.getElementById('chart-eq-' + code));
      if (ch) ch.resize();
    }} else if (tab === 'heatmap') {{
      var ch = echarts.getInstanceByDom(document.getElementById('chart-hm-' + code));
      if (ch) ch.resize();
    }}
  }}, 50);
}}

// ── Init ──
document.addEventListener('DOMContentLoaded', function() {{
  if (typeof REPORT_DATA === 'undefined' || !REPORT_DATA.products) {{
    document.getElementById('app').innerHTML = '<div style="text-align:center;padding:60px;color:#8c8c8c;"><h2>无回测数据</h2><p>请先运行回测生成结果文件</p></div>';
    return;
  }}
  buildApp();
}});
</script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description='生成投资组合回测HTML报告')
    parser.add_argument('--results-dir', default=None,
                        help='回测结果目录（默认: results/portfolio_2019_2026）')
    parser.add_argument('--output', default=None,
                        help='输出HTML文件路径（默认: <results-dir>/portfolio_report.html）')
    args = parser.parse_args()

    # Default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = args.results_dir or os.path.join(
        script_dir, 'results', 'portfolio_2019_2026')

    if not os.path.isdir(results_dir):
        print(f"[ERROR] 结果目录不存在: {results_dir}")
        sys.exit(1)

    output = args.output or os.path.join(results_dir, 'portfolio_report.html')

    print(f"[INFO] 读取回测结果: {results_dir}")
    data = load_all_data(results_dir)

    if not data['products']:
        print("[ERROR] 未找到任何品种回测数据")
        sys.exit(1)

    n_products = len(data['products'])
    print(f"[INFO] 加载 {n_products} 个品种数据")

    print("[INFO] 生成HTML报告 ...")
    html = build_html(data)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"[OK] 报告已生成: {output} ({size_mb:.1f}MB)")


if __name__ == '__main__':
    main()
