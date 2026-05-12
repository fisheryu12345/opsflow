# K线数据字段扩充功能说明

## 功能概述

在原有 OHLCV + Volume + OpenInterest 的基础上，为 KlineData 表扩充三大类额外字段，用于事后数据分析、信号质量评估和策略参数优化。

原有的 KlineData 仅存储基础行情数据，大量有价值的派生信息（结算价、涨跌停板、技术指标、K线形态等）只在运行时实时计算，不持久化。每次需要分析时都要重新计算，而且窗口不一致会导致结果偏差。本功能将这些数据全部持久化到数据库，任何人都能以一致的算法从数据库中直接查询分析，无需重复计算。

---

## 背景：为什么要做 K 线数据扩充？

### 旧模式的痛点

在实施本功能之前，系统的数据分析能力存在以下限制：

| 痛点 | 具体表现 |
|------|---------|
| **结算价缺失** | 中国期货逐日盯市以结算价（settlement）为准计算盈亏，而非收盘价。没有结算价，历史 PnL 按收盘价推算会与实际的 MTM 盈亏有偏差。比如收盘价是 3500 但结算价是 3480，按 3500 算盈亏就会有 20 点的误差。 |
| **涨跌停无法判断** | 止损单是否因为涨停/跌停无法执行？关查 K 线最高价是否触及涨停板就知道。但之前没有持久化 `upper_limit/lower_limit`，无法做这种事后归因。 |
| **跳空分析盲区** | Gap Protection 功能每天判断是否跳空过大而跳过信号，但跳空的历史记录没有保存。无法复盘：被跳过的信号如果当时开仓了会怎样？不同 gap_threshold 参数的敏感性如何？ |
| **指标重复计算** | ATR、MA、Donchian 通道只在 `calculate_indicators()` 中实时计算并缓存到 `PositionState.indicators` JSONField。但 JSONField 无法做 SQL 查询（如"查询所有 ATR > 200 的品种"），且窗口不同步时结果不一致。 |
| **K线形态无法分析** | 实体比例、影线比例、成交量相对均值等 K 线微观特征从未被记录。突破信号的 K 线是实体饱满的大阳线还是十字星？这直接影响信号质量的判断。 |

### 设计目标

1. **一次计算，随处查询** — 所有派生字段持久化到数据库列，支持 SQL 过滤、排序、聚合
2. **与实盘算法一致** — 使用与 `calculate_indicators()` 相同的计算逻辑（含 `shift(1)` 防未来函数），避免分析偏差
3. **历史数据可回填** — Phase 2/3 字段全部由 OHLCV 派生，可对已有数据批量计算
4. **后向兼容** — 所有新字段 nullable，不改变已有业务逻辑

---

## 数据生成逻辑

数据的生成分为三个环节，分别在同步流程的不同阶段执行：

```
TqSDK K线同步 (15:32 执行，结算价已最终确定)
    │
    ├── 1. 基础 OHLCV 写入 → KlineData 表 (bulk_create)
    │
    ├── 2. Phase 1: Quote Enrichment
    │     通过 api.get_quote() 获取结算价/限价等，写入最新一根 K 线
    │     此时 settlement 已最终确定，数据准确
    │
    └── 3. Phase 2/3: 指标批量计算
          加载合约全部 K 线 → compute_batch_kline_indicators()
          使用 numpy/pandas 批量计算 → bulk_update()
```

### 环节 1：Quote Enrichment（同步时实时写入）

**代码位置**: `backend/stock/infrastructure/contract_sync.py:269-320`

每次 `sync_kline_data_from_tqsdk()` 拉取新 K 线后，调用 `api.get_quote()` 获取当前报价：

```python
quote = api.get_quote(query_key)
latest_bar.settlement = Decimal(str(quote.settlement))     # 结算价
latest_bar.pre_close = Decimal(str(quote.pre_close))       # 前收盘价
latest_bar.pre_settlement = Decimal(str(quote.pre_settlement))  # 前结算价
latest_bar.upper_limit = Decimal(str(quote.upper_limit))   # 涨停板价
latest_bar.lower_limit = Decimal(str(quote.lower_limit))   # 跌停板价
latest_bar.average_price = Decimal(str(quote.average))     # 当日均价
latest_bar.close_oi = int(quote.close_oi)                  # 收盘持仓量
latest_bar.turnover = Decimal(str(quote.turnover))         # 成交额
latest_bar.save(update_fields=[...])
```

