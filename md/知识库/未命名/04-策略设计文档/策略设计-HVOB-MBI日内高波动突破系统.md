# HVOB-MBI 日内高波动突破系统

> 涉及文件: `hvob_mbi/config.py`, `hvob_mbi/screening.py`, `hvob_mbi/mbi.py`, `hvob_mbi/trading_engine.py`, `hvob_mbi/signal_recorder.py`, `hvob_mbi/models.py`, `stock/models.py` (FullContractList.night_trading), `hvob_mbi/management/commands/hvob_trading.py`

---

## 一、策略概述

HVOB-MBI（High Volatility Opening Range Breakout - Market Breadth Index）是一个纯日内系统，捕捉高波动品种开盘后的第一波方向性行情。所有持仓在收盘前强制平仓，不做隔夜。

**核心定位：** 日内趋势启动捕捉
**风控层次：** MBI 市场氛围过滤 → 时间衰减 → 跳空回避 → 单品种单日一次 → 强制平仓

---

## 二、品种分类

A/B 分类不再硬编码，从 `FullContractList.night_trading` 字段动态获取。

优先品种（平今免费/优惠 + 高波动）: `SA, FG, RB, HC, MA, TA, SC, AG, P, Y, OI, SR`
→ 筛选评分 +3 分

回避品种（双边收费）: `NI, SN, PB, ZN, CU`
→ 筛选评分 -2 分

冷门品种（流动性差，直接排除）: `FB, BB, RR, CS, B, JR, WH, PM, RI, LR, SF`

---

## 三、参数说明

### 3.1 筛选参数

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `ATR_PERCENT_RANK_TOP` | 0.02 | ATR% > 2% |
| `MIN_AMPLITUDE_5D` | 0.015 | 近 5 日平均振幅 > 1.5% |
| `OR_MIN_RATIO` | 0.8 | 开盘区间高度 >= 0.8 × 20 日平均(预留) |
| `MAX_VOL_SCORE` | 5 | 量比得分上限，防止爆量品种主导评分 |

### 3.2 交易参数

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `BREAKOUT_OFFSET_RATIO` | 0.3 | 突破偏移量 H+0.3R / L-0.3R |
| `STOP_OFFSET_RATIO` | 0.2 | 止损偏移量 L-0.2R(多) / H+0.2R(空) |
| `DEFAULT_RISK_PERCENT` | 0.005 | 单笔风险比例 0.5% |

### 3.3 时间参数

| 参数 | 值 | 含义 |
|------|----|------|
| `NIGHT_OPEN` | 21:00 | 夜盘开盘 |
| `NIGHT_OR_CLOSE` | 21:30 | 夜盘开盘区间结束 |
| `DAY_OPEN` | 9:00 | 日盘开盘 |
| `DAY_OR_CLOSE` | 9:30 | 日盘开盘区间结束 |
| `FORCE_CLOSE_TIME` | 14:55 | 强制平仓 |
| `LAST_ENTRY_TIME` | 14:30 | 最后入场时间 |

### 3.4 时间衰减系数

| 时间段 | 仓位系数 |
|--------|---------|
| 9:30 - 10:30 | 1.0 (100%) |
| 10:30 - 11:30 | 0.7 (70%) |
| 13:30 - 14:30 | 0.3 (30%) |

### 3.5 定时重启时间点

| 时间 | 用途 |
|------|------|
| 08:55 | 日盘开盘前重建连接，确保 9:00 行情数据新鲜 |
| 13:25 | 下午盘前重建，确保持续连接质量 |
| 20:55 | 夜盘开盘前重建，确保 21:00 行情数据新鲜 |

重启流程：关闭旧连接 → 等待 35s → 重建 `create_tqapi` → `wait_update(15s)` 等待就绪 → 重新订阅行情 → `wait_update(10s)` → 清空旧 `TargetPosTask`（新连接需重新创建）。

### 3.6 MBI 交易权限映射

| MBI 区间 | 定性 | 多单权重 | 空单权重 |
|----------|------|---------|---------|
| > 0.75 | 极强多头 | 1.0 | 0.0 |
| 0.65 - 0.75 | 多头 | 1.0 | 0.5 |
| 0.45 - 0.65 | 震荡 | 1.0 | 1.0 |
| 0.35 - 0.45 | 空头 | 0.5 | 1.0 |
| < 0.35 | 极强空头 | 0.0 | 1.0 |

---

## 四、核心公式

### 4.1 品种筛选评分

```
score = (atr_pct >= 0.02 ? atr_pct × 100 : 0)
      + (avg_amp >= 0.015 ? avg_amp × 50 : 0)
      + (vol_ratio > 1.0 ? min((vol_ratio - 1.0) × 10, 5) : 0)
      + (PREFERRED_PRODUCTS ? +3 : 0)
      + (AVOID_PRODUCTS ? -2 : 0)
```

