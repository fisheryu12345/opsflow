# 🟡 MEDIUM 中优先级问题

> 代码质量、安全隐患、可维护性问题的修复建议。

---

## MEDIUM-01: 部分视图集在生产环境使用 AllowAny 权限

**涉及文件**:
- [performance.py:27/39/73/107/143/212/279/358](../backend/stock/views/performance.py)
- [closed_position.py:27](../backend/stock/views/closed_position.py)

**问题描述**:
多个 ViewSet 使用了 `permission_classes = [AllowAny]`，注释标注 "仅用于开发测试，生产环境请移除"。

**影响分析**:
- 只要知道 API 路径即可访问账户权益、平仓记录、绩效指标等敏感数据
- 无认证状态下可查询任意账户的盈亏数据
- 虽然注释提醒了生产环境需要更改，但不合规范

**修复方案**:
```python
# 改为使用默认认证或自定义权限
permission_classes = [IsAuthenticated]  # 或保留现有项目认证机制
```

---

## MEDIUM-02: StrategyConfigViewSet 缺少过滤/搜索/排序

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

**修复方案**: 取消注释并添加过滤字段:
```python
filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
filterset_fields = ['name']
search_fields = ['name']
ordering_fields = ['name', 'atr_period', 'entry_period']
```

---

## MEDIUM-03: Sortino 比率为 999.9999 极端值

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

**修复方案**:
```python
if downside_std == 0:
    sortino_ratio = None  # 或 Decimal('0')，表示无法计算
```

同时在前端做 null 值处理，显示 "N/A" 或 "--"。

---

## MEDIUM-04: 最大回撤持续时间从错误起点计算

**文件**: [core/performance.py:349](../backend/stock/core/performance.py#L349)（原 scheduler/performance_cal.py）

**问题描述**:
最大回撤持续时间从回撤开始日计算到回撤结束日，
但正确定义应为从**净值最高点**到**恢复至前高**的天数。

**影响分析**:
- 低估了实际的回撤持续时间
- 如果从峰值到回撤开始有较长时间，持续天数计算偏差更大

**修复方案**:
```python
# 记录峰值日期和回撤开始日期
# max_dd_duration = 恢复到峰值前高的日期 - 达到前峰值日期的日期
# 而非 回撤结束日 - 回撤开始日
```

---

## MEDIUM-05: 函数名拼写错误 check_breakout_singal

**文件**: [tasks_daily_close.py](../backend/stock/scheduler/tasks_daily_close.py)

**问题描述**:
函数名 `check_breakout_singal` 中 "singal" 应为 "signal"。

**影响分析**:
- 影响代码可读性和维护性
- 被多个位置引用，修改需要同步更新所有调用点
- 但属于纯拼写问题，不影响功能

**修复方案**: 重命名并更新所有引用:
```python
# 旧: check_breakout_singal
# 新: check_breakout_signal
```

---

## MEDIUM-06: 嵌套 transaction.atomic() 冗余

**文件**: [infrastructure/order_signals.py](../backend/stock/infrastructure/order_signals.py)（原 tasks_daily_open.py，已迁移）

**问题描述**:
在外层已有 `with transaction.atomic()` 的上下文中，内部又嵌套了同级别的 atomic 块。

**影响分析**:
- 内层 atomic 会创建 savepoint，虽不影响正确性但增加了不必要的数据库开销
- 每个 savepoint 在 MySQL 中对应一个临时表，嵌套层级过多可能有性能影响

**修复方案**: 移除内层冗余的 `with transaction.atomic()`，统一由外层管理。

---

## MEDIUM-07: 前端删除请求包含 data 参数

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

**修复方案**: 移除 `data` 参数:
```typescript
export function DelObj(id: DelReq) {
    return request({
        url: apiPrefix + id + '/',
        method: 'delete',
    });
}
```

---

## MEDIUM-08: 前端 CRUD 配置中模糊的字段命名

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

**修复方案**: 重命名为更语义化的名称如 `keyword_search` 或 `search_field`。

---

## MEDIUM-09: 开仓执行时 API 连接可能已失效

**文件**: [tasks_daily_open.py](../backend/stock/scheduler/tasks_daily_open.py)

**问题描述**:
开盘任务在处理多个信号时，长时间持有 TqApi 连接。前面的操作（如止损平仓）可能耗时较长，
导致后续信号执行时 API 连接已超时或断开。

**影响分析**:
- 中间某个信号执行失败后，后续所有信号都无法执行
- 特别是 ADD_ON 信号（最低优先级）经常因超时而无法执行
- 当前超时处理仅是打印错误，没有重试机制

**修复方案**:
1. 对每个信号或每组信号执行前检查 API 连接状态
2. 实现自动重连机制（在连接断开时重新创建 TqApi）
3. 信号执行顺序优化：耗时操作（如 ROLLOVER）放在最后

---

## MEDIUM-10: 合约管理搜索字段配置与实际差异

**文件**: [contracts/crud.tsx](../web/src/views/apps/contracts/crud.tsx)

**问题描述**:
前端合约管理页面在 `search` 区域的 `exchange` 字段配置了 `component.options` 引用 `exchangeOptions`，
但 `exchangeOptions` 在页面加载时异步加载，初始渲染时 options 可能为空数组，
导致搜索下拉框初始为空。

**影响分析**:
- 页面首次加载时交易所下拉框短暂空白
- 异步加载完成前用户无法使用交易所筛选

**修复方案**:
```typescript
// 方法1: 添加 v-loading 状态
// 方法2: 使用内置 dict 替代动态加载 options
// 方法3: 添加 fallback 静态数据
```