**注意**: TqSDK `get_quote()` 返回的是当前实时值，不是历史值。因此 Phase 1 字段**只能从部署日起向前填充**，历史数据无法回溯。

### 环节 2：指标批量计算（同步时触发 + 可独立回填）

**代码位置**: `backend/stock/core/indicators.py:182-286`

```python
def compute_batch_kline_indicators(df: pd.DataFrame) -> pd.DataFrame:
```

**内部计算流程**:

```
输入 DataFrame (含 id, open, high, low, close, volume)
    │
    ├── True Range 计算
    │   TR = max(high-low, |high-prev_close|, |low-prev_close|)
    │   numpy 向量化运算
    │
    ├── ATR(20)
    │   SMA 方法: 从第 20 根开始，取前 20 根 TR 的均值
    │   与实盘 ATR(klines, 20) 算法一致
    │
    ├── Donchian 通道 (20)
    │   donchian_upper_20 = high.shift(1).rolling(20).max()
    │   donchian_lower_20 = low.shift(1).rolling(20).min()
    │   关键: shift(1) 防止用当日最高/最低点计算当日信号，避免未来函数
    │
    ├── MA 均线
    │   ma_10 = close.rolling(10).mean()
    │   ma_20 = close.rolling(20).mean()
    │   ma_40 = close.rolling(40).mean()
    │
    ├── 趋势因子 (逐行计算)
    │   for each row:
    │     is_bull = ma10 > ma20 > ma40
    │     is_bear = ma10 < ma20 < ma40
    │     if not (bull or bear) → trend_factor=0, trend_label=choppy
    │     gap_10_20 = |ma10-ma20| / |ma20|
    │     gap_20_40 = |ma20-ma40| / |ma20|
    │     trend_strength = min(max_gap / 0.03, 1.0)
    │     trend_factor = trend_strength * 0.5 (范围 0~0.5)
    │     trend_label: ≥0.8→strong, ≥0.3→weak, <0.3→choppy
    │
    └── K线形态元数据 (numpy 向量化)
        body_ratio = |c-o| / (h-l)
        upper_shadow_ratio = (h-max(o,c)) / (h-l)
        lower_shadow_ratio = (min(o,c)-l) / (h-l)
        close_in_range = (c-l) / (h-l)
        volume_ratio_20 = volume / volume.rolling(20).mean()
        gap_from_pre_close = (o-prev_close) / prev_close
        hit_upper_limit = (h >= upper_limit) & ~isnan(upper_limit)
        hit_lower_limit = (l <= lower_limit) & ~isnan(lower_limit)
```

**关键算法细节**:

| 指标 | 计算方式 | 与实盘一致性 |
|------|---------|------------|
| ATR(20) | SMA 均值（前 20 根 TR 平均） | ✅ 与 `tqsdk.ta.ATR` 一致 |
| Donchian(20) | `shift(1)` + `rolling(20).max()` | ✅ 与 `check_breakout_signal` 对齐 |
| 趋势因子 | MA间隙比公式 | ✅ 与 `backtest/indicators.py` 一致 |
| K线形态 | numpy 纯计算，无状态依赖 | ✅ 自包含，结果确定 |

### 环节 3：回填管理命令（对已有历史数据）

**代码位置**: `backend/stock/management/commands/backfill_kline_enrichment.py`

对于在功能上线前已存在的 K 线数据，Phase 2/3 字段需要回填。Phase 1 字段无法回填（历史结算价不可获取）。

**执行流程**:
```
1. 查询 KlineData 按 symbol 分组，取 date 升序排列
2. 对每个 symbol:
   a. 加载所有 K 线数据 (id, date, open, high, low, close, volume, upper_limit, lower_limit)
   b. 转为 DataFrame，数值列转 float
   c. 调用 compute_batch_kline_indicators()
   d. 遍历计算结果，构建 KlineData 对象
   e. bulk_update 写入数据库
3. 统计: 成功合约数 / 更新条数 / 失败数
```

**使用方式**:
```bash
python manage.py backfill_kline_enrichtion                    # 回填所有合约
python manage.py backfill_kline_enrichment --product rb,MA    # 只回填螺纹钢和甲醇
python manage.py backfill_kline_enrichment --dry-run          # 预览模式，不写入
python manage.py backfill_kline_enrichment --batch-size 2000  # 加大批处理大小
```

**首次执行统计**: 87 合约，17,464 根 K 线，0 错误

---

## 如何使用扩充字段进行策略优化

