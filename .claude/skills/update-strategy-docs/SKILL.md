---
name: update-strategy-docs
description: >
  Two-phase workflow for updating quantitative futures trading strategy documentation.
  Phase 1: Read trading logic code from backend/stock/ and update strategy design MD documents
  in md/知识库/04-策略设计文档/. Phase 2: Query Django models for live performance data and
  generate a complete HTML analysis report using the template at
  backend/templates/策略分析报告-完整数理分析.html. Trigger when user says "更新策略文档",
  "更新策略报告", "同步代码到文档", "生成策略分析报告", or similar phrases about updating
  trading strategy documentation.
---

# Strategy Documentation Update Skill

A two-phase workflow for keeping strategy documentation synchronized with the actual trading code and generating data-driven analysis reports.

## Overview

This skill has two independent phases that run sequentially:

1. **Phase 1 (同步逻辑)** — Read the actual Python trading code in `backend/stock/`, extract the real logic (parameters, formulas, conditions), and update the Markdown strategy design documents in `md/知识库/04-策略设计文档/`. These documents are PURE logic descriptions — no trading data.

2. **Phase 2 (生成报告)** — Take the updated MD docs (for theoretical/logic content) AND query the Django database models (for actual performance data), then generate a complete HTML analysis report using the template at `backend/templates/策略分析报告-完整数理分析.html`.

---

## Phase 1: Update Strategy Logic MD Documents

### Code-to-Document Mapping

Read the following code files and update the corresponding MD documents:

| Code File(s) | Topic | Target MD Doc |
|---|---|---|
| `core/indicators.py` (breakout logic), `scheduler/tasks_daily_close.py` | Donchian 20HL entry/exit signal generation | 策略设计-海龟增强V2交易全流程.md (or V3) |
| `core/atr.py`, `core/position_sizing.py` | ATR calculation, Unit sizing formula | 策略设计-海龟增强V2交易全流程.md |
| `core/stop_loss.py`, `infrastructure/stop_loss_executor.py`, `scheduler/tasks_exit_before_close.py` | Dynamic stop-loss, break-even, emergency exit | 策略说明-止损系统.md |
| `core/indicators.py` (trend_factor, trend_label) | Trend factor model, MA arrangement | 指标-趋势因子.md |
| `core/ma_slope.py` | MA10 slope ranking (comparison strategy) | 策略设计-MA10斜率排名.md |
| `infrastructure/order_execution.py`, `infrastructure/order_signals.py` | TargetPosTask management, two-step opening, gap protection | 策略设计-海龟增强V2交易全流程.md |
| `scheduler/tasks_daily_open.py` | Open-position execution (entry/rollover/add-on) | 策略设计-海龟增强V2交易全流程.md |
| `core/signal_checker.py` | Signal deduplication | 策略设计-海龟增强V2交易全流程.md |
| `core/performance.py` | Performance calculation logic | 三层绩效体系 (create or integrate into report) |
| `infrastructure/slippage_recorder.py` | Slippage recording | 功能说明-滑点统计.md (in 02-软件功能说明/) |

### How to Read and Extract Logic

When reading each code file, extract:

1. **Core formula** — The mathematical expression (e.g., `unit_lots = 4000 / (ATR × 2 × volume_multiple)`)
2. **Parameters** — All config values, their defaults, and their meanings
3. **Conditions** — All if/else branches that affect decision-making (e.g., gap protection threshold, trend factor limits)
4. **Data flow** — What inputs feed into the function and what outputs it produces
5. **Edge cases** — Any special handling (NaN protection, timeout fallback, min/max constraints)

### MD Document Structure Guidelines

Each MD doc should follow this structure:

```markdown
# 标题

> 涉及文件: file1.py, file2.py

---

## 一、核心公式

## 二、参数说明

## 三、判断条件

## 四、执行流程

## 五、边界处理
```

Use code blocks for actual Python snippets from the source. Use tables for parameter comparisons. Use formulas for mathematical expressions.

**Important rules:**
- DO write in Chinese
- DO keep formulas precise and match the actual code
- DO NOT include any trading data or performance numbers — these are purely logic documents
- DO reference file paths and line numbers where the logic lives
- DO note any differences between the V2 and V3 strategy variants

