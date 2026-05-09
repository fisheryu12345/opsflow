# 🟠 HIGH 高优先级问题

> 可能导致策略逻辑错误、数据不准确或难以排查的异常。

---

## HIGH-01: 指标计算失败时静默跳过，无日志告警

**文件**: [tasks_daily_close.py:561-563](../backend/stock/scheduler/tasks_daily_close.py#L561-L563)

**问题描述**:
```python
# 当前代码：calculate_indicators 返回 None 时没有任何日志记录
indicators = calculate_indicators(api, position.symbol, position.product_code)
if indicators is None or indicators.get('atr_20') is None:
    continue  # 静默跳过
```

**影响分析**:
- 当某个品种指标计算失败（数据不足/网络异常），整品种被静默跳过
- 没有 TradeLog 记录，排查时需要查看 ErrorLog 或外部日志
- 止损价无法更新，可能导致该品种的止损停留在旧价格
- 趋势信息无法更新，次日开盘信号可能基于旧数据

**修复方案**:
```python
indicators = calculate_indicators(api, position.symbol, position.product_code)
if indicators is None or indicators.get('atr_20') is None:
    log_trade(
        'update_all_positions_stop_loss_price',
        f"{position.symbol} 指标计算失败，跳过止损更新",
        symbol=position.symbol, log_level='WARNING'
    )
    continue
```

---

## ✅ HIGH-02: 跳空保护函数默认参数与调用方不一致 — 已修复 (2026-05-09)

**文件**: [calculate_atr.py:45](../backend/stock/scheduler/calculate_atr.py#L45)

**问题描述**:
```python
# 修复前：函数定义默认值为 2.0，与 GAP_PROTECTION_RATIO=1.5 不一致
def price_gap_protection(api, symbol, direction, gap_threshold_atr_multiplier=2.0):

# parameter_config.py — 实际配置值为 1.5
GAP_PROTECTION_RATIO = 1.5
```

**影响分析**:
- 默认值与实际使用值不一致（2.0 vs 1.5），属于代码异味
- 若未来有新的调用方未传入此参数，将使用更宽松的 2.0 阈值
- 跳空保护的严格程度直接影响风险控制效果

**修复内容**: 将 `calculate_atr.py` 中 `price_gap_protection` 函数默认值从 `2.0` 改为 `1.5`，与 `parameter_config.GAP_PROTECTION_RATIO` 保持一致。
```python
def price_gap_protection(api, symbol, direction, gap_threshold_atr_multiplier=1.5):
```

---

## HIGH-03: 开仓 PnL 计算缺少 Decimal 包装

**文件**: [tasks_daily_open.py:505](../backend/stock/scheduler/tasks_daily_open.py#L505)

**问题描述**:
```python
# 当前代码：float 类型直接存入 DecimalField
pnl = (exit_price - cost_price) * volume * volume_multiple
```
其中 `exit_price`、`cost_price` 是 Decimal，但 `volume` 和 `volume_multiple` 是 int/float，
计算结果为 float，与 DecimalField 类型不匹配。

**影响分析**:
- Django 会自动转换，但存在浮点数精度问题
- 当金额较大时（如沪深300，乘数300），精度误差会被放大
- 可能导致盈亏金额出现几毛钱到几元钱的误差

**修复方案**:
```python
from decimal import Decimal
pnl = (exit_price - cost_price) * Decimal(str(volume)) * Decimal(str(volume_multiple))
```
