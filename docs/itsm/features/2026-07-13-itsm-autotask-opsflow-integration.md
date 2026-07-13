# ITSM 自动任务节点 → OpsFlow 集成

> 提交: af55af09 | 日期: 2026-07-13
> 涉及 App: itsm, opsflow
> 类型: 功能新增

---

## 背景

ITSM 工单流程中的「自动任务」（TASK）节点原本只是一个同步 pass-through —— 进入即执行 `do_in_state({'auto_executed': True})` 后立即完成，不能承载任何实际的自动化动作。

本次将 TASK 节点与 OpsFlow 流程引擎打通:设计器可为 TASK 节点绑定一个 OpsFlow 模板;工单跑到该节点时，处理人填写模板的全局变量参数并提交，ITSM 节点**挂起等待** OpsFlow 执行完成，完成后再继续后续网关/审批。

## 实现方案

### 核心架构

整个链路横跨 ITSM(bamboo pipeline)与 OpsFlow(FlowEngine)两个执行引擎，靠 bamboo 的**多回调调度**(MULTIPLE_CALLBACK)和一个 Django Signal 桥接:

```
execute()  ──> 记录 _opsflow_params，节点进入 MULTIPLE_CALLBACK 挂起
   │
   ├─(回调①: 用户提交参数) schedule() Phase 1
   │     do_in_state → _resolve_vars → 创建 FlowExecution → set_outputs(exec_id)
   │     → FlowEngine.start(sync=False)  → return True(不 finish，继续等)
   │
   │   OpsFlow 异步执行 …… 完成 → _handle_root_state_change
   │     → flow_execution_finished.send(execution, status)
   │       → on_opsflow_finished(signal) → resolve_activity_id → activity_callback
   │
   └─(回调②: OpsFlow 完成) schedule() Phase 2 = _finalize_opsflow()
         读 execution.status → set_outputs(opsflow_*) → do_before_exit_state → finish_schedule
```

### 关键代码

**1. 两阶段 schedule 的判别** —— 用 outputs 里是否已存 `opsflow_execution_id` 区分阶段(完成回调也带 callback_data，不能用它判别):

```python
# itsm/pipeline_plugins/components.py  ItsmAutoTaskService
__need_schedule__ = True
__multi_callback_enabled__ = True   # 需要两次回调:提交参数 + OpsFlow 完成

def schedule(self, data, parent_data, callback_data=None):
    exec_id = data.get_one_of_outputs('opsflow_execution_id')
    if exec_id:
        return self._finalize_opsflow(data, ticket, state_id, exec_id)  # Phase 2
    if not callback_data:
        return True   # 继续等用户提交(return False 会把节点判 FAILED)
    # Phase 1: 起 OpsFlow
    resolved = self._resolve_vars(extras, form_fields, ticket)
    execution = self._create_opsflow_execution(template_id, extras, resolved, ticket, state_id)
    data.set_outputs('opsflow_execution_id', execution.id)  # 先落库再启动，避免竞态
    self._start_opsflow_engine(execution, extras)
    return True   # 不 finish_schedule，挂起等 OpsFlow 完成
```

**2. 变量注入** —— OpsFlow 运行时全局变量来自 `execution.template_snapshot['global_vars']`(FlowExecution 无独立 global_vars 字段)，把解析后的运行时值注入快照:

```python
# _create_opsflow_execution
snapshot = dict(template.snapshot or {}) or {'pipeline_tree': ..., 'global_vars': ...}
frozen_vars = dict(snapshot.get('global_vars', {}))
for key, value in (resolved_vars or {}).items():
    existing = frozen_vars.get(key)
    frozen_vars[key] = {**existing, 'value': value} if isinstance(existing, dict) and 'value' in existing else value
snapshot['global_vars'] = frozen_vars
execution = OpsFlowExecution.objects.create(
    template=template,
    created_by_id=ticket.creator,   # ticket.creator 是 IntegerField(用户 id)，不是实例
    context={'trigger': 'itsm_auto_task', 'ticket_id': ticket.id, 'state_id': state_id},
    template_snapshot=snapshot,
)
```

**3. 完成信号桥接** —— OpsFlow 完成时唤醒 ITSM 节点:

