# Implementation Plan: ITSM 简化触发器

> **Spec:** [2026-07-10-simplified-trigger-design.md](../specs/2026-07-10-simplified-trigger-design.md)
> **Priority:** 高
> **Pattern Reference:** SlaPolicyList.vue (table+dialog CRUD), SlaPolicySerializer (nested write), ItsmProjectViewSet

---

## Tasks

### 1. [Backend] Trigger Models + Migration

**File:** `backend/itsm/models/trigger.py` (NEW)

Create three models following the `CoreModel` pattern from `SlaPolicy`:

```python
# -*- coding: utf-8 -*-
"""Trigger models for event-driven ITSM automation."""
from django.db import models
from common.utils.models import CoreModel, table_prefix


class Trigger(CoreModel):
    EVENT_TYPE_CHOICES = (
        ('FLOW_START', '流程开始'),
        ('FLOW_END', '流程结束'),
        ('ENTER_STATE', '接入节点'),
        ('LEAVE_STATE', '离开节点'),
    )
    PRIORITY_CHOICES = (
        ('', '全部'),
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )

    name = models.CharField(max_length=128, verbose_name="触发器名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="触发器名称(英文)")
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_triggers', verbose_name='Project',
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    event_type = models.CharField(max_length=16, choices=EVENT_TYPE_CHOICES, verbose_name="事件类型")
    workflow = models.ForeignKey(
        'itsm.Workflow', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='triggers', verbose_name="流程模板",
        help_text="留空匹配所有流程",
    )
    states = models.ManyToManyField(
        'itsm.State', blank=True, related_name='triggers', verbose_name="适用节点",
        help_text="仅 ENTER_STATE/LEAVE_STATE 事件生效",
    )
    priority = models.CharField(
        max_length=4, choices=PRIORITY_CHOICES, blank=True, default='',
        verbose_name="优先级过滤",
    )
    condition = models.JSONField(
        default=dict, blank=True, verbose_name="字段条件",
        help_text='{"logic":"AND","rules":[{"field":"...","op":"==","value":"..."}]}',
    )

    class Meta:
        db_table = table_prefix + "itsm_trigger"
        verbose_name = "触发器"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name


class TriggerAction(models.Model):
    ACTION_TYPE_CHOICES = (
        ('NOTIFY', '发送通知'),
        ('WEBHOOK', 'HTTP 回调'),
        ('OPSFLOW', '触发运维流程'),
        ('MODIFY_FIELD', '修改工单字段'),
    )

    trigger = models.ForeignKey(
        Trigger, on_delete=models.CASCADE, related_name='actions', verbose_name="触发器"
    )
    order = models.IntegerField(default=0, verbose_name="执行顺序")
    action_type = models.CharField(max_length=16, choices=ACTION_TYPE_CHOICES, verbose_name="动作类型")
    config = models.JSONField(default=dict, verbose_name="动作配置")

    class Meta:
        db_table = table_prefix + "itsm_trigger_action"
        verbose_name = "触发器动作"
        verbose_name_plural = verbose_name
        ordering = ['order']

    def __str__(self):
        return f"{self.trigger.name} / {self.get_action_type_display()}"


class TriggerExecution(models.Model):
    STATUS_CHOICES = (
        ('PENDING', '等待执行'),
        ('SUCCESS', '执行成功'),
        ('FAILED', '执行失败'),
    )

    trigger = models.ForeignKey(
        Trigger, on_delete=models.SET_NULL, null=True, related_name='executions',
        verbose_name="触发器",
    )
    ticket = models.ForeignKey(
        'itsm.Ticket', on_delete=models.CASCADE, related_name='trigger_executions',
        verbose_name="工单",
    )
    event_type = models.CharField(max_length=16, verbose_name="事件类型")
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='PENDING', verbose_name="状态")
    action_results = models.JSONField(default=list, verbose_name="动作执行结果")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = table_prefix + "itsm_trigger_execution"
        verbose_name = "触发器执行记录"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} → {self.status}"
```

