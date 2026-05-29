#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
APScheduler job: replace hardcoded data in HTML report with real DB data.
Runs at 15:45 after daily close calc (15:32) and consolidated report (15:40).
"""
import os
import sys
import io
import shutil
import traceback
from datetime import datetime
from decimal import Decimal

import django
from django.conf import settings
from django.db.models import Count
from django_redis import get_redis_connection
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade, log_error
from stock.models import (
    TradingAccount, AccountPerformanceSummary, DailyEquitySnapshot,
    DailyStrategySignal, PositionState, ClosedPositionRecord,
)

FSM = 'job_update_report_final'

# Fix stdout encoding for Windows console (GBK cannot print ¥/→)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# The 4 production account IDs (skip ID 4 which is admin/test)
ACC_IDS = [1, 5, 6, 10]

HTML_PATH = os.path.join(settings.BASE_DIR, 'templates', '策略分析报告-完整数理分析.html')
TEMPLATE_PATH = HTML_PATH.replace('.html', '.template.html')


def _gather_data():
    """Query DB data needed for all replacements."""
    accounts = {a.id: a for a in TradingAccount.objects.filter(id__in=ACC_IDS)}
    perf = {}
    for aid in ACC_IDS:
        p = AccountPerformanceSummary.objects.filter(account_id=aid).first()
        perf[aid] = p

    # Signal counts per account per type
    sig_counts = {}
    for aid in ACC_IDS:
        rows = DailyStrategySignal.objects.filter(account_id=aid).values('trade_type').annotate(cnt=Count('id'))
        sig_counts[aid] = {r['trade_type']: r['cnt'] for r in rows}
        rows2 = DailyStrategySignal.objects.filter(account_id=aid, executed_status='SUCCESS').values('trade_type').annotate(cnt=Count('id'))
        sig_counts[aid]['_total'] = sum(r['cnt'] for r in rows2)
        sig_counts[aid]['_all'] = DailyStrategySignal.objects.filter(account_id=aid).count()

    # Equity snapshots
    eq_qs = {aid: list(DailyEquitySnapshot.objects.filter(account_id=aid).order_by('trade_date')) for aid in ACC_IDS}

    # Positions
    positions = {aid: list(PositionState.objects.filter(account_id=aid, units__gt=0)) for aid in ACC_IDS}

    # Closed positions
    closed_qs = list(ClosedPositionRecord.objects.filter(account_id__in=ACC_IDS).order_by('account_id'))

    return accounts, perf, sig_counts, eq_qs, positions, closed_qs


def _pct_str(val):
    if val is None:
        return '-'
    v = float(val) * 100 if abs(float(val)) < 1 else float(val)
    return f"{'+' if v >= 0 else ''}{v:.2f}%"


def _ret_str(acc):
    r = (float(acc.current_equity) - float(acc.initial_balance)) / float(acc.initial_balance) * 100
    return f"{'+' if r >= 0 else ''}{r:.2f}%"


def _yen_str(val):
    if val is None:
        return '&yen;0'
    return f'&yen;{float(val):,.2f}'


def _or_dash(val, fmt='.2f'):
    if val is None:
        return '-'
    return f'{float(val):{fmt}}'


def _dd_str(val):
    if val is None:
        return '0.00%'
    return f'{float(val):.2f}%'


def _replace_one(html, old, new):
    """Replace exactly one occurrence. Return (html, found)."""
    count = html.count(old)
    if count == 0:
        print(f'WARN: not found → {repr(old[:80])}')
        return html, False
    html = html.replace(old, new, 1)
    return html, True


def _make_chart_html(eq_qs, aid, accounts):
    """Build bar chart HTML block for account."""
    snaps = eq_qs[aid]
    if not snaps:
        return None
    vals = [(s.trade_date.strftime('%m-%d'), float(s.balance), float(s.daily_return or 0)) for s in snaps]
    max_v = max(v[1] for v in vals)
    acc = accounts[aid]
    init_bal = float(acc.initial_balance)

    bars = []
    for i, (d, b, dr) in enumerate(vals):
        h = (b / max_v * 100) if max_v > 0 else 100
        color = 'blue' if i == 0 else ('green' if dr >= 0 else 'red')
        bars.append(f'        <div class="bar {color}" style="height:{h:.2f}%;" title="¥{b:,.2f}"><span class="label">{d}</span><span class="tooltip">¥{b:,.2f}</span></div>')

    bars_str = '\n'.join(bars)
    last_bal = vals[-1][1]
    total_pnl = last_bal - float(snaps[0].balance)
    total_ret = (last_bal - init_bal) / init_bal * 100

    return f'''<div class="chart-container">
      <div class="bar-chart" style="height:200px;">
{bars_str}
      </div>
      <div style="margin-top:24px;font-size:0.8em;color:var(--text-secondary);">实盘第4日 | 当前权益 ¥{last_bal:,.2f} | 累计盈亏 ¥{total_pnl:,.2f} | 累计 {total_ret:+.2f}%</div>
    </div>'''


def _replace_chart_section(html, h3_id, new_chart_html):
    """Replace chart content within a section identified by h3 id."""
    tag = f'<h3>{h3_id}'
    start = html.find(tag)
    if start < 0:
        print(f'WARN: section {h3_id} not found')
        return html

    chart_start = html.find('<div class="chart-container">', start)
    if chart_start < 0:
        print(f'WARN: chart in {h3_id} not found')
        return html

    desc_start = html.find('<div style="margin-top:24px', chart_start)
    if desc_start < 0:
        print(f'WARN: desc div in {h3_id} not found')
        return html

    chart_end = html.find('\n    </div>\n    \n    <h3', desc_start)
    if chart_end < 0:
        chart_end = html.find('\n    </div>\n    \n    \n    ', desc_start)
    if chart_end < 0:
        chart_end = html.find('\n    </div>\n    \n    \n</div>', desc_start)
    if chart_end < 0:
        chart_end = html.find('</div>', desc_start)
        chart_end = html.find('</div>', chart_end + 6)

    if chart_end < 0:
        print(f'WARN: chart end in {h3_id} not found')
        return html

    section_header = html[start:chart_start]
    rest = html[chart_end:]
    html = html[:start] + section_header + new_chart_html + rest
    print(f'Section {h3_id}: replaced')
    return html


def _build_positions_html(positions):
    """Build s12 position table rows."""
    rows = ''
    # V2
    for p in positions.get(1, []):
        d = '多' if p.direction == 1 else '空'
        cost = float(p.cost_price) if p.cost_price else 0
        stop = float(p.stop_loss_price) if p.stop_loss_price else 0
        rows += f'  <tr><td><strong>V2</strong></td><td>{p.symbol.split(".")[-1]}</td><td>{d}</td><td>{p.contract_total_position}</td><td>{cost:,.0f}</td><td>{stop:,.2f}</td></tr>\n'
    # V3
    if positions.get(5):
        for p in positions[5]:
            d = '多' if p.direction == 1 else '空'
            cost = float(p.cost_price) if p.cost_price else 0
            stop = float(p.stop_loss_price) if p.stop_loss_price else 0
            rows += f'  <tr><td><strong>V3</strong></td><td>{p.symbol.split(".")[-1]}</td><td>{d}</td><td>{p.contract_total_position}</td><td>{cost:,.0f}</td><td>{stop:,.2f}</td></tr>\n'
    else:
        rows += '  <tr><td><strong>V3</strong></td><td colspan="5" style="text-align:center;color:var(--text-secondary);">暂无持仓</td></tr>\n'
    # Turtle
    for p in positions.get(6, []):
        d = '多' if p.direction == 1 else '空'
        cost = float(p.cost_price) if p.cost_price else 0
        stop = float(p.stop_loss_price) if p.stop_loss_price else '-'
        stop_str = f'{stop:,.2f}' if isinstance(stop, float) else stop
        rows += f'  <tr><td><strong>原版海龟</strong></td><td>{p.symbol.split(".")[-1]}</td><td>{d}</td><td>{p.contract_total_position}</td><td>{cost:,.0f}</td><td>{stop_str}</td></tr>\n'
    return rows


def job_update_report_final():
    """
    APScheduler entry point — regenerate HTML report with latest DB data.
    Schedule: Mon-Fri 15:45 (after close calc at 15:32 + consolidated report at 15:40).
    """
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:update_report_final'):
            if skip_if_not_trade_day():
                log_trade(FSM, '非交易日，跳过报告更新', symbol='N/A', log_level='INFO')
                return

            today = datetime.now()
            print(f'[{today}] Generating report...')
            log_trade(FSM, f'开始更新HTML报告', symbol='N/A', log_level='INFO')

            # Delete old HTML, then restore template baseline
            if os.path.exists(HTML_PATH):
                os.remove(HTML_PATH)
                print(f'Old HTML deleted: {HTML_PATH}')
            if os.path.exists(TEMPLATE_PATH):
                shutil.copy2(TEMPLATE_PATH, HTML_PATH)
                print(f'Template restored: {TEMPLATE_PATH} → {HTML_PATH}')
            else:
                log_error(FSM, f'模板基线文件不存在: {TEMPLATE_PATH}')
                return

            # Read the HTML file
            if not os.path.exists(HTML_PATH):
                log_error(FSM, f'HTML模板不存在: {HTML_PATH}')
                return

            with open(HTML_PATH, 'r', encoding='utf-8') as f:
                html = f.read()

            # Gather data
            accounts, perf, sig_counts, eq_qs, positions, closed_qs = _gather_data()
            t6, t1, t5, t10 = accounts[6], accounts[1], accounts[5], accounts[10]
            t6_ret, t1_ret, t5_ret, t10_ret = (_ret_str(accounts[a]) for a in [6, 1, 5, 10])
            t6_positions = '+'.join([f"{p.symbol.split('.')[-1]}{'多' if p.direction==1 else '空'}{p.contract_total_position}" for p in positions[6]]) or '无'
            t1_positions = '+'.join([f"{p.symbol.split('.')[-1]}{'多' if p.direction==1 else '空'}{p.contract_total_position}" for p in positions[1]]) or '无'
            t5_positions = '+'.join([f"{p.symbol.split('.')[-1]}{'多' if p.direction==1 else '空'}{p.contract_total_position}" for p in positions[5]]) or '无'
            hvob_closed = [c for c in closed_qs if c.account_id == 10]
            hvob_closed_total = sum(float(cp.pnl) for cp in closed_qs if cp.account_id == 10)
            t1_color = 'var(--green)' if float(t1.current_equity) >= float(t1.initial_balance) else 'var(--red)'
            t5_color = 'var(--green)' if float(t5.current_equity) >= float(t5.initial_balance) else 'var(--red)'
            t10_color = 'var(--green)' if float(t10.current_equity) >= float(t10.initial_balance) else 'var(--red)'

            # Build day label
            day_num = (today - datetime(2026, 5, 26)).days + 1
            date_label = today.strftime('%Y-%m-%d')
            time_label = today.strftime('%H:%M')

            # ── COVER PAGE ──
            html, _ = _replace_one(html,
                '生成日期: 2026-05-27 | 实盘第2日',
                f'生成日期: {date_label} | 实盘第{day_num}日')

            # ── s1 comparison grid ──

            # Turtle card
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:var(--green);">&#165;504,025</span></div>',
                f'<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:var(--green);">&#165;{t6.current_equity:,.0f}</span></div>')
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:var(--green);">+0.40%</span></div>',
                f'<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:var(--green);">{t6_ret}</span></div>')
            html, _ = _replace_one(html,
                '持仓</span><span class="stat-value">rb2610空7+jd2607多4+MA609空3</span></div>',
                f'持仓</span><span class="stat-value">{t6_positions}</span></div>')
            html, _ = _replace_one(html,
                '    <div class="stat-row"><span class="stat-label">手续费</span><span class="stat-value">¥0</span></div>',
                f'    <div class="stat-row"><span class="stat-label">手续费</span><span class="stat-value">¥{float(perf[6].commission_total) if perf[6] and perf[6].commission_total else 0:.2f}</span></div>')
            print('s1 Turtle: OK')

            # V2 card
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:var(--red);">¥501,922</span></div>',
                f'<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:{t1_color};">¥{t1.current_equity:,.0f}</span></div>')
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:var(--red);">-0.02%</span></div>',
                f'<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:{t1_color};">{t1_ret}</span></div>')
            html, _ = _replace_one(html,
                '持仓</span><span class="stat-value">rb2610空1U(6L)</span></div>',
                f'持仓</span><span class="stat-value">{t1_positions}</span></div>')

            # V2 fee — find via line-level matching
            html_lines = html.split('\n')
            v2_fee_idx = None
            for i, line in enumerate(html_lines):
                if 'class="stat-label">手续费' in line and '¥0' in line:
                    v2_fee_idx = i
                    break
            if v2_fee_idx is not None:
                old_line = html_lines[v2_fee_idx]
                new_line = old_line.replace('¥0', f'¥{float(perf[1].commission_total) if perf[1] and perf[1].commission_total else 0:.2f}')
                html_lines[v2_fee_idx] = new_line
                html = '\n'.join(html_lines)
                print(f'V2 fee: OK')
            print('s1 V2: OK')

            # V3 card
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value">¥502,000</span></div>',
                f'<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:{t5_color};">¥{t5.current_equity:,.0f}</span></div>')
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value">0.00%</span></div>',
                f'<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:{t5_color};">{t5_ret}</span></div>')
            # V3 positions
            html_lines = html.split('\n')
            for i, line in enumerate(html_lines):
                if '策略-header' in line and 'V3' in line:
                    for j in range(i, min(i+10, len(html_lines))):
                        if 'class="stat-label">持仓</span><span class="stat-value">无' in html_lines[j]:
                            html_lines[j] = html_lines[j].replace('>无<', f'>{t5_positions}<')
                            html = '\n'.join(html_lines)
                            print(f'V3 positions: OK → {t5_positions}')
                            break
                    break
            print('s1 V3: OK')

            # HVOB card
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:var(--green);">&#165;514,637</span></div>',
                f'<div class="stat-row"><span class="stat-label">当前权益</span><span class="stat-value" style="color:{t10_color};">&#165;{t10.current_equity:,.0f}</span></div>')
            html, _ = _replace_one(html,
                '<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:var(--green);">+2.55%</span></div>',
                f'<div class="stat-row"><span class="stat-label">累计收益</span><span class="stat-value" style="color:{t10_color};">{t10_ret}</span></div>')
            html, _ = _replace_one(html,
                '持仓</span><span class="stat-value">全部平仓+¥12,745</span></div>',
                f'平仓汇总</span><span class="stat-value">{"" if hvob_closed_total < 0 else "+"}¥{hvob_closed_total:,.0f}</span></div>')

            # s1 callout
            html, _ = _replace_one(html,
                '⚡ 实盘第2日：',
                f'⚡ 实盘第{day_num}日：')
            print('s1 HVOB + callout: OK')

            # ── s4 V3 filter table ──
            html, _ = _replace_one(html,
                '  <tr><td>ENTRY 信号数</td><td>—</td><td>—</td></tr>',
                f'  <tr><td>ENTRY 信号数</td><td>{sig_counts[1].get("ENTRY", 0)}</td><td>{sig_counts[5].get("ENTRY", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>STOP_LOSS 信号数</td><td>—</td><td>—</td></tr>',
                f'  <tr><td>STOP_LOSS 信号数</td><td>{sig_counts[1].get("STOP_LOSS", 0)}</td><td>{sig_counts[5].get("STOP_LOSS", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>ADD_ON 信号数</td><td>—</td><td>—</td></tr>',
                f'  <tr><td>ADD_ON 信号数</td><td>{sig_counts[1].get("ADD_ON", 0)}</td><td>{sig_counts[5].get("ADD_ON", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>当前持仓品种</td><td>0</td><td>0</td></tr>',
                f'  <tr><td>当前持仓品种</td><td>{len(positions[1])}</td><td>{len(positions[5])}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>累计收益</td><td>0.00%</td><td>0.00%</td></tr>',
                f'  <tr><td>累计收益</td><td>{t1_ret}</td><td>{t5_ret}</td></tr>')
            print('s4 table: OK')

            # ── s10 OVERVIEW TABLE ──
            html, _ = _replace_one(html,
                '  <tr><td>当前权益</td><td>&yen;504,025</td><td>&yen;501,922</td><td>&yen;502,000</td><td>&yen;514,637</td></tr>',
                f'  <tr><td>当前权益</td><td>&yen;{t6.current_equity:,.0f}</td><td>&yen;{t1.current_equity:,.0f}</td><td>&yen;{t5.current_equity:,.0f}</td><td>&yen;{t10.current_equity:,.0f}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>累计收益率</td><td>+0.40%</td><td>-0.02%</td><td>0.00%</td><td>+2.52%</td></tr>',
                f'  <tr><td>累计收益率</td><td>{t6_ret}</td><td>{t1_ret}</td><td>{t5_ret}</td><td>{t10_ret}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>最大回撤</td><td>0.00%</td><td>0.00%</td><td>0.00%</td><td>0.00%</td></tr>',
                f'  <tr><td>最大回撤</td><td>{_dd_str(perf[6].max_drawdown_all_time if perf[6] else 0)}</td><td>{_dd_str(perf[1].max_drawdown_all_time if perf[1] else 0)}</td><td>{_dd_str(perf[5].max_drawdown_all_time if perf[5] else 0)}</td><td>{_dd_str(perf[10].max_drawdown_all_time if perf[10] else 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>当前回撤</td><td>0.00%</td><td>0.00%</td><td>0.00%</td><td>0.00%</td></tr>',
                f'  <tr><td>当前回撤</td><td>{_dd_str(perf[6].current_drawdown if perf[6] else 0)}</td><td>{_dd_str(perf[1].current_drawdown if perf[1] else 0)}</td><td>{_dd_str(perf[5].current_drawdown if perf[5] else 0)}</td><td>{_dd_str(perf[10].current_drawdown if perf[10] else 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>整体胜率</td><td>-</td><td>-</td><td>-</td><td>100%</td></tr>',
                f'  <tr><td>整体胜率</td><td>{_or_dash(perf[6].overall_win_rate) if perf[6] and perf[6].overall_win_rate else "-"}</td><td>{_or_dash(perf[1].overall_win_rate) if perf[1] and perf[1].overall_win_rate else "-"}</td><td>{_or_dash(perf[5].overall_win_rate) if perf[5] and perf[5].overall_win_rate else "-"}</td><td>{_or_dash(perf[10].overall_win_rate) if perf[10] and perf[10].overall_win_rate else "-"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>盈利因子</td><td>-</td><td>-</td><td>-</td><td>999.99</td></tr>',
                f'  <tr><td>盈利因子</td><td>{_or_dash(perf[6].overall_profit_factor) if perf[6] and perf[6].overall_profit_factor else "-"}</td><td>{_or_dash(perf[1].overall_profit_factor) if perf[1] and perf[1].overall_profit_factor else "-"}</td><td>{_or_dash(perf[5].overall_profit_factor) if perf[5] and perf[5].overall_profit_factor else "-"}</td><td>{_or_dash(perf[10].overall_profit_factor) if perf[10] and perf[10].overall_profit_factor else "-"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>总交易次数</td><td>3</td><td>1</td><td>0</td><td>10</td></tr>',
                f'  <tr><td>总交易次数</td><td>{sig_counts[6]["_total"]}</td><td>{sig_counts[1]["_total"]}</td><td>{sig_counts[5]["_total"]}</td><td>{sig_counts[10]["_total"]}</td></tr>')
            html, _ = _replace_one(html,
                '	  <tr><td>累计手续费</td><td>&yen;93.04</td><td>&yen;18.96</td><td>&yen;0.00</td><td>&yen;216.00</td></tr>',
                f'	  <tr><td>累计手续费</td><td>{_yen_str(perf[6].commission_total if perf[6] else 0)}</td><td>{_yen_str(perf[1].commission_total if perf[1] else 0)}</td><td>{_yen_str(perf[5].commission_total if perf[5] else 0)}</td><td>{_yen_str(perf[10].commission_total if perf[10] else 0)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>最大连续亏损</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>',
                f'  <tr><td>最大连续亏损</td><td>{perf[6].consecutive_losses if perf[6] else 0}</td><td>{perf[1].consecutive_losses if perf[1] else 0}</td><td>{perf[5].consecutive_losses if perf[5] else 0}</td><td>{perf[10].consecutive_losses if perf[10] else 0}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>20日夏普比率</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>20日夏普比率</td><td>{_or_dash(perf[6].latest_sharpe_20d) if perf[6] and perf[6].latest_sharpe_20d else "-"}</td><td>{_or_dash(perf[1].latest_sharpe_20d) if perf[1] and perf[1].latest_sharpe_20d else "-"}</td><td>{_or_dash(perf[5].latest_sharpe_20d) if perf[5] and perf[5].latest_sharpe_20d else "-"}</td><td>{_or_dash(perf[10].latest_sharpe_20d) if perf[10] and perf[10].latest_sharpe_20d else "-"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>20日年化波动率</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>20日年化波动率</td><td>{_or_dash(perf[6].latest_volatility_20d) if perf[6] and perf[6].latest_volatility_20d else "-"}</td><td>{_or_dash(perf[1].latest_volatility_20d) if perf[1] and perf[1].latest_volatility_20d else "-"}</td><td>{_or_dash(perf[5].latest_volatility_20d) if perf[5] and perf[5].latest_volatility_20d else "-"}</td><td>{_or_dash(perf[10].latest_volatility_20d) if perf[10] and perf[10].latest_volatility_20d else "-"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>最佳单笔盈利</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>最佳单笔盈利</td><td>{_yen_str(perf[6].best_single_trade) if perf[6] and perf[6].best_single_trade else "&mdash;"}</td><td>{_yen_str(perf[1].best_single_trade) if perf[1] and perf[1].best_single_trade else "&mdash;"}</td><td>{_yen_str(perf[5].best_single_trade) if perf[5] and perf[5].best_single_trade else "&mdash;"}</td><td>{_yen_str(perf[10].best_single_trade) if perf[10] and perf[10].best_single_trade else "&mdash;"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>最差单笔亏损</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>最差单笔亏损</td><td>{_yen_str(perf[6].worst_single_trade) if perf[6] and perf[6].worst_single_trade else "&mdash;"}</td><td>{_yen_str(perf[1].worst_single_trade) if perf[1] and perf[1].worst_single_trade else "&mdash;"}</td><td>{_yen_str(perf[5].worst_single_trade) if perf[5] and perf[5].worst_single_trade else "&mdash;"}</td><td>{_yen_str(perf[10].worst_single_trade) if perf[10] and perf[10].worst_single_trade else "&mdash;"}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>累计平仓盈亏</td><td>&yen;0</td><td>&yen;0</td><td>&yen;0</td><td>&yen;12,745</td></tr>',
                f'  <tr><td>累计平仓盈亏</td><td>{_yen_str(perf[6].closed_profit_total if perf[6] else 0)}</td><td>{_yen_str(perf[1].closed_profit_total if perf[1] else 0)}</td><td>{_yen_str(perf[5].closed_profit_total if perf[5] else 0)}</td><td>{_yen_str(perf[10].closed_profit_total if perf[10] else 0)}</td></tr>')
            print('s10 overview: OK')

            # ── s10 SIGNAL STATS ──
            html, _ = _replace_one(html,
                '    <tr><td>ENTRY</td><td>2</td><td>3</td><td>3</td><td>9</td></tr>',
                f'    <tr><td>ENTRY</td><td>{sig_counts[6].get("ENTRY", 0)}</td><td>{sig_counts[1].get("ENTRY", 0)}</td><td>{sig_counts[5].get("ENTRY", 0)}</td><td>{sig_counts[10].get("ENTRY", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '    <tr><td>STOP_LOSS</td><td>0</td><td>0</td><td>0</td><td>1</td></tr>',
                f'    <tr><td>STOP_LOSS</td><td>{sig_counts[6].get("STOP_LOSS", 0)}</td><td>{sig_counts[1].get("STOP_LOSS", 0)}</td><td>{sig_counts[5].get("STOP_LOSS", 0)}</td><td>{sig_counts[10].get("STOP_LOSS", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '    <tr><td>ADD_ON</td><td>1</td><td>0</td><td>0</td><td>0</td></tr>',
                f'    <tr><td>ADD_ON</td><td>{sig_counts[6].get("ADD_ON", 0)}</td><td>{sig_counts[1].get("ADD_ON", 0)}</td><td>{sig_counts[5].get("ADD_ON", 0)}</td><td>{sig_counts[10].get("ADD_ON", 0)}</td></tr>')
            html, _ = _replace_one(html,
                '    <tr><td>ROLLOVER</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>',
                f'    <tr><td>ROLLOVER</td><td>{sig_counts[6].get("ROLLOVER", 0)}</td><td>{sig_counts[1].get("ROLLOVER", 0)}</td><td>{sig_counts[5].get("ROLLOVER", 0)}</td><td>{sig_counts[10].get("ROLLOVER", 0)}</td></tr>')
            # Total row
            for aid in ACC_IDS:
                sig_counts[aid]['_type_total'] = sum(sig_counts[aid].get(k, 0) for k in ['ENTRY', 'STOP_LOSS', 'ADD_ON', 'ROLLOVER'])
            html, _ = _replace_one(html,
                '  <tr><td><strong>总计</strong></td><td><strong>3</strong></td><td><strong>3</strong></td><td><strong>3</strong></td><td><strong>10</strong></td></tr>',
                f'  <tr><td><strong>总计</strong></td><td><strong>{sig_counts[6]["_type_total"]}</strong></td><td><strong>{sig_counts[1]["_type_total"]}</strong></td><td><strong>{sig_counts[5]["_type_total"]}</strong></td><td><strong>{sig_counts[10]["_type_total"]}</strong></td></tr>')
            # SUCCESS row
            html, _ = _replace_one(html,
                '  <tr><td>已执行(SUCCESS)</td><td>3</td><td>1</td><td>0</td><td>10</td></tr>',
                f'  <tr><td>已执行(SUCCESS)</td><td>{sig_counts[6]["_total"]}</td><td>{sig_counts[1]["_total"]}</td><td>{sig_counts[5]["_total"]}</td><td>{sig_counts[10]["_total"]}</td></tr>')
            print('s10 signals: OK')

            # ── s11 EQUITY CHARTS ──
            v2_chart = _make_chart_html(eq_qs, 1, accounts)
            if v2_chart:
                html = _replace_chart_section(html, '11.1', v2_chart)
                print('11.1 V2 chart: OK')
            v3_chart = _make_chart_html(eq_qs, 5, accounts)
            if v3_chart:
                html = _replace_chart_section(html, '11.2', v3_chart)
                print('11.2 V3 chart: OK')
            t6_chart = _make_chart_html(eq_qs, 6, accounts)
            if t6_chart:
                html = _replace_chart_section(html, '11.3', t6_chart)
                print('11.3 Turtle chart: OK')
            t10_chart = _make_chart_html(eq_qs, 10, accounts)
            if t10_chart:
                html = _replace_chart_section(html, '11.4', t10_chart)
                print('11.4 HVOB chart: OK')

            # ── s12 POSITIONS TABLE ──
            pos_rows = _build_positions_html(positions)
            s12_start = html.find('<h2>十二、持仓结构对比</h2>')
            if s12_start >= 0:
                table_tag_start = html.find('<table>', s12_start)
                table_tag_end = html.find('</table>', table_tag_start)
                if table_tag_start >= 0 and table_tag_end >= 0:
                    header_row = '    <tr><th>账户</th><th>品种</th><th>方向</th><th>手数</th><th>成本价</th><th>止损价</th></tr>\n'
                    old_table = html[table_tag_start:table_tag_end + 8]
                    new_table = f'<table>\n{header_row}{pos_rows}  </table>'
                    html = html.replace(old_table, new_table, 1)
                    print('s12 positions: OK')

            # ── s13 CLOSED POSITIONS ──
            hvob_wins = [c for c in hvob_closed if c.pnl and float(c.pnl) > 0]
            hvob_losses = [c for c in hvob_closed if c.pnl and float(c.pnl) <= 0]
            hvob_avg_win = sum(float(c.pnl) for c in hvob_wins) / len(hvob_wins) if hvob_wins else 0
            hvob_avg_loss = sum(float(c.pnl) for c in hvob_losses) / len(hvob_losses) if hvob_losses else 0
            hvob_best = max(float(c.pnl) for c in hvob_wins) if hvob_wins else 0
            hvob_worst = min(float(c.pnl) for c in hvob_losses) if hvob_losses else 0

            html, _ = _replace_one(html,
                '  <tr><td>平仓总笔数</td><td>0</td><td>0</td><td>0</td><td>1</td></tr>',
                f'  <tr><td>平仓总笔数</td><td>0</td><td>0</td><td>0</td><td>{len(hvob_closed)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>盈利笔数</td><td>0</td><td>0</td><td>0</td><td>1</td></tr>',
                f'  <tr><td>盈利笔数</td><td>0</td><td>0</td><td>0</td><td>{len(hvob_wins)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>亏损笔数</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>',
                f'  <tr><td>亏损笔数</td><td>0</td><td>0</td><td>0</td><td>{len(hvob_losses)}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>累计平仓盈亏</td><td>&yen;0</td><td>&yen;0</td><td>&yen;0</td><td>&yen;1,025</td></tr>',
                f'  <tr><td>累计平仓盈亏</td><td>&yen;0</td><td>&yen;0</td><td>&yen;0</td><td>&yen;{hvob_closed_total:,.0f}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>平均盈利</td><td>-</td><td>-</td><td>-</td><td>&yen;1,821</td></tr>',
                f'  <tr><td>平均盈利</td><td>-</td><td>-</td><td>-</td><td>&yen;{hvob_avg_win:,.0f}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>平均亏损</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>平均亏损</td><td>-</td><td>-</td><td>-</td><td>&yen;{hvob_avg_loss:,.0f}</td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>最差单笔</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>',
                f'  <tr><td>最差单笔</td><td>-</td><td>-</td><td>-</td><td>&yen;{hvob_worst:,.0f}</td></tr>')
            print('s13 closed: OK')

            # ── s17 CONCLUSION TABLE ──
            html, _ = _replace_one(html,
                '  <tr><td>原版海龟</td><td>第2日</td><td>&yen;504,025</td><td>+0.40%</td><td>0.00%</td><td>rb2610空7+jd2607多4+MA609空3</td><td><span class="tag green">3笔持仓</span></td></tr>',
                f'  <tr><td>原版海龟</td><td>第{day_num}日</td><td>&yen;{t6.current_equity:,.0f}</td><td>{t6_ret}</td><td>{_dd_str(perf[6].max_drawdown_all_time if perf[6] else 0)}</td><td>{t6_positions}</td><td><span class="tag green">3笔持仓</span></td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>海龟V2</td><td>第2日</td><td>&yen;501,922</td><td>-0.02%</td><td>0.02%</td><td>rb2610空1U(6L)</td><td><span class="tag orange">小幅浮亏</span></td></tr>',
                f'  <tr><td>海龟V2</td><td>第{day_num}日</td><td>&yen;{t1.current_equity:,.0f}</td><td>{t1_ret}</td><td>{_dd_str(perf[1].max_drawdown_all_time if perf[1] else 0)}</td><td>{t1_positions}</td><td><span class="tag orange">{len(positions[1])}品种持仓</span></td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>海龟V3</td><td>第2日</td><td>&yen;502,000</td><td>0.00%</td><td>0.00%</td><td>无(2笔PENDING)</td><td><span class="tag blue">等待突破</span></td></tr>',
                f'  <tr><td>海龟V3</td><td>第{day_num}日</td><td>&yen;{t5.current_equity:,.0f}</td><td>{t5_ret}</td><td>{_dd_str(perf[5].max_drawdown_all_time if perf[5] else 0)}</td><td>{t5_positions}</td><td><span class="tag blue">jd2607持仓</span></td></tr>')
            html, _ = _replace_one(html,
                '  <tr><td>HVOB-MBI</td><td>第2日</td><td>&yen;514,637</td><td>+2.55%</td><td>0.00%</td><td>全部平仓+&yen;12,745</td><td><span class="tag green">强劲表现</span></td></tr>',
                f'  <tr><td>HVOB-MBI</td><td>第{day_num}日</td><td>&yen;{t10.current_equity:,.0f}</td><td>{t10_ret}</td><td>{_dd_str(perf[10].max_drawdown_all_time if perf[10] else 0)}</td><td>平仓{"" if hvob_closed_total < 0 else "+"}¥{hvob_closed_total:,.0f}</td><td><span class="tag green">累计平仓</span></td></tr>')
            print('s17 conclusion: OK')

            # ── FOOTER ──
            html, _ = _replace_one(html,
                '<p>生成日期: 2026-05-27 | v3.1</p>',
                f'<p>生成日期: {date_label} {time_label} | v3.3</p>')

            # ── WRITE OUTPUT ──
            with open(HTML_PATH, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f'\n=== DONE ===')
            print(f'Output: {HTML_PATH}')
            print(f'File size: {len(html.encode("utf-8"))} bytes')
            log_trade(FSM, f'报告更新完成: {date_label} 第{day_num}日 {len(html)}bytes', symbol='N/A', log_level='INFO')

    except LockAcquisitionError:
        log_trade(FSM, '任务正在其他实例执行，跳过', symbol='N/A', log_level='INFO')
    except Exception as e:
        log_error(FSM, f'报告更新失败: {e}')
        traceback.print_exc()
