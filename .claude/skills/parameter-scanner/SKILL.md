---
name: parameter-scanner
description: >-
  A reusable framework for scanning strategy parameters and generating cross-product
  comparison HTML reports. Use this whenever the user wants to compare different values
  of a trading strategy parameter (trend_factor gap_limit, ATR period, stop-loss
  multiplier, entry period, or any numeric config) across historical K-line data,
  analyze distribution impact, cross-product uniformity, and generate a full HTML
  comparison report. Trigger phrases: "参数扫描", "参数对比", "调参", "阈值对比",
  "GAP_ATR_LIMIT", "sweep parameter", "compare thresholds", "parameter tuning",
  "what value should I use for", "找出最优参数".
---

# 策略参数扫描框架

一个通用的策略参数扫描与对比分析框架。自动连接数据库，扫描指定参数的不同取值，生成完整的 HTML 对比报告。

## 工作流程

```
用户指定参数 + 范围 → 连接 DB 获取数据 → 多阈值计算 → 分析指标 → HTML 报告
```

## 核心步骤

### Step 1: 理解参数上下文

先确定用户想扫描什么参数，扫描范围是多少。常见参数：

| 参数 | 典型范围 | 说明 |
|------|---------|------|
| GAP_ATR_LIMIT | 0.5 ~ 3.0 | trend_factor 中 MA乖离/ATR 的封顶倍数 |
| TREND_FACTOR_MAX | 0.3 ~ 0.7 | trend_factor 最大值 |
| TREND_LABEL_STRONG_RATIO | 0.70 ~ 0.90 | 强趋势标签阈值 |
| ATR_PERIOD / atr_period | 10 ~ 30 | ATR 计算周期 |
| entry_period | 10 ~ 40 | 唐奇安通道突破周期 |
| position_risk_multiplier | 1 ~ 4 | 止损距离 = N × ATR |
| protect_cost_enabled_ratio | 1.5 ~ 4.0 | 保本启用阈值(ATR倍数) |
| gap_threshold | 0.5 ~ 3.0 | 跳空放弃阈值(ATR倍数) |

如果用户没有明确范围，先问清楚再开始。

### Step 2: 连接数据库

自动检测可用的数据源：

```python
# 优先 Django ORM（有完整 Django 环境时）
try:
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'application.settings'
    django.setup()
    from stock.models import TradingAccount, KlineData
    USE_DJANGO = True
except Exception:
    USE_DJANGO = False
```

如果 Django 不可用，降级为 MySQLdb 直连：

```python
DB = dict(host='139.196.194.73', user='trade', passwd='312711936!@#GHS', db='stock', port=3306, connect_timeout=5)
conn = MySQLdb.connect(**DB)
```

Django 不可用时，提示用户哪些分析功能受限，并建议装全依赖后重跑以获得更完整结果。

如果 MySQLdb 也连不上，尝试使用 `pip install mysqlclient` 或 `pip install PyMySQL`。

### Step 3: 获取品种列表

从账户配置中获取活跃品种列表：

```python
# Django ORM 方式
from stock.models import AccountContractConfig
codes = list(AccountContractConfig.objects.filter(
    account__name='510976', is_active=True
).values_list('product_code', flat=True))

# MySQL 直连方式
cur.execute("""
    SELECT acc.product_code
    FROM stock_accountcontractconfig acc
    JOIN stock_tradingaccount ta ON acc.account_id = ta.id
    WHERE ta.name = '510976' AND acc.is_active = 1
""")
codes = [r[0] for r in cur.fetchall()]
```

如果用户要分析其他账户，相应的账户名也要改。

### Step 4: 获取 K 线数据

```python
# Django ORM
klines = KlineData.objects.filter(
    product_code__in=codes,
    ma_40__isnull=False
).values('product_code', 'date', 'ma_10', 'ma_20', 'ma_40', 'atr_20').order_by('product_code', 'date')

# MySQL
cur.execute("""
    SELECT product_code, date, ma_10, ma_20, ma_40, atr_20
    FROM stock_klinedata
    WHERE product_code IN %s AND ma_40 IS NOT NULL
    ORDER BY product_code, date
""", (codes,))
```