**File:** `backend/itsm/models/__init__.py` (MODIFY)

Add imports + `__all__` entries:
```python
from .trigger import Trigger, TriggerAction, TriggerExecution
# Add to __all__: 'Trigger', 'TriggerAction', 'TriggerExecution',
```

**Migration:** Run `python manage.py makemigrations itsm` — creates three tables.

---

### 2. [Backend] Trigger Serializers (Nested Write)

**File:** `backend/itsm/serializers/trigger.py` (NEW)

```python
# -*- coding: utf-8 -*-
"""Serializers for Trigger & TriggerAction with i18n support"""
from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import Trigger, TriggerAction


class TriggerActionSerializer(CustomModelSerializer):
    class Meta:
        model = TriggerAction
        fields = "__all__"
        read_only_fields = ['trigger']


class TriggerSerializer(CustomModelSerializer):
    actions = TriggerActionSerializer(many=True, required=False)
    state_ids = serializers.PrimaryKeyRelatedField(
        source='states', many=True,
        queryset=Trigger._meta.get_field('states').remote_field.model.objects.all(),
        required=False, write_only=True,
    )

    class Meta:
        model = Trigger
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        if instance.workflow_id:
            data['workflow_name'] = instance.workflow.display_name(lang)
        data['states'] = [
            {'id': s.id, 'name': s.name, 'type': s.type, 'node_key': s.node_key}
            for s in instance.states.all()
        ]
        # Nest actions in representation for display
        data['actions'] = TriggerActionSerializer(instance.actions.all(), many=True).data
        return data

    def create(self, validated_data):
        actions_data = validated_data.pop('actions', [])
        states = validated_data.pop('states', [])  # via source='states'
        trigger = Trigger.objects.create(**validated_data)
        trigger.states.set(states)
        for i, action_data in enumerate(actions_data):
            TriggerAction.objects.create(trigger=trigger, order=i, **action_data)
        return trigger

    def update(self, instance, validated_data):
        actions_data = validated_data.pop('actions', None)
        states = validated_data.pop('states', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if states is not None:
            instance.states.set(states)
        if actions_data is not None:
            instance.actions.all().delete()
            for i, action_data in enumerate(actions_data):
                TriggerAction.objects.create(trigger=instance, order=i, **action_data)
        return instance
```

---

### 3. [Backend] Trigger Service Layer

**File:** `backend/itsm/services/trigger_service.py` (NEW)

Full service module with TriggerMatcher, TriggerExecutor, ActionRunner, TemplateResolver, and ConditionEvaluator. Key structure:

