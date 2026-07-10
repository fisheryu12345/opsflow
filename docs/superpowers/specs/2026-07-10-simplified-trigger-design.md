# ITSM 简化触发器 — Design Spec

> **Date:** 2026-07-10
> **Status:** Design Complete (pending approval)
> **Priority:** 高 — 补全自动化短板

---

## Context

当前 ITSM 工单流程完全手动驱动：用户提交工单 → pipeline 执行 → 人工审批/填单，没有任何事件驱动的自动化能力。SLA 有超时升级、OpsFlow 有定时调度和 Webhook，但 ITSM 缺少"当工单进入审批节点时自动通知组长"这类触发器。

本设计引入一套事件驱动的触发器系统，支持流程开始/结束、进入节点/离开节点四种事件，匹配条件过滤，多动作顺序执行，异步执行保证可靠性。

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 事件类型 | FLOW_START / FLOW_END / ENTER_STATE / LEAVE_STATE | 覆盖工单全生命周期 |
| 作用域 | 全局独立配置页 | 对齐 SlaPolicy/Escalation 模式，简洁灵活 |
| 条件匹配 | 流程 + 节点 + 优先级 + 表单字段条件表达式 | 复用 ConditionDialog + conditionUtils |
| FLOW_START 条件 | 忽略字段条件，仅靠 workflow/priority 匹配 | form_data 在流程启动时为空 |
| ENTER/LEAVE 排除 START/END | ENTER_STATE/LEAVE_STATE 不触发于 START/END 节点 | FLOW_START/FLOW_END 已覆盖 |
| 执行日志保留 | 365 天 | APScheduler 每日清理过期记录 |
| 动作执行 | 异步队列表 + APScheduler | 不阻塞主流程，支持重试和审计 |
| 动作绑定 | 一个触发器多条动作，按顺序执行 | 灵活组合通知/Webhook/OpsFlow/字段修改 |
| 执行可靠性 | try/except 包裹每条 action，失败不中断后续 | 单动作失败不应影响其他动作 |

---

## 1. Data Models

### 1.1 Trigger

```
File: backend/itsm/models/trigger.py (NEW)

Trigger(CoreModel):
    name = CharField(128)
    name_en = CharField(128)
    project = FK → iam.Project (null=True)   # null = global
    is_active = BooleanField(default=True)

    # ---- Event matching ----
    event_type = CharField(choices:
        ('FLOW_START', '流程开始'),
        ('FLOW_END', '流程结束'),
        ('ENTER_STATE', '接入节点'),
        ('LEAVE_STATE', '离开节点'),
    )
    workflow = FK → Workflow (null=True, blank=True, on_delete=SET_NULL)  # null = match all
    states = M2M → State (blank=True)                  # only for ENTER_STATE/LEAVE_STATE
    priority = CharField(choices: P1/P2/P3/P4, blank=True)  # blank = match all

    # ---- Field-level condition ----
    condition = JSONField(default=dict, blank=True)
    # Format: {"logic": "AND", "rules": [{"field": "...", "op": "==", "value": "..."}]}
    # Same format as designer/conditionUtils.ts ConditionStruct
    # Empty dict = always match
```

### 1.2 TriggerAction

```
TriggerAction:
    trigger = FK → Trigger, related_name='actions', on_delete=CASCADE
    order = IntegerField(default=0)          # execution sequence
    action_type = CharField(choices:
        ('NOTIFY', '发送通知'),
        ('WEBHOOK', 'HTTP 回调'),
        ('OPSFLOW', '触发运维流程'),
        ('MODIFY_FIELD', '修改工单字段'),
    )
    config = JSONField(default=dict)
    # Per-type config:
    # NOTIFY:     {channels: ["site","wecom","dingtalk","email"],
    #              title_tpl: "工单${ticket_id}...", body_tpl: "...",
    #              receivers: ["processor","starter","leader"],
    #              custom_users: [user_ids]}
    # WEBHOOK:    {url: "https://...", method: "POST",
    #              headers: {"Authorization": "..."}, body_tpl: "{...}",
    #              timeout: 30}
    # OPSFLOW:    {flow_id: N, variable_mapping: {"${ticket_id}": "opsflow_var"}}
    # MODIFY_FIELD: {field_name: "priority", field_value: "P1",
    #                value_type: "static"|"template"}

    class Meta:
        ordering = ['order']
```