以下按分析主题分类，每类给出具体的 SQL 查询方法和分析思路。

### 1. 信号质量分析：哪些突破信号更可靠？

#### 分析目标
找出高胜率信号和假突破的共同特征，建立信号过滤规则。

#### 关键字段
`donchian_upper_20`, `donchian_lower_20`, `body_ratio`, `volume_ratio_20`, `trend_label`

#### 分析方法

**a. 突破实体与胜率的关系**

```sql
-- 查询所有突破日的 K 线实体比例分布
SELECT 
    CASE 
        WHEN body_ratio >= 0.7 THEN '实体饱满'
        WHEN body_ratio >= 0.3 THEN '实体中等'
        ELSE '十字星/小实体'
    END AS entity_type,
    COUNT(*) AS signal_count
FROM stock_klinedata
WHERE close > donchian_upper_20  -- 向上突破
   OR close < donchian_lower_20  -- 向下突破
GROUP BY entity_type;
```

在回测或分析脚本中，可以将实体比例作为过滤条件：
- 如果 `body_ratio >= 0.7` 的突破胜率显著高于 `body_ratio < 0.3` 的突破，则可以在实盘中加入实体过滤
- 优化方向：只接受实体比例 > 0.5 的突破信号

**b. 成交量确认效应**

```python
# 分析脚本思路 (pandas)
# 1. 找出所有突破信号日
# 2. 按 volume_ratio_20 分组: <0.8(缩量), 0.8-1.2(平量), >1.2(放量)
# 3. 统计每组后续 N 日的收益情况
# 预期: 放量突破的延续性优于缩量突破

analysis = df[df['close'] > df['donchian_upper_20']].copy()
analysis['vol_regime'] = pd.cut(
    analysis['volume_ratio_20'], 
    bins=[0, 0.8, 1.2, float('inf')],
    labels=['缩量', '平量', '放量']
)
# 后续计算各组平均收益...
```

**c. 趋势因子分层分析**

```sql
-- 按突破日的 trend_factor 分组统计后续表现
-- 需要结合 ClosedPositionRecord 或回测脚本
SELECT 
    CASE 
        WHEN tf.trend_factor >= 0.4 THEN '强趋势'
        WHEN tf.trend_factor >= 0.2 THEN '中趋势'
        WHEN tf.trend_factor >= 0.05 THEN '弱趋势'
        ELSE '无趋势'
    END AS trend_regime,
    COUNT(*) AS trade_count,
    AVG(cp.profit) AS avg_profit
FROM stock_klinedata tf
JOIN closed_position_records cp ON ...  -- 关联平仓记录
WHERE tf.close > tf.donchian_upper_20
GROUP BY trend_regime;
```

**优化结论示例**:
- 如果强趋势下的突破胜率 60%，无趋势下只有 35% → 考虑加入趋势过滤
- 如果放量突破的盈亏比是缩量突破的 2 倍 → 降低缩量突破的仓位权重

### 2. 止损质量分析：止损单执行情况

#### 分析目标
评估止损是否被涨跌停阻碍、跳空止损的比例、止损价位设置的合理性。

#### 关键字段
`hit_upper_limit`, `hit_lower_limit`, `gap_from_pre_close`, `atr_20`

#### 分析方法

**a. 涨跌停对止损的影响**

```sql
-- 统计在涨跌停日的 K 线
SELECT 
    COUNT(*) AS total_days,
    SUM(CASE WHEN hit_upper_limit THEN 1 ELSE 0 END) AS touch_upper_cnt,
    SUM(CASE WHEN hit_lower_limit THEN 1 ELSE 0 END) AS touch_lower_cnt
FROM stock_klinedata
WHERE symbol = 'SHFE.rb2510'
  AND date >= '2025-01-01';
```

结合止损单数据，分析有多少止损单因涨跌停无法成交：
```sql
-- 查询止损日是否触碰限价
SELECT k.date, k.hit_lower_limit, k.hit_upper_limit,
       k.low, k.lower_limit, k.high, k.upper_limit
FROM stock_klinedata k
WHERE k.symbol = 'SHFE.rb2510'
  AND k.date IN (
    SELECT DISTINCT trade_date 
    FROM stock_slippagerecord 
    WHERE trade_type = 'STOP_LOSS' 
      AND slippage_ticks > 2  -- 滑点异常大
  );
```

**b. 跳空止损分析**

