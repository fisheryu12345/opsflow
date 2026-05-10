# 🟡 MEDIUM 中优先级问题

> 代码质量、安全隐患、可维护性问题的修复建议。

---

## ✅ MEDIUM-01: 部分视图集在生产环境使用 AllowAny 权限 — 已修复 (2026-05-09)

**涉及文件**:
- [performance.py](../backend/stock/views/performance.py) — 8 处 `AllowAny` → `IsAuthenticated`
- [closed_position.py](../backend/stock/views/closed_position.py) — 1 处 `AllowAny` → `IsAuthenticated`

**问题描述**:
多个 ViewSet 使用了 `permission_classes = [AllowAny]`，注释标注 "仅用于开发测试，生产环境请移除"。

**影响分析**:
- 只要知道 API 路径即可访问账户权益、平仓记录、绩效指标等敏感数据
- 无认证状态下可查询任意账户的盈亏数据
- 虽然注释提醒了生产环境需要更改，但不合规范

**修复内容**:
- `performance.py`: 所有 8 个 ViewSet 的 `AllowAny` 改为 `IsAuthenticated`
- `closed_position.py`: 1 处 `AllowAny` 改为 `IsAuthenticated`
- 移除 `# ⚠️` 注释

---

## ✅ MEDIUM-02: StrategyConfigViewSet 缺少过滤/搜索/排序 — 已修复 (2026-05-09)

