# 🟢 LOW 低优先级问题

> 优化建议、重构方向、非功能性改进。

---

## ❌ LOW-01: Performance_cal 使用 Pandas/Numpy 处理简单计算 — 暂无计划修复

> 当前 pandas/numpy 在性能计算中仅做简单运算，但替换为纯 Python 的收益有限（节省启动时间约 1-2 秒）。鉴于系统已稳定运行，重写为纯 Python 可能引入新 bug，决定保持现状。

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

## ❌ LOW-02: 回撤曲线全量数据在 Python 层计算 — 暂无计划修复

> 当前数据量级（1 年约 250 条快照）下全量加载性能可接受。引入缓存层会增加系统复杂度，且回撤曲线查询频率低（用户手动查看 Dashboard 时触发），无需优化。

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

## ❌ LOW-05: Redis 分布式锁 key 硬编码 — 暂无计划修复

> 当前锁 key 已优化为 `lock:open:{account.id}` 实现账户级隔离，INSTANCE_ID 命名空间隔离在生产环境单实例部署下无实际需求。硬编码 key 便于运维排查（直接通过 key 名可识别用途）。

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

---

## ✅ LOW-06 (TqSDK): execute_entry_order 中存在 dead code — 已修复 (2026-05-10)

**文件**: [infrastructure/order_signals.py:316](../backend/stock/infrastructure/order_signals.py#L316)

**问题描述**:
```python
pos_after = result['pos']
if pos_after is None:
    pos_after = api.get_position(signal.symbol)  # ← 永远不会执行到
```

`wait_for_target_position` 返回 `success=False` 时已在之前提前 return。`pos_after` 为 None 的路径实际不可达。

**影响**: 无运行时影响，但增加代码维护负担。

**修复内容**: 移除死代码，`if pos_after is None` 外层分支扁平化。

---

## ✅ LOW-07 (TqSDK): calculate_atr 每笔入场被重复调用 — 已修复 (2026-05-10)

**文件**:
- [infrastructure/order_signals.py:209](../backend/stock/infrastructure/order_signals.py#L209)（execute_entry_order）
- [core/atr.py:55](../backend/stock/core/atr.py#L55)（price_gap_protection 新增 atr 参数）
- [core/position_sizing.py:10](../backend/stock/core/position_sizing.py#L10)（calculate_unit_lots 新增 atr 参数）

**问题描述**:
`execute_entry_order` → `price_gap_protection(api,...)` 内部调用 `calculate_atr()`，随后 `calculate_unit_lots(api,...)` 内部又调用一次 `calculate_atr()`。同一品种同一周期的 ATR 被重复计算 2 次。

**影响**: 每次入场信号浪费一次 API K 线查询 + 计算开销。

**修复内容**:
1. `price_gap_protection` 新增可选参数 `atr=None`，传入时跳过内部计算
2. `calculate_unit_lots` 新增可选参数 `atr=None`，传入时跳过内部计算
3. `execute_entry_order` 预先计算 ATR 一次，同时传入两个函数

两项修改均向后兼容，已有调用方不受影响。

---

## ✅ LOW-08 (TqSDK): 交易日检查创建额外 TqApi 连接 — 已修复 (2026-05-10)

**文件**: [scheduler/tasks_daily_open.py](../backend/stock/scheduler/tasks_daily_open.py)

**问题描述**:
`job_daily_open_process` 先创建一个 TqApi 连接仅用于检查交易日，关闭后又在账户循环中重新创建连接。检查逻辑可复用账户循环的第一个 `api`。

**影响**: 每次开盘任务多创建和销毁一个 TqApi 连接（约 2-3 秒开销）。

**修复内容**:
1. 移除 `check_api = create_tqapi()` + `skip_if_not_trade_day(api=check_api)` 前置检查块
2. 账户循环内新增 `is_first_account` 布尔标记
3. 第一个账户的 `api` 创建后执行 `skip_if_not_trade_day(api=api)`，非交易日提前退出（finally 块自动释放连接）

---

## ✅ LOW-10: `is_trade_day` 异常时默认返回交易日 — 已修复 (2026-05-10)

**文件**: [infrastructure/trade_day.py:55](../backend/stock/infrastructure/trade_day.py#L55)

**问题描述**:
```python
except Exception as e:
    log_error(...)
    return True  # ← TqSDK API 异常时仍返回交易日
```

交易日历 API 调用失败时默认认为是交易日，非交易日也可能执行交易任务。

**修复内容**: `return True` → `return False`。API 异常时默认非交易日，跳过任务。管理员通过 ErrorLog 排查原因后手动重试。

---

## ✅ LOW-11: 非交易日提前返回时 API 二次关闭 — 已修复 (2026-05-11)

**文件**: [scheduler/tasks_daily_open.py:38](../backend/stock/scheduler/tasks_daily_open.py#L38)

**问题描述**:
非交易日路径先调用 `safe_close_api(api)` 关闭连接再 `return`，但 `finally` 块会再次调用 `safe_close_api(api)` 在已关闭的连接上。TqApi 二次 `close()` 会抛异常（被 `except: pass` 吞掉），虽功能无影响，但日志可能输出不必要的异常痕迹。

**修复内容**: 移除 `safe_close_api(api)` 调用，由 `finally` 块统一处理关闭。

---

## ✅ LOW-12: 交易账户管理页非管理员看到开关但操作会 403 — 已修复 (2026-05-11)

**文件**: [trading-account/index.vue](../../web/src/views/apps/trading-account/index.vue#L23)

**问题描述**:
`trading-account/index.vue` 中 `is_active` 开关对所有用户可见。非管理员用户点击时，PATCH 请求因 `IsAdminUserOrReadOnly` 权限被 403 拒绝，前端乐观更新滚回并弹出错误提示。

**修复方案**: 使用 `useUserInfo().userInfos.roles` 判断是否为 admin，非管理员只显示文本状态标签（激活/停用），管理员保留 Switch 开关。

---

## ✅ LOW-13: `TradingAccountSerializer.get_strategy_name` 使用 bare `except:` — 已修复 (2026-05-11)

**文件**: [serializers/serializers.py](../../backend/stock/serializers/serializers.py#L46)

**问题描述**:
```python
def get_strategy_name(self, obj):
    try:
        return obj.strategyconfig.name if obj.strategyconfig else '-'
    except:          # ← bare except 吞所有异常
        return '-'
```

bare `except` 会吞掉 `AttributeError`、`TypeError` 等编程错误，增加调试难度。

**修复方案**: 改为 `except StrategyConfig.DoesNotExist:`，仅捕获预期的 DoesNotExist 异常。