### 1.3 TriggerExecution

```
TriggerExecution:
    trigger = FK → Trigger, on_delete=SET_NULL, null=True  # preserve history
    ticket = FK → Ticket, on_delete=CASCADE
    event_type = CharField
    status = CharField(choices: ('PENDING', 'SUCCESS', 'FAILED'))
    action_results = JSONField(default=list)
    # [{action_id: N, action_type: "NOTIFY", status: "SUCCESS"/"FAILED",
    #   error: "...", executed_at: "..."}]
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

**Retention:** TriggerExecution records older than 365 days are purged by a daily cleanup job in APScheduler:
```python
scheduler.add_job(
    lambda: TriggerExecution.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=365)
    ).delete(),
    'interval', days=1, id='trigger_execution_cleanup',
)
```

### 1.4 FK Delete Behavior

| FK | on_delete | Rationale |
|----|-----------|-----------|
| Trigger.workflow | SET_NULL | Deleted workflow → trigger becomes global (matches all) |
| Trigger.states (M2M) | CASCADE on through table | Deleted state → removed from trigger's state filter |
| TriggerAction.trigger | CASCADE | Delete trigger → delete all its actions |
| TriggerExecution.trigger | SET_NULL | Delete trigger → preserve execution history |

---

## 2. Service Layer

### 2.1 TriggerMatcher

```
File: backend/itsm/services/trigger_service.py (NEW)

class TriggerMatcher:
    @staticmethod
    def match(ticket, event_type, state_id=None) -> list[Trigger]:
        """Return active Triggers matching the event context."""
        qs = Trigger.objects.filter(
            is_active=True,
            event_type=event_type,
        )
        # Workflow filter: specified workflow OR global (null)
        qs = qs.filter(
            Q(workflow__isnull=True) |
            Q(workflow=ticket.workflow_version.workflow)
        )
        # Priority filter: specified priority OR blank
        qs = qs.filter(
            Q(priority='') | Q(priority=ticket.priority)
        )
        # State filter (ENTER/LEAVE only): specified states OR empty
        if state_id:
            from itsm.models import State
            state = State.objects.get(id=state_id)
            qs = qs.filter(
                Q(states__isnull=True) | Q(states=state)
            )

        # Evaluate field-level conditions (skip for FLOW_START — form_data is empty)
        matched = []
        for trigger in qs:
            if event_type != 'FLOW_START' and trigger.condition:
                if not ConditionEvaluator.evaluate(trigger.condition, ticket):
                    continue
            matched.append(trigger)
        return matched


class ConditionEvaluator:
    """Evaluate condition expression against ticket form data."""
    @staticmethod
    def evaluate(condition: dict, ticket) -> bool:
        if not condition or not condition.get('rules'):
            return True
        logic = condition.get('logic', 'AND')
        results = []
        for rule in condition['rules']:
            field_value = ConditionEvaluator._resolve_value(
                ticket, rule.get('source'), rule['field']
            )
            results.append(ConditionEvaluator._apply_op(
                field_value, rule['op'], rule['value']
            ))
        if logic == 'AND':
            return all(results)
        return any(results)

    @staticmethod
    def _resolve_value(ticket, source, field):
        """Resolve field value from ticket meta or node outputs."""
        # source can be 'ticket' or 'node_<key>'
        if source == 'ticket' or not source:
            return ticket.meta.get('form_data', {}).get(field)
        # For node-scoped fields, resolve from pipeline Data context
        # Bamboo pipeline stores node outputs via get_pipeline_context()
        # Flatten top-level keys: {node_key_field: value}
        pipeline_data = _get_pipeline_data(ticket.pipeline_id)
        return pipeline_data.get(f'{source}_{field}') if pipeline_data else None
