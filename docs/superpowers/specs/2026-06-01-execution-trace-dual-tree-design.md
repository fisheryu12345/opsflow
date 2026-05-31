# 执行轨迹双树结构设计

> 日期: 2026-06-01
> 状态: 设计稿 (待评审)
> 关联: bk_sops 借鉴分析文档 (`backend/opsflow/doc/bk_sops.md`)

---

## 一、背景与目标

### 问题

OpsFlow 当前运行时状态追踪是扁平的：

- `FlowExecution.node_status` 记录 `{node_id: status_string}`，仅用于前端画布着色
- `OpsLog` 记录节点概要输出，但混在数据库表中，不适合存放完整原始数据
- 生产故障排查时，无法快速定位到具体节点的详细日志和完整执行轨迹
- 节点重试历史没有保留，无法回溯"第几次重试发生了什么"

### 目标

1. **双树结构** — 显式区分模板树（pipeline_tree，静态定义）和状态树（state_tree，运行时实例）
2. **节点独立日志** — 每个节点每次执行有独立的日志文件，生产排查时直接 `grep` 定位
3. **重试历史完整保留** — 每次重试作为独立 Trace 记录，可回溯全链路
4. **节点操作统一调度** — 参考 bk_sops `NodeCommandDispatcher` 模式，标准化节点操作接口
5. **OpsLog 保持现状** — 继续作为概要记录，与节点日志文件互补

### 与 bk_sops 的关系

| 维度 | bk_sops | OpsFlow (当前) | OpsFlow (升级后) |
|------|---------|---------------|-----------------|
| 状态追踪 | ERI 状态模型 (11 张表) | `node_status` JSONField | `node_status` + `state_tree` + `NodeExecutionTrace` |
| 重试策略 | `AutoRetryNodeStrategy` 模型 | 无 | `NodeExecutionTrace.retry_count` 追踪 |
| 节点操作 | `NodeCommandDispatcher` | 散落在 FlowEngine 中 | 统一 `NodeCommandDispatcher` |
| 日志 | 无标准化日志文件 | OpsLog 表 | OpsLog + JSON Lines 日志文件 |

---

## 二、数据模型

### 2.1 NodeExecutionTrace — 节点执行轨迹

```python
class NodeExecutionTrace(models.Model):
    """节点执行轨迹 — 每个节点每次执行的完整记录"""
    execution = models.ForeignKey(FlowExecution, on_delete=models.CASCADE, related_name='traces')
    node_id = models.CharField(max_length=200, verbose_name="节点ID")
    node_label = models.CharField(max_length=200, blank=True, verbose_name="节点名称")
    atom_type = models.CharField(max_length=64, blank=True, verbose_name="原子类型")
    node_type = models.CharField(max_length=64, blank=True, verbose_name="节点类型")

    # 状态轨迹（而非单一状态）：记录每次状态变更
    status = models.CharField(max_length=16, default='pending', verbose_name="当前状态")
    status_history = models.JSONField(default=list, verbose_name="状态变更历史")
    # [{"state": "running", "at": "2026-06-01T09:02:10"}, ...]

    # 时间轨迹
    entered_at = models.DateTimeField(null=True, blank=True, verbose_name="进入时间")
    exited_at = models.DateTimeField(null=True, blank=True, verbose_name="退出时间")
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name="执行耗时(ms)")

    # 执行数据
    inputs = models.JSONField(default=dict, verbose_name="输入参数")
    outputs = models.JSONField(default=dict, verbose_name="输出结果")
    error = models.TextField(blank=True, verbose_name="错误信息")

    # 重试信息
    retry_count = models.IntegerField(default=0, verbose_name="已重试次数")
    max_retries = models.IntegerField(default=0, verbose_name="最大重试次数")

    # 日志文件引用（快速跳转）
    log_file_path = models.CharField(max_length=500, blank=True, verbose_name="日志文件路径")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_node_trace'
        unique_together = [('execution', 'node_id', 'retry_count')]
        ordering = ['execution', 'entered_at']
```

**关键设计**:

- `unique_together = (execution, node_id, retry_count)` — 每次重试创建新记录，保留完整重试历史
- `status_history` — 记录完整状态变更序列（pending→running→failed→retrying→running→finished）
- `log_file_path` — 引用节点独立日志文件，前端可直接跳转

### 2.2 FlowExecution.state_tree — 状态树快照

在现有 `FlowExecution` 上新增字段：

```python
# FlowExecution 新增
state_tree = models.JSONField(default=dict, blank=True, verbose_name="状态树快照")
```

格式：

```json
{
  "node_1": {
    "state": "finished",
    "entered_at": "2026-06-01T09:02:10",
    "exited_at": "2026-06-01T09:02:15",
    "duration_ms": 5000,
    "error": "",
    "retry_count": 0
  },
  "node_2": {
    "state": "failed",
    "entered_at": "2026-06-01T09:02:16",
    "exited_at": "2026-06-01T09:02:20",
    "duration_ms": 4000,
    "error": "Connection timeout",
    "retry_count": 2
  }
}
```