```sql
-- 查询跳空幅度分布
SELECT 
    CASE 
        WHEN ABS(gap_from_pre_close) >= 0.02 THEN '大跳空(>2%)'
        WHEN ABS(gap_from_pre_close) >= 0.01 THEN '中跳空(1%-2%)'
        WHEN ABS(gap_from_pre_close) >= 0.005 THEN '小跳空(0.5%-1%)'
        ELSE '无跳空'
    END AS gap_level,
    gap_from_pre_close,
    date, symbol
FROM stock_klinedata
WHERE ABS(gap_from_pre_close) > 0.005
ORDER BY ABS(gap_from_pre_close) DESC;
```

**优化方向**:
- 如果大量止损通过跳空触发（即开盘价直接越过止损价），说明止损价位过于接近，需要增加缓冲
- 当前使用 ATR 动态止损（2.0x~3.0x ATR），可通过分析 gap_from_pre_close 的分布来校准缓冲系数
- 例如：跳空幅度 90% 分位数为 1.5x ATR，则止损缓冲至少应设为 1.5x ATR

### 3. Gap Protection 回测与参数优化

#### 分析目标
评估当前 gap protection 规则的有效性，寻找最优 gap_threshold 参数。

#### 关键字段
`gap_from_pre_close`, `atr_20`, `donchian_upper_20`, `donchian_lower_20`

#### 分析方法

**模拟不同 gap_threshold 下的信号过滤效果**:

```python
# 分析脚本思路
thresholds = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]  # 不同 gap_threshold (x ATR)

for threshold in thresholds:
    # 对每个突破信号日:
    # 1. 计算 gap_ratio = |gap_from_pre_close| / (atr_20 / close_price)
    #    注意: atr_20 是绝对值,需要换算为相对值
    # 2. 如果 gap_ratio > threshold → 被 gap protection 跳过
    # 3. 统计被跳过的信号中,如果实际开仓了会怎样
```

**分析问题**:
- 当前设置下，gap protection 跳过了多少本该盈利的信号？
- gap_threshold = 1.0x 和 1.5x ATR 之间，对总收益的影响有多大？
- 是否存在"被跳过的好信号"的共同特征（trend_label, body_ratio 等）？

**优化结论示例**:
- 如果 gap_threshold 从 1.0x 提高到 1.5x ATR，总收益 +15% 但最大回撤 +3% → 可根据风险偏好选择
- 如果跳空 > 2x ATR 的信号几乎全部亏损 → 可以降低 gap_threshold 到 1.5x

### 4. 波动率分析：因时制宜的参数调整

#### 分析目标
根据市场波动状态动态调整策略参数。

#### 关键字段
`atr_20`, `trend_factor`, `trend_label`

#### 分析方法

**a. ATR 百分位**

```sql
-- 计算某品种当前 ATR 在历史 60 日中的百分位
WITH atr_stats AS (
    SELECT 
        atr_20,
        PERCENT_RANK() OVER (ORDER BY atr_20) AS pct_rank
    FROM stock_klinedata
    WHERE symbol = 'SHFE.rb2510'
      AND date >= '2025-03-01'
)
SELECT atr_20, ROUND(pct_rank::numeric, 2) AS percentile
FROM atr_stats
ORDER BY date DESC
LIMIT 5;
```

**b. 持仓期间波动率变化**

```python
# 分析思路: 对比开仓日和平仓日的 ATR
# 关联 PositionState(或 ClosedPositionRecord) 与 KlineData
# 计算 ratio = exit_atr / entry_atr
# 如果 ratio > 1.5, 说明持仓期间波动率大幅上升
# 此时分析: 在波动率上升时, 是否需要收紧止损?
```

**优化方向**:
- 低波动环境（ATR 处于历史 20% 分位以下）: 降低仓位或收紧止损，因为突破可能是假突破
- 高波动环境（ATR 处于历史 80% 分位以上）: 加宽止损缓冲，防止被噪声扫出
- 波动率快速上升（ATR 半月涨幅 > 30%）: 启动波动率预警，检查已有持仓

### 5. Donchian 通道有效性分析

#### 分析目标
验证 Donchian 20 通道在不同市场环境下的预测能力。

#### 关键字段
`donchian_upper_20`, `donchian_lower_20`, `close`, `close_in_range`

#### 分析方法

**a. 突破后的延续性**

