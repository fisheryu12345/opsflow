# HVOB-MBI 日内高波动突破系统

> 涉及文件: `hvob_mbi/config.py`, `hvob_mbi/screening.py`, `hvob_mbi/mbi.py`, `hvob_mbi/trading_engine.py`, `hvob_mbi/signal_recorder.py`, `hvob_mbi/models.py`, `stock/models.py` (FullContractList.night_trading)

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
| `LAST_ENTRY_TIME` | 13:30 | 最后入场时间 |

### 3.4 时间衰减系数

| 时间段 | 仓位系数 |
|--------|---------|
| 9:30 - 10:30 | 1.0 (100%) |
| 10:30 - 11:30 | 0.7 (70%) |
| 11:30 - 13:30 | 0.5 (50%) |
| 13:30 - 14:55 | 0.3 (30%) |

### 3.5 MBI 交易权限映射

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
stop_distance = OR_R × 0.2 × 2
volume = max(1, int(risk_amount / (stop_distance × volume_multiple)))
volume = min(volume, max_positions_per_day)
```

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

**返回结果：** 每条包含 `symbol, product_code, score, atr_pct, avg_amp, vol_ratio, atr_score, amp_score, vol_score, bonus, open_interest`，写入 `HvobMbiDailyState.watchlist`。

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
    ↓
night_or(21:00-21:30)
    │ 跟踪有夜盘品种（FullContractList.night_trading=True）tick 级 H/L
    ↓
night_breakout(21:30-23:00)
    │ 夜盘品种突破监测（无 MBI 过滤）
    │ 无夜盘品种不处理
    │ 每次 wait_update 检查 quote.last_price
    ↓
gap_check(9:00-9:30)
    │ 跳空检查后等待日盘开盘区间结束
    │ 9:30 关闭日盘区间 + 计算 MBI
    ↓
day_breakout(9:30-14:55)
    │ 全品种突破监测 + MBI 过滤 + 时间衰减
    │ 持续检查止损/止盈/保本/移动止盈
    ↓
force_close(14:55)
    │ TargetPosTask 设 0 → 强制平仓
    ↓
done
    │ 记录日权益、保存日状态（含完整评分明细）
```

### 6.2 数据源

所有数据通过 TqSDK 实时获取：
- **日线用于筛选：** `api.get_kline_serial(symbol, 86400, 30)` — 盘前启动时拉取
- **实时报价：** `api.get_quote(symbol)` — `wait_update` 事件循环中获取
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

### 7.7 MBI 边界值
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