```python
# -*- coding: utf-8 -*-
"""Trigger matching, execution, and action dispatch."""
import json
import logging
import re
from datetime import timedelta

import requests
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class TemplateResolver:
    """Resolve ${variable} templates against ticket context."""
    @staticmethod
    def resolve(template: str, ticket, current_state_name: str = '') -> str:
        if not template:
            return template
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
        for match in re.finditer(r'\$\{field\.(\w+)\}', template):
            field_val = ticket.meta.get('form_data', {}).get(match.group(1), '')
            template = template.replace(match.group(0), str(field_val))
        return template


class ConditionEvaluator:
    """Evaluate field-level conditions against ticket form data."""
    @staticmethod
    def evaluate(condition: dict, ticket) -> bool:
        if not condition or not condition.get('rules'):
            return True
        logic = condition.get('logic', 'AND')
        results = []
        for rule in condition['rules']:
            field_value = ConditionEvaluator._resolve_value(ticket, rule.get('source'), rule['field'])
            results.append(ConditionEvaluator._apply_op(field_value, rule['op'], rule['value']))
        return all(results) if logic == 'AND' else any(results)

    @staticmethod
    def _resolve_value(ticket, source, field):
        if source == 'ticket' or not source:
            return ticket.meta.get('form_data', {}).get(field)
        # Node-scoped fields: resolve from pipeline context
        try:
            from pipeline.eri.runtime import BambooDjangoRuntime
            runtime = BambooDjangoRuntime()
            pipeline_data = runtime.get_data(ticket.pipeline_id)
            # Flatten: {node_key_field: value}
            return pipeline_data.get(f'{source}_{field}')
        except Exception:
            return None

    @staticmethod
    def _apply_op(left, op, right):
        """Apply comparison operator. Coerce types for numeric comparison."""
        try:
            if op in ('>', '<', '>=', '<=') and left is not None:
                left = float(left)
                right = float(right)
            ops = {
                '==': lambda a, b: str(a) == str(b),
                '!=': lambda a, b: str(a) != str(b),
                '>': lambda a, b: a > b,
                '<': lambda a, b: a < b,
                '>=': lambda a, b: a >= b,
                '<=': lambda a, b: a <= b,
                'in': lambda a, b: str(a) in str(b).split(','),
                'notin': lambda a, b: str(a) not in str(b).split(','),
            }
            if op in ops:
                return ops[op](left, right)
            return True
        except (ValueError, TypeError):
            return False


class TriggerMatcher:
    @staticmethod
    def match(ticket, event_type, state_id=None) -> list:
        from itsm.models import Trigger, State

        qs = Trigger.objects.filter(is_active=True, event_type=event_type)
        qs = qs.filter(
            Q(workflow__isnull=True) |
            Q(workflow=ticket.workflow_version.workflow)
        )
        qs = qs.filter(
            Q(priority='') | Q(priority=ticket.priority)
        )
        if state_id:
            state = State.objects.get(id=state_id)
            qs = qs.filter(
                Q(states__isnull=True) | Q(states=state)
            )

        matched = []
        for trigger in qs:
            # FLOW_START: skip field conditions (form_data is empty)
            if event_type != 'FLOW_START' and trigger.condition:
                if not ConditionEvaluator.evaluate(trigger.condition, ticket):
                    continue
            matched.append(trigger)
        return matched


class ActionRunner:
    @staticmethod
    def run(action, ticket, current_state_name='') -> dict:
        try:
            if action.action_type == 'NOTIFY':
                return NotifyRunner.run(action.config, ticket, current_state_name)
            elif action.action_type == 'WEBHOOK':
                return WebhookRunner.run(action.config, ticket, current_state_name)
            elif action.action_type == 'OPSFLOW':
                return OpsflowRunner.run(action.config, ticket)
            elif action.action_type == 'MODIFY_FIELD':
                return ModifyFieldRunner.run(action.config, ticket)
            return {'status': 'FAILED', 'error': f'Unknown action: {action.action_type}'}
        except Exception as e:
            logger.warning(f'ActionRunner error: {e}')
            return {'action_type': action.action_type, 'status': 'FAILED', 'error': str(e)}


class NotifyRunner:
    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        from itsm.services.notifications import NotificationService
        title = TemplateResolver.resolve(config.get('title_tpl', ''), ticket, current_state_name)
        body = TemplateResolver.resolve(config.get('body_tpl', ''), ticket, current_state_name)
        # Resolve receivers
        receivers = config.get('receivers', [])
        users = NotifyRunner._resolve_receivers(receivers, config.get('custom_users', []), ticket)
        NotificationService.notify_users(users, title, body, config.get('channels', ['site']))
        return {'action_type': 'NOTIFY', 'status': 'SUCCESS'}
    # ... helper methods ...


class WebhookRunner:
    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        url = config.get('url')
        body_tpl = config.get('body_tpl', '{}')
        body = TemplateResolver.resolve(body_tpl, ticket, current_state_name)
        resp = requests.post(
            url, json=json.loads(body),
            headers=config.get('headers', {}),
            timeout=config.get('timeout', 30),
        )
        resp.raise_for_status()
        return {'action_type': 'WEBHOOK', 'status': 'SUCCESS', 'http_status': resp.status_code}


class OpsflowRunner:
    @staticmethod
    def run(config, ticket) -> dict:
        # Reuse TicketOpsflowConfig pattern
        from itsm.services.opsflow_trigger import OpsflowTriggerService
        OpsflowTriggerService.execute(ticket, config.get('flow_id'),
                                       config.get('variable_mapping', {}))
        return {'action_type': 'OPSFLOW', 'status': 'SUCCESS'}


class ModifyFieldRunner:
    @staticmethod
    def run(config, ticket) -> dict:
        field_name = config['field_name']
        field_value = config['field_value']
        if config.get('value_type') == 'template':
            field_value = TemplateResolver.resolve(field_value, ticket)
        ticket.meta['form_data'][field_name] = field_value
        ticket.save(update_fields=['meta'])
        return {'action_type': 'MODIFY_FIELD', 'status': 'SUCCESS'}


class TriggerExecutor:
    @staticmethod
    def enqueue(ticket, event_type, state_id=None):
        triggers = TriggerMatcher.match(ticket, event_type, state_id)
        for trigger in triggers:
            from itsm.models import TriggerExecution
            TriggerExecution.objects.create(
                trigger=trigger, ticket=ticket,
                event_type=event_type, status='PENDING',
            )

    @staticmethod
    def process_pending():
        from itsm.models import TriggerExecution
        executions = TriggerExecution.objects.filter(status='PENDING').select_related(
            'trigger', 'ticket'
        ).prefetch_related('trigger__actions')[:50]

        for exec in executions:
            try:
                results = []
                current_state_name = exec.ticket.current_status or ''
                for action in exec.trigger.actions.order_by('order'):
                    try:
                        result = ActionRunner.run(action, exec.ticket, current_state_name)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            'action_id': action.id, 'action_type': action.action_type,
                            'status': 'FAILED', 'error': str(e),
                        })
                exec.action_results = results
                has_failure = any(r.get('status') == 'FAILED' for r in results)
                exec.status = 'FAILED' if has_failure else 'SUCCESS'
            except Exception as e:
                exec.status = 'FAILED'
                exec.action_results = [{'error': str(e)}]
            exec.save()

    @staticmethod
    def cleanup_old_executions():
        """Delete TriggerExecution records older than 365 days."""
        from itsm.models import TriggerExecution
        cutoff = timezone.now() - timedelta(days=365)
        deleted, _ = TriggerExecution.objects.filter(created_at__lt=cutoff).delete()
        if deleted:
            logger.info(f'Cleaned up {deleted} old TriggerExecution records')
```

