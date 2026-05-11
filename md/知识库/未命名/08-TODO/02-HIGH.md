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
