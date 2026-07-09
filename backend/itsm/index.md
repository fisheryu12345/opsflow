# itsm — Module Index

> Last auto-updated: 2026-07-08 | Trigger commit: a5c1083f

## `Root/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `__init__.py` | ITSM service management app | - |
| `admin.py` |  | - |
| `apps.py` |  | `ItsmConfig` |
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步 | `ticket_post_save()`, `itsm_post_set_state_handler()` |
| `sla_check_job.py` | SLA 定时检查任务（APScheduler 版） | `sla_check_job()` |
| `tasks.py` | ITSM Celery 定时任务 | `sla_check()`, `auto_resolve_expired_tickets()` |
| `urls.py` | URL configuration for ITSM app | - |

## `management/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `management/__init__.py` |  | - |

## `management/commands/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `management/commands/__init__.py` |  | - |
| `management/commands/itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | `Command` |
| `management/commands/seed_itsm.py` |  | `Command` |

## `models/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `models/__init__.py` | Re-export all models for itsm app | - |
| `models/catalog.py` | ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA engine | `ServiceCategory`, `SlaPolicy` |
| `models/delegation.py` | ApprovalDelegate model — 审批委托 | `ApprovalDelegate` |
| `models/escalation.py` | Escalation Level model — SLA 超时升级配置 | `EscalationLevel` |
| `models/field.py` | ITSM Field model — 节点表单字段定义 | `Field` |
| `models/service_item.py` | ServiceItem model — 服务目录的核心实体 | `ServiceItem` |
| `models/sla.py` | ITSM SLA model — SLA 计时任务 | `SlaTask` |
| `models/state.py` | ITSM State model — 流程节点定义 | `State` |
| `models/ticket.py` |  | `State` |
| `models/transition.py` | ITSM Transition model — 节点间连线定义 | `Transition` |
| `models/workflow.py` |  | `Transition` |

## `pipeline_plugins/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `pipeline_plugins/__init__.py` |  | - |
| `pipeline_plugins/components.py` |  | - |

## `serializers/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `serializers/__init__.py` |  | - |
| `serializers/delegation.py` | Delegation serializers — 审批委托序列化器 | `DelegationSerializer`, `DelegationCreateUpdateSerializer` |
| `serializers/escalation.py` | Escalation serializers — with i18n support | `EscalationLevelSerializer` |
| `serializers/legacy.py` | Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support | `ServiceCategorySerializer`, `ServiceCategoryCreateUpdateSerializer`, `SlaPolicySerializer` |
| `serializers/service_item.py` | ServiceItem serializers — with i18n support | `ServiceItemSerializer`, `ServiceItemCreateUpdateSerializer`, `ServiceItemSubmitSerializer` |
| `serializers/ticket_serializers.py` | Ticket serializers | `TicketSerializer`, `TicketCreateSerializer`, `TicketStatusSerializer`, `SignTaskSerializer` |
| `serializers/workflow_serializers.py` | Workflow serializers — with i18n support | `WorkflowSerializer`, `WorkflowCreateSerializer`, `WorkflowVersionSerializer`, `StateSerializer` |

## `services/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `services/__init__.py` | Services package for itsm app | - |
| `services/ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `AIGenerator` |
| `services/condition_utils.py` | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import | - |
| `services/itsm_engine.py` |  | - |
| `services/notifications.py` |  | - |
| `services/opsflow_trigger.py` |  | - |
| `services/role_resolver.py` |  | - |
| `services/sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | `SlaEngine` |
| `services/workflow_builder.py` | ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | `ITSMWorkflowBuilder` |

## `tests/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `tests/__init__.py` |  | - |
| `tests/test_itsm_engine.py` |  | - |
| `tests/test_layout.py` | Layout engine 测试 — Sugiyama 布局计算 | `ComputeLayoutTests` |
| `tests/test_models.py` | ITSM 模型测试 | `TicketStatusChoicesTests`, `StateNodeKeyTests`, `TransitionNodeKeyTests` |
| `tests/test_workflow_builder.py` |  | `TicketStatusChoicesTests`, `StateNodeKeyTests`, `TransitionNodeKeyTests` |

## `views/`

| File | Description | Core Components |
|------|-------------|-----------------|
| `views/__init__.py` |  | - |
| `views/dashboard.py` |  | - |
| `views/delegation.py` | Delegation views — 审批委托 CRUD | `DelegationViewSet` |
| `views/escalation_views.py` | Escalation views — CRUD 升级级别管理 | `EscalationLevelViewSet` |
| `views/service_item.py` |  | `EscalationLevelViewSet` |
| `views/ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传 | `TicketViewSet` |
| `views/views.py` | ITSM views - ServiceCategory, SlaPolicy | `ServiceCategoryViewSet`, `SlaPolicyViewSet` |
| `views/workflow_views.py` |  | `ServiceCategoryViewSet`, `SlaPolicyViewSet` |
