# ITSM — 模块索引
> 上次自动更新: 2026-07-10 | 触发提交: c15e9353

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\__init__.py` | - | - |

## `management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\commands\__init__.py` | - | - |
| `management\commands\itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | `Command` |
| `management\commands\seed_itsm.py` | Seed complete ITSM test data — all models with i18n (zh/en) bilingual names | `Command` |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models\__init__.py` | Re-export all models for itsm app | - |
| `models\catalog.py` | ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA engine | `ServiceCategory`, `SlaPolicy` |
| `models\delegation.py` | ApprovalDelegate model — 审批委托 | `ApprovalDelegate` |
| `models\escalation.py` | Escalation Level model — SLA 超时升级配置 | `EscalationLevel` |
| `models\field.py` | ITSM Field model — 节点表单字段定义 | `Field` |
| `models\preset.py` | ITSM Preset model — reusable field value presets for workflow nodes and service items | `Preset` |
| `models\schedule.py` | SLA Working Time Model — Schedule, Day, Duration | `Duration`, `Day`, `Schedule` |
| `models\service_item.py` | ServiceItem model — 服务目录的核心实体 | `ServiceItem` |
| `models\sla.py` | ITSM SLA model — SLA 计时任务 | `SlaTask` |
| `models\state.py` | ITSM State model — 流程节点定义 | `State` |
| `models\ticket.py` | ITSM Ticket model — 工单运行时 | `generate_sn()`, `Ticket`, `TicketStatus`, `SignTask` |
| `models\transition.py` | ITSM Transition model — 节点间连线定义 | `Transition` |
| `models\workflow.py` | ITSM Workflow model — 流程模板定义与版本管理 | `Workflow`, `WorkflowVersion` |

## `pipeline_plugins/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `pipeline_plugins\__init__.py` | - | - |
| `pipeline_plugins\components.py` | ITSM Pipeline 组件注册 | `ItsmFillFormService`, `ItsmApprovalService`, `ItsmSignService`, `ItsmAutoTaskService` |

## `serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `serializers\__init__.py` | Legacy serializers (ServiceCategory, SlaPolicy) | - |
| `serializers\delegation.py` | Delegation serializers — 审批委托序列化器 | `DelegationSerializer`, `DelegationCreateUpdateSerializer` |
| `serializers\escalation.py` | Escalation serializers — with i18n support | `EscalationLevelSerializer` |
| `serializers\legacy.py` | Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support | `ServiceCategorySerializer`, `ServiceCategoryCreateUpdateSerializer`, `SlaPolicySerializer` |
| `serializers\preset.py` | Preset serializers — 预设序列化器 | `PresetSerializer` |
| `serializers\schedule.py` | Serializers for Schedule, Day, Duration models. | `DurationSerializer`, `DaySerializer`, `ScheduleSerializer` |
| `serializers\service_item.py` | ServiceItem serializers — with i18n support | `ServiceItemSerializer`, `ServiceItemCreateUpdateSerializer`, `ServiceItemSubmitSerializer` |
| `serializers\ticket_serializers.py` | Ticket serializers | `TicketSerializer`, `TicketCreateSerializer`, `TicketStatusSerializer`, `SignTaskSerializer` |
| `serializers\workflow_serializers.py` | Workflow serializers — with i18n support | `WorkflowSerializer`, `WorkflowCreateSerializer`, `WorkflowVersionSerializer`, `StateSerializer` |

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `services\__init__.py` | Services package for itsm app | - |
| `services\ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `AIGenerator` |
| `services\bamboo_engine.py` | Bamboo Engine shared utilities — ITSM hosted, also used by Opsflow. | `activity_callback()`, `revoke_by_pipeline_id()` |
| `services\condition_utils.py` | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import | - |
| `services\itsm_engine.py` | ITSMEngine — ITSM Bamboo Pipeline 执行引擎 | `ITSMEngine` |
| `services\notifications.py` | ITSM 通知服务 — 状态变更时的消息通知 | `send_wecom_notify()`, `send_dingtalk_notify()`, `send_email_notify()`, `notify_via_integration_hub()` |
| `services\opsflow_trigger.py` | ITSM 工单审批通过后触发 OpsFlow 自愈流程 | `TicketOpsflowConfig`, `OpsflowTriggerService` |
| `services\role_resolver.py` | 处理人解析器 — 将处理器类型转换为实际用户名列表 | `resolve_processors()` |
| `services\sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | `SlaEngine` |
| `services\sla_time.py` | SLA Time Engine — Working-time-aware deadline calculation. | `TimeDelta`, `MultiTimeDelta`, `SlaTime`, `resolve_leader()` |
| `services\workflow_builder.py` | ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | `ITSMWorkflowBuilder` |
| `services\workflow_validator.py` | ITSM Workflow Validator — deploy-time structural checks. | `validate_workflow()` |

