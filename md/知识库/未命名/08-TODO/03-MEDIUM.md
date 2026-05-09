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