```python
# 对每个突破信号, 计算突破后 N 日的价格方向
# 在 DataFrame 中:
# 1. 标记突破日 signal_day = (close > donchian_upper_20)
# 2. 对每个 signal_day, 取未来 N 日的 close
# 3. 判断是否继续朝突破方向运动
# 4. 统计概率

N_DAYS = 5
signals = df[df['close'] > df['donchian_upper_20']].copy()
# 用 shift(-N) 获取未来收盘价
# 计算继续上涨的比例
```

**b. 通道宽度与信号质量**

```sql
-- 计算通道宽度: (donchian_upper - donchian_lower) / close
-- 宽通道 = 市场波动大, 窄通道 = 市场盘整
SELECT 
    date,
    donchian_upper_20,
    donchian_lower_20,
    close,
    (donchian_upper_20 - donchian_lower_20) / close AS channel_width_pct
FROM stock_klinedata
WHERE symbol = 'SHFE.rb2510'
ORDER BY date DESC
LIMIT 20;
```

**优化方向**:
- 窄通道突破的成功率是否高于宽通道突破？
- 通道宽度收窄后突然放大 → 可能是趋势启动的信号
- 如果假突破的 `close_in_range` 多在 0.5 以下（收盘在 K 线下半部分）→ 可增加 `close_in_range` 过滤

---

## 实用查询 SQL 合集

以下 SQL 可以直接在 Django `python manage.py dbshell` 或数据库客户端中执行。

### 查询某品种最新 N 根 K 线的全部扩充字段

```sql
SELECT date, close, atr_20, donchian_upper_20, donchian_lower_20,
       ma_10, ma_20, ma_40, trend_factor, trend_label,
       body_ratio, volume_ratio_20, gap_from_pre_close,
       hit_upper_limit, hit_lower_limit
FROM stock_klinedata
WHERE symbol = 'SHFE.rb2510'
ORDER BY date DESC
LIMIT 20;
```

### 查找放量突破日

```sql
SELECT date, close, donchian_upper_20, donchian_lower_20,
       volume_ratio_20, body_ratio, trend_label
FROM stock_klinedata
WHERE volume_ratio_20 > 1.5
  AND (close > donchian_upper_20 OR close < donchian_lower_20)
ORDER BY volume_ratio_20 DESC;
```

### 查找所有触及涨跌停的交易日

```sql
SELECT symbol, date, close, high, low, upper_limit, lower_limit,
       hit_upper_limit, hit_lower_limit
FROM stock_klinedata
WHERE hit_upper_limit = true OR hit_lower_limit = true
ORDER BY date DESC;
```

### 查找跳空最大的交易日

```sql
SELECT symbol, date, close, gap_from_pre_close, atr_20,
       (gap_from_pre_close * close / NULLIF(atr_20, 0)) AS gap_atr_ratio
FROM stock_klinedata
WHERE ABS(gap_from_pre_close) > 0.01
ORDER BY ABS(gap_from_pre_close) DESC
LIMIT 20;
```

### 分析 trend_label 分布

```sql
SELECT trend_label, COUNT(*) AS day_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM stock_klinedata
WHERE symbol = 'SHFE.rb2510'
GROUP BY trend_label
ORDER BY day_count DESC;
```

---

## 可做的策略优化清单

| 优化方向 | 所需字段 | 分析方法 | 预期效果 |
|---------|---------|---------|---------|
| 突破信号过滤 | `body_ratio`, `volume_ratio_20` | 按实体大小和成交量分组统计胜率 | 减少假突破，提升胜率 3-8% |
| 趋势因子分层仓位 | `trend_factor`, `trend_label` | 按趋势强度分组统计盈亏比 | 强趋势加仓，弱趋势减仓 |
| 止损缓冲优化 | `gap_from_pre_close`, `atr_20` | 统计跳空幅度的 ATR 倍数分布 | 减少跳空止损，避免被扫 |
| 涨跌停预警 | `hit_upper_limit`, `hit_lower_limit` | 检查止损价是否过于接近限价 | 降低无法成交的概率 |
| 波动率自适应参数 | `atr_20` (历史百分位) | 计算当前 ATR 在 N 日中的位置 | 低波动降仓，高波动加宽止损 |
| Gap Threshold 调优 | `gap_from_pre_close`, `atr_20` | 回放不同 threshold 的参数 | 找到最优 gap protection 参数 |
| 通道有效性改进 | `donchian_upper_20`, `close_in_range` | 分析假突破的 K 线特征 | 改进通道突破确认规则 |
| 品种选择 | `atr_20`, `volume_ratio_20` | 按流动性、波动率排序品种 | 优先交易流动性好的品种 |

