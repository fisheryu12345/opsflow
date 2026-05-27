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

---

## ✅ CRITICAL-12: `api.get_trades()` 不存在 + `get_trade()` 在 `wait_update` 后创建导致空引用 — 已修复 (2026-05-16)

**涉及文件**:
- [infrastructure/stop_loss_executor.py:48](../backend/stock/infrastructure/stop_loss_executor.py#L48)
- [infrastructure/order_signals.py:523, 626](../backend/stock/infrastructure/order_signals.py#L523)
- [management/commands/run_turtle.py:585, 676](../backend/stock/management/commands/run_turtle.py#L585)
- [management/commands/run_ma10_slope.py:477](../backend/stock/management/commands/run_ma10_slope.py#L477)

**问题描述**:

**Bug 1 — `api.get_trades()` (复数) 不存在:**
TqSDK 的 API 命名规范是所有 getter 都是单数形式：`get_trade()`、`get_position()`、`get_account()`、`get_order()`。代码中 6 处使用了 `api.get_trades()` (复数)，导致运行时 `AttributeError: 'TqApi' object has no attribute 'get_trades'`，TargetPosTask 平仓完成后无法读取成交回报，整个平仓函数崩溃。

**Bug 2 — `get_trade()` 在 `wait_update()` 后创建（空引用）:**
`get_trade()` 返回的是**活引用**（live reference），底层数据仅在 `wait_update()` 执行时刷新。如果在 `wait_update()` 之后创建引用，该引用初始即为空。

```python
# 错误模式：get_trade() 在 wait_update 后创建，引用为空
while not target_pos.is_finished():
    api.wait_update(deadline=time.time() + 1)

trades = api.get_trade()          # ← 引用在 wait_update 后创建，可能为空
filled_vol = 0
for trade in trades.values():     # ← 读取空引用
```

```python
# 正确模式：先创建引用，再 wait_update 刷新数据
trades = api.get_trade()          # ← 引用在 wait_update 前创建

while not target_pos.is_finished():
    api.wait_update(deadline=time.time() + 1)

# get_trade() 引用已在 wait_update 循环中填充数据
filled_vol = 0
for trade in trades.values():
```

**Bug 3 — 循环内重复调用 `get_trade()` :**
`order_signals.py` 移仓函数 (原行 623) 中，`get_trade()` 被放在 while 循环内部，每次迭代都创建新的活引用。正确做法是循环外创建一次，循环内只调用 `wait_update()` 刷新数据。

**改进 — 成交回报确认改用 deadline 替代固定次数:**
原代码使用 `for _ in range(3): api.wait_update()` 等待成交回报，网络正常时浪费、网络波动时不够。改为 deadline 超时模式：
```python
# 改进前
api.wait_update()
api.wait_update()
api.wait_update()  # 固定 3 次，网络慢时不够，快时浪费

# 改进后
deadline = time.time() + 3
while time.time() < deadline:
    api.wait_update(deadline=min(time.time() + 0.5, deadline))
```

**改进 — 成交回报排序:**
原代码使用 `reversed(trades.values())` 按插入顺序反向取最新成交。改为 `sorted(trades.values(), key=lambda t: getattr(t, 'trade_date_time', 0) or 0)` 按实际成交时间排序，更可靠。

```python
# 改进前
for trade in reversed(trades.values()):

# 改进后
sorted_trades = sorted(trades.values(), key=lambda t: getattr(t, 'trade_date_time', 0) or 0)
for trade in sorted_trades:
```

**影响分析**:
- `api.get_trades()` 崩溃导致 TargetPosTask 平仓成功后无法记录成交价
- 降级逻辑使用 `quote.last_price` 作为替代，但实际成交价可能偏离报价
- 导致 PnL 计算不准确、滑点记录失真
- 循环内重复 `get_trade()` 浪费对象创建，不影响正确性但性能劣化

**修复内容**:
1. 全部 6 处 `get_trades()` → `get_trade()`
2. `stop_loss_executor.py`: `get_trade()` 移到 `wait_update()` 循环前
3. `order_signals.py` 移仓函数: 移除循环内 `get_trade()`，改为循环外创建引用
4. 固定次数 wait_update → deadline 超时模式
5. `reversed(trades.values())` → `sorted(..., key=trade_date_time)`

---

## ✅ CRITICAL-13: HVOB-MBI 开仓区间(OR)跟踪缺陷导致零成交 — 已修复 (2026-05-25)

**文件**: [trading_engine.py](../../backend/hvob_mbi/trading_engine.py)

**问题描述**:
HVOB-MBI 策略自上线以来从未产生过一笔交易。`_on_quote()` 未在 `night_or` 和 `gap_check` 阶段被调用，导致 OR 条目从未创建、R 值从未计算、`_check_entry()` 始终 return。

**Bug 链路 (4 个缺陷连锁)**:
1. `_check_phase` 中 `night_or` 阶段只有时间判断 + 过渡，没有调用 `_on_quote()` → 21:00-21:30 之间没有任何价格跟踪
2. `night_breakout` 阶段才开始调用 `_on_quote()` 创建 OR 条目，但 `_close_night_opening_range()` 已在过渡瞬间执行完毕 → 条目永不关闭，R 为 None
3. 日盘同理：`gap_check`(9:00-9:30)没有 `_on_quote()` 调用，`day_breakout` 阶段创建的日盘 OR 条目无法关闭
4. 即使夜盘 OR 条目存在，日盘 `_track_opening_range(is_night=False)` 因 `is_night` 不匹配跳过更新，且因 `closed=True` 直接 return，无法创建新条目

**影响分析**:
- 数据库 4 个交易日全部 trades=0, daily_pnl=0, opening_ranges={}
- 筛选正常: 每天 10-11 个候选品种，但永远无法入场
- MBI 永远返回 0.5 '中性'（所有品种因 R=None 被跳过）

**修复内容**:
1. `_check_phase`: `night_or` 和 `gap_check` 阶段调用 `_on_quote()`，跟踪 OR
2. `_on_quote`: 新增 `night_or`(夜盘 OR) 和 `gap_check`(日盘 OR) 阶段的 OR 跟踪逻辑
3. `_check_gap`: 末尾清除夜盘 OR 条目，避免阻塞日盘 OR 跟踪
4. `_init_phase`: 新增方法，根据当前时间确定启动相位（同时修复 HIGH-26）

---

## ✅ CRITICAL-14: HVOB 引擎行情价格 NaN 漏检导致 decimal.InvalidOperation 崩溃 — 已修复 (2026-05-26)

**文件**: [trading_engine.py:333](../../backend/hvob_mbi/trading_engine.py#L333)

**问题描述**:
`_on_quote()` 中 `quote.last_price` 检查了 `None` 和 `== 0`，但未检查 `float('nan')`。TqSDK 在某些品种数据未就绪时返回 NaN 价格：
- `nan != 0` 为 `True`，所以 `== 0` 检查无效
- `Decimal(str(float('nan')))` → `Decimal('NaN')`
- `Decimal('NaN') >= h_break` → `decimal.InvalidOperation` 崩溃

**影响分析**:
- 引擎在 night_breakout 阶段收到 NaN 行情时崩溃
- 整个 TradingEngine 进程退出
- 必须手动重启才能恢复交易
- 错过交易时段

**修复内容**:
1. 导入 `import math`（文件顶部）
2. 行情过滤条件追加 `math.isnan(quote.last_price)`:
```python
if quote is None or quote.last_price is None or quote.last_price == 0 or math.isnan(quote.last_price):
    continue
```

---

## ✅ CRITICAL-15: HVOB 强制平仓 NaN 价格导致 daily_pnl 被 NaN 污染 — 已修复 (2026-05-26)

**文件**: [trading_engine.py:858-861](../../backend/hvob_mbi/trading_engine.py#L858)

**问题描述**:
`_force_close_all()` 中 NaN 价格同样漏检：
```python
price = float(quote.last_price) if quote and quote.last_price else 0
if price <= 0:
    continue
```
NaN 行情下：`float(nan)` → `nan`，`nan <= 0` → `False` → 继续执行 → `_calc_pnl(pos, nan)` → `Decimal('NaN')` → `self.daily_pnl += Decimal('NaN')` → 后续所有 PnL 聚合值永久为 NaN。

**影响分析**:
- 强制平仓时的盈亏记录全部为 NaN
- `daily_pnl` 被 NaN 污染，后续任何 `+=` 操作结果均为 NaN
- `_finalize` 中的 `record_daily_equity` 写入 NaN 权益
- 日终绩效数据失真

**修复内容**:
```python
quote = self.api.get_quote(symbol)
if quote is None or quote.last_price is None or math.isnan(quote.last_price):
    continue
price = float(quote.last_price)
```

---

## ✅ CRITICAL-16: HVOB signal_recorder 未传 trend_factor/trend_label，成功开仓后写入 DB 崩溃 — 已修复 (2026-05-26)

**文件**: [signal_recorder.py:28-46](../../backend/hvob_mbi/signal_recorder.py#L28)

**问题描述**:
`record_entry_signal` 创建 `DailyStrategySignal` 时未传入 `trend_factor` 和 `trend_label`：
```python
signal = DailyStrategySignal.objects.create(
    account=account, symbol=symbol, ...,
    # trend_factor 缺失 ← 模型定义中 NOT NULL
    # trend_label 缺失  ← 模型定义中 NOT NULL
)
```

`DailyStrategySignal` 模型中这两个字段没有 `null=True, blank=True`，默认值为 `None`，MySQL 拒绝写入，抛出 `(1048, "Column 'trend_factor' cannot be null")`。

同理 `record_exit_signal` (line 58) 和 `record_stop_loss_signal` (line 84) 也存在相同的遗漏。

**影响分析**:
- TargetPosTask 实际已成交，持仓在引擎内存中正确跟踪 (`self.positions`、`self.traded`)
- 但 `DailyStrategySignal` 未写入 DB → 信号审计缺失
- 用户看到"❌ 开仓失败"误导信息（实际开仓成功）
- 引擎重启后 `_supplement_traded_from_db()` 查不到该笔信号 → `traded` 集合为空 → 同一品种可能被重复入场

**修复内容**: 三个函数中的 `DailyStrategySignal.objects.create()` 均补传：
```python
trend_factor=Decimal('0'),
trend_label='HVOB',
```