其中：
- `atr_pct = avg(high - low, 20期) / latest_close`
- `avg_amp = avg((high - low) / open, 5期)`
- `vol_ratio = latest_volume / avg(volume, 20期)`

### 4.2 突破触发价

```
多方向: h_break = OR_H + 0.3 × OR_R
空方向: l_break = OR_L - 0.3 × OR_R
```

### 4.3 止损价（永久锚定）

```
多单止损: stop_loss = OR_L - 0.2 × OR_R
空单止损: stop_loss = OR_H + 0.2 × OR_R
```

止损价在开仓时计算一次，持仓期间永不重算。

### 4.4 手数计算（风险敞口法）

```
risk_amount = balance × risk_percent
stop_distance = OR_R × (1 + BREAKOUT_OFFSET_RATIO + STOP_OFFSET_RATIO)
             = OR_R × (1 + 0.3 + 0.2) = OR_R × 1.5
volume = max(1, int(risk_amount / (stop_distance × volume_multiple)))
volume = min(volume, max_positions_per_day)
```

**注意：** `stop_distance` 是开仓价到止损价的**实际距离**。对多单而言，开仓价 ≈ OR_H + 0.3R，止损价 = OR_L - 0.2R，两者相减 = (OR_H + 0.3R) - (OR_L - 0.2R) = (OR_H - OR_L) + 0.3R + 0.2R = R + 0.5R = 1.5R。不能简化为 0.4R（原 Bug CRITICAL-31，导致仓位 3.75 倍过大）。

### 4.5 固定盈亏比止盈

```
多单止盈价: entry_price + OR_R × 1.5
空单止盈价: entry_price - OR_R × 1.5
```

### 4.6 保本触发

```
多单触发价: entry_price + OR_R（浮盈超过 1 倍止损距离）
空单触发价: entry_price - OR_R
触发后: stop_loss = entry_price
```

### 4.7 移动止盈

```
// 多单
stop_distance = entry_price - stop_loss
if price - entry_price >= stop_distance × 2:
    stop_loss = max(stop_loss, price - stop_distance)

// 空单
stop_distance = stop_loss - entry_price
if entry_price - price >= stop_distance × 2:
    stop_loss = min(stop_loss, price + stop_distance)
```

### 4.8 MBI 计算

**单品种投票 (±1 each):**

```
维度1 - 隔夜跳空:
  (open_price - pre_close) / pre_close > 0.05% → +1
  (open_price - pre_close) / pre_close < -0.05% → -1
  否则 → 0

维度2 - 区间重心:
  or_mid = (OR_H + OR_L) / 2
  or_mid > pre_close → +1
  or_mid < pre_close → -1

维度3 - 突破方向:
  last_price > OR_H → +1
  last_price < OR_L → -1
```

**汇总映射 [0,1]:**

```
total_score = sum(品种得分)
valid_count = 参与品种数
mbi_value = (total_score - (-3 × valid_count)) / (3 × valid_count - (-3 × valid_count))
           = (total_score + 3n) / 6n
```

---

## 五、判断条件

### 5.1 盘前筛选条件

筛选全市场主力合约（排除 CFFEX 品种），通过综合评分选取得分前 N 名。

**排除规则（满足任一即跳过）：**
1. 冷门品种 → `LOW_LIQUIDITY_PRODUCTS` 列表中的品种直接跳过
2. 持仓量 < 20000 手 → 使用日线 `close_oi` 字段判断
3. 数据不足 → 日线不足 25 根、ATR 计算不足 14 个数据点、振幅不足 3 天

**评分公式：**
```
score = (atr_pct >= 0.02 ? atr_pct × 100 : 0)
      + (avg_amp >= 0.015 ? avg_amp × 50 : 0)
      + (vol_ratio > 1.0 ? min((vol_ratio - 1.0) × 10, 5) : 0)
      + (PREFERRED_PRODUCTS ? +3 : 0)
      + (AVOID_PRODUCTS ? -2 : 0)
```

**选取数量：** 取评分前 `max(min_watchlist_size, min(max_positions_per_day × 2, 10))` 个品种。

**返回结果：** 每条包含 `symbol, product_code, score, atr_pct, avg_amp, vol_ratio, atr_score, amp_score, vol_score, bonus, open_interest`。筛选完成后立即通过 `_save_watchlist_items()` 写入 `HvobMbiWatchlistItem` 表（独立记录），同时保存在内存 `self.watchlist` 中供后续使用。EOD `_save_daily_state()` 也会再次持久化到 `HvobMbiDailyState.watchlist` JSON 字段。

