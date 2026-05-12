# 🔴 CRITICAL 致命问题

> 会导致盈亏数据错误或系统崩溃，需立即修复。

---

## ✅ CRITICAL-01: 临收盘止损平仓盈亏计算缺少合约乘数 — 已修复 (重构后自然解决)

**文件**: [infrastructure/stop_loss_executor.py:60](../backend/stock/infrastructure/stop_loss_executor.py#L60)（原 tasks_exit_before_close.py）

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
但 `infrastructure/stop_loss_executor.py` 中的平仓函数遗漏了该乘数，属于代码不一致 Bug。

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

**文件**: [scheduler/tasks_daily_close.py:432](../backend/stock/scheduler/tasks_daily_close.py#L432)

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

---

## ✅ CRITICAL-03: 移仓换月执行函数使用 signal.signal_direction（始终为0）而非 position.direction — 已修复 (2026-05-10)

**文件**: [infrastructure/order_signals.py:543-548](../backend/stock/infrastructure/order_signals.py#L543)

**问题描述**:
移仓换月信号中，`signal.signal_direction` 在创建时被硬编码为 `0`（见 tasks_daily_close.py:143），但 `execute_rollover_order` 中根据 `signal.signal_direction` 判断使用多头还是空头的价格和成交量。当 `signal.signal_direction === 0` 时，代码始终走 else 分支（空头），导致移仓后多头持仓的成交价格和数量记录错误。

```python
# 错误：移仓时 signal.signal_direction 总是 0
if signal.signal_direction == 1:       # 永远不成立
    entry_avg_price = float(pos_after.open_price_long)
    actual_filled = pos_after.volume_long_today
else:                                   # 始终走这里
    entry_avg_price = float(pos_after.open_price_short)  # 多头移仓却读空头价格
    actual_filled = pos_after.volume_short_today          # 多头移仓却读空头量
```

**影响分析**:
- 多头仓位移仓后，`PositionState.cost_price` 记录的是空头价格
- `contract_total_position` 记录的是空头量
- 后续止损计算、盈亏计算全部基于错误的方向数据
- 可能错过止损或错误触发止损

**修复内容**: `signal.signal_direction` → `position.direction`，使用持仓实际方向而非信号方向

---

## ✅ CRITICAL-04: `_load_config` 使用 `@lru_cache` 返回可变 dict — 已修复 (2026-05-10)

**文件**: [core/config_loader.py:40-66](../backend/stock/core/config_loader.py#L40)

**问题描述**:
`_load_config()` 被 `@lru_cache(maxsize=16)` 装饰。当被调用且缓存命中时，返回的是完全相同的可变 dict 对象。如果任何调用方修改了返回的 dict（如 `result['some_key'] = new_value`），缓存即被污染，后续所有调用方都看到被修改后的值。

```python
@lru_cache(maxsize=16)
def _load_config(account_id=None):
    # ... 构建 result dict ...
    return result  # 同一 dict 对象被缓存和复用
```

**影响分析**:
- 多账户场景下，一个账户的配置修改可能泄露到另一个账户
- 特别是 key 为 `None` 时（取默认配置），影响所有不传 account_id 的调用方
- 止损参数、趋势参数等被错误修改可能导致策略逻辑偏差

**修复内容**:
1. 移除 `@lru_cache` 装饰器（配置读取频率低，缓存收益不大）
2. 移除 `from functools import lru_cache` 导入
3. 移除 `clear_cache()` 函数
4. `_load_config` 现在每次调用都返回新的 dict 对象

---

## ✅ CRITICAL-05: 收盘计算和临收盘平仓任务缺少 Redis 分布式锁 — 已修复 (2026-05-10)

**涉及文件**: tasks_daily_close.py, tasks_exit_before_close.py

**问题描述**:
`job_daily_open_process` 已有 Redis 分布式锁保护，但 `job_daily_close_calculation` 和 `execute_exit_before_close` **没有任何跨进程锁**。多 worker 部署时会导致：
1. 同一持仓被重复平仓
2. 同一信号被重复执行
3. PositionState 数据被覆盖或删除

**影响分析**:
- 同一持仓被重复平仓
- 同一信号被重复执行
- PositionState 数据被覆盖或删除

**修复内容**:
1. `tasks_daily_close.py`：`job_daily_close_calculation` 入口添加 Redis 分布式锁
   - `lock_key = 'lock:daily_close'`，超时 900s（足够完成收盘计算）
   - 获取锁失败时打印日志并跳过本次调度
   - `finally` 块释放锁
2. `tasks_exit_before_close.py`：`execute_exit_before_close` 入口添加 Redis 分布式锁
   - `lock_key = 'lock:exit_before_close'`，超时 600s
   - 遵循与 `tasks_daily_open.py` 一致的 Redis 锁模式（`django_redis.get_redis_connection` + `nx=True` + `ex=` + `delete()`）
- 收盘计算流程添加 Redis 锁

---

## ✅ CRITICAL-06: 止损信号创建与执行不在同一事务 — 已修复 (2026-05-10)

**文件**: [infrastructure/stop_loss_executor.py:137-167](../backend/stock/infrastructure/stop_loss_executor.py#L137)

**问题描述**:
`check_and_execute_stop_loss` 中，DailyStrategySignal 先以 `executed_status='EXECUTING'` 创建并写入数据库，然后调用 `execute_stop_loss_exit`（发送真实订单），最后更新信号状态为 SUCCESS/FAILED。如果进程在信号创建后、状态更新前崩溃，信号将永久停留在 `EXECUTING` 状态。而 `check_duplicate_pending_signal` 只检查 `PENDING` 状态，`EXECUTING` 不会被识别为重复，重启后同样的止损条件会再创建新信号，导致 **重复执行同一止损**。

**影响分析**:
- 同一止损条件被多次执行
- 平仓数量翻倍，导致做反方向（开新仓）
- 如果未做仓位检查，可能产生超额亏损

**修复内容**:
1. 信号初始状态改为 `PENDING`（而非 `EXECUTING`），崩溃后 `check_duplicate_pending_signal` 可正常拦截
2. 执行前通过 `transaction.atomic()` 将 `PENDING→EXECUTING` 与执行结果状态更新捆绑
3. `record_and_reset_position` 异常被单独捕获并记录日志，不阻断事务提交（TqSDK 订单已执行）
4. 同一持仓的止损信号 ID 被复用查询，避免 filter 条件过于宽泛误更新其他信号

---

## ✅ CRITICAL-07: 信号状态更新在 transaction.atomic() 块外 — 已修复 (2026-05-11)

**文件**: [infrastructure/order_signals.py](../backend/stock/infrastructure/order_signals.py)

**问题描述**:
`execute_add_on_order`（两步开仓和标准开仓）和 `execute_exit_order` 中，`signal.executed_status` 在 `transaction.atomic()` 块外保存。具体模式：

```python
# 修复前：
with transaction.atomic():
    PositionState.objects.filter(...).update(...)  # 持仓状态已更新

signal.executed_status = 'SUCCESS'
signal.save(update_fields=['executed_status', 'updated_at'])  # 信号状态在事务外！
```

**影响分析**:
- 如果 `signal.save()` 在 PositionState 更新后失败（DB 连接中断等），持仓状态已变但信号仍为 PENDING
- 下一周期 `process_signals_by_type` 会重新执行该 PENDING 信号
- 加仓信号重放 → 重复加仓 → 仓位翻倍 + 可能超限
- 平仓信号重放 → 重复平仓 → 可能做反方向
- 止损信号因 CRITICAL-06 已有独立保护，不受此影响

**修复内容**:
1. `execute_add_on_order` 两步开仓路径：`signal.save()` 移入 `transaction.atomic()` 块内
2. `execute_add_on_order` 标准开仓路径：`signal.save()` 移入 `transaction.atomic()` 块内
3. `execute_exit_order`：`record_and_reset_position` + `signal.save()` 统一包裹 `transaction.atomic()`

---

## ✅ CRITICAL-08: 多个模拟账户共享同一 TqKq API 导致数据错乱 — 已修复 (2026-05-11)

**文件**: [infrastructure/tqapi.py](../backend/stock/infrastructure/tqapi.py), [scheduler/tasks_daily_close.py](../backend/stock/scheduler/tasks_daily_close.py)

**问题描述**:

`tasks_daily_close.py` 收盘任务的第 6-13 步逐账户循环中，模拟账户共用全局 API 连接：

```python
api = create_tqapi()          # 第1步创建，使用全局默认凭据
...
for account in accounts:
    account_api = api          # ← 模拟账户直接复用全局连接
    if not config.is_simulation:
        account_api = create_tqapi(account)  # 仅实盘创建独立连接
```

`create_tqapi()` 对模拟账户也仅使用 `_get_default_auth()`（环境变量或第一个活跃账户凭据），忽略每个账户自己的 `StrategyConfig.tqapi_account/tqapi_password`。

**影响分析**:
- 多个模拟账户（即使配了不同的天勤账号）全部连到同一个 TqKq 模拟空间
- `api.get_position(symbol)` 返回共享持仓，非当前循环账户的数据
- `api.get_account()` 返回共享余额/权益，所有模拟账户写入相同的权益快照
- `update_all_positions_stop_loss_price` 使用共享 API 的成本价算止损，止损价互相覆盖
- 绩效数据（DailyEquitySnapshot / RollingPerformanceMetrics / AccountPerformanceSummary）全部失真

**修复内容**:
1. `tqapi.py` `create_tqapi()`：当 account 是模拟账户时，使用账户自己的 `tqapi_account/tqapi_password` 创建独立的 `TqKq` 连接，不再降级到全局默认凭据
2. `tasks_daily_close.py`：每个账户（不论模拟/实盘）都调用 `create_tqapi(account)` 获取独立 API 连接，各自关闭

---

## ✅ CRITICAL-09: 两步开仓第2步完成后未 wait_update 就取持仓 — 已修复 (2026-05-12)

**文件**: [infrastructure/order_execution.py:176](../backend/stock/infrastructure/order_execution.py#L176)

**问题描述**:
`execute_two_step_opening` 第2步完成循环后直接调用 `api.get_position()`。最后一次 `wait_update()` 可能在 `target_pos.is_finished()` 循环中由任务状态更新触发而非持仓数据更新触发，导致 `get_position()` 返回过期数据。

```python
# 修复前
target_pos.cancel()
while not target_pos.is_finished():
    api.wait_update()

pos_after = api.get_position(symbol)  # ← 数据可能过期
```

**影响分析**:
- `actual_final_filled`（取 `pos_after.volume_long` 或 `volume_short`）可能不准确
- 加仓、开仓、移仓都使用此值设置 `PositionState.contract_total_position`
- 数据库记录持仓手数与交易所实际持仓手数可能不一致
- 后续止损计算、仓位管理基于错误手数

**修复内容**:
在 `get_position()` 前加一次 `api.wait_update()`，确保 position 数据已刷新：

```python
# 修复后
target_pos.cancel()
while not target_pos.is_finished():
    api.wait_update()

api.wait_update()  # 确保 position 数据刷新
pos_after = api.get_position(symbol)
```

---

## ✅ CRITICAL-10: `Decimal(str(None))` 无保护导致 PnL 计算崩溃 — 已修复 (2026-05-12)

**文件**: [infrastructure/order_execution.py:225-244](../backend/stock/infrastructure/order_execution.py#L225)

**问题描述**:
`record_and_reset_position` 中 `exit_price` 参数默认值为 `None`。当调用方未传入有效成交价且 `quote.last_price` 也无效时，`Decimal(str(None))` → `Decimal("None")` → `InvalidOperation` 崩溃。该函数整体在 `transaction.atomic()` 内，崩溃导致订单已执行但 DB 回滚 → 市场与 DB 持仓不一致。

```python
# 修复前
exit_price = avg_price if avg_price else (float(quote.last_price) if quote and quote.last_price else None)
# exit_price 可能为 None
pnl = (Decimal(str(exit_price)) - cost_price) * ...  # exit_price=None → 崩溃
```

**影响分析**:
- `transaction.atomic()` 内崩溃 → 订单已发但 DB 回滚
- 市场持仓已变但 PositionState 未更新 → 次日信号生成基于错误持仓
- `ClosedPositionRecord` 缺失 → 绩效统计偏差

**修复内容**:
1. 新增 `safe_decimal(value, default=Decimal('0'))` 工具函数，None 或无效值返回 default
2. PnL 计算: `Decimal(str(exit_price))` → `safe_decimal(exit_price)`
3. DB 写入: `Decimal(str(exit_price))` → `safe_decimal(exit_price)`
4. `cost_price` 为 None 时: `cost_price or Decimal('0')` 防止 TypeError
5. `position.indicators.get('trend_factor', 0)` 可能返回 None → `safe_decimal()` 包装

---

## ✅ CRITICAL-11: 移仓 Phase 3 DB 写入无事务保护 — 已修复 (2026-05-12)

**文件**: [infrastructure/order_signals.py:861-933](../backend/stock/infrastructure/order_signals.py#L861)

**问题描述**:
`execute_rollover_order` Phase 3 的 DB 写入操作（delete + create + update + save）在 `transaction.atomic()` 块外。Phase 2（历史指标计算）有 `with transaction.atomic():`，但 Phase 3 被排除在外。

```python
# 修复前结构
try:                                    # 外层 try
    with transaction.atomic():          # Phase 2 — 有事务
        ...历史指标计算...

    try:                                # Phase 3 — 无事务
        existing_new.delete()
        PositionState.objects.create(...)
        PositionState.objects.filter(id=position.id).delete()
        signal.save(...)
        return True
    except:
        return False
except:
    ...
```

**影响分析**:
- `existing_new.delete()` 成功 → `PositionState.create()` 失败 → 新合约持仓数据永久丢失
- `PositionState.objects.filter(id=position.id).delete()` 成功 → `signal.save()` 失败 → 旧合约已删但信号标记失败 → 无法追溯
- 上述异常概率低但后果严重（数据不可逆丢失）

**修复内容**:
Phase 3 套上 `try + with transaction.atomic():` 双层保护:

```python
# 修复后结构
try:                                    # 外层 try
    with transaction.atomic():          # Phase 2
        ...历史指标计算...

    try:                                # 新增 try
        with transaction.atomic():      # Phase 3 — 有事务了
            existing_new.delete()
            PositionState.objects.create(...)
            ...
        return True
    except Exception as e:              # Phase 3 异常处理
        ...
        return False
except:                                 # 外层异常处理
    ...
```
