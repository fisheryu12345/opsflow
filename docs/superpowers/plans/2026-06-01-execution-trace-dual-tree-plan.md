# Execution Trace Dual Tree — Implementation Plan

**Goal:** 实现执行轨迹双树结构，包括 `NodeExecutionTrace` 模型、`state_tree` 快照、节点独立日志文件、`NodeCommandDispatcher` 节点操作调度层。

**Spec:** [2026-06-01-execution-trace-dual-tree-design.md](../specs/2026-06-01-execution-trace-dual-tree-design.md)

**Architecture:** 在现有 OpsFlow 架构上增量叠加，不修改现有代码的核心逻辑。所有新增功能通过 signals.py 扩展 + 新文件实现。

---

## File Map

```
backend/opsflow/
├── models.py                          # 修改: +NodeExecutionTrace, +FlowExecution.state_tree
├── signals.py                         # 修改: +_update_state_tree, +_record_node_trace, +_write_node_trace_log
├── serializers.py                     # 修改: +NodeExecutionTraceSerializer, +FlowExecutionDetailSerializer
├── views/execution_views.py           # 修改: +traces/trace_log actions, retry/skip 升级
│
├── core/
│   ├── trace_logger.py                # 新增: NodeTraceLogger 日志写入器
│   └── node_dispatcher.py             # 新增: NodeCommandDispatcher 节点操作调度器
│
├── management/
│   └── commands/
│       └── clean_node_trace_logs.py   # 新增: 日志清理管理命令
│
└── tests/
    └── test_trace.py                  # 新增: 轨迹双树测试用例
```

---

### Task 1: 模型扩展

**Files:**
- Modify: `backend/opsflow/models.py`

- [ ] **Step 1: 添加 NodeExecutionTrace 模型**

  在 `models.py` 末尾添加新模型，`db_table='ops_node_trace'`，`unique_together = [('execution', 'node_id', 'retry_count')]`。

  ```python
  class NodeExecutionTrace(models.Model):
      execution = models.ForeignKey(FlowExecution, on_delete=models.CASCADE, related_name='traces')
      node_id = models.CharField(max_length=200, verbose_name="节点ID")
      node_label = models.CharField(max_length=200, blank=True)
      atom_type = models.CharField(max_length=64, blank=True)
      node_type = models.CharField(max_length=64, blank=True)
      status = models.CharField(max_length=16, default='pending')
      status_history = models.JSONField(default=list)
      entered_at = models.DateTimeField(null=True, blank=True)
      exited_at = models.DateTimeField(null=True, blank=True)
      duration_ms = models.IntegerField(null=True, blank=True)
      inputs = models.JSONField(default=dict)
      outputs = models.JSONField(default=dict)
      error = models.TextField(blank=True)
      retry_count = models.IntegerField(default=0)
      max_retries = models.IntegerField(default=0)
      log_file_path = models.CharField(max_length=500, blank=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)

      class Meta:
          db_table = 'ops_node_trace'
          unique_together = [('execution', 'node_id', 'retry_count')]
          ordering = ['execution', 'entered_at']
  ```

- [ ] **Step 2: FlowExecution 添加 state_tree 字段**

  ```python
  # FlowExecution 类中新增
  state_tree = models.JSONField(default=dict, blank=True, verbose_name="状态树快照")
  ```

- [ ] **Step 3: 生成并执行 migration**

  ```bash
  python manage.py makemigrations opsflow
  python manage.py migrate opsflow
  ```

---

### Task 2: NodeTraceLogger — 日志写入器

**Files:**
- Create: `backend/opsflow/core/trace_logger.py`

- [ ] **Step 1: 实现 NodeTraceLogger 类**

  封装 JSON Lines 日志文件的写入和读取，包含：
  - `__init__(self, execution_id)` — 创建日志目录
  - `log(node_id, event, data)` — 通用写入（核心方法）
  - `log_state(node_id, from_state, to_state)` — 状态变更事件
  - `log_output(node_id, outputs)` — 执行输出事件
  - `log_error(node_id, error, stderr)` — 错误事件
  - `log_tower(node_id, job_data)` — Tower 作业事件
  - `log_tower_event(node_id, event_data)` — Tower 详细事件
  - `log_retry(node_id, retry_count, reason)` — 重试事件
  - `read_log(node_id) -> list[dict]` — 读取并解析日志文件
  - `write_metadata(metadata)` — 写入执行元数据（仅创建时一次）

  日志路径: `{settings.LOG_DIR}/opsflow/tasks/{execution_id}/{node_id}.log`

  格式: 每行一条 `{"timestamp": "...", "node_id": "...", "event": "...", "data": {...}}`