### Step 5: 定义计算函数

根据要扫描的参数，写出对应的计算函数。函数签名统一为：

```python
def compute(
    ma10: float | None,
    ma20: float | None,
    ma40: float | None,
    atr: float | None,
    param_value: float,  # 当前要扫描的参数值
) -> tuple[float | None, str | None]:
    """返回 (trend_factor, trend_label) 或 (None, None)"""
```

示例：扫描 GAP_ATR_LIMIT

```python
def compute_tf(ma10, ma20, ma40, atr, gap_limit):
    if ma10 is None or ma20 is None or ma40 is None or atr is None or atr == 0:
        return None, None
    bull = ma10 > ma20 > ma40
    bear = ma10 < ma20 < ma40
    if not (bull or bear):
        return 0.0, 'choppy'
    gap = max(abs(ma10-ma20)/atr, abs(ma20-ma40)/atr)
    s = min(gap / gap_limit, 1.0)
    tf = round(s * 0.5, 4)
    if s >= 0.80:
        lbl = 'strong_bull' if bull else 'strong_bear'
    elif s >= 0.30:
        lbl = 'weak_bull' if bull else 'weak_bear'
    else:
        lbl = 'choppy'
    return tf, lbl
```

如果是其他参数（如 ATR_PERIOD），计算逻辑会不同，需相应调整 compute 函数。

### Step 6: 多阈值计算

对所有品种的 K 线数据遍历，对每个参数值计算指标：

```python
# param_values: 要扫描的参数值列表，如 [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0]
all_data = {v: [] for v in param_values}           # 全部tf值
product_data = {v: {c: [] for c in codes} for v in param_values}  # 分品种
labels_data = {v: [] for v in param_values}         # 标签记录
stops_data = {v: [] for v in param_values}          # 止损距离

for code in codes:
    for row in klines:
        ma10 = float(row.ma_10) if row.ma_10 else None
        ma20 = float(row.ma_20) if row.ma_20 else None
        ma40 = float(row.ma_40) if row.ma_40 else None
        atr = float(row.atr_20) if row.atr_20 else None
        for v in param_values:
            tf, lbl = compute(ma10, ma20, ma40, atr, v)
            if tf is not None:
                all_data[v].append(tf)
                product_data[v][code].append(tf)
                labels_data[v].append(lbl)
                if atr and atr > 0:
                    stops_data[v].append(2 * (1 + tf) * atr)
```

### Step 7: 分析指标计算

**7a. 分布分析 (Distribution)**

将 trend_factor 值分桶统计：

```python
buckets = ['=0', '0~0.1', '0.1~0.2', '0.2~0.3', '0.3~0.4', '0.4~0.5']
for v in param_values:
    vals = all_data[v]
    for b in buckets:
        cnt = ...
    mean = sum(vals) / len(vals)
```

关键指标：
- **饱和率 (≥0.4占比)**: trend_factor 达到 0.4 以上的比例，反映参数激进程度
- **零值率 (=0占比)**: 无趋势信号的比例，反映参数敏感度
- **均值**: trend_factor 整体水平

**7b. 品种均匀性 (Cross-product Uniformity)**

计算各品种均值之间的变异程度：

```python
means = [st.mean(product_data[v][c]) for c in codes if product_data[v][c]]
cv = st.stdev(means) / st.mean(means)   # 变异系数，越小越好
range_ = max(means) - min(means)         # 品种间极差
max_dev = max(abs(m/st.mean(means)-1) for m in means) * 100  # 最大偏离%
```

均匀性越好（CV 越小）→ 参数对各品种影响一致，越不需要单独调参。

**7c. 标签分布 (Label Distribution)**

统计各标签占比：

```python
label_counts = {l: labels_data[v].count(l) for l in ['strong_bull','weak_bull','choppy','weak_bear','strong_bear']}
strong_pct = (label_counts['strong_bull'] + label_counts['strong_bear']) / len(labels_data[v]) * 100
```

