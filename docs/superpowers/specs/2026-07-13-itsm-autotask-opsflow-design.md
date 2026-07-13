# ITSM 自动任务节点 → OpsFlow 流程对接设计

> 日期: 2026-07-13 | 状态: Design
> 涉及 App: itsm, opsflow

---

## 背景

ITSM 的"自动任务"（TASK）节点当前是空壳——立即完成。需改造为真正嵌入 OpsFlow 的执行节点，支持：用户在节点注入运行时数据、发起 OpsFlow 执行、等待完成后继续下游。

## 设计概览

**约束：**
1. 用户可在 TASK 节点注入/填充运行时数据给 OpsFlow（类似填单）
2. OpsFlow 执行完 → 信号回调 → ITSM 节点完成 → 流程继续

**生命周期：**

```
execute(): 进入节点,展示参数填写界面
     │ (user fills form, submits)
     ▼
schedule(callback_data=form): 阶段1 — 创建 FlowExecution + 启动 OpsFlow
     │
     ▼
OpsFlow 异步执行 ... (可能含审批)
     │
     ▼
OpsFlow FINISHED → Django signal → bamboo_engine.api.callback()
     │
     ▼
schedule(callback_data=null): 阶段2 — 检测 FINISHED → 回写 → finish_schedule()
```

---

## 1. 数据模型

### State.extras 新增键

```json
{
  "opsflow_template_id": 12,
  "opsflow_template_name": "服务器重启",
  "opsflow_scheme_id": 3,
  "opsflow_variable_mapping": {
    "server_ip": "${field.server_ip}",
    "reason": "${ticket_title}"
  }
}
```

| 键 | 类型 | 说明 |
|---|---|---|
| `opsflow_template_id` | int | FlowTemplate.id；null = 无 OpsFlow 配置（回退旧行为） |
| `opsflow_template_name` | str | 仅展示 |
| `opsflow_scheme_id` | int | ExecutionScheme.id（可选） |
| `opsflow_variable_mapping` | dict | 设计时静态映射；运行时用户填写的字段自动合并 |

### 运行时数据合并

传给 OpsFlow 的 `global_vars` 由两部分合并：

| 来源 | 说明 |
|------|------|
| `extras.opsflow_variable_mapping` | 设计时配置，`${ticket_title}` 等模板变量在运行时解析 |
| `callback_data.fields` | 用户在 TASK 节点填写的表单数据，字段名直接作为变量名 |

运行时字段优先级高于静态映射（同名 key 覆盖）。

---

## 2. OpsFlow 完成回调（关键基础设施）

### 2.1 OpsFlow 侧：FlowEngine 完成时发射信号

在 `backend/opsflow/core/flow_engine.py` 的 `_on_pipeline_finish()` 中添加：

```python
from django.dispatch import Signal
flow_execution_finished = Signal()  # providing_args=['execution', 'status']

def _on_pipeline_finish(self, status, error=None):
    self.execution.status = status
    self.execution.save()
    flow_execution_finished.send(
        sender=self.__class__,
        execution=self.execution,
        status=status,
    )
```

### 2.2 ITSM 侧：监听信号 + 回调 bamboo

在 `backend/itsm/signals.py` 中新增：

```python
from opsflow.core.flow_engine import flow_execution_finished
from bamboo_engine import api as bamboo_api
from pipeline.eri.runtime import BambooDjangoRuntime

@receiver(flow_execution_finished)
def on_opsflow_finished(sender, execution, status, **kwargs):
    """OpsFlow 执行完成 → 回调 ITSM pipeline 中等待的 TASK 节点"""
    ctx = execution.context or {}
    if ctx.get('trigger') != 'itsm_auto_task':
        return  # only handle ITSM-triggered executions

    ticket_id = ctx.get('ticket_id')
    state_id = ctx.get('state_id')
    if not ticket_id or not state_id:
        return

    ticket = Ticket.objects.filter(id=ticket_id).first()
    if not ticket or not ticket.pipeline_id:
        return

    # Find the bamboo node for this state
    states = ticket.pipeline_tree.get('activities', {})
    node_id = None
    for nid, ndata in states.items():
        inputs = ndata.get('component', {}).get('inputs', {})
        if str(inputs.get('state_id', {}).get('value', '')) == str(state_id):
            node_id = nid
            break

    if node_id:
        bamboo_api.callback(BambooDjangoRuntime(), node_id, ticket.pipeline_id_version)
```

---

## 3. ItsmAutoTaskService 重写