### 5.2 入场条件

| 场景 | 阶段 | 触发条件 | 仓位 |
|------|------|---------|------|
| 夜盘突破 | night_breakout | 价格突破 H+0.3R 或 L-0.3R | 100%（无 MBI 过滤） |
| 日盘突破 | day_breakout | 同上 | 时间衰减 × MBI 权重 |
| 跳空穿越 | gap_check | 开盘价在夜盘区间外 | 拉黑，不交易 |

### 5.3 出场条件

| 类型 | 触发条件 |
|------|---------|
| 止损 | 多: `price <= stop_loss` / 空: `price >= stop_loss` |
| 固定止盈 | 多: `price >= entry_price + 1.5 × R` / 空: `price <= entry_price - 1.5 × R` |
| 保本 | 浮盈超过 1 倍 R 后，止损拉至开仓价 |
| 移动止盈 | 浮盈超过 2 倍止损距离后，止损跟随移动 |
| 强制平仓 | 14:55 全部平仓 |

### 5.4 禁止交易条件

1. 品种已被拉黑（跳空穿越）→ 全天禁止
2. 品种已交易（单品种单日一次）→ 禁止二次入场
3. MBI 权限禁止（日盘）：多单 MBI < 0.35 时禁止，空单 MBI > 0.75 时禁止

---

## 六、执行流程

### 6.1 相位流程

```
screening(启动)
    │ 盘前筛选：TqSDK 拉取日线计算 ATR%/振幅/成交量
    │ 返回 dict 格式评分明细
    │ 调用 _save_watchlist_items() 写入 HvobMbiWatchlistItem 表
    │ 内存 self.watchlist 中保留完整列表供交易使用
    ↓
night_or(21:00-21:30)
    │ 等待夜盘开盘区间结束
    │ 21:30 使用 TqSDK get_kline_serial(symbol, 60, 30) 获取最近 30 根 1 分钟 K 线
    │ 计算 OR_H = max(kline.high), OR_L = min(kline.low), OR_R = OR_H - OR_L
    │ K 线数据来自 TqSDK 服务器，程序崩溃重启后仍可正确计算
    ↓
night_breakout(21:30-次日9:00)
    │ 夜盘品种突破监测（无 MBI 过滤，夜盘覆盖整个时段因缺少日盘数据无法计算 MBI）
    │ 无夜盘品种不处理
    │ 每次 wait_update 检查 quote.last_price
    ↓
  [20:55 定时重启] ──→ 关闭连接 → 等待 35s → 重建 → 继续
    ↓
gap_check(9:00-9:30)
    │ 跳空检查后等待日盘开盘区间结束
    │ 9:30 关闭日盘区间 + 计算 MBI
    ↓
  [08:55 定时重启] ──→ 关闭连接 → 等待 35s → 重建 → 继续
    ↓
day_breakout(9:30-14:55)
    │ 全品种突破监测 + MBI 过滤 + 时间衰减
    │ 持续检查止损/止盈/保本/移动止盈
    ↓
  [13:25 定时重启] ──→ 关闭连接 → 等待 35s → 重建 → 继续
    ↓
force_close(14:55)
    │ TargetPosTask 设 0 → 强制平仓
    ↓
done
    │ wait_update() 刷新账户数据 → 记录日权益
    │ 保存日状态（含完整评分明细）
```

### 6.2 数据源

所有数据通过 TqSDK 实时获取：
- **日线用于筛选：** `api.get_kline_serial(symbol, 86400, 30)` — 盘前启动时拉取
- **实时报价：** `api.get_quote(symbol)` — `wait_update` 事件循环中获取
- **1 分钟 K 线：** `api.get_kline_serial(symbol, 60, 30)` — 夜盘 21:30 计算开盘区间 OR（崩溃安全）；日盘 9:30 也用于 `_close_day_opening_range()`（引擎迟到启动时回补完整区间）
- **5 分钟 K 线：** `api.get_kline_serial(symbol, 300, 50)` — 用于 MBI 计算

### 6.3 执行方式

通过 `TargetPosTask` 设置目标仓位：
- 开仓：`TargetPosTask.set_target_volume(n或-n)`
- 平仓：`TargetPosTask.set_target_volume(0)`

### 6.4 信号记录

开平仓信号写入现有表：
- `DailyStrategySignal`：`trade_type='ENTRY'/'EXIT'/'STOP_LOSS'`，备注 JSON 含 OR 数据、MBI、退出原因
- `ClosedPositionRecord`：平仓记录（无 strategy 字段，与海龟共用同一张表）
- `DailyEquitySnapshot`：日权益快照

---

## 七、边界处理

