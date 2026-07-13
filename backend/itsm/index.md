# itsm — 模块索引

> 上次自动更新: 2026-07-13 | 触发提交: af55af09

---

## `根目录`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | ITSM service management app | — |
| `admin.py` | — | — |
| `apps.py` | — | `class ItsmConfig` |
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步 | `ticket_post_save()` — 工单保存后 — 根据状态变化触发 SLA<br>`itsm_post_set_state_handler()` — 监听 bamboo 节点状态变更 → 同步 ITSM 工单状态<br>`on_opsflow_finished()` — OpsFlow execution done → callback ITSM pipeline's waiting TASK node. |
| `sla_check_job.py` | SLA 定时检查任务（APScheduler 版） | `sla_check_job()` — SLA 定时检查 — 每分钟执行 |
| `tasks.py` | ITSM Celery 定时任务 | `sla_check()` — SLA 定时检查 — 每分钟执行<br>`auto_resolve_expired_tickets()` — 自动关闭超时未处理的草稿工单（每日执行） |
| `urls.py` | URL configuration for ITSM app | — |

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | — |
| `__init__.py` | — | — |
| `itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | `class Command` |
| `seed_itsm.py` | Seed complete ITSM test data — all models with i18n (zh/en) bilingual names | `class Command` |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Re-export all models for itsm app | — |
| `catalog.py` | ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA engine | `class ServiceCategory` — 服务分类 — 服务目录的一级/二级分类<br>`class SlaPolicy` — SLA 策略定义 — binds a Schedule (working time model) to a priority level. |
| `delegation.py` | ApprovalDelegate model — 审批委托 | `class ApprovalDelegate` — 审批委托 — 将审批权限临时委托给其他用户 |
| `escalation.py` | Escalation Level model — SLA 超时升级配置 | `class EscalationLevel` — 升级级别 — SLA 超时后的处理层级 |
| `fc_designer.py` | FcDesigner settings — per-business form designer UI preferences | `class FcDesignerSettings` — Per-business FcDesigner UI settings — shared across all projects/users in a business. |
| `field.py` | ITSM Field model — 节点表单字段定义 | `class Field` — 表单字段定义 — 绑定到 State |
| `notification_template.py` | NotificationTemplate model for reusable notification presets. | `class NotificationTemplate` — 通知模板 — 预设标题/正文/渠道/接收人，触发器选择即可复用 |
| `preset.py` | ITSM Preset model — reusable field value presets for workflow nodes and service items | `class Preset` — 可复用的字段值预设 |
| `schedule.py` | SLA Working Time Model — Schedule, Day, Duration | `class Duration` — Working time segment within a single day, e.g. "Morning 08:00-12:00".<br>`class Day` — Day classification: NORMAL (recurring weekday), WORKDAY (overtime range), HOLIDAY (exclusion range).<br>`class Schedule` — Working schedule aggregating NORMAL days, WORKDAY overtime days, and HOLIDAY exclusions. |
| `service_item.py` | ServiceItem model — 服务目录的核心实体 | `class ServiceItem` — 服务项 — 服务目录的核心实体 |
| `sla.py` | ITSM SLA model — SLA 计时任务 | `class SlaTask` — SLA 计时任务 — 工单级别的计时 |
| `state.py` | ITSM State model — 流程节点定义 | `class State` — 流程节点 — 对应 pipeline 中的一个活动 |
| `ticket.py` | ITSM Ticket model — 工单运行时 | `generate_sn()`<br>`class Ticket` — ITSM 工单 — pipeline 驱动的运行实例<br>`class TicketStatus` — 节点运行时状态 — 工单在每个节点上的实时状态<br>`class SignTask` — 会签/审批记录 — 每个审批人的操作 |
| `transition.py` | ITSM Transition model — 节点间连线定义 | `class Transition` — 节点间流转线 — 可选条件表达式 |
| `trigger.py` | Trigger models for event-driven ITSM automation. | `class Trigger` — 触发器 — 工单事件 → 自动化动作映射<br>`class TriggerAction` — 触发器动作 — 一条触发器可有多条动作，按 order 顺序执行<br>`class TriggerExecution` — 触发器执行记录 — 异步执行日志，365 天自动清理 |
| `workflow.py` | ITSM Workflow model — 流程模板定义与版本管理 | `class Workflow` — ITSM 流程模板 — 设计时定义<br>`class WorkflowVersion` — 流程版本 — 部署快照，工单运行的依据 |

## `pipeline_plugins/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | — |
| `components.py` | ITSM Pipeline 组件注册 | `class ItsmFillFormService` — 填单节点 — 等待用户提交表单<br>`class ItsmApprovalService` — 审批节点 — 支持单签/会签<br>`class ItsmSignService` — 会签节点 — 多审批人，根据 finish_condition 决定<br>`class ItsmAutoTaskService` — 自动任务节点 — OpsFlow 集成：用户填写参数后启动 OpsFlow，等待完成后继续<br>`class ItsmFillFormComponent` |