---

## 关键设计约束

1. **TqSDK 历史报价不可用**: `get_quote()` 返回当前值，Phase 1 字段（settlement, upper_limit 等）只能从部署日起向前填充
2. **防未来函数**: Donchian 通道使用 `shift(1)` 防止在当日用当日最高/最低点计算信号。这确保任何基于此数据的分析都不会有幸存者偏差
3. **同步定时**: 结算价在 15:00 收盘后约 30 分钟才最终确定。收盘计算任务已从 15:02 调整为 **15:32 执行**，确保 get_quote() 获取到的结算价、涨跌停板等数据准确无误。详见 `backend/stock/scheduler/scheduler.py`。
4. **所有字段 nullable**: 后向兼容，现有代码不受影响。查询时需注意 `NULL` 值处理
5. **Django DecimalField**: NaN/inf 值在写入前会被转换为 `None`，详见 `clean_nan_for_decimal()`

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `backend/stock/models.py` | KlineData 模型新增字段（约 25 个） |
| `backend/stock/core/indicators.py` | `compute_batch_kline_indicators()` 批量计算函数 |
| `backend/stock/core/indicators.py` | `compute_trend_factor_from_backtest()` 趋势因子函数 |
| `backend/stock/infrastructure/contract_sync.py` | 同步流程中集成 quote enrichment + 指标计算 |
| `backend/stock/management/commands/backfill_kline_enrichment.py` | 历史数据回填管理命令 |
| `backend/stock/serializers/serializers.py` | Serializer 更新（KlineData 全字段） |
| `backend/stock/migrations/0078_*` | Phase 1 数据库迁移 |
| `backend/stock/migrations/0079_*` | Phase 2/3 数据库迁移 |

---

## 迁移记录

| 迁移 | 内容 | 生成日期 |
|------|------|----------|
| `0078_klinedata_average_price_klinedata_close_oi_and_more` | Phase 1 字段（settlement, pre_close, upper_limit, lower_limit 等 8 个） | 2026-05-10 |
| `0079_klinedata_atr_20_klinedata_body_ratio_and_more` | Phase 2/3 字段（atr_20, body_ratio, upper_shadow_ratio 等 17 个） | 2026-05-10 |

---

## 附录：字段总表

| 阶段 | 字段名 | 中文名 | 类型 | 数据来源 | 可回填 |
|------|--------|--------|------|---------|--------|
| P1 | settlement | 结算价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | pre_close | 前收盘价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | pre_settlement | 前结算价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | upper_limit | 涨停板价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | lower_limit | 跌停板价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | average_price | 当日均价 | Decimal(12,2) | TqSDK quote | ❌ |
| P1 | close_oi | 收盘持仓量 | BigIntegerField | TqSDK quote | ❌ |
| P1 | turnover | 成交额 | Decimal(20,2) | TqSDK quote | ❌ |
| P2 | atr_20 | ATR(20) | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | donchian_upper_20 | 唐奇安上轨 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | donchian_lower_20 | 唐奇安下轨 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | ma_10 | 10日均线 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | ma_20 | 20日均线 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | ma_40 | 40日均线 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P2 | trend_factor | 趋势因子 | Decimal(6,3) | MA 派生 | ✅ |
| P2 | trend_label | 趋势标签 | CharField(20) | MA 派生 | ✅ |
| P2 | true_range | 真实波幅 | Decimal(12,2) | OHLCV 派生 | ✅ |
| P3 | body_ratio | 实体比例 | Decimal(8,4) | OHLCV 派生 | ✅ |
| P3 | upper_shadow_ratio | 上影线比例 | Decimal(8,4) | OHLCV 派生 | ✅ |
| P3 | lower_shadow_ratio | 下影线比例 | Decimal(8,4) | OHLCV 派生 | ✅ |
| P3 | close_in_range | 收盘位置 | Decimal(8,4) | OHLCV 派生 | ✅ |
| P3 | volume_ratio_20 | 成交量比 | Decimal(8,3) | OHLCV 派生 | ✅ |
| P3 | gap_from_pre_close | 跳空幅度 | Decimal(8,4) | OHLCV 派生 | ✅ |
| P3 | hit_upper_limit | 触及涨停 | BooleanField | OHLCV 派生 | ✅ |
| P3 | hit_lower_limit | 触及跌停 | BooleanField | OHLCV 派生 | ✅ |

---

**实施完成时间**: 2026-05-10  
**文档更新**: 2026-05-12
