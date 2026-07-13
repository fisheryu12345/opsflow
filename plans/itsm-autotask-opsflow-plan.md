# Implementation Plan: ITSM 自动任务节点 → OpsFlow 对接

## Context

设计文档: `docs/superpowers/specs/2026-07-13-itsm-autotask-opsflow-design.md`

将 ITSM 的 TASK 节点从空壳改为真正的 OpsFlow 执行节点：用户在节点注入运行时数据 → 创建 FlowExecution → 等待 OpsFlow 完成 → 回写 ITSM。

## Tasks

### 1. [OpsFlow] FlowEngine 完成信号

**文件**: `backend/opsflow/core/flow_engine.py`

在文件顶部（imports 之后）新增信号定义：

```python
from django.dispatch import Signal
flow_execution_finished = Signal()  # providing_args=['execution', 'status', 'root_id']
```

### 2. [OpsFlow] 信号发射

**文件**: `backend/opsflow/signals/handlers.py`

在 `_handle_root_state_change()` 中，`execution.save()` 之后添加信号发射：

```python
# After line 174 (COMPLETED branch):
from opsflow.core.flow_engine import flow_execution_finished
flow_execution_finished.send(
    sender=_handle_root_state_change,
    execution=execution,
    status='FINISHED',
)

# After line 182 (FAILED branch):
flow_execution_finished.send(
    sender=_handle_root_state_change,
    execution=execution,
    status='FAILED',
)
```

### 3. [ITSM] 监听 OpsFlow 信号 + 回调 bamboo

**文件**: `backend/itsm/signals.py`

在文件末尾新增：

```python
from opsflow.core.flow_engine import flow_execution_finished
from bamboo_engine import api as bamboo_api
from pipeline.eri.runtime import BambooDjangoRuntime

@receiver(flow_execution_finished)
def on_opsflow_finished(sender, execution, status, **kwargs):
    ctx = execution.context or {}
    if ctx.get('trigger') != 'itsm_auto_task':
        return
    ticket_id = ctx.get('ticket_id')
    if not ticket_id:
        return
    from itsm.models.ticket import Ticket
    ticket = Ticket.objects.filter(id=ticket_id).first()
    if not ticket or not ticket.pipeline_id:
        return
    # Find the bamboo node_id for this state via pipeline_id_map
    meta = ticket.meta or {}
    id_map = meta.get('_pipeline_id_map', {})
    node_id = None
    for state_id_str, elem_id in id_map.items():
        if str(ctx.get('state_id')) == state_id_str:
            node_id = elem_id
            break
    if node_id:
        bamboo_api.callback(BambooDjangoRuntime(), node_id, ticket.pipeline_id_version)
```

### 4. [ITSM] ItsmAutoTaskService 重写

**文件**: `backend/itsm/pipeline_plugins/components.py`

完全替换 `ItsmAutoTaskService`（lines 209-225）和 `ItsmAutoTaskComponent`（lines 247-250）：

```python
class ItsmAutoTaskService(Service):
    __need_schedule__ = True

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.do_before_enter_state(state_id)
        return True

    def schedule(self, data, parent_data, callback_data=None):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        extras = data.get_one_of_inputs('extras') or {}
        ticket = Ticket.objects.get(id=ticket_id)

        # Phase 1: user submitted form → start OpsFlow
        if callback_data:
            form_fields = callback_data.get('fields', {}) or {}
            ticket.do_in_state(state_id, form_fields,
                               callback_data.get('operator', 'system'))

            template_id = extras.get('opsflow_template_id')
            if not template_id:
                # No OpsFlow: backward compat → auto complete
                ticket.do_before_exit_state(state_id, 'system')
                self.finish_schedule()
                return True

            resolved = self._resolve_vars(extras, form_fields, ticket)
            execution = self._start_opsflow(template_id, extras, resolved, ticket)
            data.set_outputs('opsflow_execution_id', execution.id)
            return True

        # Phase 2: OpsFlow callback → check status
        exec_id = data.get_one_of_outputs('opsflow_execution_id')
        if not exec_id:
            return False

        from opsflow.models import FlowExecution
        execution = FlowExecution.objects.get(id=exec_id)
        if execution.status == 'running':
            return False

        if execution.status == 'completed':
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
            ticket.add_comment("OpsFlow执行失败")

        ticket.do_before_exit_state(state_id, 'system')
        ticket.save()
        self.finish_schedule()
        return True

    @staticmethod
    def _resolve_vars(extras, form_fields, ticket):
        mapping = extras.get('opsflow_variable_mapping', {})
        result = {}
        ctx = {
            'ticket_id': ticket.id, 'ticket_sn': ticket.sn,
            'ticket_title': ticket.title, 'ticket_type': ticket.itsm_type,
            'ticket_priority': ticket.priority,
            'ticket_creator': str(ticket.creator or ''),
        }
        fm = (ticket.meta or {}).get('form_data', {})
        for k, v in fm.items():
            ctx[f'field.{k}'] = v
        for k, v in mapping.items():
            result[k] = _simple_template(v, ctx)
        result.update(form_fields)  # runtime overrides static
        return result

    @staticmethod
    def _start_opsflow(template_id, extras, resolved_vars, ticket):
        from opsflow.models import FlowTemplate, FlowExecution
        from opsflow.core.flow_engine import FlowEngine
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
            from opsflow.models import ExecutionScheme
            execution.apply_scheme(scheme_id)
        FlowEngine(execution).start(sync=False)
        return execution


def _simple_template(template, ctx):
    """Simple ${key} template substitution."""
    import re
    def _replace(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return re.sub(r'\$\{(\w+(?:\.\w+)?)\}', _replace, template)


# Component registration (unchanged, just updates bound_service)
class ItsmAutoTaskComponent(Component):
    name = 'ITSM 自动任务'
    code = 'itsm_auto_task'
    bound_service = ItsmAutoTaskService
```

