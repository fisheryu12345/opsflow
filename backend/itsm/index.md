# itsm — 模块索引

> 自动生成: 2026-07-12 | 触发提交: 4217dad2

## `根目录/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | ITSM service management app | - |
| `admin.py` | - | - |
| `apps.py` | - | ItsmConfig |
## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
## `management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | Command |
| `seed_itsm.py` | Seed complete ITSM test data — all models with i18n (zh/en) bilingual names | Command |
## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Re-export all models for itsm app | - |
| `catalog.py` | ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA engine | ServiceCategory, SlaPolicy |
| `delegation.py` | ApprovalDelegate model — 审批委托 | ApprovalDelegate |
| `escalation.py` | Escalation Level model — SLA 超时升级配置 | EscalationLevel |
| `field.py` | ITSM Field model — 节点表单字段定义 | Field |
| `notification_template.py` | NotificationTemplate model for reusable notification presets. | NotificationTemplate |
| `preset.py` | ITSM Preset model — reusable field value presets for workflow nodes and service items | Preset |
| `schedule.py` | SLA Working Time Model — Schedule, Day, Duration | Duration, Day, Schedule |
| `service_item.py` | ServiceItem model — 服务目录的核心实体 | ServiceItem |
| `sla.py` | ITSM SLA model — SLA 计时任务 | SlaTask |
| `state.py` | ITSM State model — 流程节点定义 | State |
| `ticket.py` | ITSM Ticket model — 工单运行时 | Ticket, TicketStatus, SignTask, generate_sn() |
| `transition.py` | ITSM Transition model — 节点间连线定义 | Transition |
| `trigger.py` | Trigger models for event-driven ITSM automation. | Trigger, TriggerAction, TriggerExecution |
| `workflow.py` | ITSM Workflow model — 流程模板定义与版本管理 | Workflow, WorkflowVersion |
## `pipeline_plugins/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `components.py` | ITSM Pipeline 组件注册 | ItsmFillFormService, ItsmApprovalService, ItsmSignService, ItsmAutoTaskService |
## `serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `change_calendar.py` | Serializer for Change Calendar aggregated response items. | CalendarItemSerializer |
| `delegation.py` | Delegation serializers — 审批委托序列化器 | DelegationSerializer, DelegationCreateUpdateSerializer |
| `escalation.py` | Escalation serializers — with i18n support | EscalationLevelSerializer |
| `legacy.py` | Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support | ServiceCategorySerializer, ServiceCategoryCreateUpdateSerializer, SlaPolicySerializer |
| `notification_template.py` | Serializer for NotificationTemplate with i18n support | NotificationTemplateSerializer |
| `preset.py` | Preset serializers — 预设序列化器 | PresetSerializer |
| `schedule.py` | Serializers for Schedule, Day, Duration models. | DurationSerializer, DaySerializer, ScheduleSerializer |
| `service_item.py` | ServiceItem serializers — with i18n support | ServiceItemSerializer, ServiceItemCreateUpdateSerializer, ServiceItemSubmitSerializer |
| `ticket_serializers.py` | Ticket serializers | TicketSerializer, TicketCreateSerializer, TicketStatusSerializer, SignTaskSerializer |
| `trigger.py` | Serializers for Trigger & TriggerAction with i18n support | TriggerActionSerializer, TriggerSerializer |
| `workflow_serializers.py` | Workflow serializers — with i18n support | WorkflowSerializer, WorkflowCreateSerializer, WorkflowVersionSerializer, StateSerializer |
## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Services package for itsm app | - |
| `ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | AIGenerator |
| `bamboo_engine.py` | Bamboo Engine shared utilities — ITSM hosted, also used by Opsflow.
Extracts duplicate static method | activity_callback(), revoke_by_pipeline_id() |
| `change_calendar.py` | Change Calendar aggregation service. | ChangeCalendarService |
| `condition_utils.py` | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import | - |
| `itsm_engine.py` | ITSMEngine — ITSM Bamboo Pipeline 执行引擎 | ITSMEngine |
| `notifications.py` | ITSM 通知服务 — 状态变更时的消息通知 | NotificationService, send_wecom_notify(), send_dingtalk_notify(), send_email_notify() |
| `opsflow_trigger.py` | ITSM 工单审批通过后触发 OpsFlow 自愈流程 | TicketOpsflowConfig, OpsflowTriggerService |
| `role_resolver.py` | 处理人解析器 — 将处理器类型转换为实际用户名列表 | resolve_processors() |
| `sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | SlaEngine |
| `sla_time.py` | SLA Time Engine — Working-time-aware deadline calculation. | TimeDelta, MultiTimeDelta, SlaTime, resolve_leader() |
| `trigger_service.py` | Trigger matching, execution, and action dispatch. | TemplateResolver, ConditionEvaluator, TriggerMatcher, ActionRunner |
| `workflow_builder.py` | ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | ITSMWorkflowBuilder |
| `workflow_validator.py` | ITSM Workflow Validator — deploy-time structural checks. | validate_workflow() |
## `根目录/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步 | ticket_post_save(), itsm_post_set_state_handler() |
| `sla_check_job.py` | SLA 定时检查任务（APScheduler 版） | sla_check_job() |
| `tasks.py` | ITSM Celery 定时任务 | sla_check(), auto_resolve_expired_tickets() |
## `tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `test_itsm_engine.py` | ITSMEngine 测试 — PipelineWrapper 迁移验证 | ITSMEngineRunTests, ITSMEnginePauseResumeRevokeTests |
| `test_layout.py` | Layout engine 测试 — Sugiyama 布局计算 | ComputeLayoutTests |
| `test_models.py` | ITSM 模型测试 | TicketStatusChoicesTests, StateNodeKeyTests, TransitionNodeKeyTests, WorkflowCreateVersionNodeKeyTests |
| `test_sla_time.py` | Tests for SLA working time model — SlaTime engine + SlaEngine integration. | TestTimeDelta, TestMultiTimeDelta, TestSlaTime5x8, TestSlaTime7x24 |
| `test_workflow_builder.py` | ITSMWorkflowBuilder 测试 — 验证 pipeline tree 构建 | BuildTreeBasicTests |
| `test_workflow_validator.py` | Workflow Validator tests — 12 validation rules for ITSM workflow structure. | TestValidSimpleFlow, TestMissingStartEnd, TestCycleDetection, TestTransitionRefsValid |
## `根目录/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `urls.py` | URL configuration for ITSM app | - |
## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `base.py` | ViewSet base class — project isolation + multi-tenant permission support | ProjectFilteredViewSet, ProjectReadOnlyViewSet |
| `change_calendar.py` | Change Calendar ViewSet — aggregates ITSM tickets + OpsFlow schedules. | ChangeCalendarViewSet |
| `dashboard.py` | ITSM Dashboard view — 看板数据聚合 | DashboardViewSet |
| `delegation.py` | Delegation views — 审批委托 CRUD | DelegationViewSet |
| `escalation_views.py` | Escalation views — CRUD 升级级别管理 | EscalationLevelViewSet |
| `notification_template_views.py` | NotificationTemplate CRUD — project-scoped with multi-tenant isolation | NotificationTemplateViewSet |
| `preset_views.py` | Preset ViewSet — 预设管理 CRUD | PresetViewSet |
| `schedule_views.py` | ViewSets for Schedule, Day, Duration CRUD. | DurationViewSet, DayViewSet, ScheduleViewSet |
| `service_item.py` | ServiceItem views — 服务目录 CRUD + 提交申请 | ServiceItemViewSet |
| `ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传 | TicketViewSet |
| `trigger_views.py` | Trigger CRUD — project-scoped with multi-tenant isolation | TriggerViewSet |
| `views.py` | ITSM views - ServiceCategory, SlaPolicy | ServiceCategoryViewSet, SlaPolicyViewSet |
| `workflow_views.py` | ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成 | ItsmProjectViewSet, WorkflowViewSet, WorkflowVersionViewSet, StateViewSet |