### 7.1 数据不足
- `screening.py`：日线不足 25 根、ATR 计算不足 14 个数据点、振幅不足 3 天 → 跳过该品种
- `screening.py`：CFFEX（中金所）品种直接排除（与日内策略不相关）
- `screening.py`：`LOW_LIQUIDITY_PRODUCTS` 列表品种直接排除
- `screening.py`：持仓量 `close_oi < 20000` 跳过
- `screening.py`：量比得分上限 `MAX_VOL_SCORE = 5`，防止爆量品种主导评分
- `mbi.py`：无 Quote 数据或开盘区间未关闭 → 跳过该品种
- `mbi.py`：无有效品种 → 默认 MBI = 0.5（中性）

### 7.2 账户余额异常
- `trading_engine.py`：`api.get_account().balance <= 0` → 使用 `100000` 作为 fallback

### 7.3 合约信息缺失
- `trading_engine.py`：`FullContractList` 中找不到合约 → 跳过该品种
- `PnL计算`：找不到合约时使用 `volume_multiple = 1`

### 7.4 止损距离为零
- `trading_engine.py`：`stop_distance <= 0` → 返回手数 `1`（最小开仓）

### 7.5 强制平仓数据缺失
- 报价为 0 或 None → 跳过该持仓（理论上不会发生，因 14:55 仍在交易时段）

### 7.6 区间跟踪阶段保护
- 同一品种在同一交易时段（夜盘/日盘）各只有一个开盘区间
- 区间关闭后不再更新（`closed` 标志保护）
- 夜盘阶段只更新夜盘品种的区间，日盘阶段只更新日盘品种的区间
- 夜盘 OR 在 21:30 一次性通过 1 分钟 K 线计算（非增量跟踪），不存在中途重启丢失数据的问题

### 7.7 连接重建保护

- `_check_restart` 使用 `restart_key = now.strftime('%Y-%m-%d-%H%M')` 防重复，同一分钟只触发一次
- `_reconnect` 中 `safe_close_api` → `time.sleep(35)` → `create_tqapi`，确保交易所网关连接完全刷新
- 重建后调用 `_subscribe_all()` 重新获取所有品种的 `get_quote` / `get_kline_serial` 代理引用
- 旧 `TargetPosTask` 绑定已关闭的连接，需清空后按需重新创建
- 重建期间内存状态（`positions`、`opening_ranges`、`banned`、`traded`、`watchlist`）完整保留，不受影响
- 重连**不会**重新执行筛选（`_do_screening`），仅恢复行情订阅和交易执行。`watchlist` 使用重建前已在内存中的数据，避免了重复筛选改变观察池导致持仓不一致

### 7.8 `_finalize` 数据保鲜

- 主循环退出（`phase='done'`）后，调用 `wait_update()` 确保 `get_account()` 读取的是最新权益数据
- 避免了在 `_force_close_all` 内部 `wait_update()` 之后到 `_finalize` 之间可能的数据陈旧问题

### 7.9 MBI 边界值
- `score_for_symbol` 平开判断阈值 `abs(gap_pct) < 0.0005` — 基本平开不投票
- `get_trading_permission` 中 `>= 0.45` 和 `> 0.45` 的区别：震荡区间包含下边界 0.45，不包含上边界 0.65

---

## 八、模型说明

### HvobMbiConfig（每账户策略配置）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| account | FK→TradingAccount | - | 关联账户 |
| is_active | BooleanField | True | 是否启用 |
| risk_percent | Decimal(5,4) | 0.005 | 单笔风险比例 |
| max_daily_loss_percent | Decimal(5,4) | 0.02 | 单日最大亏损比例 |
| fix_reward_risk_ratio | Decimal(4,2) | 1.5 | 固定盈亏比 |
| trailing_stop_enabled | BooleanField | True | 启用移动止盈 |
| trailing_stop_trigger_times | Decimal(4,1) | 2.0 | 移动止盈触发倍数 |
| min_watchlist_size | IntegerField | 5 | 观察池最小数量 |
| max_positions_per_day | IntegerField | 5 | 单日最大持仓数 |

### HvobMbiWatchlistItem（观察池条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| account | FK→TradingAccount | 关联账户 |
| trade_date | DateField(db_index) | 交易日 |
| rank | IntegerField | 排名 1~N |
| symbol | CharField(50) | 合约代码 |
| product_code | CharField(20) | 品种代码 |
| score | FloatField | 综合评分 |
| atr_pct | FloatField | ATR% |
| avg_amp | FloatField | 5日平均振幅 |
| vol_ratio | FloatField | 量比 |
| atr_score | FloatField | ATR得分 |
| amp_score | FloatField | 振幅得分 |
| vol_score | FloatField | 量能得分 |
| bonus | IntegerField | 品种奖惩（+3优选/-2回避） |
| open_interest | IntegerField | 持仓量 |