```python
class ItsmAutoTaskService(Service):
    __need_schedule__ = True  # async — waits for user input then OpsFlow

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.do_before_enter_state(state_id)
        return True  # enter schedule loop

    def schedule(self, data, parent_data, callback_data=None):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        extras = data.get_one_of_inputs('extras') or {}
        ticket = Ticket.objects.get(id=ticket_id)

        # ── Phase 1: User submits form → start OpsFlow ──
        if callback_data:
            form_fields = callback_data.get('fields', {}) or {}
            ticket.do_in_state(state_id, form_fields,
                               callback_data.get('operator', 'system'))

            template_id = extras.get('opsflow_template_id')
            if not template_id:
                ticket.do_before_exit_state(state_id, 'system')
                self.finish_schedule()
                return True

            # Merge: static mapping + runtime form fields
            resolved = self._resolve_variables(extras, form_fields, ticket)
            execution = self._create_execution(template_id, extras, resolved, ticket)
            data.set_outputs('opsflow_execution_id', execution.id)
            return True  # continue waiting (Phase 2)

        # ── Phase 2: OpsFlow callback → check status ──
        exec_id = data.get_one_of_outputs('opsflow_execution_id')
        if not exec_id:
            return False  # still waiting for user

        execution = FlowExecution.objects.get(id=exec_id)

        if execution.status == 'RUNNING':
            return False  # keep waiting

        self._handle_completion(execution, ticket, state_id, data)
        ticket.do_before_exit_state(state_id, 'system')
        ticket.save()
        self.finish_schedule()
        return True

    # ── Helpers ──

    @staticmethod
    def _resolve_variables(extras, form_fields, ticket):
        """Merge static mapping + runtime form data"""
        mapping = extras.get('opsflow_variable_mapping', {})
        result = {}
        # Build template context
        ctx = {
            'ticket_id': ticket.id, 'ticket_sn': ticket.sn,
            'ticket_title': ticket.title, 'ticket_type': ticket.itsm_type,
            'ticket_priority': ticket.priority,
            'ticket_creator': str(ticket.creator or ''),
        }
        fm = (ticket.meta or {}).get('form_data', {})
        for k, v in fm.items():
            ctx[f'field.{k}'] = v
        # Resolve static mapping
        for k, v in mapping.items():
            result[k] = _template_sub(v, ctx)
        # Merge runtime fields (override)
        result.update(form_fields)
        return result

    @staticmethod
    def _create_execution(template_id, extras, resolved_vars, ticket):
        template = FlowTemplate.objects.get(id=template_id)
        execution = FlowExecution.objects.create(
            template=template,
            created_by=ticket.creator,
            context={
                'trigger': 'itsm_auto_task',
                'ticket_id': ticket.id,
                'ticket_sn': ticket.sn,
                'state_id': extras.get('_state_id'),
            },
            template_snapshot=template.snapshot or template.pipeline_tree,
            global_vars=resolved_vars,
        )
        scheme_id = extras.get('opsflow_scheme_id')
        if scheme_id:
            execution.apply_scheme(scheme_id)
        FlowEngine(execution).start(sync=False)
        return execution

    @staticmethod
    def _handle_completion(execution, ticket, state_id, data):
        if execution.status == 'FINISHED':
            ticket.meta['opsflow_result'] = {
                'execution_id': execution.id,
                'outputs': execution.outputs,
            }
            ticket.add_comment(f"OpsFlow「{execution.template.name}」执行完成")
            for k, v in (execution.outputs or {}).items():
                data.set_outputs(f'opsflow_{k}', v)
        else:
            ticket.meta['opsflow_result'] = {
                'execution_id': execution.id,
                'status': 'FAILED',
            }
            ticket.add_comment(f"OpsFlow执行失败")
```

---

## 4. workflow_builder.py

```python
elif stype == 'TASK':
    el = ServiceActivity(component_code='itsm_auto_task', id=elem_id, skippable=True)
    el.name = state.get('name', '')
    el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
    el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
    el.component.inputs['extras'] = Var(type=Var.PLAIN, value=state.get('extras', {}))
    _register_field_outputs(data, sid_str, state, node_id_map)
```

---

## 5. 前端

### NodeConfigPanel.vue — TASK 节点新增 OpsFlow 配置

```vue
<template v-if="node.type === 'TASK'">
  <!-- 现有处理人配置 ... -->

  <el-divider>OpsFlow 配置</el-divider>
  <el-form-item label="OpsFlow 模板">
    <el-select v-model="node.extras.opsflow_template_id" placeholder="选择模板"
               clearable @change="onOpsflowTemplateChange" style="width:100%">
      <el-option v-for="t in opsflowTemplates" :label="t.name" :value="t.id" />
    </el-select>
  </el-form-item>
  <el-form-item label="执行方案" v-if="node.extras.opsflow_template_id">
    <el-select v-model="node.extras.opsflow_scheme_id" placeholder="可选" clearable style="width:100%">
      <el-option v-for="s in opsflowSchemes" :label="s.name" :value="s.id" />
    </el-select>
  </el-form-item>
  <el-form-item label="变量映射">
    <el-table :data="varMappingRows" size="small" border>
      <el-table-column label="OpsFlow 变量名">
        <template #default="{ row }"><el-input v-model="row.key" size="small" /></template>
      </el-table-column>
      <el-table-column label="工单字段">
        <template #default="{ row }">
          <el-input v-model="row.value" size="small" placeholder="${ticket_title}" />
        </template>
      </el-table-column>
    </el-table>
  </el-form-item>
</template>
```

### useDesigner.ts — 同步 `extras`

```ts
const dirtyKeys = [
  ...existing,
  'extras', 'execute_type', 'api_url', 'api_method',
]
```

---

## 6. 关键文件

| 文件 | 变更 |
|------|------|
| `backend/itsm/pipeline_plugins/components.py` | ItsmAutoTaskService 重写（execute + 双阶段 schedule） |
| `backend/opsflow/core/flow_engine.py` | 新增 `flow_execution_finished` 信号 |
| `backend/itsm/signals.py` | 新增 OpsFlow 完成回调处理 |
| `backend/itsm/services/workflow_builder.py` | TASK 传入 extras |
| `web/.../NodeConfigPanel.vue` | TASK 节点 OpsFlow 配置表单 |
| `web/.../useDesigner.ts` | 同步 extras |

## 7. 兼容性

- 旧 TASK 节点（`extras` 无 `opsflow_template_id`）：用户提交表单后立即完成（回退旧行为）
- Fire & forget 模式：去掉 `__need_schedule__` 的等待逻辑时需显式设置

## 8. 验证

1. TASK 节点无 OpsFlow 模板 → 用户提交表单 → 立即完成（旧行为）
2. 配置 OpsFlow 模板 → 用户填写参数提交 → OpsFlow 启动 → 完成后 ITSM 继续
3. 静态映射 `${ticket_title}` + 运行时字段同时传递
4. OpsFlow 失败 → ITSM 记录日志 → 节点完成不阻塞