### 2.3 数据关系

| 字段 | 用途 | 更新频率 | 前端使用场景 |
|------|------|---------|-------------|
| `node_status` | 轻量状态字典 | 每次状态变更 | MonitorCanvas 节点着色 |
| `state_tree` | 含时间/耗时/错误详情 | 每次状态变更 | 详情面板、排查分析 |
| `NodeExecutionTrace` | 完整轨迹 + 重试历史 | 每次状态变更 + 重试 | 轨迹 API 查询、历史回溯 |
| 节点日志文件 | 完整原始数据 | 增量追加 | 日志查看器、grep 定位 |

---

## 三、信号处理器升级

### 3.1 升级后流程

```
post_set_state 信号
  → _update_execution_node_status()     # node_status（不变）
  → _update_state_tree()                # 新增：同步更新 state_tree
  → _record_node_trace()                # 新增：写入 NodeExecutionTrace
  → _log_node_result()                  # OpsLog（不变）
  → _write_node_trace_log()             # 新增：写入节点独立日志文件
  → _notify_node_status()               # WS 推送（不变）
```

### 3.2 state_tree 增量更新

```python
def _update_state_tree(execution, node_id, to_state):
    """增量更新 state_tree，不覆盖已有字段"""
    STATUS_MAP = {
        states.FINISHED: "completed",
        states.FAILED: "failed",
        states.RUNNING: "running",
    }
    mapped = STATUS_MAP.get(to_state)
    if not mapped:
        return

    tree = dict(execution.state_tree or {})
    entry = dict(tree.get(node_id, {}))
    entry['state'] = mapped

    if mapped == 'running':
        entry['entered_at'] = timezone.now().isoformat()
    elif mapped in ('completed', 'failed'):
        entry['exited_at'] = timezone.now().isoformat()
        if entry.get('entered_at'):
            delta = (timezone.now() - datetime.fromisoformat(entry['entered_at']))
            entry['duration_ms'] = int(delta.total_seconds() * 1000)

    tree[node_id] = entry
    execution.state_tree = tree
    execution.save(update_fields=['state_tree'])
```

### 3.3 NodeExecutionTrace upsert 逻辑

```python
def _record_node_trace(execution, node_id, to_state, node_info=None):
    """创建或更新 NodeExecutionTrace 记录"""
    # 从 context 或 node_status 读取当前重试次数
    retry_count = _get_current_retry_count(execution, node_id)

    trace, created = NodeExecutionTrace.objects.get_or_create(
        execution=execution,
        node_id=node_id,
        retry_count=retry_count,
        defaults={
            'node_label': node_info.get('label', '') if node_info else '',
            'status': _map_state(to_state),
            'entered_at': timezone.now() if to_state == states.RUNNING else None,
            'inputs': _capture_inputs(execution, node_id),
        }
    )

    if not created:
        history = list(trace.status_history or [])
        history.append({'state': _map_state(to_state), 'at': timezone.now().isoformat()})
        trace.status_history = history
        trace.status = _map_state(to_state)

        if to_state in (states.FINISHED, states.FAILED):
            trace.exited_at = timezone.now()
            if trace.entered_at:
                trace.duration_ms = int(
                    (trace.exited_at - trace.entered_at).total_seconds() * 1000
                )
            trace.outputs = _capture_outputs(execution, node_id)

        trace.save()
```

---

## 四、节点日志文件系统

### 4.1 目录结构

```
{LOG_DIR}/opsflow/tasks/{execution_id}/
  ├── node_1.log       # 每个节点独立日志文件（JSON Lines）
  ├── node_2.log
  ├── execution.json   # 执行总览（所有节点索引 + 摘要）
  └── metadata.json    # 执行元数据（模板快照引用）
```

### 4.2 JSON Lines 格式

每行一条结构化 JSON，按事件类型分类：

```jsonl
{"timestamp":"2026-06-01T09:02:15.123","node_id":"node_1","event":"output","data":{"stdout":"Disk OK: 45% used","returncode":0}}
{"timestamp":"2026-06-01T09:02:20.456","node_id":"node_2","event":"error","data":{"stderr":"Connection timeout","error":"SSHException"}}
{"timestamp":"2026-06-01T09:02:30.789","node_id":"node_3","event":"tower","data":{"job_id":1234,"status":"running","progress":45}}
{"timestamp":"2026-06-01T09:02:10.000","node_id":"node_1","event":"state","data":{"from":"pending","to":"running"}}
```

事件类型：`state` | `output` | `error` | `tower` | `tower_event` | `retry`

### 4.3 NodeTraceLogger

```python
class NodeTraceLogger:
    """节点轨迹日志写入器 — 每个节点独立的 JSON Lines 日志文件"""

    def __init__(self, execution_id):
        self.log_dir = os.path.join(settings.LOG_DIR, 'opsflow', 'tasks', str(execution_id))

    def log(self, node_id, event, data):     # 通用写入
    def log_state(self, node_id, from_state, to_state):
    def log_output(self, node_id, outputs):
    def log_error(self, node_id, error, stderr=""):
    def log_tower(self, node_id, job_data):
    def read_log(self, node_id) -> list[dict]:
```