唯一约束：`unique_together = (account, trade_date, symbol)`。筛选完成后立即通过 `_save_watchlist_items()` 批量写入（`bulk_create` + `ignore_conflicts=True`），EOD `_save_daily_state()` 再次调用以覆盖可能遗漏的品种。

前端通过 `GET /api/stock/hvob-watchlist/` 接口分页查询，支持按日期和账户筛选。

### HvobMbiDailyState（每日状态快照）

| 字段 | 类型 | 说明 |
|------|------|------|
| account | FK→TradingAccount | 关联账户 |
| trade_date | DateField | 交易日 |
| watchlist | JSONField | 当日观察池列表（dict 格式，含 symbol/product_code/score/atr_pct/avg_amp/vol_ratio/atr_score/amp_score/vol_score/bonus/open_interest 评分明细） |
| mbi_value | DecimalField | MBI 值 |
| mbi_label | CharField | MBI 标签（极强多头/多头/中性/空头/极强空头） |
| opening_ranges | JSONField | 开盘区间 `{symbol: {H,L,R}}` |
| banned_symbols | JSONField | 跳空穿越拉黑品种 |
| traded_symbols | JSONField | 已交易品种 |
| total_trades | IntegerField | 交易次数 |
| daily_pnl | DecimalField | 日盈亏 |
| is_complete | BooleanField | 是否完成 |

---

## 九、独立部署说明

本系统作为独立 Django app `hvob_mbi` 部署，与现有海龟系统完全隔离。

**启动命令：**
```bash
python manage.py hvob_trading --account=1          # 实盘运行
python manage.py hvob_trading --account=1 --dry-run # 观察模式（不交易）
```

**运行方式：** TqSDK `wait_update` 事件循环，从启动持续运行到 14:55 强制平仓后自动退出。建议通过 systemd / supervisor 管理进程生命周期。

---

## 十、2026-05-25 BUG 修复记录

### 10.1 CRITICAL-13：开盘区间(OR)跟踪从未工作（零成交 Bug）

HVOB-MBI 策略自上线以来从未产生过一笔交易。数据库记录显示所有交易日 trades=0、opening_ranges={}。

**根因链路（4 个缺陷连锁）：**
1. `_check_phase` 中 `night_or` 阶段只有时间判断 + 过渡，没有调用 `_on_quote()` → 21:00-21:30 之间没有任何价格跟踪
2. `night_breakout` 阶段才开始调用 `_on_quote()` 创建 OR 条目，但 `_close_night_opening_range()` 已在过渡瞬间执行完毕 → 条目永不关闭，R 为 None
3. 日盘同理：`gap_check`(9:00-9:30)没有 `_on_quote()` 调用，`day_breakout` 阶段创建的日盘 OR 条目无法关闭
4. 即使夜盘 OR 条目存在，日盘 `_track_opening_range(is_night=False)` 会因 `is_night` 不匹配而跳过更新，且因 `closed=True` 直接 return，无法创建新条目

**修复要点：**
- `_check_phase` 将 `if phase and t >= TIME` 的二合一条件拆分为嵌套 if/else
- `night_or` 阶段 else 分支调用 `_on_quote('night_or')` 跟踪夜盘 OR
- `gap_check` 阶段 else 分支调用 `_on_quote('gap_check')` 跟踪日盘 OR
- `_check_gap()` 末尾添加夜盘 OR 条目清除逻辑，让出日盘 OR 跟踪

### 10.2 HIGH-27：夜盘开盘区间崩溃不可恢复（K 线法重写）

夜盘阶段(21:00-21:30)引擎崩溃重启后，开盘区间数据从零开始重新收集，导致 21:30 计算的区间不完整。

**根因：** 原实现通过 `_track_opening_range` 在 `wait_update` 循环中逐笔跟踪 quote 的 H/L，数据仅存在于内存中。重启后内存清空，必须重新收集 30 分钟才能得到完整区间，而重启时间可能已是 21:15+，剩余时间不足。

**修复要点：**
- 移除 `night_or` 阶段的 `_on_quote` → `_track_opening_range` 调用链
- 重写 `_close_night_opening_range()`：使用 `api.get_kline_serial(symbol, 60, 30)` 获取最近 30 根 1 分钟 K 线
- 直接从 K 线数据计算 `H = max(high)`, `L = min(low)`, `R = H - L`
- 数据源为 TqSDK 服务器，不受本地程序崩溃影响，任何时候调用均可得到完整 30 分钟区间
- 日盘 OR（9:00-9:30）仍保持 tick 级增量跟踪（因日盘 OR 关闭前已计算 MBI，且重启在 08:55 已完成，不存在数据丢失窗口）

