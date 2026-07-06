# itsm — 模块索引
> 上次自动更新: 2026-07-07 | 触发提交: bafc693b
---

## `根目录`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | ITSM service management app | ITSM service management app |
| `admin.py` | - | - |
| `apps.py` | - | `ItsmConfig` |
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步 | `ticket_post_save()` — 工单保存后 — 根据状态变化触发 SLA; `itsm_post_set_state_handler()` — 监听 bamboo 节点状态变更 → 同步 ITSM 工单状态 |
| `sla_check_job.py` | SLA 定时检查任务（APScheduler 版） | `sla_check_job()` — SLA 定时检查 — 每分钟执行 |
| `tasks.py` | ITSM Celery 定时任务 | `sla_check()` — SLA 定时检查 — 每分钟执行; `auto_resolve_expired_tickets()` — 自动关闭超时未处理的草稿工单（每日执行） |
| `urls.py` | URL configuration for ITSM app | URL configuration for ITSM app |

## `management`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/__init__.py` | - | - |

## `management\commands`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/commands/__init__.py` | - | - |
| `management/commands/itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | `Command` |
| `management/commands/seed_itsm.py` | Seed complete ITSM test data — all models | `Command` |

## `models`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models/__init__.py` | Re-export all models for itsm app | Re-export all models for itsm app |
| `models/catalog.py` | ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA e | `ServiceCategory` — 服务分类 — 服务目录的一级/二级分类; `SlaPolicy` — SLA 策略定义 |
| `models/delegation.py` | ApprovalDelegate model — 审批委托 | `ApprovalDelegate` — 审批委托 — 将审批权限临时委托给其他用户 |
| `models/escalation.py` | Escalation Level model — SLA 超时升级配置 | `EscalationLevel` — 升级级别 — SLA 超时后的处理层级 |
| `models/field.py` | ITSM Field model — 节点表单字段定义 | `Field` — 表单字段定义 — 绑定到 State |
| `models/service_item.py` | ServiceItem model — 服务目录的核心实体 | `ServiceItem` — 服务项 — 服务目录的核心实体 |
| `models/sla.py` | ITSM SLA model — SLA 计时任务 | `SlaTask` — SLA 计时任务 — 工单级别的计时 |
| `models/state.py` | ITSM State model — 流程节点定义 | `State` — 流程节点 — 对应 pipeline 中的一个活动 |
| `models/ticket.py` | ITSM Ticket model — 工单运行时 | `generate_sn()`; `Ticket` — ITSM 工单 — pipeline 驱动的运行实例; `TicketStatus` — 节点运行时状态 — 工单在每个节点上的实时状态; `SignTask` — 会签/审批记录 — 每个审批人的操作 |
| `models/transition.py` | ITSM Transition model — 节点间连线定义 | `Transition` — 节点间流转线 — 可选条件表达式 |
| `models/workflow.py` | ITSM Workflow model — 流程模板定义与版本管理 | `Workflow` — ITSM 流程模板 — 设计时定义; `WorkflowVersion` — 流程版本 — 部署快照，工单运行的依据 |

## `pipeline_plugins`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `pipeline_plugins/__init__.py` | - | - |
| `pipeline_plugins/components.py` | ITSM Pipeline 组件注册 | `ItsmFillFormService` — 填单节点 — 等待用户提交表单; `ItsmApprovalService` — 审批节点 — 支持单签/会签; `ItsmSignService` — 会签节点 — 多审批人，根据 finish_condition 决定; `ItsmAutoTaskService` — 自动任务节点 — 执行自动化操作; `ItsmFillFormComponent` |

## `serializers`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `serializers/__init__.py` | - | - |
| `serializers/delegation.py` | Delegation serializers — 审批委托序列化器 | `DelegationSerializer` — 委托列表/详情序列化器; `DelegationCreateUpdateSerializer` — 委托创建/更新序列化器 — user 由视图自动设置 |
| `serializers/escalation.py` | Escalation serializers | `EscalationLevelSerializer` |
| `serializers/legacy.py` | Serializers for ITSM app | `ServiceCategorySerializer`; `ServiceCategoryCreateUpdateSerializer`; `SlaPolicySerializer` |
| `serializers/service_item.py` | ServiceItem serializers | `ServiceItemSerializer` — 服务项列表/详情序列化器; `ServiceItemCreateUpdateSerializer` — 服务项创建/更新序列化器; `ServiceItemSubmitSerializer` — 提交服务申请序列化器 |
| `serializers/ticket_serializers.py` | Ticket serializers | `TicketSerializer`; `TicketCreateSerializer`; `TicketStatusSerializer`; `SignTaskSerializer` |
| `serializers/workflow_serializers.py` | Workflow serializers | `WorkflowSerializer`; `WorkflowCreateSerializer`; `WorkflowVersionSerializer`; `StateSerializer`; `TransitionSerializer` |