---

### 4. [Backend] TriggerViewSet + URL Registration

**File:** `backend/itsm/views/trigger_views.py` (NEW)

```python
# -*- coding: utf-8 -*-
"""Trigger CRUD — project-scoped with multi-tenant isolation"""
from ..models import Trigger, TriggerExecution
from ..serializers.trigger import TriggerSerializer
from .workflow_views import ItsmProjectViewSet
from rest_framework.decorators import action
from rest_framework.response import Response


class TriggerViewSet(ItsmProjectViewSet):
    """触发器 CRUD — project-scoped"""
    model = Trigger
    queryset = Trigger.objects.prefetch_related('actions', 'states').select_related('workflow')
    serializer_class = TriggerSerializer
    filter_fields = ['event_type', 'workflow', 'is_active']
    ordering = ['-create_datetime']

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        trigger = self.get_object()
        qs = TriggerExecution.objects.filter(trigger=trigger).order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                [{'id': e.id, 'status': e.status, 'event_type': e.event_type,
                  'action_results': e.action_results, 'created_at': e.created_at,
                  'ticket_id': e.ticket_id}
                 for e in page]
            )
        return Response([])
```

**File:** `backend/itsm/urls.py` (MODIFY)

Add import and router registration:
```python
from .views.trigger_views import TriggerViewSet

# Inside router registrations block:
router.register(r'triggers', TriggerViewSet)
```

