# itsm — Module Index

> Last auto-update: 2026-07-11 | Trigger commit: c029ad11

## `models/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `catalog.py` | ServiceCategory and SlaPolicy — service catalog + SLA policy | `ServiceCategory`, `SlaPolicy` |
| `delegation.py` | ApprovalDelegate model — approval delegation | `ApprovalDelegate` |
| `escalation.py` | Escalation Level model — SLA timeout escalation chain | `EscalationLevel` |
| `field.py` | ITSM Field model — per-node field definitions | `Field` |
| `notification_template.py` | NotificationTemplate model — reusable notification presets | `NotificationTemplate` |
| `preset.py` | ITSM Preset model — reusable field value presets | `Preset` |
| `schedule.py` | SLA Working Time Model — Schedule, Day, Duration | `Duration`, `Day`, `Schedule` |
| `service_item.py` | ServiceItem model — service catalog core entity | `ServiceItem` |
| `sla.py` | ITSM SLA model — ticket SLA timer | `SlaTask` |
| `state.py` | ITSM State model — workflow node definition | `State` |
| `ticket.py` | ITSM Ticket model — workflow runtime instance | `Ticket`, `TicketStatus`, `SignTask` |
| `transition.py` | ITSM Transition model — edge with condition | `Transition` |
| `trigger.py` | Trigger models for event-driven ITSM automation | `Trigger`, `TriggerAction`, `TriggerExecution` |
| `workflow.py` | ITSM Workflow model — template + versioning | `Workflow`, `WorkflowVersion` |

## `services/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `ai_generator.py` | AI flow generation | `AIGenerator` |
| `bamboo_engine.py` | Bamboo Engine shared utilities | `activity_callback()`, `revoke_by_pipeline_id()` |
| `change_calendar.py` | Change Calendar aggregation — Ticket + SchedulePlan | `ChangeCalendarService` |
| `condition_utils.py` | Condition expression evaluation | shared with opsflow |
| `itsm_engine.py` | ITSM Bamboo Pipeline execution engine | `ITSMEngine` |
| `notifications.py` | ITSM notification service | `NotificationService` |
| `opsflow_trigger.py` | ITSM to OpsFlow bridge | `TicketOpsflowConfig`, `OpsflowTriggerService` |
| `role_resolver.py` | Processor resolver | `resolve_processors()` |
| `sla_engine.py` | SLA engine — ticket SLA lifecycle | `SlaEngine` |
| `sla_time.py` | SLA Time Engine — working-time deadline calculation | `SlaTime`, `TimeDelta`, `MultiTimeDelta` |
| `trigger_service.py` | Trigger matching, execution, and action dispatch | `TriggerMatcher`, `TriggerExecutor`, `ActionRunner`, `TemplateResolver` |
| `workflow_builder.py` | ITSM Workflow to bamboo-pipeline converter | `ITSMWorkflowBuilder` |
| `workflow_validator.py` | ITSM Workflow Validator — deploy-time checks | `validate_workflow()` |

## `views/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `base.py` | ViewSet base — project isolation | `ProjectFilteredViewSet` |
| `change_calendar.py` | Change Calendar ViewSet | `ChangeCalendarViewSet` |
| `dashboard.py` | ITSM Dashboard view | `DashboardViewSet` |
| `delegation.py` | Delegation views | `DelegationViewSet` |
| `escalation_views.py` | Escalation views | `EscalationLevelViewSet` |
| `notification_template_views.py` | NotificationTemplate CRUD | `NotificationTemplateViewSet` |
| `preset_views.py` | Preset ViewSet | `PresetViewSet` |
| `schedule_views.py` | Schedule/Day/Duration CRUD | `DurationViewSet`, `DayViewSet`, `ScheduleViewSet` |
| `service_item.py` | ServiceItem views | `ServiceItemViewSet` |
| `ticket_views.py` | ITSM Ticket views | `TicketViewSet` |
| `trigger_views.py` | Trigger CRUD | `TriggerViewSet` |
| `views.py` | ServiceCategory, SlaPolicy | `ServiceCategoryViewSet`, `SlaPolicyViewSet` |
| `workflow_views.py` | Workflow engine views | `ItsmProjectViewSet`, `WorkflowViewSet`, `StateViewSet` |

## `serializers/`

| File | Purpose |
|------|---------|
| `change_calendar.py` | `CalendarItemSerializer` — unified ticket + schedule output |
| `notification_template.py` | `NotificationTemplateSerializer` |
| `trigger.py` | `TriggerSerializer` (nested actions), `TriggerActionSerializer` |

## Root (`itsm/`)

| File | Purpose |
|------|---------|
| `signals.py` | Post-save handlers — SLA + post_set_state sync + trigger enqueue |
| `sla_check_job.py` | `sla_check_job()` — periodic SLA checker |
| `tasks.py` | Celery tasks — `sla_check()`, `auto_resolve_expired_tickets()` |
| `urls.py` | URL routing — SimpleRouter + AI generation paths |

## `pipeline_plugins/`

| File | Purpose |
|------|---------|
| `components.py` | Bamboo pipeline component registration — FillForm/Approval/Sign/AutoTask |