### 10.3 HIGH-26：白天启动引擎卡死

引擎固定从 `night_or` 阶段启动，白天启动(9:00-21:00)会卡死到 21:30 才前进。

**根因：** 无 `_init_phase()` 根据当前时间修正相位。

**修复要点：**
- 新增 `_init_phase()` 方法，根据当前时间映射到正确启动相位
- `screening` 后在 `run()` 中调用 `_init_phase()`
- 若当前时间已收盘（14:55 后），early return 直接结束

### 10.4 HIGH-28：20:55 定时重启误触发 gap_check 切换

20:55 定时重启后，`_check_phase` 错误地从 `night_breakout` 切换到 `gap_check`，导致夜盘 OR 被清除、日盘 OR 在 20:55 被错误初始化。

**根因：** `_check_phase` 中 `night_breakout → gap_check` 的切换条件为 `DAY_OPEN <= t < NIGHT_OPEN`（9:00-21:00），20:55 满足条件误触发。期望的切换窗口仅为 9:00-9:30。

**修复要点：**
- 切换条件收紧为 `DAY_OPEN <= t < DAY_OR_CLOSE`（9:00-9:30）
- 21:00+ 的定时重启不再误切相位

### 10.5 MEDIUM-29：MBI 权重和时间衰减未作用于实际手数

`get_trading_permission()` 返回 0.5（半仓）和时间衰减返回 0.3（30%）时，实际开仓手数不受影响，始终为 `_calc_volume` 计算的全仓。

**根因：** `_calc_volume(symbol, direction, r)` 只使用风险敞口法，不接收 `weight` 参数。`weight` 在 `_check_entry` 中计算后仅存入 `Position.weight`（从未被读取），未参与手数计算。

**修复要点：**
- `_calc_volume` 返回基础手数后，乘以 `weight` 再取整：`volume = max(1, int(volume * weight))`
- weight=0 的场景（MBI 禁止方向）已在之前被 `if weight <= 0: return` 过滤

### 10.6 LOW-30：21:30 整点启动无夜盘 OR

引擎在 21:30 整点启动时，`_init_phase()` 直接跳到 `night_breakout`，跳过了 `night_or → night_breakout` 过渡中的 `_close_night_opening_range()` 调用，导致夜盘品种全天无 OR 数据。

**根因：** `_close_night_opening_range()` 仅在 `_check_phase` 的 `night_or → night_breakout` 分支调用。21:30+ 启动时起始相位已是 `night_breakout`，该分支不再执行。

**修复要点：**
- `_restore_night_breakout_state()` 在 DB 中找不到已保存 OR、且当前时间 >= 21:30 时，直接调用 `_close_night_opening_range()` 用 K 线计算
- 0:00-9:00 凌晨启动有已保存的夜盘 OR（前一晚的），走正常恢复路径

### 10.7 CRITICAL-31：stop_distance 公式错误（仓位 3.75 倍过大）

`_calc_volume()` 中 `stop_distance` 计算为 `OR_R × 0.2 × 2 = 0.4R`，但开仓价到止损价的**实际距离**为 `R + 0.3R + 0.2R = 1.5R`，导致风险敞口法计算的手数偏大 3.75 倍，实际风险比例约为 1.8%（非预期的 0.5%）。

**根因：** `stop_distance` 被误解为止损偏移量（`OR_L - 0.2R` 到 `OR_L` 的距离 = `0.2R`），而非开仓价到止损价的全距离。对多单：
```
开仓价 = OR_H + 0.3R
止损价 = OR_L - 0.2R
实际距离 = (OR_H + 0.3R) - (OR_L - 0.2R) = R + 0.5R = 1.5R
```

**修复要点：**
- `stop_distance = float(or_r) * (1 + BREAKOUT_OFFSET_RATIO + STOP_OFFSET_RATIO)`
- 即 `1.5 × R`，反映真实的入口到止损距离
- 同步更新 Section 4.4 公式

### 10.8 MEDIUM-32：跳空检查使用错误价格（quote.open 非开盘价）

`_check_gap()` 使用 `quote.open` 判断是否跳空穿越夜盘 OR，但 9:00 日盘开盘时 `quote.open` 仍为夜盘 21:00 的开盘价（始终在夜盘 OR 内），导致 gap 检测永远不触发。

**问题表现：**
| 场景 | OR_H | OR_L | quote.open（夜盘） | quote.last_price（日盘集合竞价后） |
|------|------|------|------|------|
| 正常 | 3500 | 3480 | 3490（在 OR 内） | 3520（突破 OR_H）→ 应拉黑 |
| 异常 | 3500 | 3480 | 3490（在 OR 内） | 3460（跌破 OR_L）→ 应拉黑 |