```

### 2.2 TriggerExecutor

```
class TriggerExecutor:
    @staticmethod
    def enqueue(ticket, event_type, state_id=None):
        """Match triggers and create PENDING executions."""
        triggers = TriggerMatcher.match(ticket, event_type, state_id)
        for trigger in triggers:
            TriggerExecution.objects.create(
                trigger=trigger,
                ticket=ticket,
                event_type=event_type,
                status='PENDING',
            )

    @staticmethod
    def process_pending():
        """Called by APScheduler every 10s. Process batch of pending executions."""
        executions = TriggerExecution.objects.filter(
            status='PENDING'
        ).select_related('trigger', 'ticket').prefetch_related(
            'trigger__actions'
        )[:50]

        for execution in executions:
            try:
                results = []
                for action in execution.trigger.actions.order_by('order'):
                    try:
                        result = ActionRunner.run(action, execution.ticket)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            'action_id': action.id,
                            'action_type': action.action_type,
                            'status': 'FAILED',
                            'error': str(e),
                        })
                execution.action_results = results
                has_failure = any(r.get('status') == 'FAILED' for r in results)
                execution.status = 'FAILED' if has_failure else 'SUCCESS'
            except Exception as e:
                execution.status = 'FAILED'
                execution.action_results = [{'error': str(e)}]
            execution.save()
```

### 2.3 ActionRunner

```
class ActionRunner:
    """Dispatch to action-type-specific runners."""

    @staticmethod
    def run(action, ticket) -> dict:
        if action.action_type == 'NOTIFY':
            return NotifyRunner.run(action.config, ticket)
        elif action.action_type == 'WEBHOOK':
            return WebhookRunner.run(action.config, ticket)
        elif action.action_type == 'OPSFLOW':
            return OpsflowRunner.run(action.config, ticket)
        elif action.action_type == 'MODIFY_FIELD':
            return ModifyFieldRunner.run(action.config, ticket)
        return {'status': 'FAILED', 'error': f'Unknown action type: {action.action_type}'}


class TemplateResolver:
    """Resolve ${variable} templates in strings."""
    @staticmethod
    def resolve(template: str, ticket, current_state_name: str = '') -> str:
        replacements = {
            'ticket_id': str(ticket.id),
            'ticket_title': ticket.title or '',
            'priority': ticket.priority or '',
            'current_state': current_state_name or '',
            'starter_name': ticket.creator.username if ticket.creator else '',
            'processor_name': ticket.processor.username if ticket.processor else '',
        }
        for key, val in replacements.items():
            template = template.replace(f'${{{key}}}', str(val))
        # Resolve ${field.xxx} from form_data
        import re
        for match in re.finditer(r'\$\{field\.(\w+)\}', template):
            field_val = ticket.meta.get('form_data', {}).get(match.group(1), '')
            template = template.replace(match.group(0), str(field_val))
        return template
```

**Action runners:**

| Runner | Behavior |
|--------|----------|
| `NotifyRunner` | 调用 `NotificationService.notify_users()` — 传入渠道列表、标题模板、正文模板、接收人 |
| `WebhookRunner` | `requests.post(url, json=body, headers=headers, timeout=timeout)` — body 通过 `TemplateResolver` 渲染 |
| `OpsflowRunner` | 复用 `OpsflowTriggerService` — 创建 `FlowExecution` 并异步启动 |
| `ModifyFieldRunner` | 更新 `ticket.meta['form_data'][field_name]`，调用 `ticket.save(update_fields=['meta'])` |

### 2.4 Signal Integration Points

**`backend/itsm/signals.py` — `itsm_post_set_state_handler`** 中插入：

```python
# After state mapping logic, when a node transitions:
# Exclude START/END nodes — FLOW_START/FLOW_END events cover these timings
from itsm.models.state import State
if state_id and bamboo_state == 'READY':
    state = State.objects.get(id=state_id)
    if state.type not in (State.START, State.END):
        TriggerExecutor.enqueue(ticket, 'ENTER_STATE', state_id)
if state_id and old_bamboo_state == 'RUNNING':
    state = State.objects.get(id=state_id)
    if state.type not in (State.START, State.END):
        TriggerExecutor.enqueue(ticket, 'LEAVE_STATE', state_id)
```

**`backend/itsm/services/itsm_engine.py` — `ITSMEngine.run()`** 中插入：

```python
# After pipeline is started:
def run(self):
    ...
    result = bamboo_engine_api.run_pipeline(...)
    if result.result:
        TriggerExecutor.enqueue(ticket, 'FLOW_START')
    ...