---

### 5. [Backend] Signal Integration + Engine Hooks + Scheduler

**File:** `backend/itsm/signals.py` (MODIFY)

In `itsm_post_set_state_handler`, after the existing status mapping logic, insert trigger enqueue. Locate the section where `node_status` is updated and add:

```python
# ---- Trigger enqueue for ENTER_STATE / LEAVE_STATE ----
from itsm.models import State as StateModel
if state_id and to_state == states.READY:
    from itsm.services.trigger_service import TriggerExecutor
    state = StateModel.objects.get(id=state_id)
    if state.type not in ('START', 'END'):
        TriggerExecutor.enqueue(ticket, 'ENTER_STATE', state_id)
# LEAVE_STATE: detect when a node transitions AWAY from RUNNING
# Track previous state in a local dict or use the old node_status entry
if state_id and previous_to_state == states.RUNNING:
    from itsm.services.trigger_service import TriggerExecutor
    state = StateModel.objects.get(id=state_id)
    if state.type not in ('START', 'END'):
        TriggerExecutor.enqueue(ticket, 'LEAVE_STATE', state_id)
```

Note: The LEAVE_STATE detection needs the bamboo node's PREVIOUS state. The `post_set_state` signal provides `to_state` but not `from_state`. To detect the LEAVE transition, check `ticket.node_status` before mutation — if the node was previously `'RUNNING'`, it's a LEAVE event.

**File:** `backend/itsm/services/itsm_engine.py` (MODIFY)

In `ITSMEngine.run()`, after successful pipeline start:

```python
from itsm.services.trigger_service import TriggerExecutor
TriggerExecutor.enqueue(self.ticket, 'FLOW_START')
```

**File:** `backend/itsm/models/ticket.py` (MODIFY)

In `do_before_end_pipeline()`, before stopping SLA:

```python
from itsm.services.trigger_service import TriggerExecutor
TriggerExecutor.enqueue(self, 'FLOW_END')
```

**File:** `backend/itsm/apps.py` (MODIFY)

In `ItsmConfig.ready()`, inside the existing APScheduler `if` block, add two new jobs:

```python
from itsm.services.trigger_service import TriggerExecutor

scheduler.add_job(
    TriggerExecutor.process_pending,
    trigger=IntervalTrigger(seconds=10),
    id='itsm_trigger_executor',
    name='Trigger executor',
    replace_existing=True,
    coalesce=True,
    max_instances=1,
    misfire_grace_time=5,
)

scheduler.add_job(
    TriggerExecutor.cleanup_old_executions,
    trigger=IntervalTrigger(days=1),
    id='itsm_trigger_cleanup',
    name='Trigger execution cleanup',
    replace_existing=True,
    coalesce=True,
    max_instances=1,
    misfire_grace_time=3600,
)
```

---

### 6. [Backend] IAM Seed — Page Config + Permissions

**File:** `backend/iam/management/commands/seed_iam_page_configs.py` (MODIFY)

In `_seed_permissions()`, add:
```python
('itsm:trigger:edit', '编辑触发器', 'itsm'),
```

In `_seed_page_configs()`, add the ITSM tab entry (sort to appear after schedule):
```python
{'key': 'trigger', 'label_zh': '触发器', 'label_en': 'Triggers', 'icon': 'Lightning',
 'required_perm': None, 'sort': 70},
```

Add buttons under a new `'trigger'` key:
```python
'trigger': [
    {'key': 'edit', 'label_zh': '编辑触发器', 'label_en': 'Edit Trigger',
     'icon': 'Edit', 'required_perm': 'itsm:trigger:edit', 'style': 'primary', 'sort': 10},
],
```