**7d. 止损影响 (Stop-loss Impact)**

```python
mean_stop = st.mean(stops_data[v]) if stops_data[v] else 0
# 相对基准的变化
chg = (mean_stop / baseline_stop - 1) * 100
```

止损公式: `stop_distance = 2 × (1 + trend_factor) × ATR`

**注意**: trend_factor 为 0 时止损距离 = 2×ATR（基准），0.5 时 = 3×ATR（最宽）。所以 trend_factor 整体越高，止损越宽。

### Step 8: 生成 HTML 报告

使用 `gen_tf_report.py` 的 HTML 模板风格生成报告。报告应包含以下部分：

**1. 报告头部**
- 报告标题、生成日期
- 扫描参数名称、扫描范围
- 数据概况（品种数、总样本量）

**2. 核心指标汇总表**

| 参数值 | 均值 | ≥0.4占比% |=0占比% | 强标签率% | CV | 品种极差 | 止损变化% |
|--------|------|----------|--------|-----------|-----|---------|----------|
| 0.03(pct) | 0.165 | 5.5 | 77.4 | 6.8 | 0.317 | 0.3495 | - |
| 2.0 | 0.180 | 11.3 | 71.2 | 13.2 | 0.190 | 0.1943 | 0% |
| 2.2 | 0.165 | 8.2 | 74.8 | 10.1 | 0.197 | 0.2091 | -1.5% |

**3. 分布对比** — 分桶表格 + 文字分析

**4. 品种均匀性** — 各品种均值对比 + CV/极差/最大偏离

**5. 品种偏离度** — 各品种均值 vs 整体均值的偏离百分比

**6. 止损影响** — 各品种止损均值 + 相对变化

**7. 推荐结论** — 基于以上指标给出参数推荐值

报告模板参考 `gen_tf_report.py` 的 HTML 结构，需包含：
- `<style>` 内嵌 CSS（表格交错行色、hover 效果、柱状条等）
- 所有数据在 HTML 中内联，不依赖外部文件
- 关键数字重点标记（如推荐行高亮）
- report 文件名: `parameter_scan_{参数名}_{日期}.html`

### Step 9: 报告解读指南

报告交给用户后，解释以下指标的含义：

- **饱和率(≥0.4)**: trend_factor 达到上限区域的比例。太高说明参数过于激进(太多满格信号)，太低说明参数过于保守(信号太弱)。一般目标在 8%~15%。
- **CV(变异系数)**: 各品种均值之间的差异程度。CV 越小，参数在所有品种上表现越一致，越无需单独调参。
- **品种极差**: 均值最高品种与最低品种的差值。越小越好。
- **止损变化**: 相对基准参数，止损距离的平均变化百分比。正数表示止损变宽（风险更大），负数表示止损变窄。

## 参考实现

已有的完整实现可参考：
- `backend/sweep_gap_atr_limit.py` — 简单的参数扫描脚本
- `backend/compare_1.8_2.0_2.2.py` — 多阈值对比
- `backend/full_tf_comparison.py` — 完整对比 + CSV 导出
- `backend/gen_tf_report.py` — HTML 报告生成（最新完整版本）

这些文件在本项目的 `backend/` 目录下，编写代码时直接读取复用其中的模式。特别是 HTML 报告的结构和 CSS 样式。

## 注意事项

1. **Python 版本兼容性**: 环境中可能是 Python 3.14，部分库（django-filter, channels 等）可能不兼容。优先使用 MySQLdb 直连方式，Django ORM 仅在有完整环境时使用。
2. **编码问题**: Windows 环境下 print 输出中文可能触发 GBK 编码错误，所有输出文本用英文。
3. **HTML 报告路径**: 生成到 `backend/` 目录下，文件名包含日期避免覆盖。
4. **品种列表**: 账户 510976 的活跃品种有 22 个，其他账户需单独查询。
5. **数据量**: 22 品种 × 数年历史数据约 3000~5000 条记录，计算量不大。
6. **不要在报告中包含数据库密码** — MySQL 密码等敏感信息不能写入 HTML。