```

**`backend/itsm/models/ticket.py` — `do_before_end_pipeline()`** 中插入：

```python
def do_before_end_pipeline(self):
    TriggerExecutor.enqueue(self, 'FLOW_END')
    SlaEngine.stop_ticket_sla(self)
    self.set_status('finished', operator='system')
    ...
```

### 2.5 Scheduler

**`backend/itsm/apps.py` — `ready()`** 新增 job：

```python
scheduler.add_job(
    TriggerExecutor.process_pending,
    'interval',
    seconds=10,
    id='trigger_executor',
    replace_existing=True,
)
```

---

## 3. API Layer

### 3.1 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/itsm/triggers/` | list | List triggers (`?workflow=&event_type=&is_active=`) |
| `POST /api/itsm/triggers/` | create | Create trigger with nested actions |
| `GET /api/itsm/triggers/{id}/` | retrieve | Get trigger detail |
| `PUT /api/itsm/triggers/{id}/` | update | Update trigger (replaces actions + states) |
| `DELETE /api/itsm/triggers/{id}/` | destroy | Delete trigger (cascade deletes actions) |
| `GET /api/itsm/triggers/{id}/executions/` | list | Execution history for this trigger |

### 3.2 New Files

| File | Purpose |
|------|---------|
| `backend/itsm/serializers/trigger.py` | TriggerSerializer (nested actions write) + TriggerActionSerializer |
| `backend/itsm/views/trigger_views.py` | TriggerViewSet (extends ItsmProjectViewSet) |

### 3.3 TriggerSerializer (nested write)

```python
class TriggerActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerAction
        fields = ['id', 'order', 'action_type', 'config']

class TriggerSerializer(serializers.ModelSerializer):
    actions = TriggerActionSerializer(many=True)
    state_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=State.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Trigger
        fields = ['id', 'name', 'name_en', 'project', 'is_active',
                  'event_type', 'workflow', 'state_ids', 'priority',
                  'condition', 'actions', 'created_at', 'updated_at']

    def create(self, validated_data):
        actions_data = validated_data.pop('actions', [])
        state_ids = validated_data.pop('state_ids', [])
        trigger = Trigger.objects.create(**validated_data)
        trigger.states.set(state_ids)
        for i, action_data in enumerate(actions_data):
            TriggerAction.objects.create(trigger=trigger, order=i, **action_data)
        return trigger

    def update(self, instance, validated_data):
        actions_data = validated_data.pop('actions', None)
        state_ids = validated_data.pop('state_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if state_ids is not None:
            instance.states.set(state_ids)
        if actions_data is not None:
            instance.actions.all().delete()
            for i, action_data in enumerate(actions_data):
                TriggerAction.objects.create(trigger=instance, order=i, **action_data)
        return instance
```

---

## 4. Frontend

### 4.1 TriggerList.vue (NEW)

Follows existing `SlaPolicyList.vue` table+dialog CRUD pattern.

**Table columns:** 名称 | 事件类型(标签) | 匹配流程 | 优先级 | 启用开关 | 操作(编辑/删除)

**Create/Edit Dialog** (el-dialog, width: 800px):

| Section | Fields |
|---------|--------|
| 基本信息 | name, name_en, project selector, is_active switch |
| 触发事件 | event_type dropdown → conditional: workflow selector, states multi-select, priority dropdown |
| 匹配条件(可选) | Collapsible panel with embedded ConditionDialog — field condition expression builder |
| 动作列表 | Draggable action cards, each card: action_type dropdown + type-specific config form |
| | NOTIFY: channel multi-check + title_tpl input + body_tpl textarea + receiver checkboxes |
| | WEBHOOK: url input + method select + body_tpl textarea |
| | OPSFLOW: flow selector + variable mapping key-value pairs |
| | MODIFY_FIELD: field_name input + field_value input + static/template toggle |

**Template variable hints:** All text fields show a tooltip listing available variables:
`${ticket_id}`, `${ticket_title}`, `${priority}`, `${current_state}`, `${starter_name}`, `${processor_name}`, `${field.xxx}`