- [ ] **Step 2: 异常处理**

  所有文件操作用 try/except OSError 包裹，仅记录 warning 不抛异常，不影响主流程。

---

### Task 3: signals.py 扩展

**Files:**
- Modify: `backend/opsflow/signals.py`

- [ ] **Step 1: 新增 `_update_state_tree()`**

  ```python
  def _update_state_tree(execution, node_id, to_state):
      """增量更新 FlowExecution.state_tree"""
      STATUS_MAP = {states.FINISHED: "completed", states.FAILED: "failed", states.RUNNING: "running"}
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
              delta = timezone.now() - datetime.fromisoformat(entry['entered_at'])
              entry['duration_ms'] = int(delta.total_seconds() * 1000)
      if mapped == 'failed':
          # 从 context 或 outputs 提取错误信息
          entry['error'] = _get_node_error(execution, node_id)
      tree[node_id] = entry
      execution.state_tree = tree
      execution.save(update_fields=['state_tree'])
  ```

- [ ] **Step 2: 新增 `_record_node_trace()`**

  在 `on_post_set_state` 处理器中，子节点状态变更时调用。
  - `get_or_create` 以 `(execution, node_id, retry_count)` 为键
  - created=True → 首次进入，设置 inputs/entered_at
  - created=False → 追加 status_history，终态时计算 duration_ms/outputs

- [ ] **Step 3: 新增 `_write_node_trace_log()`**

  调用 `NodeTraceLogger` 写入 output/error 事件，并更新 `NodeExecutionTrace.log_file_path`。

- [ ] **Step 4: 集成到 `on_post_set_state` 信号处理器**

  在现有 `on_post_set_state` 中，子节点分支末尾追加调用：
  ```python
  if node_id != root_id:
      _update_execution_node_status(execution, node_id, to_state)
      _update_state_tree(execution, node_id, to_state)        # 新增
      _record_node_trace(execution, node_id, to_state)         # 新增
      if to_state in (states.FINISHED, states.FAILED):
          _log_node_result(execution, node_id, ...)
          _write_node_trace_log(execution, node_id, ...)       # 新增
          _notify_node_status(...)
  ```

- [ ] **Step 5: `_get_current_retry_count()` 辅助函数**

  从 FlowEngine 的 context 或现有 Trace 记录推断当前重试次数。

- [ ] **Step 6: `_capture_inputs/outputs()` 辅助函数**

  通过 `get_execution_data_outputs()` 框架 API 获取节点数据。

---

### Task 4: NodeCommandDispatcher

**Files:**
- Create: `backend/opsflow/core/node_dispatcher.py`

- [ ] **Step 1: 实现 NodeCommandDispatcher 类**

  ```python
  class NodeCommandDispatcher:
      def __init__(self, execution):
          self.execution = execution
          self.engine = FlowEngine(execution)

      def retry(self, node_id, operator=""):
          # 1. 从现有 Trace 获取 retry_count
          # 2. 创建新 Trace 记录 (retry_count+1, status=retrying)
          # 3. 调用 NodeTraceLogger.log_retry()
          # 4. 调用 self.engine.retry(node_id)
          # 5. 返回标准化结果

      def skip(self, node_id, operator=""):
          # 1. 调用 self.engine.skip(node_id)
          # 2. 返回标准化结果

      def get_trace(self, node_id):
          # 查询 (execution, node_id) 所有 retry_count 的记录

      def get_trace_log(self, node_id):
          # 从 NodeExecutionTrace.log_file_path 读取文件

      def get_state_tree(self):
          # 返回 self.execution.state_tree
  ```

- [ ] **Step 2: 返回值标准化**

  所有方法返回 `{"result": bool, "message": str, "data": any}` 格式。

---

### Task 5: Serializer 升级

**Files:**
- Modify: `backend/opsflow/serializers.py`

- [ ] **Step 1: 新增 NodeExecutionTraceSerializer**

  `exclude = ['execution']`，其余字段自动映射。