### Files to Update

The documents to update are in `md/知识库/未命名/04-策略设计文档/`:
- `策略设计-海龟增强V2交易全流程.md` — V2 strategy full workflow
- `策略设计-海龟增强V3交易全流程.md` — V3 strategy full workflow (if differs from V2)
- `策略说明-止损系统.md` — Stop loss system
- `指标-趋势因子.md` — Trend factor indicators
- `策略设计-原版海龟对比组.md` — Comparison with original Turtle
- `策略设计-双均线对照组.md` — MA crossover comparison
- `策略设计-MA10斜率排名.md` — MA10 slope ranking

Also in `md/知识库/未命名/02-软件功能说明/` if applicable:
- `功能说明-滑点统计.md` — Slippage statistics

---

## Phase 2: Generate HTML Analysis Report

After updating the MD documents, generate the HTML report.

### Template

The report template is at: `backend/templates/策略分析报告-完整数理分析.html`

This is a 1031-line standalone HTML file with 16 sections (s1-s16). The template currently contains static/example data. Your job is to:

1. **Read the updated MD docs** — Extract the theoretical logic content for sections that describe strategy mechanics (s1-s9, s11, s13-s14)
2. **Query the database** — Replace static example values with real performance data for data-driven sections
3. **Generate a new HTML file** — Write the output to `backend/templates/策略分析报告-完整数理分析.html` (overwriting the template) or to a new file like `策略分析报告-生成日期.html`

### Database Model Mapping

For data-driven sections, query Django models via a Python script. Key models and which sections need them:

| Section | Data Needed | Model(s) to Query |
|---|---|---|
| s2 (参数配置) | Actual strategy parameter values | `StrategyConfig` (via `account.strategyconfig`) |
| s4 (仓位计算) | Real ATR/乘数/Unit values per product | `FullContractList` (volume_multiple), `KlineData` (atr_20) |
| s10 (三层绩效) | All performance metrics | `AccountPerformanceSummary`, `RollingPerformanceMetrics`, `DailyEquitySnapshot`, `DailyStrategySignal`, `ClosedPositionRecord` |
| s6 (加仓分析) | Entry prices, add-on frequency | `PositionState`, `DailyStrategySignal` (trade_type=ADD_ON) |
| s15 (收益期望) | Actual returns, equity curve | `DailyEquitySnapshot`, `AccountPerformanceSummary` |
| s12 (敏感性) | Not directly queryable — keep as theoretical | N/A |

### Account Filtering

There are 5 accounts in the DB, but only 4 trading accounts. **Always filter to these 4** (skip account 4 which is the admin test account):

| ID | Name | Strategy | AccountPerformanceSummary key |
|---|---|---|---|
| 1 | 510976 | 海龟V2 | `commission_total=18.96` |
| 5 | 510977 | 海龟V3 | `commission_total=0.00` |
| 6 | 510988 | 原版海龟(Turtle) | `commission_total=93.04` |
| 10 | 510978 | HVOB-MBI | `commission_total=107.90`, `closed_profit_total=4200.00` |

### Data Query Approach

Use a Python script with Django ORM. **Critical: Set PYTHONUTF8=1 to avoid GBK encoding errors** when printing Chinese/¥ characters:

```python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'application.settings'
os.environ['PYTHONUTF8'] = '1'
django.setup()

from stock.models import TradingAccount, AccountPerformanceSummary, DailyEquitySnapshot, DailyStrategySignal, ClosedPositionRecord
from django.db.models import Count, Sum
```

For data-driven sections, first query all the data you need, then generate replacement strings matching the HTML exactly.

### s10 账户总览 — DB Field Mapping

Column order in table: **原版海龟 (Acc 6)** / **海龟V2 (Acc 1)** / **海龟V3 (Acc 5)** / **HVOB-MBI (Acc 10)**

