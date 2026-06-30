# itsm — 模块索引

> 上次自动更新: 2026-06-30 | 触发提交: c46945dd

---

## 根目录

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | 包初始化 | — |
| `apps.py` | Django AppConfig，注册信号 | `class ItsmConfig(AppConfig)` |
| `urls.py` | URL 路由注册 (10 ViewSets + AI 视图) | `router.register()`, `AIGenerateView` |
| `signals.py` | Django 信号处理 | — |
| `tasks.py` | Celery 异步任务 | `auto_resolve()` |
| `admin.py` | Django Admin 注册 | — |

## `management/commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `seed_itsm.py` | 完整种子数据 (14 cat + 4 SLA + 5 groups + 3 workflows + 7 escalations + 5 rules + 8 duty + 10 incidents + 6 changes + 6 requests + 3 problems) | `class Command(BaseCommand)` — `_create_service_categories()`, `_create_workflows()`, `_create_skill_groups()`, ... |
| `itsm_check_sla.py` | SLA 超时检查命令 | — |
| `start_itsm_scheduler.py` | 独立 APScheduler 进程 (ES/SLA) | — |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `workflow.py` | 流程模板 + 版本管理 | `class Workflow(CoreModel)` — `project` FK, `create_version()`; `class WorkflowVersion` — 运行时快照 JSON |
| `ticket.py` | 工单运行时 (pipeline 驱动) | `class Ticket(CoreModel)` — `project`+`business` FK, `set_status()`; `class TicketStatus`; `class SignTask` |
| `incident.py` | 事件/变更/请求/问题 + 分类 + SLA | `Incident`, `Change`, `ServiceRequest`, `Problem`, `ServiceCategory`, `SlaPolicy` (全含 `project` FK) |
| `sla.py` | SLA 优先级矩阵 + 计时任务 | `class PriorityMatrix`; `class SlaTask` |
| `skill_group.py` | 技能组 + 值班排班 | `class SkillGroup` — `business` FK, `leader`, `members` M2M; `class OnDutySchedule` — `project` FK |
| `assign_rule.py` | 自动分派路由规则 | `class AssignRule(CoreModel)` — `project` FK, `match_category/priority/itsm_type`, `target_group`, `assign_mode` |
| `escalation.py` | 多级升级策略 | `class EscalationLevel(CoreModel)` — `project` FK, `group/level/timeout_minutes/action/notify_users` |
| `delegation.py` | 审批委托 (临时转交) | `class ApprovalDelegate(CoreModel)` |
| `transfer_log.py` | 分派/转派审计日志 | `class TicketTransferLog(CoreModel)` |
| `state.py` | 流程节点定义 | `class State(CoreModel)` |
| `transition.py` | 流程连线定义 | `class Transition(CoreModel)` |
| `field.py` | 节点表单字段 | `class Field(CoreModel)` — LAYOUT_CHOICES 12/8/6/4/3 |

## `serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `workflow_serializers.py` | Workflow/WorkflowVersion/State/Transition/Field | `WorkflowVersionSerializer` 含 `workflow_name` |
| `ticket_serializers.py` | Ticket/TicketStatus/SignTask | `TicketSerializer`, `TicketCreateSerializer` |
| `legacy.py` | Incident/Change/ServiceRequest/Problem/Category/Sla | 6 个 CRUD 序列化器 |
| `assign_serializers.py` | SkillGroup/OnDuty/AssignRule/Escalation/TransferLog | 含 `leader_name`, `group_name`, `user_name`, `target_group_name`, `match_category_name` |
| `delegation.py` | ApprovalDelegate | `DelegationSerializer` 含 `user_name`/`delegate_to_name`; `DelegationCreateUpdateSerializer` (`user` read_only) |

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `assign_engine.py` | 自动分派引擎 (规则匹配→人选确定→执行) | `class AssignEngine(ticket, project_id)` — `auto_assign()`, `_match_rule()` project-scoped, `manual_assign()` |
| `escalation_service.py` | 多级升级检测与执行 | `class EscalationService` — `check_and_escalate()`, `_process_ticket()` project-scoped |
| `sla_engine.py` | SLA 计时与升级 | `class SlaEngine` — `start_ticket_sla()` project-scoped, `check_all_active_sla()` |
| `pipeline_wrapper.py` | Bamboo Pipeline 封装 | `class PipelineWrapper` — `run_pipeline()`, `pause/resume/revoke`, `activity_callback()` |
| `opsflow_trigger.py` | ITSM→OpsFlow 执行触发 | `class OpsflowTriggerService`, `class TicketOpsflowConfig` |
| `state_machine.py` | 工单状态机 | `class StateMachine` |
| `ai_generator.py` | AI 工作流生成 (LLM→节点/连线) | `class AIGenerator` |
| `notifications.py` | 通知服务 | `class NotificationService` |
| `role_resolver.py` | 角色解析 | 审批人/处理人查找 |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `workflow_views.py` | 流程模板 + 版本 + 节点/连线/字段 API | `class ItsmProjectViewSet` — IAM+ProjectFilteredViewSet+dvadmin响应; `WorkflowViewSet` (deploy/rollback); `WorkflowVersionViewSet`; `StateViewSet` (sync); `TransitionViewSet` (sync); `FieldViewSet` (batch_update) |
| `ticket_views.py` | 工单 CRUD + 提交/审批/分派/挂起/恢复/关闭/文件上传 | `class TicketViewSet(ItsmProjectViewSet)` — submit/approve/reject/suspend/resume/close/assign/auto_assign/upload_file/node_submit/status |
| `views.py` | 事件/变更/请求/问题/分类/SLA | `IncidentViewSet` (assign/resolve/close); `ChangeViewSet` (approve/reject); `ServiceRequestViewSet`; `ProblemViewSet`; `ServiceCategoryViewSet`; `SlaPolicyViewSet` |
| `assign_views.py` | 技能组/排班/分派/升级/日志 | `SkillGroupViewSet` (business-scoped, add_member/remove_member); `OnDutyScheduleViewSet`; `AssignRuleViewSet`; `EscalationLevelViewSet`; `TicketTransferLogViewSet` |
| `dashboard.py` | 看板 API | `class DashboardView` |
| `delegation.py` | 委托 CRUD + 切换 + 我的委托 | `class DelegationViewSet` — toggle_active/my_delegations, `perform_create` 自动设 user |

## `tests/`

| 文件 | 用途 |
|------|------|
| `test_models.py` | 模型创建/字段/约束测试 |
| `test_services.py` | AssignEngine/SlaEngine/EscalationService 单元测试 |
| `test_views.py` | ViewSet API 端点测试 |

## `pipeline_plugins/`

| 文件 | 用途 |
|------|------|
| `components.py` | Bamboo Pipeline 自定义组件 (ITSM 审批/填单节点) |
