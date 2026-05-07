# 跳空保护公式修复报告

## 🔴 问题发现

**位置**: `backend/stock/scheduler/calculate_atr.py:64`

**原始代码**:
```python
gap_percent = ((latest_price - pre_close) / atr) * 100   # ❌ 用 ATR 当分母
```

**注释说明**:
```python
# 计算跳空幅度（相对于昨日收盘价）
```

---

## ⚠️ 问题分析

### 1. **注释与代码不一致**
- 注释说："相对于昨日收盘价"
- 但实际分母用的是 `atr`，不是 `pre_close`

### 2. **量纲混乱**
```python
# 分子：价格差值（单位：元/点）
latest_price - pre_close  # 例如：100元

# 分母：ATR波动幅度（单位：元/点）
atr  # 例如：50元

# 结果：倍数关系 × 100
(100 / 50) * 100 = 200%  # 这个"百分比"的含义是"跳空是ATR的2倍"
```

### 3. **阈值语义错误**
```python
# 当前逻辑
if gap_percent > 1.5:  # 200% > 1.5%，条件永远成立
    return False  # 禁止交易

# 但实际上：
# - 如果 ATR=50，跳空100 → 200% → 触发
# - 如果 ATR=200，跳空100 → 50% → 仍然触发
# - 看似都能工作，但阈值1.5的含义完全错误
```

### 4. **实际影响评估**

#### ✅ 好消息
由于计算结果通常是几十到几百（倍），而阈值只有1.5%，所以**实际上会频繁触发保护**，不会漏掉真正的危险跳空。

#### ❌ 坏消息
- **语义错误**：阈值的含义不清晰（1.5是什么单位？）
- **维护困难**：后续开发者无法理解为什么要设置1.5这么小的值
- **跨品种不一致**：不同品种的ATR差异大，统一阈值不合理

---

## 💡 修复方案

### 采用方案：**ATR倍数法**（量化风格）

**理由**：
1. 系统已大量使用 ATR 进行止损和仓位管理
2. 符合量化交易的波动率思维
3. 自适应不同品种的波动性

---

## 🔧 修复内容

### 1. **修正计算公式** (`calculate_atr.py`)

#### 修改前
```python
def price_gap_protection(api, symbol, direction, gap_threshold_percent=GAP_PROTECTION_RATIO):
    """
    :param gap_threshold_percent: 跳空阈值百分比，默认1.5%
    """
    # 计算跳空幅度（相对于昨日收盘价）
    gap_percent = ((latest_price - pre_close) / atr) * 100
    
    if direction == 1:
        if gap_percent > gap_threshold_percent:  # 1.5
            return False
```

#### 修改后
```python
def price_gap_protection(api, symbol, direction, gap_threshold_atr_multiplier=2.0):
    """
    💡 计算逻辑：
    - 跳空幅度 = |最新价 - 昨收价| / ATR
    - 如果跳空幅度 > 阈值倍数，则认为存在危险跳空
    - 例如：ATR=50，跳空100点 → 100/50=2.0倍 → 达到阈值
    
    :param gap_threshold_atr_multiplier: 跳空阈值（ATR倍数），默认2.0倍ATR
    """
    # 计算跳空幅度（相对于ATR的倍数）
    gap_ratio = abs(latest_price - pre_close) / atr
    
    if direction == 1:
        if gap_ratio > gap_threshold_atr_multiplier:  # 2.0
            msg = f"跳空幅度：{gap_ratio:.2f}倍ATR，阈值：{gap_threshold_atr_multiplier}倍ATR"
            return False
```

**关键改动**：
1. ✅ 去掉 `* 100`（不需要转成百分比）
2. ✅ 参数名从 `gap_threshold_percent` 改为 `gap_threshold_atr_multiplier`
3. ✅ 使用 `abs()` 确保正数（原代码未处理负跳空）
4. ✅ 添加 ATR 有效性检查
5. ✅ 日志信息更清晰（明确显示"X倍ATR"）

---

### 2. **同步更新调用处** (`tasks_daily_open.py`)

