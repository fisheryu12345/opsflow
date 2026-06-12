# itsm — 模块索引

> 上次自动更新: 2026-06-12

---

## `itsm/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | ITSM service management app |
| `admin.py` |  | feat(itsm,monitor): create ITSM service management and Monit |
| `apps.py` | 123 | `ItsmConfig` |
| `signals.py` | ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 | `ticket_post_save()` — 工单保存后 — 根据状态变化触发 SLA |
| `tasks.py` | ITSM Celery 定时任务 | `sla_check()` — SLA 定时检查 — 每分钟执行<br>`auto_resolve_expired_tickets()` — 自动关闭超时未处理的草稿工单（每日执行） |
| `urls.py` |  | URL configuration for ITSM app |

## `itsm\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |

## `itsm\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `itsm_check_sla.py` | ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态 | `Command` |

## `itsm\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Re-export all models for itsm app |
| `delegation.py` | ApprovalDelegate model — 审批委托 | `ApprovalDelegate` — 审批委托 — 将审批权限临时委托给其他用户 |
| `field.py` | ITSM Field model — 节点表单字段定义 | `Field` — 表单字段定义 — 绑定到 State |
| `incident.py` | ITSM model definitions | `ServiceCategory` — 服务分类 — 服务目录的一级/二级分类<br>`SlaPolicy` — SLA 策略定义<br>`Incident` — 事件工单 (Incident)<br>`Change` — 变更申请 (Change)<br>`ServiceRequest` — 服务请求 (Service Request)<br>`Problem` — 问题管理 (Problem) |
| `sla.py` | ITSM SLA model — SLA 策略、优先级矩阵、计时任务 | `PriorityMatrix` — 优先级矩阵 — 紧急程度 × 影响范围 → 优先级<br>`SlaTask` — SLA 计时任务 — 工单级别的计时 |
| `state.py` | ITSM State model — 流程节点定义 | `State` — 流程节点 — 对应 pipeline 中的一个活动 |
| `ticket.py` | ITSM Ticket model — 工单运行时 | `Ticket` — ITSM 工单 — pipeline 驱动的运行实例<br>`TicketStatus` — 节点运行时状态 — 工单在每个节点上的实时状态<br>`SignTask` — 会签/审批记录 — 每个审批人的操作<br>`generate_sn()` |
| `transition.py` | ITSM Transition model — 节点间连线定义 | `Transition` — 节点间流转线 — 可选条件表达式 |
| `workflow.py` | ITSM Workflow model — 流程模板定义与版本管理 | `Workflow` — ITSM 流程模板 — 设计时定义<br>`WorkflowVersion` — 流程版本 — 部署快照，工单运行的依据 |

## `itsm\pipeline_plugins/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `components.py` | ITSM Pipeline 组件注册 | `ItsmFillFormService` — 填单节点 — 等待用户提交表单<br>`ItsmApprovalService` — 审批节点 — 支持单签/会签<br>`ItsmSignService` — 会签节点 — 多审批人，根据 finish_condition 决定<br>`ItsmAutoTaskService` — 自动任务节点 — 执行自动化操作<br>`ItsmFillFormComponent`<br>`ItsmApprovalComponent` |

## `itsm\serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `delegation.py` | Delegation serializers — 审批委托序列化器 | `DelegationSerializer` — 委托列表/详情序列化器<br>`DelegationCreateUpdateSerializer` — 委托创建/更新序列化器 |
| `legacy.py` | Serializers for ITSM app | `ServiceCategorySerializer`<br>`ServiceCategoryCreateUpdateSerializer`<br>`SlaPolicySerializer`<br>`IncidentSerializer`<br>`IncidentCreateUpdateSerializer`<br>`ChangeSerializer` |
| `ticket_serializers.py` | Ticket serializers | `TicketSerializer`<br>`TicketCreateSerializer`<br>`TicketSubmitSerializer` — 提交工单（启动 pipeline）<br>`TicketApproveSerializer` — 审批工单<br>`TicketStatusSerializer`<br>`SignTaskSerializer` |
| `workflow_serializers.py` | Workflow serializers | `WorkflowSerializer`<br>`WorkflowCreateSerializer`<br>`WorkflowVersionSerializer`<br>`StateSerializer`<br>`TransitionSerializer`<br>`FieldSerializer` |

## `itsm\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for itsm app |
| `ai_generator.py` | AI 驱动的 ITSM 工作流生成器 | `AIGenerator` — AI 驱动的 ITSM 工作流生成器 |
| `notifications.py` | ITSM 通知服务 — 状态变更时的消息通知 | `NotificationService` — 通知服务 — 发送工单状态通知<br>`send_wecom_notify()` — 企业微信机器人消息<br>`send_dingtalk_notify()` — 钉钉机器人消息<br>`send_email_notify()` — SMTP 邮件通知<br>`notify_via_integration_hub()` — 通过 Integration Hub 通道发送通知 (如果可用)<br>`get_config_from_ticket()` — 从 ticket.meta 或 settings 中读取通知配置 |
| `opsflow_trigger.py` | ITSM 工单审批通过后触发 OpsFlow 自愈流程 | `TicketOpsflowConfig` — ITSM 工单类型到 OpsFlow 模板的映射配置<br>`OpsflowTriggerService` — ITSM 工单审批通过后触发 OpsFlow 自愈流程的服务 |
| `pipeline_wrapper.py` | PipelineWrapper — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树 | `PipelineWrapper` — ITSM 工作流转 pipeline 执行引擎 |
| `role_resolver.py` | 处理人解析器 — 将处理器类型转换为实际用户名列表 | `resolve_processors()` — 解析处理人配置，返回用户名列表 |
| `sla_engine.py` | SLA 引擎 — 工单级别计时与升级管理 | `SlaEngine` — SLA 引擎 — 管理工单的 SLA 计时与升级 |
| `state_machine.py` | ITSM services — state machine, SLA timer, escalation engine | `can_transition()` — 检查状态转换是否合法<br>`apply_sla_policy()` — 应用 SLA 策略，计算截止时间<br>`check_sla_compliance()` — 检查 SLA 合规状态<br>`auto_escalate()` — 自动升级 — 超时未处理返回 True |

## `itsm\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `dashboard.py` | ITSM Dashboard view — 看板数据聚合 | `DashboardViewSet` — ITSM 看板 — 数据聚合（只读） |
| `delegation.py` | Delegation views — 审批委托 CRUD | `DelegationViewSet` — 审批委托 CRUD |
| `ticket_views.py` | ITSM Ticket views — 工单管理、提交、审批、状态管理 | `TicketViewSet` — 工单管理 |
| `views.py` | ITSM views - Incident, Change, ServiceRequest, Problem, ServiceCategory, SlaPolicy | `ServiceCategoryViewSet` — 服务分类 CRUD<br>`SlaPolicyViewSet` — SLA 策略 CRUD<br>`IncidentViewSet` — 事件工单管理<br>`ChangeViewSet` — 变更申请管理<br>`ServiceRequestViewSet` — 服务请求管理<br>`ProblemViewSet` — 问题管理 |
| `workflow_views.py` | ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成 | `WorkflowViewSet` — 流程模板管理<br>`WorkflowVersionViewSet` — 流程版本管理<br>`StateViewSet` — 节点管理<br>`TransitionViewSet` — 连线管理<br>`FieldViewSet` — 字段管理<br>`AIGenerateView` — AI 生成工作流 (APIView) |
