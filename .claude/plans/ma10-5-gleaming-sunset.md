# MA10 斜率排名策略设计

## Context

基于用户需求：以 MA10 曲线斜率作为趋势强度指标，每日对所有品种计算 MA10 斜率，取排名前 5 的做多、排名后 5 的做空。需要设计开仓规则、平仓规则及设计理由。**不加仓、不移仓**，开仓后即固定仓位。

## Strategy Design: Entry / Exit Rules & Rationale

### 1. MA10 斜率计算

```
slope_pct = (MA10[t] - MA10[t - slope_period]) / MA10[t - slope_period] * 100
```

- 取当日 MA10 值与 `slope_period` 天前的 MA10 值计算百分比变化
- 用百分比确保不同价格水平的品种间可比（如铜 70000 vs 玉米 2400）
- 默认 `slope_period = 3`（MA10 的 3 日变化率，既平滑又灵敏）

**为什么用斜率而不是直接用 MA10 值或价格？**
- MA10 值的绝对大小不可比；斜率（变化率）在所有品种间统一尺度
- 斜率 > 0 = 上升趋势，斜率 < 0 = 下降趋势，越大表示趋势越强

### 2. 每日排名流程

每日收盘后（~15:30-15:32，在现有 `job_daily_close_calculation` 框架内）：

1. 遍历所有活跃主力合约（`FullContractList` 中 `is_active=True`）
2. 查询 `KlineData`，获取最近 `slope_period + 10` 天的 `ma_10` 数据（确保有足够数据计算）
3. 计算每个品种的 `ma_10_slope_pct`
4. 排除数据不足的品种
5. 按 slope 降序排列 → **Top 5 = 多头候选，Bottom 5 = 空头候选**

### 3. 入场规则

**多头入场（所有条件必须同时满足）：**
| # | 条件 | 说明 |
|---|------|------|
| 1 | 品种排名在前 5 (`ranking_top_n`) | 最强上升趋势 |
| 2 | `ma_10_slope_pct > min_slope_threshold` (默认 0.05%) | 排除基本走平的情况 |
| 3 | 当前无该品种的多头持仓（或持仓方向为空） | 不重复开/需反向 |
| 4 | 当前多头总持仓数 < `max_positions_per_side` (默认 5) | 不超过上限 |
| 5 | 当日尚未生成该品种的 PENDING ENTRY 信号 | 防重复 |

**空头入场（所有条件必须同时满足）：**
| # | 条件 | 说明 |
|---|------|------|
| 1 | 品种排名在后 5 | 最强下降趋势 |
| 2 | `ma_10_slope_pct < -min_slope_threshold` | 排除基本走平 |
| 3 | 当前无该品种的空头持仓（或持仓方向为多） | 不重复开/需反向 |
| 4 | 当前空头总持仓数 < `max_positions_per_side` | 不超过上限 |
| 5 | 当日尚未生成该品种的 PENDING ENTRY 信号 | 防重复 |

**执行时间：** 信号在收盘后生成（PENDING），次日开盘后执行（09:00-09:02）。这与现有系统的每日信号流程一致。

**为什么收盘后生成信号、次日开盘执行？** 因为排名基于日线 MA10，日线收盘后排名才是稳定的。盘中实时计算 rank 会反复变化导致频繁开平。

### 4. 离场规则

**触发任意一条即平仓：**

| 优先级 | 离场类型 | 多头条件 | 空头条件 | 设计目的 |
|--------|----------|----------|----------|----------|
| 1 (主) | **排名退化离场** | 品种跌出前 12 名 (`exit_threshold_rank=12`) | 品种升出倒数 12 名 | 趋势相对强度显著减弱 |
| 2 (辅) | **趋势反转离场** | `ma_10_slope_pct < 0` | `ma_10_slope_pct > 0` | 自身的趋势方向已变 |
| 3 (安全) | **硬止损离场** | 价格 <= 入场价 - `atr_stop_multiplier` × ATR | 价格 >= 入场价 + `atr_stop_multiplier` × ATR | 防跳空/黑天鹅 |

**为什么用 5→12 的缓冲区而不是 5→6？**
- 海龟系统用 20 日入场、10 日离场（入场周期 × 0.5 = 离场周期），本质是缓冲区
- MA10 斜率日间波动天然比价格大，排名在 5-12 之间浮动是正常的，给 7 个名次的缓冲区可有效减少"刚入场就出场"的反复磨损
- 实际上 `exit_threshold_rank = ranking_top_n * exit_rank_multiple`，`exit_rank_multiple = 2.4 ≈ 12/5`

**为什么需要趋势反转离场？** 防止"矮子里拔将军"——所有品种都走平下跌时，跌得最少的可能排名还在前 5，但自身斜率已为负，此时应离场。

**为什么需要硬止损？** 排名离场每日只检查一次（收盘），如果出现跳空低开/高开（例如开盘跌停），在没有盘中监控的情况下，等不到收盘就已经大幅亏损。硬止损作为安全网，在盘中实时检查。

### 5. 其他设计要点

**仓位管理：**
- 每品种固定 1 单位，不加仓
- 每单位手数 = `floor(账户权益 × risk_per_trade_pct / (stop_multiplier × ATR × 合约乘数))`
- 默认 `risk_per_trade_pct = 1.0%`，10 个仓位总风险 10%
- 单品种最大手数下限 1 手，上限可配置

**盘中实时模块（可选）：**
- 如果启动实时监控模式，盘中检查硬止损条件
- 但不做盘中排名（排名只在收盘后重算）

**与现有系统的整合：**
- 信号模型复用 `DailyStrategySignal`，`trade_type` 用 `ENTRY` / `STOP_LOSS`
- 持仓模型复用 `PositionState`，但 `units` 固定为 1
- 策略配置复用 `StrategyConfig`，新增以下字段