`quote.open` 始终在夜盘 OR 内，gap_check 形同虚设。

**修复要点：**
- 将 `current_price = float(quote.open)` 改为 `current_price = float(quote.last_price)`
- `quote.last_price` 在 9:00 集合竞价后反映真实成交价
- 符合用户指示"2 用现价"

### 10.9 LOW-33：gap_check 阶段启动日盘 OR 不完整

引擎从 `gap_check` 阶段启动（08:55 重启后）时，日盘 9:00-9:30 的 OR 跟踪减少了已过去的时间窗口：若 9:15 才开始跟踪，OR 只剩 15 分钟数据而非完整的 30 分钟。

**根因：** `_close_day_opening_range()` 原实现依赖 `_track_opening_range` 的 tick 级增量数据，但在引擎迟到启动场景下不存在历史 tick 数据。

**修复要点：**
- 重写 `_close_day_opening_range()`：优先使用 `api.get_kline_serial(symbol, 60, 30)` 获取 30 根 1 分钟 K 线
- 仅当 K 线不足 30 根时回退到 tick 增量数据 + 剩余的有限分钟
- K 线数据来自服务器，无论何时调用均可得到 9:00-9:30 的完整区间

---

## Alpha 因子分析

### 策略定位

HVOB-MBI 是系统内**唯一的纯日内策略**，所有持仓在收盘前强制平仓。其 Alpha 来源与过夜趋势跟踪策略完全不同——捕捉的是开盘后短期价格发现过程中的动量溢出。

### 因子拆解

#### 因子一：开盘区间突破（HVOB — 核心 Alpha）

**定义**：开盘后 30 分钟（夜盘 21:00-21:30，日盘 9:00-9:30）形成开盘区间 OR = [OR_L, OR_H, R = OR_H - OR_L]。

```
多方向：h_break = OR_H + 0.3 × R
空方向：l_break = OR_L - 0.3 × R
```

**计算方式**：夜盘 21:30 通过 TqSDK `get_kline_serial(symbol, 60, 30)` 获取最近 30 根 1 分钟 K 线计算 H/L/R，日盘 9:30 通过 tick 级价格跟踪（期间每笔 quote 更新 H/L）计算。两种方式均可在程序崩溃重启后正确恢复——K 线数据来自服务器，日盘 tick 数据在 gap_check 阶段实时重建。

**数理本质**：开盘后 30 分钟的区间代表了市场在集合竞价后的初始价格发现区域。当价格突破区间 + 0.3R 的偏移量时，意味着开盘区间的平衡被打破，新的方向性行情启动。

**HVOB 的核心假设**：
1. 开盘区间反映了隔夜信息消化后的初步均衡
2. 突破此均衡需要新的信息驱动（strong momentum）
3. 突破后的方向性行情至少能覆盖 0.3R 的偏移成本

**因子属性**：

| 属性 | 值 |
|------|-----|
| 因子类型 | 日内突破（Intraday Breakout） |
| 持仓周期 | 分钟级至小时级 |
| 预期胜率 | ~45-55%（高于过夜策略） |
| 预期盈亏比 | ~1.5-2:1（固定 1.5 倍 R/P 止盈） |
| 最佳环境 | 高波动、方向性强的交易日 |
| 最差环境 | 低波动横盘（区间突破后即反转） |

#### 因子二：品种筛选（波动率择优因子）

**公式**：
```
score = (atr_pct >= 0.02 ? atr_pct × 100 : 0)
      + (avg_amp >= 0.015 ? avg_amp × 50 : 0)
      + (vol_ratio > 1.0 ? min((vol_ratio - 1.0) × 10, 5) : 0)
      + (PREFERRED_PRODUCTS ? +3 : 0)
      + (AVOID_PRODUCTS ? -2 : 0)
```

**数理本质**：选高波动品种做日内突破，因为：
1. **波动率是突破的燃料**——高波动品种的突破更有可能延续
2. **持仓量 > 20000 手**确保流动性，支撑快速进出
3. **平今优惠品种加分**——降低高频交易的摩擦成本

**因子属性**：

| 属性 | 值 |
|------|-----|
| 因子类型 | 品种选择（Security Selection） |
| Alpha 贡献方式 | 提升交易的期望收益——选最好的品种交易 |
| 评分维度 | ATR 百分比 + 振幅 + 量比 + 品种偏好 |

#### 因子三：MBI 市场氛围（方向权重因子）

**MBI 公式**：
```
单品种投票：3 个维度（隔夜跳空、区间重心、突破方向），各 ±1
总得分范围：[-3n, +3n]
MBI = (total_score + 3n) / 6n   → 映射到 [0, 1]
```

**MBI → 交易权限映射**：