## `services`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `services/__init__.py` | Services package for itsm app | Services package for itsm app |
| `services/ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `AIGenerator` — AI 驱动的 ITSM 工作流生成器 |
| `services/condition_utils.py` | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import | ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import |
| `services/itsm_engine.py` | ITSMEngine — ITSM Bamboo Pipeline 执行引擎 | `ITSMEngine` — ITSM 工单执行引擎 — BambooDjangoRuntime 驱动 |
| `services/notifications.py` | ITSM 通知服务 — 状态变更时的消息通知 | `send_wecom_notify()` — 企业微信机器人消息; `send_dingtalk_notify()` — 钉钉机器人消息; `send_email_notify()` — SMTP 邮件通知; `notify_via_integration_hub()` — 通过 Integration Hub 通道发送通知 (如果可用); `get_config_from_ticket()` — 从 ticket.meta 或 settings 中读取通知配置 |
| `services/opsflow_trigger.py` | ITSM 工单审批通过后触发 OpsFlow 自愈流程 | `TicketOpsflowConfig` — ITSM 工单类型到 OpsFlow 模板的映射配置; `OpsflowTriggerService` — ITSM 工单审批通过后触发 OpsFlow 自愈流程的服务 |
| `services/role_resolver.py` | 处理人解析器 — 将处理器类型转换为实际用户名列表 | `resolve_processors()` — 解析处理人配置，返回用户名列表 |
| `services/sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | `SlaEngine` — SLA 引擎 — 管理工单的 SLA 计时与升级 |
| `services/workflow_builder.py` | ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | `ITSMWorkflowBuilder` — 将 ITSM WorkflowVersion 快照转换为 bamboo-engine pipeline tree |

## `tests`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `tests/__init__.py` | - | - |
| `tests/test_itsm_engine.py` | ITSMEngine 测试 — PipelineWrapper 迁移验证 | `ITSMEngineRunTests` — ITSMEngine.run() — pipeline 启动; `ITSMEnginePauseResumeRevokeTests` — ITSMEngine.pause/resume/revoke — pipeline 生命周期管理 |
| `tests/test_layout.py` | Layout engine 测试 — Sugiyama 布局计算 | `ComputeLayoutTests` — 布局引擎基本功能 |
| `tests/test_models.py` | ITSM 模型测试 | `TicketStatusChoicesTests`; `StateNodeKeyTests`; `TransitionNodeKeyTests`; `WorkflowCreateVersionNodeKeyTests`; `SlaTaskPausedAtTests` |
| `tests/test_workflow_builder.py` | ITSMWorkflowBuilder 测试 — 验证 pipeline tree 构建 | `BuildTreeBasicTests` — 基础节点映射 |

## `views`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views/__init__.py` | - | - |
| `views/dashboard.py` | ITSM Dashboard view — 看板数据聚合 | `DashboardViewSet` — ITSM 看板 — 数据聚合（只读） |
| `views/delegation.py` | Delegation views — 审批委托 CRUD | `DelegationViewSet` — 审批委托 CRUD |
| `views/escalation_views.py` | Escalation views — CRUD 升级级别管理 | `EscalationLevelViewSet` — 升级级别 CRUD（全局配置，非项目隔离） |
| `views/service_item.py` | ServiceItem views — 服务目录 CRUD + 提交申请 | `ServiceItemViewSet` — 服务目录管理 — 服务项 CRUD + 提交申请 |
| `views/ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传 | `TicketViewSet` — 工单管理 — project-scoped with environment gate |
| `views/views.py` | ITSM views - ServiceCategory, SlaPolicy | `ServiceCategoryViewSet` — 服务分类 CRUD — project-scoped; `SlaPolicyViewSet` — SLA 策略 CRUD — project-scoped |
| `views/workflow_views.py` | ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成 | `ItsmProjectViewSet` — ITSM project-scoped ViewSet — 整合 IAM ProjectFilteredViewSet ; `WorkflowViewSet` — 流程模板管理 — project-scoped with multi-tenant isolation; `WorkflowVersionViewSet` — 流程版本管理; `StateViewSet` — 节点管理; `TransitionViewSet` — 连线管理 |