## `tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `tests\__init__.py` | ITSM tests package | - |
| `tests\test_itsm_engine.py` | ITSMEngine 测试 — PipelineWrapper 迁移验证 | `ITSMEngineRunTests`, `ITSMEnginePauseResumeRevokeTests` |
| `tests\test_layout.py` | Layout engine 测试 — Sugiyama 布局计算 | `ComputeLayoutTests` |
| `tests\test_models.py` | ITSM 模型测试 | `TicketStatusChoicesTests`, `StateNodeKeyTests`, `TransitionNodeKeyTests`, `WorkflowCreateVersionNodeKeyTests` |
| `tests\test_sla_time.py` | Tests for SLA working time model — SlaTime engine + SlaEngine integration. | `dt()`, `d()`, `TestTimeDelta`, `TestMultiTimeDelta` |
| `tests\test_workflow_builder.py` | ITSMWorkflowBuilder 测试 — 验证 pipeline tree 构建 | `BuildTreeBasicTests` |
| `tests\test_workflow_validator.py` | Workflow Validator tests — 12 validation rules for ITSM workflow structure. | `TestValidSimpleFlow`, `TestMissingStartEnd`, `TestCycleDetection`, `TestTransitionRefsValid` |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views\__init__.py` | -*- coding: utf-8 -*- | - |
| `views\base.py` | ViewSet base class — project isolation + multi-tenant permission support | `ProjectFilteredViewSet`, `ProjectReadOnlyViewSet` |
| `views\dashboard.py` | ITSM Dashboard view — 看板数据聚合 | `DashboardViewSet` |
| `views\delegation.py` | Delegation views — 审批委托 CRUD | `DelegationViewSet` |
| `views\escalation_views.py` | Escalation views — CRUD 升级级别管理 | `EscalationLevelViewSet` |
| `views\preset_views.py` | Preset ViewSet — 预设管理 CRUD | `PresetViewSet` |
| `views\schedule_views.py` | ViewSets for Schedule, Day, Duration CRUD. | `DurationViewSet`, `DayViewSet`, `ScheduleViewSet` |
| `views\service_item.py` | ServiceItem views — 服务目录 CRUD + 提交申请 | `ServiceItemViewSet` |
| `views\ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传 | `TicketViewSet` |
| `views\views.py` | ITSM views - ServiceCategory, SlaPolicy | `ServiceCategoryViewSet`, `SlaPolicyViewSet` |
| `views\workflow_views.py` | ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成 | `ItsmProjectViewSet`, `WorkflowViewSet`, `WorkflowVersionViewSet`, `StateViewSet` |

## `根目录/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | ITSM service management app | - |
| `admin.py` | - | - |
| `apps.py` | Register and start SLA periodic check via APScheduler (dev mode only) | `ItsmConfig` |
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步 | `ticket_post_save()`, `itsm_post_set_state_handler()` |
| `sla_check_job.py` | SLA 定时检查任务（APScheduler 版） | `sla_check_job()` |
| `tasks.py` | ITSM Celery 定时任务 | `sla_check()`, `auto_resolve_expired_tickets()` |
| `urls.py` | URL configuration for ITSM app | - |