In `_seed_role_permissions()`, add to itsm_admin role:
```python
'itsm:trigger:edit',
```

---

### 7. [Frontend] API Client

**File:** `web/src/api/itsm/index.ts` (MODIFY)

Add after existing `createCrudApi` exports:
```typescript
export const triggerApi = createCrudApi('triggers')
```

---

### 8. [Frontend] i18n Translation Keys

**File:** `web/src/i18n/pages/itsm/zh-cn.ts` (MODIFY)

Add `trigger` section:
```typescript
trigger: {
  title: '触发器',
  create: '新建触发器',
  edit: '编辑触发器',
  delete: '删除触发器',
  deleteConfirm: '确定删除此触发器?',
  eventType: '事件类型',
  eventFlowStart: '流程开始',
  eventFlowEnd: '流程结束',
  eventEnterState: '接入节点',
  eventLeaveState: '离开节点',
  matchWorkflow: '适用流程',
  matchStates: '适用节点',
  matchPriority: '优先级过滤',
  matchAllWorkflows: '全部流程',
  matchAllStates: '全部节点',
  matchAllPriorities: '全部优先级',
  condition: '匹配条件(可选)',
  conditionHelp: '表单字段条件表达式，留空表示总是匹配',
  actions: '动作列表',
  addAction: '添加动作',
  actionType: '动作类型',
  actionNotify: '发送通知',
  actionWebhook: 'HTTP 回调',
  actionOpsflow: '触发运维流程',
  actionModifyField: '修改工单字段',
  notifyChannels: '通知渠道',
  notifyTitleTpl: '标题模板',
  notifyBodyTpl: '正文模板',
  notifyReceivers: '接收人',
  receiverProcessor: '处理人',
  receiverStarter: '提单人',
  receiverLeader: '组长',
  receiverCustom: '指定用户',
  webhookUrl: 'URL',
  webhookMethod: '请求方法',
  webhookBodyTpl: '请求体模板',
  webhookTimeout: '超时(秒)',
  opsflowFlow: '运维流程',
  opsflowVarMapping: '变量映射',
  modifyFieldName: '字段名',
  modifyFieldValue: '字段值',
  modifyValueStatic: '静态值',
  modifyValueTemplate: '模板变量',
  templateHints: '可用变量: ${ticket_id}, ${ticket_title}, ${priority}, ${current_state}, ${starter_name}, ${processor_name}, ${field.字段名}',
  executionHistory: '执行历史',
  executionStatus: '状态',
  executionTime: '执行时间',
  statusPending: '等待执行',
  statusSuccess: '成功',
  statusFailed: '失败',
},
```

**File:** `web/src/i18n/pages/itsm/en.ts` (MODIFY)

Add equivalent `trigger` section with English values.

---

### 9. [Frontend] TriggerList.vue Component

**File:** `web/src/views/apps/itsm/components/TriggerList.vue` (NEW)

Follow the EXACT pattern from `SlaPolicyList.vue`:

**Template structure:**
- Outer `<div>` wrapper
- `<div class="itsm-table-card">` with header (title + create button with `v-can="'itsm:trigger:edit'"`)
- `<el-table>` with columns: 名称 | 事件类型(tag) | 流程 | 优先级 | 启用(switch) | 操作(edit/delete)
- `<el-dialog>` with form sections (width: 800px, `destroy-on-close`, `append-to-body`)
  - Basic info: name, name_en, project selector, is_active switch
  - Event config: event_type dropdown → conditional: workflow selector, states multi-select (filtered by workflow), priority dropdown
  - Condition (collapsible): embedded `ConditionDialog` — pass ticket form fields from the selected workflow
  - Actions list: v-for cards, each with action_type dropdown + type-specific config
- Execution history: optional `<el-dialog>` for viewing past executions

