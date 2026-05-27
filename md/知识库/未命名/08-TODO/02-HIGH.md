# 🟠 HIGH 高优先级问题

> 可能导致策略逻辑错误、数据不准确或难以排查的异常。

---

## ✅ HIGH-01: 指标计算失败时静默跳过，无日志告警 — 已修复 (2026-05-09)

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

**修复内容**: 在 `job_daily_close_calculation` 的指标计算循环中，result 返回 None 时和异常捕获时均添加 `log_trade` 记录。
```python
# 修复后
if result:
    ...
else:
    log_trade('job_daily_close_calculation',
              f"{contract['symbol']} 指标计算返回空，跳过",
              symbol=contract['symbol'], log_level='WARNING')

except Exception as e:
    log_trade('job_daily_close_calculation', msg,
              symbol=contract['symbol'], log_level='ERROR')
```

---

## ✅ HIGH-02: 跳空保护函数默认参数与调用方不一致 — 已修复 (2026-05-09)

**文件**: [core/atr.py:51](../backend/stock/core/atr.py#L51)（原 scheduler/calculate_atr.py，已迁移）

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

**修复内容**: 将 `calculate_atr.py` 中 `price_gap_protection` 函数默认值从 `2.0` 改为 `1.5`，与 `core.config_loader.get_config('GAP_PROTECTION_RATIO')` 保持一致。
```python
def price_gap_protection(api, symbol, direction, gap_threshold_atr_multiplier=1.5):
```

---

## ❌ HIGH-03: 开仓 PnL 计算缺少 Decimal 包装 — 不是BUG（Django 自动转换，精度影响可忽略）

**文件**: [infrastructure/order_signals.py](../backend/stock/infrastructure/order_signals.py)（原 tasks_daily_open.py，已迁移）

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

---

## ✅ HIGH-04: StrategyConfig 明文存储 TqSDK 密码 — 已修复 (2026-05-10)

**文件**: [views/strategyconfig.py:13](../backend/stock/views/strategyconfig.py#L13)

**问题描述**:
`StrategyConfigViewSet` 使用 `ModelViewSet` 且只有 `IsAuthenticated` 权限，任何已登录用户都可读取和修改 TqSDK 账号密码。

**影响分析**:
- 任意系统用户（非管理员）可通过 API 获取交易账号密码
- 可通过 API 修改账号密码导致交易系统无法登录

**修复内容**: `permission_classes` 从 `[IsAuthenticated]` 改为 `[IsAdminUser]`，仅管理员可访问策略配置 API。

---

## ✅ HIGH-05: `AccountContractConfigViewSet` 缺少账户访问验证 — 已修复 (2026-05-10)

**文件**: [views/account_contract.py:68-76,106-113,127-161](../backend/stock/views/account_contract.py#L68)

**问题描述**:
`toggle`、`batch_toggle`、`available` 三个端点接收 `account_id` 参数，但未调用 `validate_account_access()` 校验当前用户对该账户的操作权限。

**影响分析**: 用户可查看/修改其他账户的品种配置。

**修复内容**: 三个端点均在确定 `account_id` 后调用 `validate_account_access()`，越权操作返回 403。

---

## ✅ HIGH-06: `test.py` 包含生产环境交易凭证 — 已修复 (2026-05-10)

**文件**: [views/test.py:4,27,80,138,207,234](../backend/stock/views/test.py#L4)

**问题描述**:
`test.py` 硬编码了 TqSDK 账号密码 `yupei1986`/`yupei1986` 共 6 处，包含实盘交易 API 调用代码。

**修复内容**: 已删除 `test.py` 文件。

---

## ✅ HIGH-07: FullContractList 和 RollingPerformanceMetrics 缺少唯一约束 — 已修复 (2026-05-10)

**文件**: [models.py:170-174,424-431](../backend/stock/models.py#L170)

**问题描述**:
`FullContractList` 没有 `unique_together = ('exchange', 'product_code', 'symbol')`，同一合约可被重复插入多次。`RollingPerformanceMetrics` 没有 `unique_together = ('account', 'calc_date', 'window_days')`，同一计算可产生多条重复记录。

**影响分析**:
- `FullContractList` 重复数据导致合约选择器出现重复项
- 移仓检测可能匹配到错误的合约行
- `RollingPerformanceMetrics` 重复记录导致绩效指标数值膨胀

**修复内容**:
1. `FullContractList.Meta` 添加 `unique_together = ('exchange', 'product_code', 'symbol')`
2. `RollingPerformanceMetrics.Meta` 添加 `unique_together = ('account', 'calc_date', 'window_days')`
3. 生成并运行迁移 `0068_add_unique_constraints`
4. 经验证：当前数据库无重复记录，约束已直接生效

---

## ✅ HIGH-08 (前端): StrategyConfig `GetObj` URL 缺少尾部斜杠 — 已修复 (2026-05-10)

**文件**: [strategyconfig/api.ts:9-11](../web/src/views/apps/strategyconfig/api.ts#L9)

**问题描述**:
`GetObj` 拼接的 URL 为 `apiPrefix + id`（无尾部斜杠），但 DRF 默认 `APPEND_SLASH=True`。所有其他 CRUD 端点都使用 `apiPrefix + id + '/'`。缺少斜杠会导致请求被 302 重定向或 404。

**修复内容**: `apiPrefix + id` → `apiPrefix + id + '/'`

---

## ✅ HIGH-09 (前端): 合约统计 `fetchStats` 响应结构解析错误 — 已修复 (2026-05-10)

**文件**: [contracts/useContract.ts:35-43](../web/src/views/apps/contracts/useContract.ts#L35)

**问题描述**:
`fetchStats()` 检查 `res.total !== undefined` 后赋值 `stats.value = res`。但后端 `statistics()` 返回的是非标准格式 `{"total": ..., "by_exchange": [...]}`（无 `code`/`data` 包裹），触发 Axios 拦截器"非标准返回"错误日志。同时 `ContractStats` 接口声明的 `active`/`inactive` 字段后端未提供。

**影响分析**: 统计弹窗功能可用（因拦截器对无 `code` 的响应直接透传），但每次打开都会触发错误日志记录，且前后端响应格式不统一。

**修复内容**:
1. 后端 `contract.py`：`statistics()` 返回标准格式 `{'code': 2000, 'msg': 'success', 'data': {'total': ..., 'by_exchange': [...]}}`
2. 前端 `useContract.ts`：改为检查 `res.code === 2000 && res.data` 后赋值 `stats.value = res.data`

---

## ✅ HIGH-10 (前端): 错误日志"清除全部"只删除第一条 — 已修复 (2026-05-10)

**文件**: [errorlog/index.vue:98-107](../web/src/views/apps/errorlog/index.vue#L98)

**问题描述**:
`handleClearAll` 遍历 `list.value` 逐条删除，但每次 `deleteLog` 调用后 `fetchData()` 会替换 `list.value`，导致后续迭代操作过期引用。同时 N 次多余的 `fetchData` 调用造成性能浪费。

**影响分析**: "清除全部"功能名不副实，用户误以为已清除但多数记录仍在

**修复内容**:
1. 用 `list.value.map(item => item.id)` 快照所有 ID，迭代不再依赖 `list.value` 引用
2. 避免 `deleteLog` 中 `fetchData` 替换数组导致的迭代失效问题

---

## ✅ HIGH-11 (前端): `userInfo` 缺少 `roles` 属性 — 路由守卫可能崩溃 — 已修复 (2026-05-10)

**文件**: [stores/userInfo.ts:44-59](../web/src/stores/userInfo.ts#L44)

**问题描述**:
`frontEnd.ts:31` 检查 `useUserInfo().userInfos.roles.length` 确定用户角色是否为空。但 `UserInfosState` 接口中只有 `role_info: any[]`，没有 `roles` 属性。API 返回的角色数据被赋到 `role_info` 而非 `roles`，导致 `userInfos.roles` 为 `undefined`，`.length` 调用抛出 TypeError。

**影响分析**:
- 路由守卫执行时 `undefined.length` 抛出 TypeError，后续动态路由添加中断
- 菜单过滤函数 (`setFilterHasRolesMenu`) 接收 `undefined` 而非角色数组，过滤逻辑全部失效
- 实际表现：用户登录后可能看不到菜单或路由守卫提前返回

**修复内容**:
1. `UserInfosState` 接口添加 `roles: string[]`
2. `userInfo.ts` state 默认值添加 `roles: []`
3. `updateUserInfos()` 中从 `role_info[].key` 提取角色标识数组赋值给 `roles`
4. `setUserInfos()` 中 API 分支和 Session 回填分支均添加 `roles` 赋值逻辑
5. 旧缓存兼容：Session 回填时检测 `roles` 为空则自动从 `role_info` 重建

---

## ✅ HIGH-12 (TqSDK): 止损平仓后读取 trades 缺少最后一次 wait_update — 已修复 (2026-05-10)

**文件**: [infrastructure/stop_loss_executor.py:34-40](../backend/stock/infrastructure/stop_loss_executor.py#L34)

**问题描述**:
`execute_stop_loss_exit` 中 `target_pos.is_finished()` 循环退出后立即调 `api.get_trades()`：
```python
while not target_pos.is_finished():
    api.wait_update(deadline=time.time() + 1)
    if time.time() - start_time > 60:
        return False, 0, Decimal('0')

trades = api.get_trades()  # ← 成交数据可能还没到达
```

TqSDK 的成交回报（Trade）在 `wait_update()` 期间推送到内存对象。最后一次 `wait_update()` 如果只推进了任务状态（`is_finished=True`）但成交回报尚未到达，`get_trades()` 返回空或不完整的成交列表。

**影响分析**:
- `filled_volume=0` → 回退到 `quote.last_price` 计算盈亏（`order_execution.py:219`）
- PnL 记录使用近似价格而非实际成交价
- 多次止损平仓时累计偏差放大

**修复建议**:
```python
# target_pos 完成后，多等几轮 wait_update 确保成交数据到达
for _ in range(3):
    api.wait_update()
trades = api.get_trades()
```
---

## ✅ HIGH-13 (TqSDK): 移仓操作不记录平仓 PnL — 已修复 (2026-05-10)

**文件**: [infrastructure/order_signals.py:446-502](../backend/stock/infrastructure/order_signals.py#L446)

**问题描述**:
`execute_rollover_order` 的 Phase 1 平仓旧合约后，未创建 `ClosedPositionRecord`。Phase 3 直接 `delete()` 旧 `PositionState`。

**影响分析**:
- 移仓产生的盈亏完全丢失，不纳入绩效计算（胜率、盈亏比、最大回撤等均有偏差）
- `ClosedPositionRecord` 中缺少移仓记录，交易历史不完整
- 越频繁移仓的品种，数据偏差越大

**修复内容**:
Phase 1 平仓成功后增加平仓记录创建:
1. 3 轮 `api.wait_update()` 等待成交回报到达
2. 遍历 `api.get_trades()` 统计实际成交手数和均价（同 `stop_loss_executor.py` 模式）
3. 查 `FullContractList.volume_multiple` 计算实际 PnL
4. 创建 `ClosedPositionRecord` 包含 account/symbol/direction/volume/exit_price/cost_price/pnl/holding_days
5. 成交数据不足时回退到 `quote.last_price` 近似计算

---

## ✅ HIGH-15: 两步开仓路径未设置 `open_date` — 已修复 (2026-05-10)

**文件**: [infrastructure/order_signals.py:238-254](../backend/stock/infrastructure/order_signals.py#L238)

**问题描述**:
`execute_entry_order` 两步开仓路径的 `update_or_create` defaults 中缺少 `open_date` 字段。直接开仓路径（line 325）正确设置了该字段。

**影响分析**:
- 两步开仓建立的仓位 `open_date=NULL`
- 平仓时 `holding_days` 无法计算（为 `None`）
- 持仓周期统计缺失

**修复内容**: two_step_entry 路径的 defaults 中添加 `'open_date': timezone.now().date()`

---

## ✅ HIGH-16: 品种停用后持仓跟踪冻结 — 已修复 (2026-05-10)

**文件**: [scheduler/tasks_daily_close.py:564-571](../backend/stock/scheduler/tasks_daily_close.py#L564)

**问题描述**:
`job_daily_close_calculation` 的指标计算只对 `AccountContractConfig.is_active=True` 的品种执行。停用品种的持仓指标不再更新，止损价、高低价跟踪均冻结。

**影响分析**:
- 停用品种的 `indicators`(ATR/MA/trend) 冻结 → 止损价不跟随市场移动
- 若市场逆向波动，止损不会调整，可能造成超预期亏损
- `highest_close`/`lowest_close` 依赖 `latest_close_price` 也无法更新

**修复内容**: 指标计算的品种范围从仅 `active_product_codes` 扩展到 `active_product_codes | position_product_codes`（有持仓的品种也纳入计算）。ENTRY 信号生成仍按 active 过滤，不受影响。
`

---

## ✅ HIGH-17: 移仓成交确认仅固定 3 次 wait_update — 已修复 (2026-05-11)

**文件**: [infrastructure/order_signals.py:574-577](../backend/stock/infrastructure/order_signals.py#L574)

**问题描述**:
`execute_rollover_order` Phase 1 平仓旧合约后，仅执行 3 次 `api.wait_update()` 等待成交回报：

```python
for _ in range(3):
    api.wait_update()
```

**影响分析**:
- 部分成交场景下，3 次 `wait_update()` 不足以收到全部成交回报
- `filled_volume` 统计为部分值或 0 → PnL 记录为近似值而非实际值
- 多次移仓的累计偏差放大
- 大户持仓拆分成交（各交易所常见）时问题最明显

**修复内容**:
1. 使用带超时（10秒）的循环替代固定 3 次更新
2. 每次 `wait_update()` 后重新统计 `api.get_trades()` 中该合约+该方向的成交手数
3. 全部成交到达后提前退出循环
4. 超时后仍使用已收集到的部分成交数据（最差情况：fallback 到 `quote.last_price`）

---

## ✅ HIGH-18: 加仓两步策略未考虑已有持仓，min_position 检查失败 — 已修复 (2026-05-12)

**文件**: [infrastructure/order_signals.py:97,118-124,192-198](../backend/stock/infrastructure/order_signals.py#L97)

**问题描述**:
`execute_add_on_order` 两步开仓策略的 `adjusted_volume` 直接使用 `min_position_check['adjusted_volume']`（= `min_position`），假设起始持仓为 0。但加仓场景当前持仓 > 0（如 1 手），第 1 步目标是 `min_position` 手时，实际开仓增量 = `min_position - 当前持仓 < min_position`，TqSDK 拒绝执行。

失败日志示例：
```
GFEX.lc2609 第1步：设置目标持仓 5手
... TqSDK 警告: 剩余开仓手数 4 小于最小开仓手数 5，不进行开仓
```

此外，两步开仓失败和普通 TargetPosTask 失败路径均未更新 `signal.remark`，前端显示原始信号描述，无法直观看到失败原因。

**影响分析**:
- 当 `当前持仓 %gt; 0` 且 `order_volume < min_position` 时，加仓必然失败
- 失败后 signal 停留在 PENDING，无法自动重试
- 失败原因不直观，排查困难

**修复内容**:
1. `adjusted_volume = position.contract_total_position + min_pos` — 第 1 步目标 = 当前持仓 + 最小开仓限制，确保开仓增量 >= min_position
2. 两步开仓失败路径增加 `signal.remark`，记录计划手数、最小开仓限制、当前持仓、目标手数、开仓增量
3. 普通 TargetPosTask 失败路径同样增加 `signal.remark`，记录计划手数和目标手数
4. `signal.save()` 追加更新 `remark` 字段

---

## ✅ HIGH-19: `is_api_connected` 使用 `get_account()` 永远返回 True，连接检测失效 — 已修复 (2026-05-12)

**文件**: [infrastructure/tqapi.py:67-79](../backend/stock/infrastructure/tqapi.py#L67)

**问题描述**:
`is_api_connected` 调用 `api.get_account()` 检测连接，但 TqSDK 的 `get_account()` 返回懒加载代理对象，不进行网络 I/O。即使 WebSocket 已断开也不会报错。

**影响分析**:
- `ensure_api_connected()` 实际是空操作，永远不会触发重连
- `tasks_daily_open.py` 中三个信号批次间的连接健康检查全部无效
- API 断开后无法自动恢复，后续交易调用全部失败

**修复内容**:
将 `api.get_account()` 改为 `api.wait_update(deadline=time.time() + 0.5)`，给 TqSDK 机会处理连接事件。

---

## ✅ HIGH-20: 移仓 `update_or_create` 可能覆盖新合约已有持仓 — 已修复 (2026-05-12)

**文件**: [infrastructure/order_signals.py:847-866](../backend/stock/infrastructure/order_signals.py#L847)

**问题描述**:
`execute_rollover_order` Phase 3 使用 `update_or_create(symbol=new_symbol)` 创建新合约持仓，未检查该合约是否已有持仓记录。如果已有记录会被旧数据覆盖。

**影响分析**:
- 新合约上已有持仓时，单位数、开仓价等全部被旧数据覆盖
- 数据不可逆丢失

**修复内容**:
1. 创建前先查询 `(account, new_symbol)` 是否已有 `units > 0` 的持仓
2. 有持仓时合并：累加单位数，按持仓量加权均价
3. 无持仓时正常创建，清理残留的零单位记录

---

## ✅ HIGH-21: 止损平仓超时硬编码 60s — 已修复 (2026-05-12)

**文件**: [infrastructure/stop_loss_executor.py:40](../backend/stock/infrastructure/stop_loss_executor.py#L40)

**问题描述**:
`execute_stop_loss_exit` 的超时检查使用硬编码 `60` 秒，未使用可配置的 `TIMEOUT_SECONDS`。其他所有超时操作（`wait_for_target_position`、`execute_two_step_opening` 等）均使用配置值。

**影响分析**:
- `TIMEOUT_SECONDS` 配置值被忽略
- 如果配置 > 60，止损比其他操作更早超时，流动性差时容易失败
- 如果配置 < 60，止损等待时间比配置长，延长任务阻塞时间

**修复内容**:
1. 导入 `TIMEOUT_SECONDS = get_config('TIMEOUT_SECONDS')`
2. 硬编码 `60` 替换为 `TIMEOUT_SECONDS`

---

## ✅ HIGH-22: 止损无成交价时记录虚假巨亏 PnL — 已修复 (2026-05-12)

**文件**: [infrastructure/stop_loss_executor.py:63-68](../backend/stock/infrastructure/stop_loss_executor.py#L63)

**问题描述**:
`execute_stop_loss_exit` 中 TargetPosTask 无成交回报 `filled_volume=0` 时，回退到 `quote.last_price`。当 `quote.last_price` 也为 None 时，使用 `Decimal('0')` 作为成交价：

```python
# 修复前
if filled_volume > 0:
    avg_price = total_cost / Decimal(str(filled_volume))
else:
    quote = api.get_quote(position.symbol)
    avg_price = Decimal(str(quote.last_price)) if quote.last_price else Decimal('0')
    filled_volume = position.contract_total_position
```

0 价传入 `record_and_reset_position` 后，PnL 计算为 `(0 - cost_price) * volume * volume_multiple`，记录一笔远超实际的虚假巨亏。且 `filled_volume` 被强制设为 `contract_total_position`，即使实际成交为 0。

**影响分析**:
- `ClosedPositionRecord.pnl` 记录一笔虚假巨额亏损（可达真实止损亏损的数十倍）
- 品种胜率、盈亏比、累计盈亏全部失真
- 账户绩效指标被严重扭曲

**修复内容**:
去掉 `Decimal('0')` 回退，无成交也无行情时返回失败等待人工处理：

```python
# 修复后
if filled_volume > 0:
    avg_price = total_cost / Decimal(str(filled_volume))
else:
    quote = api.get_quote(position.symbol)
    if quote and quote.last_price:
        avg_price = Decimal(str(quote.last_price))
        filled_volume = position.contract_total_position
    else:
        log_error('execute_stop_loss_exit',
                  f"{position.symbol} 无成交回报且无行情报价，无法确定平仓价")
        return False, 0, Decimal('0')
```

---

## 🔴 HIGH-23: `wait_update()` 无超时导致收盘任务在无持仓账户上无限阻塞 — 已修复 (2026-05-12)

**文件**: [tasks_daily_close.py:395](../backend/stock/scheduler/tasks_daily_close.py#L395)

**问题描述**:
`update_all_positions_stop_loss_price` 中无条件执行 `api.wait_update()` 且不带 `deadline` 参数：

```python
def update_all_positions_stop_loss_price(api, account):
    positions = PositionState.objects.filter(account=account, units__gt=0)
    # 【修复】确保 TqSDK 持仓数据已加载
    api.wait_update()  # ← 没有 deadline！
    for position in positions:
        ...
```

收盘后 TqSDK 不再推送新行情，`wait_update()` 永远等不到数据更新。

**触发条件**:
- 激活了新账户但没有持仓（`units=0`），`positions` queryset 为空
- 但 `wait_update()` 在 `for position in positions` 之前无条件执行
- 有持仓的账户（如 510976，9 个持仓）不受影响：TqSDK 连接后会推送持仓数据，`wait_update()` 能正常返回

**影响分析**:
- 收盘任务无限阻塞，`job_daily_close_calculation` 永远不结束
- Redis 锁被一直持有，次日调度也失败
- 所有账户的绩效指标无法更新
- 必须手动重启 gunicorn 恢复

**修复内容**:
1. `positions.exists()` 前置判断：无持仓时跳过 `wait_update`
2. 即使有持仓，也加 `deadline=time.time() + 5` 兜底

```python
if positions.exists():
    api.wait_update(deadline=time.time() + 5)
```


## ✅ HIGH-24: 重连后 MySQL gone away 导致进程崩溃 — 已修复 (2026-05-22)

**文件**: [infrastructure/tqapi.py](../../backend/stock/infrastructure/tqapi.py#L42)

**问题描述**:
`_reconnect()` 执行 `safe_close_api` → `time.sleep(35)` → `create_tqapi(self.account)`。`create_tqapi()` 内部 `StrategyConfig.objects.get()` 在 35s 空闲后使用已关闭的 MySQL 连接，抛出 `MySQL server has gone away`。

**影响分析**:
- HVOB 引擎 20:55 夜盘重启时崩溃，整个 TradingEngine 进程中断
- 错过夜盘交易时段

**修复内容**:
在 `create_tqapi()` 和 `_get_default_auth()` 的 ORM 查询前添加 `close_old_connections()`:

```python
close_old_connections()
config = StrategyConfig.objects.get(account_id=acct_id)
```

同时添加 `from django.db import close_old_connections` 导入。


## ✅ HIGH-25: 移仓换月 Phase 2 失败后 PositionState 残留脏数据 — 已修复 (2026-05-22)

**文件**: [infrastructure/order_signals.py](../../backend/stock/infrastructure/order_signals.py#L723)

**问题描述**:
`execute_rollover_order` 中 Phase 1（平旧仓）成功后，Phase 2（开新仓）可能因行情、资金等原因失败。但 PositionState 未被重置，残留 `units>0`、`contract_total_position>0`、`direction!=0`，系统误以为还有持仓，阻止后续开仓。

**影响分析**:
- 移仓失败后该品种无法再次开仓
- 需人工修复数据库才能恢复交易
- 影响所有通过 `execute_rollover_order` 移仓的品种

**修复内容**:
Phase 1 平仓完成后立即重置 PositionState，无论 Phase 2 是否成功：

---

## ✅ HIGH-26: HVOB-MBI 白天启动引擎卡死在 night_or 阶段 — 已修复 (2026-05-25)

**文件**: [trading_engine.py](../../backend/hvob_mbi/trading_engine.py#L158-L173)

**问题描述**:
引擎固定从 `night_or` 阶段启动。若引擎在 9:00-21:00 之间启动（如进程崩溃重启、服务器重启），会卡在 `night_or` 直到 21:30 才前进，期间不做任何有用工作。

**影响分析**:
- 白天启动后需等待 8-12 小时才进入下一相位
- 错过日盘开盘区间跟踪，当天无法交易
- 进程看起来在运行但实际不处理行情数据

**修复内容**:
新增 `_init_phase()` 方法，按时间降序检查当前时刻设定正确相位：
- 21:30+ → night_breakout
- 21:00-21:30 → night_or
- 14:55-21:00 → done（提前退出）
- 9:30-14:55 → day_breakout
- 9:00-9:30 → gap_check
- 0:00-9:00 → night_breakout

```python
PositionState.objects.filter(id=position.id).update(**{
    'units': 0, 'contract_total_position': 0, 'direction': 0,
    'highest_close': None, 'lowest_close': None,
    'stop_loss_price': None, 'protect_cost_enabled': False,
    'open_date': None, 'cost_price': None, 'first_open_price': None,
    'latest_close_price': None, 'indicators': None,
    'h20_price': None, 'l20_price': None,
    'trend_info': None, 'is_rollover_needed': False,
})
```

---

## ✅ HIGH-27: HVOB 跳空检查 `_check_gap` NaN 漏检 — 已修复 (2026-05-26)

**文件**: [trading_engine.py:457](../../backend/hvob_mbi/trading_engine.py#L457)

**问题描述**:
`_check_gap()` 中 NaN 价格漏检，与 `_on_quote` 同样的问题：
```python
if quote is None or quote.last_price is None:
    continue
```
NaN 行情通过检查后，后续判断 `nan < or_['L']` 和 `nan > or_['H']` 均为 False（NaN 比较特性），打印"正常"但实际上无有效数据。同时该 NaN 价格被用于初始化日盘 OR 基线。

**影响分析**:
- 跳空检查打印"正常"误导日志
- 日盘 OR 基线可能被 NaN 污染
- gap_check 阶段（9:00-9:30）行情应已就绪，实际影响极低，但健壮性不足

**修复内容**: 追加 `math.isnan(quote.last_price)` 过滤。

---

## ✅ HIGH-28: HVOB `_check_restart` 精确分钟匹配可能漏触发 — 已修复 (2026-05-26)

**文件**: [trading_engine.py:267-276](../../backend/hvob_mbi/trading_engine.py#L267)

**问题描述**:
`_check_restart` 使用精确分钟匹配判断重启时间：
```python
if (now.hour == 8 and now.minute == 55):
```
`wait_update` 最长阻塞 30 秒（`deadline=time.time() + 30`）。如果循环恰好在 8:55:00 时处于 wait_update 阻塞中，直到 8:55:30 才返回，此时 `now.minute == 55` 已不成立，重启被漏过。

**影响分析**:
- TqSDK 连接每天最多错过 3 次定时重启
- 长时间运行后连接可能因累计问题（内存泄漏/网络抖动）退化
- 8:55 重启失败 → 9:00 日盘开始时连接可能不稳定
- 实际概率较低（1 秒窗口 + 30 秒阻塞 = ~3% / 次），但完全可避免

**修复内容**: 改为 ±1 分钟范围匹配：
```python
restart_hour_minutes = [(8, 55), (13, 25), (20, 55)]
now_total = now.hour * 60 + now.minute
in_window = any(h * 60 + m - 1 <= now_total <= h * 60 + m + 1 for h, m in restart_hour_minutes)
```

---

## ❌ HIGH-29: 两步开仓使用 `volume_short`/`volume_long` 记录错误持仓量 — 已修复 (2026-05-27)

**文件**: [infrastructure/order_execution.py:199-202](../../backend/stock/infrastructure/order_execution.py#L199)

**问题描述**:

两步开仓策略中，`execute_two_step_opening` 使用 `pos_after.volume_short`/`pos_after.volume_long` 记录实际成交手数：

```python
# 修复前
if direction == 1:
    actual_final_filled = pos_after.volume_long
else:
    actual_final_filled = pos_after.volume_short
```

`volume_short`/`volume_long` 反映的是**总持仓量**而非**净持仓量**。当第二步 TargetPosTask 因 `support_open_min_volume=True` 触发"反向开仓"（用开仓替代平仓来满足最小开仓限制），实际净持仓与总持仓不一致。

**实盘案例（CZCE.MA609，2026-05-27）**:

```
calculate_unit_lots → 4手/Unit，order_volume=4手
min_position=4，两步开仓: 先开4手，再平1手

第1步: TargetPosTask.set_target_volume(-4) → 开空4手
第2步: TargetPosTask(api, symbol, support_open_min_volume=True).set_target_volume(-3)
       → 调整量1手 < min_position(4)，TqSDK 不开平仓，而是"开多1手"
       → 净持仓 = -4 + 1 = -3（交易所显示3手空单，正确）
       → 但 volume_short = 4（空头总持仓未减少）

DB 记录: contract_total_position = volume_short = 4 ❌
交易所实际: 3手 ✅
```

**影响分析**:
- `contract_total_position` 多记 1 手，持仓管理页面显示与交易所不一致
- 加仓和止损计算依赖 `contract_total_position`，但加仓手数通过 `order_volume` 计算不受影响
- 止损平仓使用 TargetPosTask 设目标 0，不受 `contract_total_position` 影响
- 主要影响持仓记录准确性

**修复内容**: 在 `execute_two_step_opening()` 中，将 `volume_long`/`volume_short` 改为 `abs(pos_after.pos)`，使用净持仓作为实际成交手数：

```python
# 修复后
# 使用 net 净持仓而非 volume_long/volume_short，因为 support_open_min_volume=True 时
# TqSDK 可能用反向开仓代替平仓来满足最小开仓限制，导致 volume_long 或 volume_short
# 反映的是总持仓而非净持仓。
actual_final_filled = abs(pos_after.pos)
```

**验证方法**: 两步开仓成功后，打印日志对比 `pos.pos`（净持仓）和 `volume_short`/`volume_long`（总持仓），两者在 `support_open_min_volume=True` 触发反向开仓时会出现差异。