- [ ] **Step 2: 新增 FlowExecutionDetailSerializer**

  继承 `FlowExecutionSerializer`，追加 `state_tree` 字段和 `trace_summary` SerializerMethodField。

  ```python
  class FlowExecutionDetailSerializer(FlowExecutionSerializer):
      trace_summary = serializers.SerializerMethodField()

      class Meta(FlowExecutionSerializer.Meta):
          fields = FlowExecutionSerializer.Meta.fields + ['state_tree', 'trace_summary']

      def get_trace_summary(self, obj):
          return NodeExecutionTrace.objects.filter(execution=obj).values(
              'node_id', 'status', 'retry_count', 'duration_ms',
              'entered_at', 'exited_at', 'error'
          ).order_by('entered_at')
  ```

- [ ] **Step 3: 更新 ViewSet 的 serializer_class**

  `FlowExecutionViewSet` 使用 `FlowExecutionDetailSerializer` 作为详情序列化器（可选：覆写 `get_serializer_class` 区分 list/detail）。

---

### Task 6: API 端点升级

**Files:**
- Modify: `backend/opsflow/views/execution_views.py`

- [ ] **Step 1: 新增 `traces` Action**

  ```python
  @action(detail=True, methods=['get'])
  def traces(self, request, pk=None):
      """获取节点轨迹列表，支持 ?node_id=xxx 过滤"""
      execution = self.get_object()
      node_id = request.query_params.get('node_id')
      qs = NodeExecutionTrace.objects.filter(execution=execution)
      if node_id:
          qs = qs.filter(node_id=node_id)
      qs = qs.order_by('entered_at')
      serializer = NodeExecutionTraceSerializer(qs, many=True)
      return Response({
          'code': 2000, 'msg': 'success',
          'data': {'state_tree': execution.state_tree or {}, 'traces': serializer.data},
      })
  ```

- [ ] **Step 2: 新增 `trace_log` Action**

  ```python
  @action(detail=True, methods=['get'])
  def trace_log(self, request, pk=None):
      """读取节点日志文件内容"""
      node_id = request.query_params.get('node_id')
      if not node_id:
          return Response({'code': 4000, 'msg': 'node_id required'})
      dispatcher = NodeCommandDispatcher(self.get_object())
      result = dispatcher.get_trace_log(node_id)
      if not result['result']:
          return Response({'code': 4000, 'msg': result['message']})
      return Response({'code': 2000, 'msg': 'success', 'data': result['data']})
  ```

- [ ] **Step 3: 升级 `retry_node` Action**

  改用 `NodeCommandDispatcher` 替代直接调用 `FlowEngine.retry()`。

- [ ] **Step 4: 升级 `skip_node` Action**

  改用 `NodeCommandDispatcher` 替代直接调用 `FlowEngine.skip()`。

---

### Task 7: 日志清理管理命令

**Files:**
- Create: `backend/opsflow/management/commands/clean_node_trace_logs.py`

- [ ] **Step 1: 实现 CleanNodeTraceLogs 命令**

  ```python
  class Command(BaseCommand):
      help = '清理 N 天前的节点轨迹日志文件'
      
      def add_arguments(self, parser):
          parser.add_argument('--days', type=int, default=30, help='保留天数')
      
      def handle(self, *args, **options):
          days = options['days']
          threshold = timezone.now() - timedelta(days=days)
          log_root = os.path.join(settings.LOG_DIR, 'opsflow', 'tasks')
          if not os.path.exists(log_root):
              return
          count = 0
          for exec_dir in os.listdir(log_root):
              dir_path = os.path.join(log_root, exec_dir)
              mtime = datetime.fromtimestamp(os.path.getmtime(dir_path))
              if mtime < threshold:
                  shutil.rmtree(dir_path)
                  count += 1
          self.stdout.write(f"Cleaned {count} execution log directories")
  ```

---

### Task 8: 测试用例

**Files:**
- Create: `backend/opsflow/tests/test_trace.py`

- [ ] **Step 1: NodeExecutionTrace 模型测试**
  - `unique_together` 约束验证
  - `status_history` 追加不覆盖

- [ ] **Step 2: NodeTraceLogger 测试**
  - 写入后读取验证 JSON Lines 格式
  - 文件不存在返回空列表

- [ ] **Step 3: _update_state_tree 测试**
  - 增量更新不丢失已有字段
  - duration_ms 自动计算

- [ ] **Step 4: NodeCommandDispatcher 测试**
  - retry 返回正确格式
  - get_trace_log 文件读取

---

### Task 9: 更新文档

**Files:**
- Modify: `backend/opsflow/doc/TODO.md`
- Modify: `backend/opsflow/doc/05-feature-status.md`

- [ ] **Step 1: TODO.md** — 标记已完成项
- [ ] **Step 2: 05-feature-status.md** — 新增执行轨迹双树功能条目