**Script pattern:**
```typescript
import { ref, watch, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { triggerApi, workflowApi } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const emits = defineEmits<{ (e: 'stats', v: any[]): void }>()
// ... reactive state, loadItems, loadOptions, onCreate, onEdit, onSave, onDelete
```

**State picker linkage:** When `form.event_type` is ENTER_STATE or LEAVE_STATE, show the `states` multi-select. When `form.workflow` changes, fetch states for that workflow. When event_type is FLOW_START/FLOW_END, hide `states` picker.

**Key computed:**
```typescript
const showStatePicker = computed(() =>
  form.value.event_type === 'ENTER_STATE' || form.value.event_type === 'LEAVE_STATE'
)
```

---

### 10. [Frontend] ITSM index.vue Integration

**File:** `web/src/views/apps/itsm/index.vue` (MODIFY)

1. Import TriggerList:
```typescript
import TriggerList from './components/TriggerList.vue'
```

2. Add tab content block (follow the existing pattern):
```html
<div v-if="isVisited('trigger')" v-show="activeTab === 'trigger'" class="itsm-section g-fade-in-up">
  <TriggerList :active="activeTab === 'trigger'" />
</div>
```

3. Add `'trigger'` to the `useTabLazyLoad` tabs array.

4. Add hero stats switch case:
```typescript
case 'trigger':
  updateStats([{ value: '-', label: '触发器总数' }, { value: '-', label: '已启用' }])
  break
```

Note: The tab itself is data-driven from `page-permissions` API — once `seed_iam_page_configs` includes the trigger tab, it appears automatically. The lazy-load block just needs to exist.

---

### 11. Verification

**Backend tests:**
```bash
python manage.py test itsm.tests.test_trigger
```

Covering the 22 test cases from the spec: model CRUD, TriggerMatcher matching logic, TriggerExecutor enqueue/process, ActionRunner dispatch, TemplateResolver, failure isolation, signal integration.

**Frontend build check:**
```bash
cd web && npx vue-tsc --noEmit && npm run build
```

**Manual end-to-end:**
1. `python manage.py seed_iam_page_configs` — trigger tab appears
2. Navigate to ITSM → 触发器 tab
3. Create trigger: FLOW_START + NOTIFY action
4. Submit a matching ticket → check TriggerExecution created
5. Verify notification received via configured channels
6. Check execution history in trigger detail

---

## File Summary

| # | Action | File |
|---|--------|------|
| 1 | NEW | `backend/itsm/models/trigger.py` |
| 2 | MODIFY | `backend/itsm/models/__init__.py` |
| 3 | NEW | `backend/itsm/serializers/trigger.py` |
| 4 | NEW | `backend/itsm/services/trigger_service.py` |
| 5 | NEW | `backend/itsm/views/trigger_views.py` |
| 6 | MODIFY | `backend/itsm/urls.py` |
| 7 | MODIFY | `backend/itsm/signals.py` |
| 8 | MODIFY | `backend/itsm/services/itsm_engine.py` |
| 9 | MODIFY | `backend/itsm/models/ticket.py` |
| 10 | MODIFY | `backend/itsm/apps.py` |
| 11 | MODIFY | `backend/iam/management/commands/seed_iam_page_configs.py` |
| 12 | MODIFY | `web/src/api/itsm/index.ts` |
| 13 | MODIFY | `web/src/i18n/pages/itsm/zh-cn.ts` |
| 14 | MODIFY | `web/src/i18n/pages/itsm/en.ts` |
| 15 | NEW | `web/src/views/apps/itsm/components/TriggerList.vue` |
| 16 | MODIFY | `web/src/views/apps/itsm/index.vue` |
| 17 | NEW | `backend/itsm/tests/test_trigger.py` |

- **New files:** 6 (models, serializers, service, views, frontend, tests)
- **Modified files:** 10 (models init, urls, signals, engine, ticket, apps, seed, api, i18n×2, index.vue)
- **Migration:** 1 auto-generated migration