### 6. 参数汇总

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `slope_period` | 3 | MA10 斜率计算周期（日） |
| `ranking_top_n` | 5 | 每方向候选品种数 |
| `exit_threshold_rank` | 12 | 排名退出阈值 |
| `min_slope_threshold` | 0.05 | 最小斜率阈值（%） |
| `max_positions_per_side` | 5 | 每方向最大持仓数 |
| `risk_per_trade_pct` | 1.0 | 每笔风险占权益百分比 |
| `atr_stop_multiplier` | 2.5 | 硬止损 ATR 倍数 |

---

## Implementation Plan

### Files to Create

| File | Purpose |
|------|---------|
| `md/知识库/未命名/04-策略设计文档/策略设计-MA10斜率排名.md` | 策略设计文档（中文，含完整规则+理由） |
| `backend/stock/core/ma_slope.py` | MA10 斜率计算核心模块（被调度任务和背测共用） |
| `backend/stock/backtest/strategy_ma10_slope.py` | 回测策略逻辑（多品种同时评估的排名引擎） |
| `backend/stock/backtest/config_ma10_slope.py` | 回测配置（独立于现有 BacktestConfig） |
| `backend/stock/management/commands/run_ma10_slope.py` | 实盘管理命令 |

### Files to Modify

| File | Change |
|------|--------|
| `backend/stock/models.py` → `StrategyConfig` | 新增 MA10 斜率参数 field（slope_period, ranking_top_n, exit_threshold_rank 等） |
| `backend/stock/core/config_loader.py` | 新增 DEFAULTS + FIELD_MAP 条目 |
| `backend/stock/scheduler/tasks_daily_close.py` | 新增 `check_ma10_slope_signals()` 函数，在收盘任务末尾调用 |

### Implementation Steps

**Step 1 — 策略设计文档**
- 写 `md/知识库/未命名/04-策略设计文档/策略设计-MA10斜率排名.md`
- 包含完整的中文设计说明：计算方式、排名逻辑、入场 5 条件、离场 3 条件、每个规则的设计理由

**Step 2 — 核心计算模块 `core/ma_slope.py`**
- 函数 `compute_ma10_slope(kline_data_df, slope_period=3)` → 返回 `slope_pct`
- 函数 `rank_by_ma10_slope(account=None, date=None, slope_period=3)` → 返回 `(long_candidates, short_candidates)`，各含 Top N
  - 从 `KlineData` 查询所有活跃标的的最新 `ma_10` 数据
  - 按 `product_code` 去重，每个品种只取主力合约
  - 计算斜率 → 排序 → 取 Top/Bottom N
  - 排除已有持仓的品种（信号检查器复用 `check_duplicate_pending_signal`）
- 函数 `calculate_ma10_slope_series(df, slope_period=3)` → 纯 pandas 回测用

**Step 3 — 模型配置扩展**
- `StrategyConfig` 新增字段（带 migration）:
  - `slope_period`: IntegerField(default=3)
  - `ranking_top_n`: IntegerField(default=5)
  - `exit_threshold_rank`: IntegerField(default=12)
  - `min_slope_threshold`: DecimalField(default=0.05)
  - `max_positions_per_side`: IntegerField(default=5)
  - `risk_per_trade_pct`: DecimalField(default=1.0)
  - `atr_stop_multiplier`: DecimalField(default=2.5)
- `config_loader.py` 新增对应的 DEFAULTS + FIELD_MAP + type_map

**Step 4 — 收盘信号生成**
- `tasks_daily_close.py` 新增 `check_ma10_slope_signals(account)`:
  1. 调用 `rank_by_ma10_slope()` 获取候选
  2. 遍历候选 → 检查持仓 → 生成 ENTRY 信号（`DailyStrategySignal`，`trade_type='ENTRY'`）
  3. 遍历现有持仓 → 检查是否满足离场条件 → 生成 STOP_LOSS 信号
- 在 `job_daily_close_calculation()` 末尾调用（需判断是否启用该策略）

**Step 5 — 实盘管理命令 `run_ma10_slope.py`**
- 参照 `run_turtle.py` 结构，`--mode once | monitor | exit_only`
- `_handle_once`: 计算排名并输出
- `_handle_monitor`: 开盘执行入场/离场 + 盘中硬止损监控
- 复用 `order_signals.py` 中的 `execute_entry_order` / `execute_exit_order`

**Step 6 — 回测**
- `config_ma10_slope.py`: MA10 slope 专用 backtest config 类
- `strategy_ma10_slope.py`: 多品种排名回测引擎
  - 加载所有品种日线数据
  - 每日: 计算所有品种 MA10 斜率 → 排名 → 决策 → 次日开盘执行
  - 记录持仓和 equity curve
- 参考现有 `backtest/engine.py` + `portfolio.py` 的结构

### Verification

1. **核心计算测试**: 用已知数据的品种验证 `compute_ma10_slope` 结果与手算一致
2. **排名逻辑测试**: 造 10 个品种的模拟 MA10 数据，验证排名和前 5/后 5 选取正确
3. **回测验证**: 对历史 3 年数据跑回测，检查信号生成是否符合预期
4. **实盘 dry-run**: `run_ma10_slope --mode once` 查看每日排名输出，确认逻辑正确

### Key Constraints

- 不引入新的第三方依赖
- 回测和实盘共用 `core/ma_slope.py` 中的计算逻辑
- 信号通过 `DailyStrategySignal` 持久化，与现有系统一致
- 持仓通过 `PositionState` 管理，复用现有的 `order_execution` 基础设施
- 遵循项目日志约定（`log_trade` / `log_error`）
