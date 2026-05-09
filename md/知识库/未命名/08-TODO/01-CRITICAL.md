# 🔴 CRITICAL 致命问题

> 会导致盈亏数据错误或系统崩溃，需立即修复。

---

## CRITICAL-01: 临收盘止损平仓盈亏计算缺少合约乘数

**文件**: [tasks_exit_before_close.py:187](../backend/stock/scheduler/tasks_exit_before_close.py#L187)

**问题描述**:
```python
# 当前错误代码（缺少 volume_multiple）：
pnl = (avg_price - position.cost_price) * Decimal(str(filled_volume))

# 正确代码应包含合约乘数：
volume_multiple = Decimal(str(contract_info.volume_multiple))
pnl = (avg_price - position.cost_price) * Decimal(str(filled_volume)) * volume_multiple
```

**影响分析**:
- `ClosedPositionRecord.pnl` 记录值比实际少 `volume_multiple` 倍
- 螺纹钢(乘数=10): PnL 记录仅为实际的 1/10
- 沪深300股指期货(乘数=300): PnL 记录仅为实际的 1/300
- 所有通过 `execute_exit_before_close` 平仓的记录盈亏都错误
- 进而影响: 品种胜率统计、累计盈亏、绩效指标等所有依赖 PnL 的模块

**根因**: `tasks_daily_open.py` 中平仓函数已正确包含 `volume_multiple`（第503行），
但 `tasks_exit_before_close.py` 中的平仓函数遗漏了该乘数，属于代码不一致 Bug。

**修复方案**:
```python
# 获取合约乘数
quote = api.get_quote(position.symbol)
volume_multiple = Decimal(str(quote.volume_multiple))

# 计算盈亏（含合约乘数）
if position.direction == 1:
    pnl = (avg_price - position.cost_price) * Decimal(str(filled_volume)) * volume_multiple
else:
    pnl = (position.cost_price - avg_price) * Decimal(str(filled_volume)) * volume_multiple
```

**关联风险**: 同文件中 `commission`（手续费）计算也可能存在类似问题，需检查。

---

## ✅ CRITICAL-02: 止损更新函数中 `api.get_position()` 无异常保护 — 已修复 (2026-05-09)

**文件**: [tasks_daily_close.py:576](../backend/stock/scheduler/tasks_daily_close.py#L576)

**问题描述**:
```python
# 修复前：直接调用 API 获取持仓成本价，无 try/except
cost_price = api.get_position(position.symbol).open_price_long  # 多头
# 或
cost_price = api.get_position(position.symbol).open_price_short  # 空头
```

**影响分析**:
- 当 TqApi 连接已经断开(网络波动/超时)，直接抛出异常
- 当持仓在 TqSdk 端已不存在(手动平仓)，`get_position` 返回 None 导致 `AttributeError`
- 整个 `update_all_positions_stop_loss_price()` 函数中断
- 导致: 所有品种的止损价无法更新，错过止损保护

**复现场景**:
1. 收盘计算任务执行到 Step 7 时 API 连接已超时
2. 某个品种在系统中存在 PositionState，但在 TqSdk 端已被手动平仓
3. 移仓换月后旧合约在 TqSdk 端已不存在

**修复内容**:
1. 在 `tasks_daily_close.py` 的 `api.get_position()` 调用处添加 try/except 保护
2. API 获取失败时自动降级使用数据库中的 `position.cost_price`
3. 若数据库也无成本价，记录错误日志并跳过该品种，不影响其他品种
4. 添加了 `log_error` 导入

**修复后代码**:
```python
try:
    tq_pos = api.get_position(position.symbol)
    cost_price = tq_pos.open_price_long  # 或 open_price_short
except Exception as e:
    log_trade(..., f"API获取{position.symbol}成本价失败({e})，使用数据库记录", ...)
    cost_price = position.cost_price
    if cost_price is None:
        log_error(..., f"{position.symbol} 数据库和API均无成本价，跳过止损更新")
        continue
```