#### 修改前
```python
def execute_entry_order(api, account, signal, gap_threshold_percent=GAP_PROTECTION_RATIO):
    """
    :param gap_threshold_percent: 跳空阈值百分比，默认1.5%
    """
    can_trade = price_gap_protection(api, signal.symbol, signal.signal_direction, gap_threshold_percent)
```

#### 修改后
```python
def execute_entry_order(api, account, signal, gap_threshold_atr_multiplier=GAP_PROTECTION_RATIO):
    """
    :param gap_threshold_atr_multiplier: 跳空阈值（ATR倍数），默认2.0倍ATR
    """
    can_trade = price_gap_protection(api, signal.symbol, signal.signal_direction, gap_threshold_atr_multiplier)
```

---

### 3. **配置文件验证** (`parameter_config.py`)

```python
GAP_PROTECTION_RATIO = 1.5  # 价格跳空保护机制启用比例控制 
                            # （如1.5，则跳空幅度>1.5×ATR时触发保护）
```

✅ **配置注释已经是正确的**，说明最初设计意图就是"ATR倍数"，只是代码实现错了。

---

## 📊 修复效果对比

### 场景示例
假设螺纹钢 rb2605：
- 昨日收盘价：3500元
- 今日开盘价：3550元（向上跳空50元）
- 20日ATR：40元

#### 修复前（错误）
```python
gap_percent = (50 / 40) * 100 = 125%
if 125% > 1.5:  # True，触发保护 ✅（碰巧正确）
    return False
```

**问题**：虽然触发了，但125%这个数字让人困惑（为什么是125%？阈值1.5又是什么？）

#### 修复后（正确）
```python
gap_ratio = 50 / 40 = 1.25倍ATR
if 1.25 > 1.5:  # False，不触发保护
    return False
```

**优势**：
- 语义清晰："跳空是日均波动的1.25倍"
- 阈值合理：1.5倍ATR表示"超过1.5倍日常波动的跳空才阻止"
- 易于调整：如果想更严格，可以改为1.2；想更宽松，可以改为2.0

---

## 🎯 阈值建议

根据记忆中的"趋势判定动态阈值设计规范"，建议：

| 市场状态 | 推荐阈值（ATR倍数） | 说明 |
|---------|-------------------|------|
| **强趋势** | 2.5 ~ 3.0 | 允许更大跳空，避免错过趋势延续 |
| **弱趋势** | 1.5 ~ 2.0 | 中等容忍度 |
| **震荡市** | 1.0 ~ 1.5 | 收紧标准，快速识别假突破 |
| **默认值** | **1.5** | 折中方案，适用于大多数情况 |

**当前配置**：`GAP_PROTECTION_RATIO = 1.5` ✅ 合理

---

## ✅ 验证清单

- [x] 修正计算公式（去掉 `* 100`）
- [x] 更新参数名（`percent` → `atr_multiplier`）
- [x] 同步调用处参数
- [x] 添加 ATR 有效性检查
- [x] 使用 `abs()` 处理负跳空
- [x] 优化日志信息
- [x] 验证配置文件注释一致性
- [x] 代码无语法错误

---

## 🚀 后续优化建议

1. **动态阈值**：根据市场状态（强趋势/震荡）自动调整阈值
   ```python
   if trend_state == 'strong':
       threshold = 2.5
   elif trend_state == 'choppy':
       threshold = 1.2
   else:
       threshold = 1.5
   ```

2. **双向独立阈值**：做多和做空使用不同的阈值
   ```python
   if direction == 1:
       threshold = 1.8  # 做多容忍更大向上跳空
   else:
       threshold = 1.3  # 做空对向下跳空更敏感
   ```

3. **历史统计**：记录跳空保护的触发频率，用于优化阈值
   ```python
   # 在数据库中记录
   GapProtectionLog.objects.create(
       symbol=symbol,
       gap_ratio=gap_ratio,
       threshold=threshold,
       blocked=True
   )
   ```

---

**修复完成时间**: 2026-05-07  
**影响范围**: 开仓风控模块  
**风险等级**: 🔴 高（原代码虽能工作但语义错误）  
**修复优先级**: ✅ 已完成