**State picker workflow linkage:** When `event_type` is ENTER_STATE or LEAVE_STATE, the `states` multi-select dropdown filters its options based on the selected `workflow`:
- No workflow selected → show all states from all workflows (grouped by workflow name)
- Workflow selected → show only states belonging to that workflow (fetched via `GET /api/itsm/workflows/{id}/states/` or extracted from the workflow's deployed version)
- FLOW_START/FLOW_END selected → hide `states` picker entirely (not applicable)

### 4.2 ITSM Tab Integration

Add to `seed_iam_page_configs.py` a new page permission record:
- `key: 'trigger'`, `app: 'itsm'`, `label_zh: '触发器'`, `icon: 'Lightning'`

The frontend `index.vue` tab rendering is data-driven — new tab appears automatically when the API returns it.

### 4.3 API Client

```typescript
// web/src/api/itsm/index.ts
export const triggerApi = createCrudApi('triggers')
export const triggerExecutionApi = createCrudApi('trigger-executions')
```

### 4.4 i18n

Namespace: `message.itsmPage.trigger.*`

Key entries (zh-CN + en):
- `title`, `create`, `edit`, `delete`
- `eventType`: event type labels (流程开始/Flow Start, 流程结束/Flow End, 接入节点/Enter State, 离开节点/Leave State)
- `actionType`: action type labels (发送通知/Notify, HTTP回调/Webhook, 触发运维流程/OpsFlow, 修改工单字段/Modify Field)
- `matchWorkflow`, `matchStates`, `matchPriority`, `condition`
- `actionConfig`: action config field labels (通知渠道/Channels, 标题模板/Title Template, etc.)
- `templateHints`: template variable hints

---

## 5. Execution Flow

```
Workflow/Ticket event occurs
  │
  ├─ FLOW_START     → ITSMEngine.run()
  ├─ FLOW_END        → Ticket.do_before_end_pipeline()
  ├─ ENTER_STATE     → signals.post_set_state (READY)
  └─ LEAVE_STATE     → signals.post_set_state (from RUNNING)
       │
       ▼
  TriggerExecutor.enqueue(ticket, event_type, state_id)
       │
       ▼
  TriggerMatcher.match()
    ├─ Filter: is_active + event_type
    ├─ Filter: workflow (null or match)
    ├─ Filter: priority (blank or match)
    ├─ Filter: states (empty or match)
    └─ Filter: condition (empty or ConditionEvaluator)
       │
       ▼
  For each matched Trigger:
    TriggerExecution.objects.create(status='PENDING')
       │
       ▼ (APScheduler, every 10s)
  TriggerExecutor.process_pending()
    ├─ Fetch batch of PENDING executions
    ├─ For each, run actions in order:
    │   ├─ NotifyRunner  → NotificationService.notify_users()
    │   ├─ WebhookRunner → requests.post()
    │   ├─ OpsflowRunner → FlowEngine.run()
    │   └─ ModifyFieldRunner → ticket.meta update
    └─ Update execution.status + action_results
```

---

## 6. Migration Plan

### 6.1 Migration operations (single migration)

1. CreateModel: Trigger
2. CreateModel: TriggerAction
3. CreateModel: TriggerExecution

No data migration needed — brand new feature, no existing data to migrate.

### 6.2 Rollback

Reverse migration drops all three tables. No side effects on existing data.

---

## 7. Files Summary

### New Files (6)

| File | Purpose |
|------|---------|
| `backend/itsm/models/trigger.py` | Trigger, TriggerAction, TriggerExecution models |
| `backend/itsm/services/trigger_service.py` | TriggerMatcher, TriggerExecutor, ActionRunner, TemplateResolver |
| `backend/itsm/serializers/trigger.py` | TriggerSerializer, TriggerActionSerializer |
| `backend/itsm/views/trigger_views.py` | TriggerViewSet |
| `backend/itsm/tests/test_trigger.py` | Unit + integration tests |
| `web/src/views/apps/itsm/components/TriggerList.vue` | Trigger management page |

### Modified Files (10)

| File | Change |
|------|--------|
| `backend/itsm/models/__init__.py` | Export Trigger, TriggerAction, TriggerExecution |
| `backend/itsm/signals.py` | Insert ENTER_STATE/LEAVE_STATE enqueue in post_set_state handler |
| `backend/itsm/services/itsm_engine.py` | Insert FLOW_START enqueue in run() |
| `backend/itsm/models/ticket.py` | Insert FLOW_END enqueue in do_before_end_pipeline() |
| `backend/itsm/urls.py` | Register trigger router |
| `backend/itsm/apps.py` | Add trigger_executor APScheduler job |
| `web/src/api/itsm/index.ts` | Add triggerApi |
| `web/src/views/apps/itsm/index.vue` | Add trigger tab (data-driven, via seed_iam_page_configs) |
| `web/src/i18n/pages/itsm/zh-cn.ts` | Add trigger.* keys |
| `web/src/i18n/pages/itsm/en.ts` | Add trigger.* keys |
| `backend/iam/management/commands/seed_iam_page_configs.py` | Add trigger page permission |

### Removed (0)

No files removed.

---

## 8. Test Plan

### Unit Tests

| ID | Test | Verify |
|----|------|--------|
| T1 | TriggerMatcher — no conditions | Returns all active triggers matching event_type |
| T2 | TriggerMatcher — workflow filter | Matches specific workflow or null (global) |
| T3 | TriggerMatcher — state filter | ENTER/LEAVE matches specific state or empty |
| T4 | TriggerMatcher — priority filter | Matches specific priority or blank |
| T5 | TriggerMatcher — field condition | `{"logic":"AND","rules":[{"field":"urgency","op":"==","value":"紧急"}]}` filters correctly |
| T6 | TriggerExecutor.enqueue — no match | No TriggerExecutions created when nothing matches |
| T7 | TriggerExecutor.enqueue — with match | Creates PENDING TriggerExecutions for each matched trigger |
| T8 | TriggerExecutor.process_pending — multi-action order | Actions executed in `order` sequence |
| T9 | NotifyRunner | Calls NotificationService with correct channels/receivers/templates |
| T10 | WebhookRunner | HTTP POST with rendered template body |
| T11 | OpsflowRunner | Creates FlowExecution record |
| T12 | ModifyFieldRunner | Updates ticket.meta.form_data[field_name] |
| T13 | TemplateResolver | `${ticket_id}`, `${field.xxx}` correctly resolved |
| T14 | Failure isolation | Single action failure doesn't block subsequent actions; execution marked FAILED |

### Integration Tests

| ID | Test | Verify |
|----|------|--------|
| T15 | FLOW_START enqueue | ITSMEngine.run() triggers enqueue |
| T16 | FLOW_END enqueue | do_before_end_pipeline() triggers enqueue |
| T17 | ENTER_STATE enqueue | post_set_state READY triggers enqueue |
| T18 | LEASE_STATE enqueue | post_set_state from RUNNING triggers enqueue |
| T19 | Trigger CRUD API | list/create/retrieve/update/delete with nested actions |
| T20 | TriggerExecution list API | Returns paginated execution history for trigger |
| T21 | End-to-end: FLOW_START → notify | Trigger fires, execution processes, notification sent |
| T22 | End-to-end: ENTER_STATE with condition | Only matching tickets trigger the action |

### Manual Verification

| Step | Action | Expected |
|------|--------|----------|
| V1 | Navigate to ITSM → 触发器 tab | Trigger list page loads |
| V2 | Click 新建, fill form with NOTIFY action | Trigger created, appears in list |
| V3 | Create ticket matching trigger conditions | TriggerExecution appears in history |
| V4 | Check notification | User receives configured notification |
| V5 | Toggle is_active off | No new executions for disabled trigger |
| V6 | Edit trigger — change workflow filter | Updated trigger only matches new workflow |

---

## 9. Verification

After implementation, verify end-to-end:

1. `python manage.py migrate` — single migration runs cleanly
2. `python manage.py test itsm.tests.test_trigger` — all 22 tests pass
3. Create a Trigger in UI → saves with nested actions
4. Submit a ticket matching trigger → TriggerExecution created, actions processed within 10s
5. Notification received via configured channels
6. Trigger execution history visible in UI
7. Disable trigger → no further executions
8. Modify field action updates ticket form data correctly