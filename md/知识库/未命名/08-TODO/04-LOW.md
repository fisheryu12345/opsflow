# 🟢 LOW 低优先级问题

> 优化建议、重构方向、非功能性改进。

---

## LOW-01: Performance_cal 使用 Pandas/Numpy 处理简单计算

**文件**: [core/performance.py](../backend/stock/core/performance.py)（原 scheduler/performance_cal.py）

**问题描述**:
`performance_cal.py` 引入了 pandas 和 numpy，但实际只用于极简单的运算
（如列表均值、标准差），完全可以使用纯 Python + `statistics` 模块或
`Decimal` 数学运算替代。

**影响分析**:
- pandas/numpy 是非常重的依赖（占用约 100MB+ 安装空间）
- 对于 Web 服务来说，导入 pandas 会显著增加进程启动时间和内存占用
- 当前使用场景属于"用牛刀杀鸡"

**修复建议**:
```python
# 替代 numpy.mean
def mean(values):
    return sum(values) / len(values) if values else 0

# 替代 numpy.std  
def std(values):
    if len(values) < 2:
        return 0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5
```

---

## LOW-02: 回撤曲线全量数据在 Python 层计算

**文件**: [performance.py:300-326](../backend/stock/views/performance.py#L300-L326)

**问题描述**:
`DrawdownCurveView` 从数据库查询所有权益快照并加载到 Python 列表，然后逐行计算回撤。
当数据量较大时（1年 ≈ 250 条，5年 ≈ 1250 条），这种全量加载方式效率较低。

**影响分析**:
- 每次请求回撤曲线都需全表扫描并传输所有快照数据
- Django ORM 的 `values()` 返回的 QuerySet 虽然延迟加载，但最终仍会加载所有记录到内存
- 虽当前数据量级下影响不大，但考虑未来扩展

**优化建议**:
1. 按年分区查询：前端只请求某一年度的数据
2. 结果缓存：使用 Redis 或 Django Cache 缓存计算后的结果（TTL 1天）
3. 数据库层面计算峰值：使用窗口函数（PostgreSQL）或应用层+缓存

---

## ✅ LOW-03: 缺少类型注解和文档字符串 — 已修复 (2026-05-09)

**涉及文件**:
- [tasks_daily_close.py](../backend/stock/scheduler/tasks_daily_close.py) — 7 个函数
- [tasks_daily_open.py](../backend/stock/scheduler/tasks_daily_open.py) — 1 个函数

**问题描述**:
部分关键函数缺少类型注解或文档字符串，特别是 `tasks_daily_close.py` 和 `tasks_daily_open.py`
中的核心业务函数。

**影响分析**: 增加代码理解和维护成本，降低 IDE 智能提示效果。

**修复内容**:
- `check_breakout_signal` 添加完整参数注解 (`symbol: str`, `product_code: str`, `trend_factor: float`, `trend_label: str`, `breakout_info: dict`, `trade_type: str`) 和返回类型 (`-> bool`) 及文档字符串
- `check_exit_signals`, `check_rollover_signals`, `check_add_position_signals`, `update_all_positions_high_low_price`, `update_all_positions_stop_loss_price`, `job_daily_close_calculation` 全部添加 `-> None` 返回类型
- `job_daily_open_process` 添加 `-> None` 返回类型

---

## ✅ LOW-04: API 端点使用 ModelViewSet 暴露写操作 — 已修复 (2026-05-09)

**涉及文件**:
- [position.py](../backend/stock/views/position.py) — PositionStateViewSet
- [closed_position.py](../backend/stock/views/closed_position.py) — ClosedPositionRecordViewSet
- [trade_log.py](../backend/stock/views/trade_log.py) — TradeLogViewSet, ErrorLogViewSet

**问题描述**:
这些数据由系统自动生成/维护，前端页面也设置为只读/禁止编辑，
但后端 ViewSet 仍然继承了 `ModelViewSet`，保留了 create/update/delete 端点。

**影响分析**:
- 违反了 Command-Query 分离原则
- 虽然前端隐藏了编辑按钮，但通过 API 工具仍可直接调用写操作
- 存在误操作或数据被篡改的风险

**修复内容**:
- `PositionStateViewSet`: `ModelViewSet` → `ReadOnlyModelViewSet`
- `ClosedPositionRecordViewSet`: `ModelViewSet` → `ReadOnlyModelViewSet`
- `TradeLogViewSet`: `ModelViewSet` → `ReadOnlyModelViewSet`
- `ErrorLogViewSet`: `ModelViewSet` → `mixins.ListModelMixin + mixins.RetrieveModelMixin + mixins.DestroyModelMixin + GenericViewSet`（保留删除清理功能）

---

## LOW-05: Redis 分布式锁 key 硬编码

**文件**: [tasks_daily_open.py](../backend/stock/scheduler/tasks_daily_open.py)

**问题描述**:
Redis 分布式锁的 key 是直接硬编码的字符串 `"lock:open"`。

**影响分析**:
- 如果未来部署多个策略实例，锁 key 可能冲突
- 缺少命名空间隔离
- 运维时无法区分锁的来源

**优化建议**:
```python
import os
LOCK_KEY = f"lock:open:{os.environ.get('INSTANCE_ID', 'default')}"
```

或从配置文件中读取:
```python
from django.conf import settings
LOCK_KEY = getattr(settings, 'REDIS_LOCK_OPEN_KEY', 'lock:open')
```