| Table Row | DB Source | Notes |
|---|---|---|
| 当前权益 | `TradingAccount.current_equity` | Format with `&yen;` + thousands comma, round to integer |
| 累计收益率 | `(current_equity - initial_balance) / initial_balance × 100` | Show sign: "+0.40%", "-0.02%", "0.00%", "+2.52%" |
| 整体胜率 | `AccountPerformanceSummary.overall_win_rate` | `100%` or `-` (if no closed trades) |
| 盈利因子 | `AccountPerformanceSummary.overall_profit_factor` | `999.99` or `-` (if no closed trades) |
| 总交易次数 | `DailyStrategySignal` count where `executed_status='SUCCESS'` | Per account |
| 累计手续费 | `AccountPerformanceSummary.commission_total` | Format `&yen;N` (e.g. `&yen;93.04`) |
| 最大连续亏损 | `AccountPerformanceSummary.consecutive_losses` | 0 if none |
| 20日夏普比率 | `RollingPerformanceMetrics` (20d) | Or `-` if not enough data |
| 最佳单笔盈利 | `AccountPerformanceSummary.best_single_trade` | Or `-` |
| 最差单笔亏损 | `AccountPerformanceSummary.worst_single_trade` | Or `-` |
| 累计平仓盈亏 | `AccountPerformanceSummary.closed_profit_total` | Format `&yen;N` (e.g. `&yen;4,200`) |

**总交易次数 定义**: Count of `DailyStrategySignal.objects.filter(account=acc, executed_status='SUCCESS')` — this represents actual orders placed, NOT closed round-trip trades.

### s10 信号统计对比 — DB Query

Query:
```python
qs = DailyStrategySignal.objects.values('account_id', 'trade_type', 'executed_status')\
    .annotate(cnt=Count('id')).order_by('account_id', 'trade_type', 'executed_status')
```

Column order: Turtle(Acc6) / V2(Acc1) / V3(Acc5) / HVOB(Acc10)
Row order: ENTRY → STOP_LOSS → ADD_ON → ROLLOVER → 总计 → 已执行(SUCCESS)

### s12 持仓结构对比 — Column Rules

**CRITICAL: The "单位" column MUST NOT be included.** The table has only 6 columns:

```
<tr><th>账户</th><th>品种</th><th>方向</th><th>手数</th><th>成本价</th><th>止损价</th></tr>
```

- The V3 "暂无持仓" row must use `colspan="6"` (not 7)
- Each data row has exactly 6 `<td>` elements (no unit column)

### s13 平仓盈亏明细 — Closed Positions

Query `ClosedPositionRecord.objects.filter(account=acc)` for each account. Key fields:
- `symbol`, `direction`, `volume`, `exit_price`, `cost_price`
- `pnl` — profit/loss (format `&yen;N` with thousands separator)
- `holding_days`, `trade_date`

### HTML File Format Constraints (重要!)

The report file has specific formatting that `.replace()` must match exactly:

1. **Indentation: 4 SPACES only** (NOT tabs). Exception: line 396 (累计手续费) uses `\t` (tab) + 2 spaces
2. **Line endings**: Windows CRLF (`\r\n`) — Python `open(..., 'r')` handles this transparently
3. **¥ symbol**: Table cells use `&yen;` HTML entity. Text content uses raw `¥` (U+00A5/\xa5)
4. **Never use Edit tool** for this file — the indentation mix (4 spaces, some 2 spaces, one tabbed line) causes Edit to fail. Always use a Python script with `.replace()` on exact strings
5. **Verify uniqueness**: After each `.replace()`, assert `old in html` and check `html.count(old) == 1`
6. **CRITICAL: Encoding setup for Python scripts** — must set `PYTHONUTF8=1` to avoid console crash when printing `¥` characters:
   ```python
   os.environ['PYTHONUTF8'] = '1'
   ```
   Or use `set PYTHONUTF8=1` before `python script.py` in bash/cmd.
   Or write to a UTF-8 text file instead of console output:
   ```python
   with open('debug.txt', 'w', encoding='utf-8') as f:
       f.write(str(data))
   ```

### Section-by-Section Filling Guide

For each section in the template:

- **s1 (架构总览)** — Read from the updated MD docs. Static architecture description.
- **s2 (参数配置)** — Query `StrategyConfig` for each account's actual parameter values. Replace the hardcoded table.
- **s3 (开仓逻辑)** — Read from updated MD docs (breakout logic). Keep theoretical content.
- **s4 (仓位计算)** — Query `FullContractList` for real `volume_multiple` values, `KlineData` for real `atr_20`. Calculate actual Unit lots and show in the table.
- **s5 (趋势因子)** — Read from updated MD docs + `指标-趋势因子.md`. Keep theoretical content.
- **s6 (加仓分析)** — Read from updated MD docs for theory. Query `PositionState` for current entry levels and `DailyStrategySignal` for add-on history for real examples.
- **s7 (止损系统)** — Read from updated MD docs + `策略说明-止损系统.md`. Keep theoretical content.
- **s8 (保本兜底)** — Read from updated MD docs. Keep theoretical content.
- **s9 (信号执行)** — Read from updated MD docs. Keep theoretical content.
- **s10 (三层绩效)** — **Most important data-driven section.** Replace all hardcoded metrics with real data:
  - Query `AccountPerformanceSummary` for: annualized_return, max_drawdown, overall_win_rate, overall_profit_factor, sharpe ratio, total trades, commission_total, closed_profit_total, best_single_trade, worst_single_trade
  - Query `DailyEquitySnapshot` for equity curve data (latest N days balance) — ordered by `trade_date`
  - Query `DailyStrategySignal` grouped by `account_id`, `trade_type`, `executed_status` for signal comparison table
  - Query `RollingPerformanceMetrics` for window-based metrics (20d, 60d, 120d sharpe/volatility)
  - Generate a CSS bar chart from actual daily return data
  - **总交易次数**: Use count of SUCCESS signals, NOT `AccountPerformanceSummary.total_trades_all_time` (which counts closed round-trip trades only)
- **s11 (风险场景)** — Read from updated MD docs. Keep theoretical but check if any risk scenarios should be updated based on actual incidents in ErrorLog.
- **s12 (敏感性)** — Keep as theoretical analysis (no direct DB source).
- **s12 (持仓结构对比)** — Updated from `PositionState` model. **No "单位" column.** 6-column table only.
- **s13 (海龟对比)** — Read from updated docs. Keep theoretical content.
- **s14 (回测差异)** — Read from updated docs. Keep theoretical content.
- **s15 (收益期望)** — Replace hardcoded equity scale table with real data from `AccountPerformanceSummary`. Generate equity curve bar chart from `DailyEquitySnapshot`.
- **s16 (结论)** — Update the metrics dashboard with real data from `AccountPerformanceSummary`. Keep qualitative conclusions.

### Output Format

- Update the cover page date to today's date
- Keep the existing CSS and HTML structure intact
- Replace hardcoded values in tables, metric cards, and charts with real data
- For sections without DB data sources (pure theory), the existing content should still be reviewed against the updated MD docs for correctness
- Save the output to: `backend/templates/策略分析报告-完整数理分析.html`

---

## Execution Checklist

When triggered, follow these steps in order:

1. **Read code** — Read the key Python files in `backend/stock/core/`, `backend/stock/infrastructure/`, `backend/stock/scheduler/` to understand current logic
2. **Read existing MD docs** — Read the current state of all docs in `md/知识库/04-策略设计文档/` and `02-软件功能说明/`
3. **Update MD docs** — Write updated content to the MD files, ensuring formulas and parameters match the actual code
4. **Read the HTML template** — Read `backend/templates/策略分析报告-完整数理分析.html` to understand current structure. **Note file format**: 4-space indentation, `&yen;` in table cells, CRLF line endings
5. **Query DB** — Use Django ORM via Python script (set `PYTHONUTF8=1`). Filter to 4 trading accounts only (IDs 1, 5, 6, 10 — skip ID 4 which is admin test account)
6. **Generate HTML** — Use a Python script with `.replace()` on exact strings (NOT the Edit tool — indentation issues cause silent failures). Assert each replacement was found before applying. Clean up the temp script afterward
7. **Verify changes** — Read back the updated sections to confirm: s10 账户总览 table, s10 信号统计对比 table, s12 持仓结构对比 (no 单位 column)
8. **Report results** — Summarize what was updated in the MD docs and what data was refreshed in the HTML report