## `serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | — |
| `change_calendar.py` | Serializer for Change Calendar aggregated response items. | `class CalendarItemSerializer` — Unified calendar item — output only, no model backing. |
| `delegation.py` | Delegation serializers — 审批委托序列化器 | `class DelegationSerializer` — 委托列表/详情序列化器<br>`class DelegationCreateUpdateSerializer` — 委托创建/更新序列化器 — user 由视图自动设置 |
| `escalation.py` | Escalation serializers — with i18n support | `class EscalationLevelSerializer` |
| `legacy.py` | Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support | `class ServiceCategorySerializer`<br>`class ServiceCategoryCreateUpdateSerializer`<br>`class SlaPolicySerializer` |
| `notification_template.py` | Serializer for NotificationTemplate with i18n support | `class NotificationTemplateSerializer` |
| `preset.py` | Preset serializers — 预设序列化器 | `class PresetSerializer` — 预设 CRUD 序列化器 — 更新时级联同步引用该预设的 State |
| `schedule.py` | Serializers for Schedule, Day, Duration models. | `class DurationSerializer`<br>`class DaySerializer`<br>`class ScheduleSerializer` |
| `service_item.py` | ServiceItem serializers — with i18n support | `class ServiceItemSerializer` — 服务项列表/详情序列化器<br>`class ServiceItemCreateUpdateSerializer` — 服务项创建/更新序列化器<br>`class ServiceItemSubmitSerializer` — 提交服务申请序列化器 |
| `ticket_serializers.py` | Ticket serializers | `class TicketSerializer`<br>`class TicketCreateSerializer`<br>`class TicketStatusSerializer`<br>`class SignTaskSerializer` |
| `trigger.py` | Serializers for Trigger & TriggerAction with i18n support | `class TriggerActionSerializer`<br>`class TriggerSerializer` |
| `workflow_serializers.py` | Workflow serializers — with i18n support | `class WorkflowSerializer`<br>`class WorkflowCreateSerializer`<br>`class WorkflowVersionSerializer`<br>`class StateSerializer`<br>`class TransitionSerializer` |

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Services package for itsm app | — |
| `ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `class AIGenerator` — AI 驱动的 ITSM 工作流生成器 |
| `bamboo_engine.py` | Bamboo Engine shared utilities — ITSM hosted, also used by Opsflow. Extracts duplicate static methods from ITS | `activity_callback()` — Send node callback to bamboo-engine (approval/fill-form done).<br>`revoke_by_pipeline_id()` — Revoke pipeline directly (for callers without ticket/execution reference).<br>`resolve_activity_id()` — Resolve ITSM State.id → bamboo element id via ticket._pipeline_id_map. |
| `change_calendar.py` | Change Calendar aggregation service. | `class ChangeCalendarService` — Aggregate change-related items from ITSM and OpsFlow. |
| `condition_utils.py` | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import | — |
| `itsm_engine.py` | ITSMEngine — ITSM Bamboo Pipeline 执行引擎 | `class ITSMEngine` — ITSM 工单执行引擎 — BambooDjangoRuntime 驱动 |
| `notifications.py` | ITSM 通知服务 — 状态变更时的消息通知 | `send_wecom_notify()` — 企业微信机器人消息<br>`send_dingtalk_notify()` — 钉钉机器人消息<br>`send_email_notify()` — SMTP 邮件通知<br>`notify_via_integration_hub()` — 通过 Integration Hub 通道发送通知 (如果可用)<br>`get_config_from_ticket()` — 从 ticket.meta 或 settings 中读取通知配置 |
| `opsflow_trigger.py` | ITSM 工单审批通过后触发 OpsFlow 自愈流程 | `class TicketOpsflowConfig` — ITSM 工单类型到 OpsFlow 模板的映射配置<br>`class OpsflowTriggerService` — ITSM 工单审批通过后触发 OpsFlow 自愈流程的服务 |
| `role_resolver.py` | 处理人解析器 — 将处理器类型转换为实际用户名列表 | `resolve_processors()` — 解析处理人配置，返回用户名列表 |
| `sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | `class SlaEngine` — SLA 引擎 — 管理工单的 SLA 计时与升级 |
| `sla_time.py` | SLA Time Engine — Working-time-aware deadline calculation. | `class TimeDelta` — A single continuous interval between two timezone-aware datetimes.<br>`class MultiTimeDelta` — An ordered, non-overlapping collection of TimeDelta intervals.<br>`class SlaTime` — Working-time-aware SLA calculator.<br>`resolve_leader()` — Resolve the leader/manager for a given processor username.<br>`notify_specific_users()` — Notify a list of specific usernames about SLA escalation. |
| `trigger_service.py` | Trigger matching, execution, and action dispatch. | `class TemplateResolver` — Resolve ${variable} templates in action config strings.<br>`class ConditionEvaluator` — Evaluate condition expression against ticket form data.<br>`class TriggerMatcher` — Match active triggers against a ticket event context.<br>`class ActionRunner` — Dispatch action execution to type-specific runners.<br>`class NotifyRunner` — Send notification via NotificationService. |
| `workflow_builder.py` | ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | `class ITSMWorkflowBuilder` — 将 ITSM WorkflowVersion 快照转换为 bamboo-engine pipeline tree |
| `workflow_validator.py` | ITSM Workflow Validator — deploy-time structural checks. | `validate_workflow()` — Validate ITSM workflow structure before deployment. |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | — |
| `base.py` | ViewSet base class — project isolation + multi-tenant permission support | `class ProjectFilteredViewSet` — Project-scoped ViewSet with multi-tenant permission enforcement.<br>`class ProjectReadOnlyViewSet` — Read-only variant — disables all write operations. |
| `change_calendar.py` | Change Calendar ViewSet — aggregates ITSM tickets + OpsFlow schedules. | `class ChangeCalendarViewSet` — 变更日历 — unified timeline of ITSM tickets and OpsFlow schedules. |
| `dashboard.py` | ITSM Dashboard view — 看板数据聚合 | `class DashboardViewSet` — ITSM 看板 — 数据聚合（只读） |
| `delegation.py` | Delegation views — 审批委托 CRUD | `class DelegationViewSet` — 审批委托 CRUD |
| `escalation_views.py` | Escalation views — CRUD 升级级别管理 | `class EscalationLevelViewSet` — 升级级别 CRUD（全局配置，非项目隔离） |
| `fc_designer_settings.py` | GET/PUT FcDesigner settings by business (resolved from ?project_id=) | `class FcDesignerSettingsView` |
| `notification_template_views.py` | NotificationTemplate CRUD — project-scoped with multi-tenant isolation | `class NotificationTemplateViewSet` — 通知模板 CRUD — project-scoped |
| `preset_views.py` | Preset ViewSet — 预设管理 CRUD | `class PresetViewSet` — 预设管理 — 支持按类型过滤 ?preset_type=role_list |
| `schedule_views.py` | ViewSets for Schedule, Day, Duration CRUD. | `class DurationViewSet` — Duration CRUD.<br>`class DayViewSet` — Day CRUD.<br>`class ScheduleViewSet` — Schedule CRUD — project-scoped + global. |
| `service_item.py` | ServiceItem views — 服务目录 CRUD + 提交申请 | `class ServiceItemViewSet` — 服务目录管理 — 服务项 CRUD + 提交申请 |
| `ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传 | `class TicketViewSet` — 工单管理 — project-scoped with environment gate |
| `trigger_views.py` | Trigger CRUD — project-scoped with multi-tenant isolation | `class TriggerViewSet` — 触发器 CRUD — project-scoped |
| `views.py` | ITSM views - ServiceCategory, SlaPolicy | `class ServiceCategoryViewSet` — 服务分类 CRUD — project-scoped<br>`class SlaPolicyViewSet` — SLA 策略 CRUD — project-scoped |
| `workflow_views.py` | ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成 | `class ItsmProjectViewSet` — ITSM project-scoped ViewSet — 整合 IAM ProjectFilteredViewSet + dvadmin 响应格式<br>`class WorkflowViewSet` — 流程模板管理 — project-scoped with multi-tenant isolation<br>`class WorkflowVersionViewSet` — 流程版本管理<br>`class StateViewSet` — 节点管理<br>`class TransitionViewSet` — 连线管理 |