| MBI 区间 | 定性 | 多单权重 | 空单权重 |
|----------|------|---------|---------|
| > 0.75 | 极强多头 | 1.0 | 0.0 |
| 0.65 - 0.75 | 多头 | 1.0 | 0.5 |
| 0.45 - 0.65 | 震荡 | 1.0 | 1.0 |
| 0.35 - 0.45 | 空头 | 0.5 | 1.0 |
| < 0.35 | 极强空头 | 0.0 | 1.0 |

**数理本质**：MBI 是一个**日内广谱情绪指标**，通过全市场品种的隔夜跳空、开盘重心、突破方向投票来衡量整体市场氛围。它在日盘阶段限制逆势交易——MBI 极强多头时不做空，极强空头时不做多。

**因子属性**：

| 属性 | 值 |
|------|-----|
| 因子类型 | 市场情绪（Market Sentiment） |
| Alpha 贡献方式 | 过滤逆势交易，提升盈亏比 |
| 计算频率 | 日盘开盘区间关闭后（9:30）计算一次，全天不变 |

#### 因子四：时间衰减（信号质量递减因子）

```
9:30 - 10:30: 仓位系数 1.0（100%）
10:30 - 11:30: 仓位系数 0.7（70%）
13:30 - 14:30: 仓位系数 0.3（30%）
```

**数理逻辑**：开盘区的突破信号质量随时间衰减。越接近收盘，剩余交易时间越少，突破行情的延续可能性越低。时间衰减通过线性降低仓位来反映这种信号质量递减。

#### 因子五：固定盈亏比止盈 + 移动止盈

```
固定止盈: entry_price ± 1.5 × R
移动止盈: 浮盈超过 2 倍止损距离后，止损跟随移动
```

**固定盈亏比 1.5:1 的数学意义**：
- 如果胜率是 40%，期望收益为：`0.4 × 1.5 - 0.6 × 1 = 0`（盈亏平衡点）
- 当胜率 > 40% 时策略即有正期望
- 固定盈亏比简化了出场决策，避免了"贪婪/恐惧"的人为干扰

#### 因子六：保本触发

```
触发价: entry_price ± 1.0 × R（浮盈超过 1 倍止损距离）
触发后: stop_loss = entry_price
```

确保盈利交易不会变亏损——在日内交易中尤其重要，因为多次小亏损可以快速侵蚀资金。

### 因子交互与执行流程

```
盘前 (15:00 收盘后 / 启动时):
  品种筛选因子 → 选出 top N 高波动品种
        ↓
夜盘 (21:00-21:30):
  等待开盘区间结束
  21:30 用 1 分钟 K 线计算 → OR_H, OR_L, R（崩溃安全）
        ↓
夜盘突破 (21:30-次日 9:00):
  HVOB 突破因子 → 突破即入场（因缺少日盘数据无法计算 MBI，不做方向过滤）
        ↓
日盘 (9:00-9:30):
  开盘区间跟踪 + MBI 计算
        ↓
日盘突破 (9:30-14:55):
  HVOB 突破因子 → 突破入场
  MBI 情绪因子 → 限制交易方向
  时间衰减因子 → 降低午后仓位
        ↓
持仓期间:
  固定止盈因子 → 1.5R 止盈
  保本因子 → 浮盈 1R 后拉保本
  移动止盈因子 → 浮盈 2R 后跟随
        ↓
14:55:
  强制平仓（不留隔夜）
```

### 与过夜策略的因子差异

| 维度 | HVOB-MBI（日内） | 海龟 V2（过夜） |
|------|-----------------|----------------|
| Alpha 时间尺度 | 分钟-小时 | 天-周-月 |
| 持仓周期 | 数小时 | 数天至数周 |
| 胜率 | 较高（45-55%） | 较低（35-40%） |
| 盈亏比 | 1.5-2:1 | 2.5-3:1 |
| 关键因子 | 开盘区间突破 + MBI | 唐奇安突破 + ATR 止损 |
| 市场情绪 | MBI 广谱指标 | 无（仅价格数据） |
| 过夜风险 | 无（收盘平仓） | 有（跳空保护处理） |
| 交易频率 | 高（每日 1-5 笔） | 低（每品种每 1-2 周一笔） |

### 因子贡献度估算

| 因子 | Alpha 贡献 | 说明 |
|------|-----------|------|
| HVOB 开盘区间突破 | ~50% | 核心信号来源 |
| 品种筛选（波动率择优） | ~15% | 选对品种比选对方向更重要 |
| MBI 市场氛围 | ~12% | 避免逆势交易 |
| 固定盈亏比止盈 | ~10% | 系统化出场纪律 |
| 时间衰减 | ~8% | 信号质量递减管理 |
| 保本 + 移动止盈 | ~5% | 优化出场
