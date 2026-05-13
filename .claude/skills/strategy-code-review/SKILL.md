---
name: strategy-code-review
description: Review strategy code changes against the strategy design document. Use this whenever the user modifies trading strategy code (tasks_daily_open.py, tasks_daily_close.py, order_signals.py, order_execution.py, stop_loss_executor.py, indicators.py, atr.py, stop_loss.py, position_sizing.py, signal_checker.py) or asks you to "review the logic", "check if it matches", "verify the strategy", "does this align with the doc", or similar phrases about strategy correctness. Do NOT trigger for general code changes unrelated to trading strategy.
---

# Strategy Code Review

Review strategy code changes against the canonical strategy design documents. Your job is to find discrepancies between the documented intent and the actual implementation.

## Trigger Carefully

This skill triggers for strategy-related code changes. When invoked:
1. Identify what files changed (git diff or user description)
2. Locate the relevant strategy design document(s)
3. Systematically trace the affected logic chain
4. Report discrepancies

## Strategy Documents

The ground truth is in `md/知识库/未命名/04-策略设计文档/`. The primary document is `策略设计-海龟增强V2交易全流程.md`. Other strategy variants have their own documents:
- `策略设计-海龟增强V3交易全流程.md`
- `策略设计-原版海龟对比组.md`
- `策略设计-双均线对照组.md`
- `策略设计-MA10斜率排名.md`
- `策略说明-止损系统.md`
- `指标-趋势因子.md`

Read the relevant document(s) first. The strategy doc is the authoritative spec — code must match it.

## Review Scope

Always check the COMPLETE chain, not just the changed file:

```
信号生成 → 信号存储 → 开盘执行 → 止损更新 → 紧急止损 → 收盘计算 → 绩效记录
```

For each link in the chain, verify:

### 1. Entry (ENTRY)

- **Trigger condition**: Donchian 20HL breakout only, no MA filter. Breakout uses prior 20-day H/L, NOT including today's bar.
- **Skip choppy entry**: When `skip_choppy_entry=True`, signals with `trend_label in ('choppy', 'neutral')` → CANCELLED
- **Position sizing**: `unit_lots = 4000 / (ATR * 2 * contract_multiplier)`
- **Gap protection**: `gap_ratio > 1.5 * ATR` → cancel with remark
- **Min position**: Two-step open when `planned_volume < min_position`
- **PositionState init**: Check all fields set: `units=1`, `direction`, `contract_total_position`, `last_add_price`, `first_open_price`, `highest_close`, `lowest_close`, `open_date`, `entry_trend_factor`, `entry_trend_label`, `entry_atr`

### 2. Stop-Loss (STOP_LOSS)

- **Signal generation (15:02 after close)**: `latest_close < stop_loss` (long) or `latest_close > stop_loss` (short) → STOP_LOSS signal
- **Emergency stop (14:57)**: Uses `quote.last_price` (NOT `latest_close_price` from DB)
- **Dynamic stop calculation**: 
  - Long: `highest_close - 2 * (1 + factor) * atr`
  - Short: `lowest_close + 2 * (1 + factor) * atr`
- **Cost protection**: enabled when profit > `PROTECT_COST_ENABLED_RATIO * ATR`. Final stop = max(dynamic, protect) for long, min(dynamic, protect) for short
- **Bidirectional extremum tracking**: Both `highest_close` and `lowest_close` tracked regardless of direction
- **Execution priority**: STOP_LOSS is highest priority in open task

### 3. Add-On (ADD_ON)

- **Signal generation**: Only when `0 < units < 3`
- **1→2 units**: benchmark = `last_add_price`, threshold = `0.5 * ATR`
- **1→3 units (direct)**: benchmark = `last_add_price`, threshold = `1.0 * ATR`
- **2→3 units**: benchmark = `first_open_price`, threshold = `1.0 * ATR`
- **Cap**: never exceed `POSITION_MAX_UNITS = 3`
- **Execution**: TargetPosTask target increment, update `units`, `contract_total_position`, `last_add_price`

### 4. Rollover (ROLLOVER)

- **Trigger**: `is_rollover_needed=True` from contract sync
- **Phase 1**: Close old contract (TargetPosTask=0)
- **Phase 2**: Open new contract (same direction, same volume, min position check)
- **Phase 3**: Init new contract's high/low/stop from 20-day history, create new PositionState, delete old
- **Priority**: After ENTRY, before ADD_ON

### 5. Exit Trend Recording