```python
# opsflow/core/flow_engine.py
flow_execution_finished = Signal()   # receivers: execution, status

# opsflow/signals/handlers.py _handle_root_state_change
flow_execution_finished.send(sender=..., execution=execution, status='FINISHED')  # or 'FAILED'

# itsm/signals.py on_opsflow_finished
node_id = resolve_activity_id(ticket, state_id)   # state_id → node_key → 加盐 element id
activity_callback(node_id, {'source': 'opsflow_finished', 'opsflow_status': status})
```

### 数据流

```
设计器 NodeConfigPanel(选模板) → State.extras.opsflow_template_id
   → WorkflowVersion 快照 → ITSMWorkflowBuilder 注入 el.component.inputs['extras']
   → TASK 节点 execute() 读 extras → ticket.meta._opsflow_params
   → 前端 TaskNodeForm 读 template_id → GET /global-variables/ 渲染表单
   → node_submit(fields) → schedule Phase 1 → FlowExecution.template_snapshot.global_vars
   → OpsFlow 执行 → NodeExecutionTrace.outputs → opsflow_result + opsflow_<key> outputs
   → 下游排他网关可引用
```

### 设计决策

- **为什么用 MULTIPLE_CALLBACK 而非同步等待**:OpsFlow 异步执行(Celery)，ITSM 节点必须挂起让出 worker，靠事件回调唤醒，不能阻塞。
- **为什么 `resolve_activity_id` 下沉到 service**:`_pipeline_id_map` 的 key 是 node_key 而非 state_id，解析逻辑原在 `TicketViewSet._get_activity_id`;信号处理器复用它会造成 signal→view 反向依赖，故抽到 `itsm/services/bamboo_engine.py` 供 view 与 signal 共用。
- **为什么前端不缓存变量定义到 meta**:`_opsflow_params` 只存 `template_id`，变量定义实时走 `/global-variables/` API 拉取，避免与模板双写不一致。
- **前端组件抽取 + 共享 composable**:`GlobalVarInput`(纯渲染)+ `useTemplateVars`(拉取/归一化)被 SubmitWizard 和 TaskNodeForm 共用，`coerce` 开关控制 checkbox/cascader/multiple 的数组强制转换。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/pipeline_plugins/components.py` | `ItsmAutoTaskService` 两阶段 schedule、变量解析、执行创建、输出聚合 |
| `backend/itsm/services/bamboo_engine.py` | `resolve_activity_id()` state_id→element id 解析(view+signal 共用) |
| `backend/itsm/services/workflow_builder.py` | TASK 节点注入 `extras` 输入 |
| `backend/itsm/signals.py` | `on_opsflow_finished` 完成回调 → 唤醒 ITSM 节点 |
| `backend/opsflow/core/flow_engine.py` | `flow_execution_finished` 信号定义 + fail/cancel 显式 emit |
| `backend/opsflow/signals/handlers.py` | pipeline 完成/失败时发送信号 |
| `web/src/components/GlobalVarInput.vue` | 全局变量输入渲染组件(多类型) |
| `web/src/composables/useTemplateVars.ts` | 变量拉取 + 归一化(fetch/normalize/load) |
| `web/src/views/apps/itsm/components/TaskNodeForm.vue` | 工单详情内 TASK 节点参数表单 |
| `web/src/views/apps/itsm/designer/components/NodeConfigPanel.vue` | 设计器为 TASK 节点绑定 OpsFlow 模板 |

## 使用方式

1. 设计器中选中 TASK(自动任务)节点 → 「OpsFlow 模板」下拉选择要执行的流程模板 → 保存并部署。
2. 工单流转到该节点，处理人在工单详情看到模板全局变量表单 → 填写 → 「提交并执行 OpsFlow」。
3. ITSM 节点挂起，OpsFlow 后台执行;完成后节点自动继续，结果写入 `ticket.meta.opsflow_result` 和 `opsflow_*` 输出(供下游网关引用)。
4. 未绑定模板的 TASK 节点保持旧的同步 pass-through 自动完成。

### 关联文档

- 相关调试记录: [2026-07-13-autotask-schedule-and-callback-fixes.md](../debug/2026-07-13-autotask-schedule-and-callback-fixes.md)
