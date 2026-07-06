# itsm -- Module Index

> Last auto-update: 2026-07-06 | Post-cleanup: removed legacy Incident/Change/AssignEngine

---

## `management/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `management\commands\seed_itsm.py` | Seed ITSM test data | `Command` |

## `models/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `models\catalog.py` | ServiceCategory and SlaPolicy | `ServiceCategory -- 服务分类`; `SlaPolicy -- SLA 策略定义` |
| `models\delegation.py` | ApprovalDelegate model | `ApprovalDelegate -- 审批委托` |
| `models\field.py` | ITSM Field model — 节点表单字段定义 | `Field -- 表单字段定义 — 绑定到 State` |
| `models\service_item.py` | ServiceItem model | `ServiceItem -- 服务项 — 服务目录的核心实体` |
| `models\sla.py` | SLA model | `PriorityMatrix -- 优先级矩阵`; `SlaTask -- SLA 计时任务` |
| `models\state.py` | ITSM State model — 流程节点定义 | `State -- 流程节点` |
| `models\ticket.py` | ITSM Ticket model — 工单运行时 | `Ticket -- ITSM 工单 — pipeline 驱动的运行实例`; `TicketStatus -- 节点运行时状态`; `SignTask -- 会签/审批记录` |
| `models\transition.py` | ITSM Transition model — 节点间连线定义 | `Transition -- 节点间流转线` |
| `models\workflow.py` | ITSM Workflow model | `Workflow -- ITSM 流程模板`; `WorkflowVersion -- 流程版本` |

## `pipeline_plugins/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `pipeline_plugins\components.py` | ITSM Pipeline 组件注册 | `ItsmFillFormService -- 填单节点`; `ItsmApprovalService -- 审批节点`; `ItsmSignService -- 会签节点` |

## `serializers/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `serializers\delegation.py` | Delegation serializers | `DelegationSerializer` |
| `serializers\legacy.py` | ServiceCategory/SlaPolicy serializers | `ServiceCategorySerializer`; `SlaPolicySerializer` |
| `serializers\service_item.py` | ServiceItem serializers | `ServiceItemSerializer` |
| `serializers\ticket_serializers.py` | Ticket serializers | `TicketSerializer` |
| `serializers\workflow_serializers.py` | Workflow serializers | `WorkflowSerializer` |

## `services/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `services\ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `AIGenerator` |
| `services\condition_utils.py` | ITSM 条件表达式工具 |  |
| `services\itsm_engine.py` | ITSMEngine — Pipeline 执行引擎 | `ITSMEngine` |
| `services\notifications.py` | ITSM 通知服务 | `NotificationService` |
| `services\opsflow_trigger.py` | ITSM 工单审批触发 OpsFlow | `OpsflowTriggerService` |
| `services\role_resolver.py` | 处理人解析器 | `resolve_processors()` |
| `services\sla_engine.py` | SLA 引擎 | `SlaEngine` |
| `services\workflow_builder.py` | ITSMWorkflowBuilder | `ITSMWorkflowBuilder` |

## `tests/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `tests\test_itsm_engine.py` | ITSMEngine 测试 | `ITSMEngineRunTests` |
| `tests\test_layout.py` | Layout engine 测试 | `ComputeLayoutTests` |
| `tests\test_models.py` | ITSM 模型测试 | `TicketStatusChoicesTests`; `StateNodeKeyTests`; `ServiceItemTests` |
| `tests\test_workflow_builder.py` | ITSMWorkflowBuilder 测试 | `BuildTreeBasicTests` |

## `views/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `views\dashboard.py` | ITSM Dashboard view | `DashboardViewSet` |
| `views\delegation.py` | Delegation views | `DelegationViewSet` |
| `views\service_item.py` | ServiceItem views | `ServiceItemViewSet` |
| `views\ticket_views.py` | ITSM Ticket views | `TicketViewSet` |
| `views\views.py` | ServiceCategory/SlaPolicy views | `ServiceCategoryViewSet`; `SlaPolicyViewSet` |
| `views\workflow_views.py` | ITSM Workflow views | `ItsmProjectViewSet`; `WorkflowViewSet` |