**文件**: [strategyconfig.py:17](../backend/stock/views/strategyconfig.py#L17)

**问题描述**:
```python
class StrategyConfigViewSet(viewsets.ModelViewSet):
    queryset = StrategyConfig.objects.all()
    serializer_class = StrategyConfigSerializer
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]  ← 被注释
```

**影响分析**:
- 策略配置列表不支持按名称搜索
- 不支持按任何字段排序
- 当配置条目增多时（>20条），前端无法筛选检索

**修复内容**: 取消注释并添加过滤字段:
```python
filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
filterset_fields = ['product_code']
search_fields = ['name']
ordering_fields = ['name']
```

---

## ✅ MEDIUM-03: Sortino 比率为 999.9999 极端值 — 已修复 (2026-05-09)

**文件**: [core/performance.py:194](../backend/stock/core/performance.py#L194)（原 scheduler/performance_cal.py）

**问题描述**:
```python
if downside_std == 0:
    sortino_ratio = Decimal('999.9999')  # 无下行风险时的极端值
```

**影响分析**:
- 刚开仓或数据不足时，下行标准差为 0 的概率很高
- 999.9999 的极端值严重影响 Dashboard 展示
- 雷达图的坐标轴会被极端值拉伸，其他指标不可见

**修复内容**: 极端值改为 None，Dashboard 显示 "--"。
```python
# 修复后
if downside_std == 0:
    sortino_ratio = None
# 同时修复同文件的 profit_loss_ratio 极端值 Decimal('999.99') → None
```

---

## ✅ MEDIUM-04: 最大回撤持续时间从错误起点计算 — 已修复 (2026-05-09)

**文件**: [core/performance.py:349](../backend/stock/core/performance.py#L349)（原 scheduler/performance_cal.py）

**问题描述**:
最大回撤持续时间从回撤开始日计算到回撤结束日，
但正确定义应为从**净值最高点**到**恢复至前高**的天数。

**影响分析**:
- 低估了实际的回撤持续时间
- 如果从峰值到回撤开始有较长时间，持续天数计算偏差更大

**修复内容**: 改用 (trade_date, balance) 元组遍历，追踪 drawdown_start_date，在 equity 恢复至峰值时计算完整 peak→recovery 天数。同时处理数据末尾仍在回撤中的情况。

---

## ✅ MEDIUM-05: 函数名拼写错误 check_breakout_singal — 已修复 (2026-05-09)

**文件**: [tasks_daily_close.py](../backend/stock/scheduler/tasks_daily_close.py)

**问题描述**:
函数名 `check_breakout_singal` 中 "singal" 应为 "signal"。

**影响分析**:
- 影响代码可读性和维护性
- 被多个位置引用，修改需要同步更新所有调用点
- 但属于纯拼写问题，不影响功能

**修复内容**: 函数定义 + 内部引用 + 调用点共 3 处全部重命名为 `check_breakout_signal`。

---

## ✅ MEDIUM-06: 嵌套 transaction.atomic() 冗余 — 已修复 (代码重构后自然解决)

**文件**: [infrastructure/order_signals.py](../backend/stock/infrastructure/order_signals.py)（原 tasks_daily_open.py，已迁移）

**问题描述**:
在外层已有 `with transaction.atomic()` 的上下文中，内部又嵌套了同级别的 atomic 块。

**影响分析**:
- 内层 atomic 会创建 savepoint，虽不影响正确性但增加了不必要的数据库开销
- 每个 savepoint 在 MySQL 中对应一个临时表，嵌套层级过多可能有性能影响

**修复说明**: `order_signals.py` 重构后各函数独立管理事务，`process_signals_by_type` 外层无 atomic 包裹，不再有嵌套问题。

---

## ✅ MEDIUM-07: 前端删除请求包含 data 参数 — 已修复 (前端重写后自然解决)

**文件**: [closed-position/api.ts:40](../web/src/views/apps/closed-position/api.ts#L40)

**问题描述**:
```typescript
export function DelObj(id: DelReq) {
    return request({
        url: apiPrefix + id + '/',
        method: 'delete',
        data: { id },  // ← DRF DELETE 请求不支持 body
    });
}
```

**影响分析**: 某些 HTTP 代理或浏览器可能丢弃 DELETE 请求的 body。DRF 的 `destroy` 方法不从 request.data 读取参数，所以 `data: { id }` 实际无效。

**修复说明**: 交易页面全面重写为 Vue3 Composition API 后，`api.ts` 已替换为仅含 `GetList` 的新版本，不再有 `DelObj`/DELETE 请求。

---

## ✅ MEDIUM-08: 前端 CRUD 配置中模糊的字段命名 — 已修复 (前端重写后自然解决)

**文件**: 多个前端 CRUD 文件（position/crud.tsx, closed-position/crud.tsx 等）

**问题描述**:
搜索字段的 key 被命名为 `search`，与 CRUD 框架的搜索功能语义重叠：
```typescript
columns: {
    search: {     // ← 这是搜索字段的 column key，不是搜索配置
        title: '关键词搜索',
        search: { // ← 这是真正的搜索配置
            show: true,
        },
    },
}
```

**影响分析**: 阅读代码时容易混淆 "search" 是指搜索字段还是搜索配置，增加维护成本。

**修复说明**: 所有交易页面 CRUD 已被 Vue3 Composition API 重写，`crud.tsx` 文件已删除，该问题不再存在。

---

## ✅ MEDIUM-09: 开仓执行时 API 连接可能已失效 — 已修复 (2026-05-09)

**文件**: [tasks_daily_open.py](../backend/stock/scheduler/tasks_daily_open.py)

**问题描述**:
开盘任务在处理多个信号时，长时间持有 TqApi 连接。前面的操作（如止损平仓）可能耗时较长，
导致后续信号执行时 API 连接已超时或断开。

**影响分析**:
- 中间某个信号执行失败后，后续所有信号都无法执行
- 特别是 ADD_ON 信号（最低优先级）经常因超时而无法执行
- 当前超时处理仅是打印错误，没有重试机制

**修复内容**:
1. `tqapi.py` 新增 `is_api_connected()`（轻量级连接健康检查）和 `ensure_api_connected()`（断开自动重连）
2. `order_signals.py` `process_signals_by_type()` 处理前检查连接，断开时跳过并记录日志
3. `tasks_daily_open.py` 各信号批次间调用 `ensure_api_connected()`，断开时自动重连

---

## ✅ MEDIUM-10: 合约管理搜索字段配置与实际差异 — 已修复 (前端重写后自然解决)

**文件**: [contracts/crud.tsx](../web/src/views/apps/contracts/crud.tsx)

**问题描述**:
前端合约管理页面在 `search` 区域的 `exchange` 字段配置了 `component.options` 引用 `exchangeOptions`，
但 `exchangeOptions` 在页面加载时异步加载，初始渲染时 options 可能为空数组，
导致搜索下拉框初始为空。

**影响分析**:
- 页面首次加载时交易所下拉框短暂空白
- 异步加载完成前用户无法使用交易所筛选

**修复说明**: FastCRUD 已被 Vue3 自定义组件替代，该问题不再存在。

---

## ✅ MEDIUM-11: 移仓换月 K线同步使用连续合约但指标计算使用实际合约 — 已修复 (2026-05-10)

**文件**: [infrastructure/contract_sync.py:196](../backend/stock/infrastructure/contract_sync.py#L196), [core/indicators.py:83](../backend/stock/core/indicators.py#L83)

**问题描述**:
`sync_kline_data_from_tqsdk` 使用连续合约 `KQ.m@{exchange}.{product_code}` 获取 K 线数据，而 `calculate_indicators` 使用 `FullContractList.symbol` 调用 `api.get_kline_serial()`。两者在临近交割月时的 K 线数据会产生显著差异。

**影响分析**:
- KlineData 表中存储的是连续合约数据（前端的图表展示基于此）
- 策略指标计算使用的是实际合约数据
- 两者在换月前后出现偏离，导致策略信号与图表展示不匹配

**修复内容**:
1. symbol 格式统一 (2026-05-10):
   - `contract_sync.py` 删除去掉交易所前缀的代码，`underlying_symbol` 裸代码自动补前缀
   - `FullContractList.symbol` 存储完整格式如 `SHFE.rb2510`
   - 新建 `fix_symbol_format` 管理命令更新存量数据
   - 所有 TqSDK API 调用现在使用正确格式

2. KlineData 数据源统一 (2026-05-10):
   - `sync_kline_data_from_tqsdk` 改用 `contract.symbol`（实际合约）代替 `KQ.m@{exchange}.{product_code}`（连续合约）获取 K 线
   - KlineData 与 `calculate_indicators` 使用同一数据源，不再有偏离
   - 前端 K 线图与策略指标所见一致

---

## ✅ MEDIUM-12: 跳空保护对多空方向逻辑相同 — 过于保守 — 已修复 (2026-05-10)

**文件**: [core/atr.py:73-92](../backend/stock/core/atr.py#L73)

**问题描述**:
`price_gap_protection` 中 `direction == 1` 和 `direction == -1` 分支执行完全相同的逻辑 — 都检查 `abs(gap) > threshold`。但正确的逻辑应是：
- 多头入场：跳空高开（gap up）危险 — 买入价过高
- 空头入场：跳空低开（gap down）危险 — 卖出价过低

**影响分析**: 跳空高开会同时阻止多头和空头开仓，过于保守；在跳空低开时应该阻止空头而非多头。

**修复内容**:
1. 多头方向：计算 `gap_up = (latest_price - pre_close) / atr`，仅 `gap_up > threshold` 时拦截（跳空高开买入太贵）
2. 空头方向：计算 `gap_down = (pre_close - latest_price) / atr`，仅 `gap_down > threshold` 时拦截（跳空低开卖出太便宜）
3. 反向跳空（多头遇低开、空头遇高开）视为有利，不拦截
4. 日志信息区分多空，明确标注拦截原因

---

## ✅ MEDIUM-13: 合约同步未重置 `is_rollover_needed` 状态 — 已修复 (2026-05-10)

**文件**: [infrastructure/contract_sync.py:117-126](../backend/stock/infrastructure/contract_sync.py#L117)

**问题描述**:
当 `units == 0`（持仓已平）时，`sync_contract_list_from_tqsdk` 更新 symbol 但未将 `is_rollover_needed` 重置为 `False`。如果之前有未执行的移仓标记，该标记会残留。当同品种新开仓后，`is_rollover_needed=True` 仍存在，导致触发虚假的移仓检查。

**修复内容**: `units=0` 的更新追加 `is_rollover_needed=False`。

---

## ✅ MEDIUM-14: Redis 分布式锁超时可能不足 — 已修复 (2026-05-10)

**文件**: [utils/redis_lock.py](../backend/stock/utils/redis_lock.py)

**问题描述**:
`redis.set(lock_key, 'true', nx=True, ex=600)` 设置 600 秒（10 分钟）超时。如果某个账户处理多个信号类型时超时（如 `wait_for_target_position` 对每个信号阻塞 60 秒），锁自动释放后另一个调度实例可能开始同时处理同一账户的信号。

**影响分析**: 锁超时释放后，另一个调度实例可能开始处理同一账户，导致信号重复执行或数据竞争。

**修复内容**:
1. 新建 `utils/redis_lock.py`：提供带自动续期的 Redis 分布式锁上下文管理器 `redis_lock()`
   - 短 TTL（默认 30s），进程崩溃后锁快速自动释放
   - 后台 daemon 线程每 15s 续期一次，长任务不超时
   - `LockAcquisitionError` 异常用于调用方区分"获取锁失败"和"业务异常"
2. 三个 APScheduler 入口全部改用新锁：
   - `tasks_daily_open.py`：`lock:open:{account.id}`（每账户独立锁）— 替换原 `ex=600` 直写模式
   - `tasks_daily_close.py`：`lock:daily_close`（全局锁）— 替换原 `ex=900` 直写模式
   - `tasks_exit_before_close.py`：`lock:exit_before_close`（全局锁）— 替换原 `ex=600` 直写模式
3. `tasks_daily_open.py` 增加外层 `try/finally` 确保 `LockAcquisitionError` 时 `safe_close_api(api)` 仍被执行

---

## ✅ MEDIUM-15: 夜盘交易日期归属问题 — 已修复 (重构后自然解决)

**涉及文件**: [scheduler/scheduler.py:71](../backend/stock/scheduler/scheduler.py#L71)（已移除）

**问题描述**:
夜盘（21:02）使用 `date.today()` 记录信号日期。但中国期货市场夜盘通常属于下一个交易日（如周五夜盘属于下周一的交易日）。可能导致信号日期记录错误，影响交易日历判断。

**修复说明**: 原 `scheduler/scheduler.py` 已在重构中移除，`tasks_daily_open.py` 中虽保留 `datetime.now().date()`，但 `current_date` 当前为死参数（仅传入 `send_open_report` 但函数体内未使用），实际无影响。

---

## ✅ MEDIUM-16 (前端): K线图快速切换合约存在竞态条件 — 已修复 (2026-05-10)

**文件**: [useKline.ts:267-314](../web/src/views/apps/kline/useKline.ts#L267)

**问题描述**:
快速切换品种时，`fetchData` 为异步且无取消机制或过期响应保护。前一个品种的响应若晚于后一个到达，会覆盖 `klineList` 和 `tradeMarkers` 为旧数据，图表展示错误的 K 线。

**修复内容**:
1. 新增 `fetchSeq` 计数器，每次 `fetchData()` 调用时 `++fetchSeq` 标记当前请求
2. `const seq = ++fetchSeq` 记录本次请求序号
3. API 响应到达后检查 `if (seq !== fetchSeq) return` — 过期响应被丢弃
4. `finally` 中仅最新请求设置 `loading.value = false`
5. `nextTick` 后再次检查序号，防止 DOM 更新期间品种已切换

---

## ✅ MEDIUM-17 (前端): 持仓表 `unrealized_pnl` 排序字段不存在 — 已修复 (2026-05-10)

**文件**: [position/index.vue:42](../web/src/views/apps/position/index.vue#L42)

**问题描述**:
表格列声明 `prop="unrealized_pnl"`，但 `PositionRecord` 接口没有该字段。`sortable="custom"` 时 Element Plus 尝试访问 `row.unrealized_pnl` 得到 `undefined`，排序功能失效。

**修复内容**: 添加 `@sort-change` 事件处理，按 `calcUnrealizedPnl(row)` 的计算结果对当前页数据排序。

---

## ✅ MEDIUM-18 (前端): 交易日志缺少账户过滤 — 已修复 (2026-05-10)

**文件**: [tradelog/useTradeLog.ts:44](../web/src/views/apps/tradelog/useTradeLog.ts#L44)

**问题描述**:
`useTradeLog` 的 watcher 未包含 `accountStore.currentAccountId`，API 请求也不带 `account` 参数。切换账户后交易日志仍显示全部数据，与其他页面的行为不一致。

**修复内容**:
1. 导入 `useAccountStore`，创建 `accountStore` 实例
2. API 请求参数中添加 `params.account = accountStore.currentAccountId`
3. watcher 添加 `() => accountStore.currentAccountId` 依赖，切换账户自动刷新

---

## ✅ MEDIUM-19 (前端): 账户合约管理初始化重复请求 API — 已修复 (2026-05-10)

**文件**: [account-contract/useAccountContract.ts:117-137](../web/src/views/apps/account-contract/useAccountContract.ts#L117)

**问题描述**:
`onMounted` 中的 `init()` 显式调用 `fetchData()`，同时 `watch(currentAccountId)` 也在账户加载后触发 `fetchData()`，导致初始化时发出两次完全相同的 HTTP 请求。

**修复内容**:
1. 移除 `init()` 函数及其显式 `fetchData()` 调用
2. watcher 添加 `{ immediate: true }`，初始化时自动触发一次数据加载
3. `onMounted` 只负责账户加载，不负责数据获取（职责分离）
4. 修复后：无论账户是否已加载，始终只发一次 API 请求

---

## ✅ MEDIUM-20 (前端): 路由生成对多角色用户产生重复条目 — 已修复 (2026-05-10)

**文件**: [router/frontEnd.ts:83-97](../web/src/router/frontEnd.ts#L83)

**问题描述**:
`setFilterRoute` 中 `filterRoute.push({ ...route })` 为每个匹配角色创建浅拷贝。如果一个路由匹配多个角色（如 `roles: ['admin', 'common']`），同一路由会重复添加，导致 `router.addRoute` 重复注册并产生 Vue Router 警告。

**修复内容**:
1. 嵌套 `forEach` 改为 `route.meta.roles.some(metaRole => userRoles.includes(metaRole))`
2. 每个路由最多被添加一次，无论用户拥有多少个匹配角色
3. 同时缓存 `userInfos.value.roles` 到局部变量 `userRoles`，减少重复读取