- `ClosedPositionRecord.entry_*` copied from PositionState (frozen at entry)
- `exit_*` from signal (at exit)
- `exit_atr` from real-time `calculate_atr()`
- MFE/MAE from `highest_close`/`lowest_close`

### 6. Signal State Flow

```
PENDING → EXECUTING → SUCCESS | FAILED | CANCELLED
```

- `check_duplicate_pending_signal`: Only one PENDING signal per symbol per trade_type per day

### 7. Execution Priority (Open Task)

1. STOP_LOSS (highest)
2. ENTRY
3. ROLLOVER
4. ADD_ON (lowest)

This order must not change.

### 8. Key Parameters

| Parameter | Value | Where used |
|-----------|-------|------------|
| `POSITION_RISK_BASE_AMOUNT` | 4000 | position_sizing.py |
| `POSITION_RISK_MULTIPLIER` | 2 | position_sizing.py |
| `POSITION_MAX_UNITS` | 3 | entry/add_on logic |
| `PROTECT_COST_ENABLED_RATIO` | 2.5 | stop_loss update |
| `GAP_PROTECTION_RATIO` | 1.5 | entry gap check |
| `TIMEOUT_SECONDS` | 60 | order execution |
| `TREND_GAP_LIMIT` | 0.03 | trend factor calc |
| `TREND_FACTOR_MAX` | 0.5 | trend factor calc |

Verify these against `backend/stock/parameter_config.py` and `backend/stock/core/config_loader.py`.

## Report Format

Output a structured report with these sections:

### Summary
One-line verdict: PASS / MINOR ISSUES / MAJOR ISSUES

### Changes Detected
List the changed files and a one-line summary of each change.

### Chain Review
For each affected chain link:
| Link | Matches Doc? | Notes |
|------|-------------|-------|
| Signal generation | ✅ / ⚠️ / ❌ | What's different |
| Signal execution | ✅ / ⚠️ / ❌ | What's different |
| ... | ... | ... |

### Discrepancies Found
For each discrepancy:
1. **Where**: file:line
2. **Doc says**: what the strategy document specifies
3. **Code does**: what the code actually implements
4. **Impact**: none / minor / major (does it affect PnL or risk?)
5. **Fix suggestion**: how to align

### Parameter Audit
If parameters changed, list old vs new with impact assessment.

### Verification Checklist
Specific things to test manually after deploying.

## Key Files Reference

Read these files when they are affected by the change:

| File | Role |
|------|------|
| `backend/stock/scheduler/tasks_daily_open.py` | Open execution: STOP_LOSS → ENTRY → ROLLOVER → ADD_ON |
| `backend/stock/scheduler/tasks_daily_close.py` | Close calculation: signal gen + stop update + performance |
| `backend/stock/scheduler/tasks_exit_before_close.py` | 14:57 emergency stop |
| `backend/stock/infrastructure/order_signals.py` | Signal execution: entry/add_on/exit/rollover |
| `backend/stock/infrastructure/order_execution.py` | Execution tools: wait, min position, two-step, record |
| `backend/stock/infrastructure/stop_loss_executor.py` | Emergency stop: execute + check |
| `backend/stock/core/indicators.py` | ATR, MA, Donchian, trend factor calculation |
| `backend/stock/core/atr.py` | ATR calc + gap protection |
| `backend/stock/core/stop_loss.py` | Stop loss pure functions |
| `backend/stock/core/position_sizing.py` | Unit lot calculation |
| `backend/stock/core/signal_checker.py` | Duplicate signal prevention |
| `backend/stock/core/performance.py` | Performance metrics + commission tracking |
| `backend/stock/models.py` | PositionState, DailyStrategySignal, ClosedPositionRecord |
| `backend/stock/parameter_config.py` | All configurable parameters |

## Important Notes

- The strategy doc says Donchian 20HL is the ONLY entry filter. If you see MA alignment checks in code that are not for trend_factor, flag it.
- The system uses `latest_close_price` for 15:02 stop checks, but `quote.last_price` for 14:57 emergency stop. This is intentional — do not flag it.
- `cost_price` is synced daily from TqSDK `open_price_long`/`open_price_short` — add-on operations do NOT update `cost_price`. This is intentional.
- The open task reads PENDING signals from DailyStrategySignal. If a signal was created today but the open task hasn't run yet, it should still be PENDING — do not flag this as stale data.
- Backtest code (`backend/stock/backtest/`) is an independent offline tool with different MA filtering. It may not match the live system — flag discrepancies only if they affect comparison validity, not as bugs.