### 5. [ITSM] workflow_builder.py 传 extras

**文件**: `backend/itsm/services/workflow_builder.py`

找到 TASK 分支（约 line 118），在 `el.component.inputs` 中添加 extras：

```python
el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
el.component.inputs['extras'] = Var(type=Var.PLAIN, value=state.get('extras', {}))  # ← new
```

### 6. [Frontend] useDesigner.ts — 同步 extras

**文件**: `web/src/views/apps/itsm/designer/useDesigner.ts`

Line 45, add `'extras'` to dirtyKeys:

```ts
const dirtyKeys = ['_usePreset', 'preset_id', 'preset', ...existing..., 'extras']
```

Line 501, add `extras` to save payload:

```ts
return {
  ...(n.originId && typeof n.originId === 'number' ? { id: n.originId } : {}),
  ...existing...,
  fields: n.fields || [],
  extras: n.extras || {},   // ← new
}
```

### 7. [Frontend] NodeConfigPanel.vue — OpsFlow 配置表单

**文件**: `web/src/views/apps/itsm/designer/components/NodeConfigPanel.vue`

在 TASK 节点配置区（`<template v-if="node.type === 'TASK'">` 结尾，约 line 145 之前）添加：

```vue
<el-divider>OpsFlow 配置</el-divider>
<el-form-item label="OpsFlow 模板">
  <el-select v-model="node.extras.opsflow_template_id"
             placeholder="选择 OpsFlow 模板" clearable style="width:100%"
             @change="onOpsflowTemplateSelect">
    <el-option v-for="t in opsflowTemplates" :key="t.id"
               :label="t.name" :value="t.id" />
  </el-select>
</el-form-item>
<el-form-item v-if="node.extras.opsflow_template_id" label="执行方案">
  <el-select v-model="node.extras.opsflow_scheme_id"
             placeholder="执行方案(可选)" clearable style="width:100%">
    <el-option v-for="s in opsflowSchemes" :key="s.id"
               :label="s.name" :value="s.id" />
  </el-select>
</el-form-item>
<el-form-item v-if="node.extras.opsflow_template_id" label="变量映射">
  <div v-for="(row, i) in varMappingRows" :key="i" class="var-mapping-row">
    <el-input v-model="row.key" placeholder="OpsFlow 变量名" size="small" style="width:45%" />
    <el-input v-model="row.value" placeholder="${ticket_title}" size="small" style="width:45%" />
    <el-button link type="danger" size="small" @click="varMappingRows.splice(i,1)">✕</el-button>
  </div>
  <el-button link type="primary" size="small" @click="varMappingRows.push({key:'',value:''})">
    + 添加映射
  </el-button>
</el-form-item>
```

在 script 中添加数据和方法：

```ts
const opsflowTemplates = ref<any[]>([])
const opsflowSchemes = ref<any[]>([])

onMounted(async () => {
  try {
    const res = await request({ url: '/api/opsflow/templates/', method: 'get', params: { page_size: 500 } })
    opsflowTemplates.value = (res as any).data || (res as any).results || []
  } catch { /* silent */ }
})
```

Add `onOpsflowTemplateSelect()` and `varMappingRows` computed.

### 8. Migration

无数据库迁移。`extras` 已是 JSONField，无需改动。

### 9. Verification

- [ ] Backend: `python manage.py test itsm.tests.test_models --failfast`
- [ ] Build: `cd web && npm run build`
- [ ] Manual: 创建 TASK 节点 → 配置 OpsFlow 模板 → 用户提交 → OpsFlow 执行 → 完成回写
- [ ] Backward compat: TASK 节点无 OpsFlow 模板 → 提交后立即完成（旧行为）