### 4.4 日志清理

通过 management command 或定时任务，清理 N 天前的日志目录。

---

## 五、NodeCommandDispatcher

### 5.1 架构

```
NodeCommandDispatcher
  ├── retry(node_id)         → 重试失败节点（自动创建新 Trace）
  ├── skip(node_id)          → 跳过失败节点
  ├── get_trace(node_id)     → 查询节点轨迹明细（含所有重试历史）
  ├── get_trace_log(node_id) → 读取节点日志文件内容
  └── get_state_tree()       → 获取完整状态树
```

### 5.2 与 FlowEngine 的关系

| FlowEngine (引擎层) | NodeCommandDispatcher (调度层) |
|---------------------|------------------------------|
| start/pause/resume/cancel | retry/skip/forced_fail |
| retry() / skip() 调用 bamboo-engine API | **调用** FlowEngine 同名方法 + **追加 Trace 记录** |
| 不关心操作日志 | 自动记录操作到 Trace + 日志文件 |
| 无返回值标准化 | `{result, message, data}` 标准化返回值 |

### 5.3 返回值格式

与 bk_sops `EngineAPIResult` 对齐：

```python
# 成功
{'result': True, 'message': '正在重试节点 node_1', 'data': {'node_id': 'node_1'}}
# 失败
{'result': False, 'message': '节点 node_1 不存在', 'data': None}
```

---

## 六、API 升级

### 6.1 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/opsflow/executions/{id}/traces/` | 轨迹列表（`?node_id=xxx` 过滤） |
| GET | `/api/opsflow/executions/{id}/trace_log/?node_id=x` | 读取节点日志文件 |

### 6.2 现有端点升级

| 方法 | 路径 | 变更 |
|------|------|------|
| POST | `/api/opsflow/executions/{id}/retry_node/` | 改用 Dispatcher，自动记录重试 Trace |
| POST | `/api/opsflow/executions/{id}/skip_node/` | 改用 Dispatcher，自动记录跳过 Trace |
| GET | `/api/opsflow/executions/{id}/` | Serializer 增加 `state_tree` + `trace_summary` 字段 |

### 6.3 Serializer

```python
class FlowExecutionDetailSerializer(FlowExecutionSerializer):
    trace_summary = SerializerMethodField()

    def get_trace_summary(self, obj):
        # 返回不含完整 outputs 的轨迹摘要
        return NodeExecutionTrace.objects.filter(execution=obj).values(
            'node_id', 'status', 'retry_count', 'duration_ms',
            'entered_at', 'exited_at', 'error'
        ).order_by('entered_at')
```

---

## 七、文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **修改** | `models.py` | 新增 `NodeExecutionTrace` 模型 + `FlowExecution.state_tree` 字段 |
| **修改** | `signals.py` | 新增 `_update_state_tree()` / `_record_node_trace()` / `_write_node_trace_log()` |
| **新增** | `core/trace_logger.py` | `NodeTraceLogger` 日志写入器 |
| **新增** | `core/node_dispatcher.py` | `NodeCommandDispatcher` 节点操作调度器 |
| **修改** | `serializers.py` | 新增 `NodeExecutionTraceSerializer` + `FlowExecutionDetailSerializer` |
| **修改** | `views/execution_views.py` | 新增 `traces`/`trace_log` Action + 升级 retry/skip |
| **修改** | `urls.py` | 无需变更（@action 自动注册） |
| **新增** | `tests/` 测试用例 | 模型/日志/Dispatcher/signals 测试 |
| **新增** | management command | `clean_node_trace_logs` 日志清理 |

---

## 八、测试策略

| 层级 | 测试目标 | 方法 |
|------|---------|------|
| 单元 | `NodeExecutionTrace` 模型约束 | `unique_together` 验证、状态历史追加 |
| 单元 | `NodeTraceLogger` 读写 | mock 文件操作、临时目录测试 |
| 单元 | `NodeCommandDispatcher` | mock FlowEngine，验证返回值格式 |
| 单元 | `_update_state_tree()` | 增量更新不覆盖已有字段 |
| 集成 | 完整执行流程 | TestExecutor 流程验证 state_tree + Trace + 日志文件 |
| 集成 | 重试场景 | 模拟失败→retry→验证新 Trace 记录 |

---

## 九、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 日志文件磁盘占用 | 长时间运行可能产生大量日志 | 清理策略（默认保留 30 天）、文件大小告警 |
| signals.py 性能 | 增加 3 个同步操作可能拖慢信号处理 | 日志文件写入有 try/except 降级，不抛异常 |
| 数据冗余 | node_status / state_tree / Trace 三份状态 | 各自职责明确，不互相替代 |
| 迁移现有执行 | 已有执行记录没有 state_tree/Trace | 向后兼容，旧数据读取时返回空值 |
