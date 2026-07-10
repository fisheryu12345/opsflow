# ITSM — 开发进度跟踪

> 最后更新: 2026-07-10 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐☆ (4.5/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | AI 生成器未用真实 LLM，双向 OpsFlow 审批集成未完成 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 工作流模板引擎 | P0 | ✅ | Workflow/State/Transition/Field 管理 | 完整 CRUD + deploy 版本快照 + 版本回滚 |
| 工单生命周期 | P0 | ✅ | Ticket CRUD + 流转 | submit/node_submit/approve/reject/suspend/resume/close + assign/auto_assign |
| Pipeline 驱动执行 | P0 | ✅ | Bamboo-engine DAG 驱动 | ITSMEngine(run/pause/resume/revoke/callback) + post_set_state 信号同步 |
| 4 种节点类型 | P0 | ✅ | 填单/审批/会签/自动任务 | ItsmFillForm/ItsmApproval/ItsmSign/ItsmAutoTask 组件 |
| 3 种网关类型 | P0 | ✅ | 排他/并行/条件并行网关 | EXCLUSIVE/ParallelGateway / PARALLEL/ConditionalParallelGateway / CONDITIONAL_PARALLEL/ConditionalParallelGateway + by_field 条件 + ConvergeGateway 自动配对 |
| 多级审批/会签 | P0 | ✅ | 多审批人/顺序/并行 | SignTask + RoleResolver(6种解析) + delegation |
| 可视化表单设计器 | P1 | ✅ | 拖拽设计工单表单 | FormDesigner.vue 三栏可视化拖拽(vuedraggable)，14种字段+Section+COL布局 |
| 升级层级体系 | P1 | ✅ | SLA 超时后的处理层级 | EscalationLevel 模型 CRUD + 前端升级 Tab(表格+编辑+用户多选) + seed 数据 |
| SLA 引擎 | P1 | ✅ | 端到端计时 + 超时通知 | SlaEngine(ITSMEngine.run启动→pipeline结束停止) + APScheduler 60s 检测 + notify_sla_violation + sla_info 前端展示 |
| 通知渠道 | P1 | ✅ | 钉钉/企微/邮件/IntegrationHub | 4 个 channel 实现 |
| 审批委托 | P1 | ✅ | 代理审批 | 时间范围+工单类型过滤 |
| 传统 ITSM 模型 | P1 | ✅ | Incident/Change/Problem/ServiceRequest | 完整 CRUD + 状态转换 |
| OpsFlow 集成 | P1 | ✅ | 审批后触发 OpsFlow 执行 | TicketOpsflowConfig + on_ticket_approved 完整 |
| 仪表盘 | P1 | ✅ | 工单统计(含 assigned/receiving) | summary/my_tasks/trend/status_dist/overdue |
| 工单分派/转派 | P1 | ✅ | 手动+自动分派 | assign/auto_assign API + 前端对话框(技能组筛选) |
| i18n 国际化 | P1 | ✅ | 中英文翻译 | itsm/zh-cn.ts + en.ts，SkillGroup/OnDutySchedule/AssignRule/EscalationLevel 完成 |
| DevOps 测试 | P1 | ✅ | 43+ 个单元测试 | test_models(14) + test_views(4) + test_services(8) + test_itsm_engine(8) + test_workflow_builder(11) + test_layout(3) |
| 多租户对齐 | P1 | ✅ | Project/Business FK 隔离 | ITSM 核心模型注入 project/business FK，ViewSet 继承 ItsmProjectViewSet |
| SlaPolicy 模型 | P1 | ✅ | SLA 策略定义 | SlaPolicy(priority+response+resolve) + SlaTask 计时任务 |
| AI 智能生成 | P2 | 🔄 | LLM 生成工作流 | AIGenerator：内置关键词模板引擎，<b>未接入真实 DeepSeek</b> |
| 服务目录 | P2 | ✅ | 可请求的 IT 服务项 | ServiceItem 模型 + 双模式(flow/lightweight) + 服务市场(分类树+卡片) + 服务详情(表单+提交) + 管理后台(CRUD+预览) |
| OpsFlow 双向审批 | P2 | 📅 | OpsFlow 审批节点创建 ITSM 工单 | 仅 ITSM→OpsFlow 单向，反向未实现 |
| Monitor 告警→工单 | P2 | 📅 | 告警自动创建工单 | 无 Ticket ← Alert 集成 |
| 变更日历 | P2 | 📅 | 变更时间线展示 | 无前端组件 |
| AI 全面 LLM 替代 | P2 | 📅 | DeepSeek 替代关键词模板 | — |

## TODO

### P0
- [ ] 无

### P1
- [ ] AIGenerator 接入 DeepSeek

### P2
- [ ] OpsFlow 审批节点 ↔ ITSM 工单双向
- [ ] Monitor 告警 → 创建工单
- [ ] 变更日历前端

### 2026-07-07 Update
> 提交: bafc693b
- SLA 端到端计时: 启动移至 ITSMEngine.run()，停止由 pipeline EndEvent 统一处理，移除节点级双重触发 → ✅
- APScheduler: BackgroundScheduler 替代 Celery Beat，60s 间隔运行 SLA 检查 → ✅
- 超时通知: _execute_escalation 调用 notify_sla_violation() → ✅
- 前端 SLA 显示: 工单列表 SLA 列(状态+倒计时) + 详情 SLA 信息卡片 → ✅
- 仪表板 deadline: 超时统计从 7 天硬编码改为 SlaTask.deadline → ✅
- 升级层级体系: EscalationLevel 模型重新实现(level/timeout/action/notify_users) + ViewSet CRUD + 前端完整 Tab(CRUD表格+编辑对话框+用户多选) + seed 数据 → ✅
- 清理: PriorityMatrix(未使用)、cost_seconds(未更新) → ✅
- 修复: remaining_seconds=0 假零 bug、APScheduler 时区硬编码、N+1 查询、seed_itsm --force 更新升级级别 → ✅

### 2026-07-05 Update #2
> 提交: e4b1923c
- 服务目录: ServiceItem 模型 + flow/lightweight 双模式 + 服务市场(分类树+卡片) + 服务详情(表单+提交) + 管理后台(CRUD+预览) + 12个种子服务项 → ✅
- SignTask 通过 TicketStatus pk 查询修复 → ✅
- SLA stopped 状态重置支持（审批节点复用同一 SLA）→ ✅
- WorkflowVersion rollback 保留 node_key，StateSync 保护旧状态 → ✅
- 前端设计器清理 console.log + 连线数据引用修复 → ✅

### 2026-07-05 Update
> 提交: 229bae20
- node_key 稳定标识: State/Transition 新增 node_key 字段，Workflow create_version 改用 node_key 做快照 key，Ticket get_state 支持 node_key 双向查找，Pipeline activity ID 用 node_key 匹配 bamboo element → ✅
- 前端设计器增强: 节点拖入自动初始化(node_key+默认数据)，连线连接校验(禁止非法连接)，Stencil 重构(clone→createNode)，旧流程无 node_key 兼容 → ✅
- SLA 暂停/恢复增强: SlaTask.paused_at 字段 + pause/resume 时长补偿 + start_ticket_sla 改用 get_or_create 不覆盖 → ✅
- 工单详情内联填单: NORMAL 节点运行时渲染表单字段(TEXT/SELECT/FILE)，联动 NodeSubmit 后端，从 WorkflowVersion 合并字段定义 → ✅
- 删除已废弃 state_machine.py → ✅
- 服务目录设计文档完成，待 Phase1 编码 → 📅

### 2026-06-30 Update #2
> 提交: 6377ca67
- 多租户对齐: 12个模型加 project/business FK + 0010 migration → ItsmProjectViewSet 基类 (ProjectFilteredViewSet+TenantPermission+dvadmin响应+NULL兼容+dept_belong_id allow_null) → 6个ViewSet全切换 → AssignEngine/SlaEngine/EscalationService 加 project_id 租户过滤 → ✅
- 全局项目选择器: stores/project.ts (全局Pinia) + GlobalProjectSwitcher.vue (导航栏) + service.ts 自动注入 project_id + 8个opsflow子页面清理本地ProjectSwitcher → ✅
- SLA 编辑: index.vue 新增 SLA 编辑弹窗 (name/response_minutes/resolve_minutes/is_active) + onSlaToggle 保存后端 → ✅
- 委托修复: DelegationCreateUpdateSerializer user 设 read_only + user_name/delegate_to_name 序列化字段 → ✅
- 序列化器名补全: SkillGroup(leader_name)/OnDuty(group_name/user_name)/AssignRule(target_group_name/match_category_name)/Escalation(group_name) → ✅
- dept_belong_id: CustomModelSerializer allow_null=True 根因修复 → ✅
- 对话框遮罩: 5个子页面 el-dialog 加 append-to-body → ✅
- 布局切换删除: setings.vue 移除4个layout切换卡片 → ✅
- 种子数据: 完整重写 seed_itsm.py (Workflows/SkillGroups/AssignRules/Escalations/OnDuty) → ✅
- Bug 修复: workflow_name 保存/creator FK/流程模板删除+图标/事件新建工单/Check import/el-radio label→value/Delegation Check import → ✅

### 2026-06-30 Update #1
> 提交: 840aa4ea~ba3112f
- 分派体系: SkillGroup/OnDutySchedule/AssignRule/EscalationLevel/TicketTransferLog 模型 + AssignEngine + EscalationService → ✅
- 可视化表单设计器: FormDesigner.vue 三栏拖拽设计器 → ✅
- 版本回滚: WorkflowVersionViewSet.rollback → ✅
- 仪表盘修复: assigned/receiving/running 状态筛选 → ✅
- i18n: itsm/zh-cn.ts + en.ts 翻译文件，管理页面全部完成 → ✅
- 测试: 26 个 test case (models 14 + views 4 + services 8) → ✅
- APScheduler: start_itsm_scheduler 独立进程 → ✅
- 多租户对齐: ITSM 核心模型注入 project/business FK，ItsmProjectViewSet 统一 project-scoped → ✅
- Bug 修复: escalation_service escalated_at datetime 类型、assign_engine user=None 守卫、dashboard ACTIVE_STATUSES、tasks set_status、onBeforeUnmount import → ✅

### 2026-07-04 Update
> 提交: 1d8ddc88
- ITSM 引擎重构: PipelineWrapper → ITSMEngine（实例化模式，与 FlowEngine 对齐），新增 ITSMWorkflowBuilder 和 condition_utils → ✅
- 信号增强: post_set_state 监听（bamboo 节点状态 → TicketStatus 同步）→ ✅
- 布局引擎共享: opsflow/core/layout/ → common/utils/layout/（零修改 copy）→ ✅
- 三种网关: EXCLUSIVE（排他网关）+ PARALLEL（并行网关）+ CONDITIONAL_PARALLEL（条件并行网关，原 ROUTER_P）→ ✅
- 条件表达式扩展: condition_type=by_field 结构化条件，表单字段 NodeOutput 注册到 data.inputs → ✅
- 组件输出: ItsmFillForm/ApprovalService 新增 data.set_outputs() 供网关条件运行时引用 → ✅
- 前端设计器: 排他/并行/条件并行网关拖拽 + 出边校验 + by_field 条件编辑面板 → ✅
- 测试: test_itsm_engine(8) + test_workflow_builder(11) + test_layout(3) 新增 → ✅
- eri migration 修复: RenameIndex → AddIndex，SQLite 测试兼容 → ✅

### 2026-07-07 Update
> 提交: db5ad6f9
- 子 Tab 组件化重构: tickets/workflows/sla/escalation 内联 tab → 4 个独立组件（TicketList/WorkflowList/SlaPolicyList/EscalationList），index.vue 从 ~1200 行降至 ~250 行 → ✅
- ProjectFilteredViewSet 过滤修复: 工单详情 404 — perform_create() 补齐 project_id 赋值 + get_queryset() 仅对 list/create 应用 project_id 过滤 → ✅
- Dashboard ECharts 重复初始化修复 + ServiceMarket i18n HTML 警告修复 → ✅
- 前端规范更新: 子 Tab 强制组件模式 + ProjectFilteredViewSet 过滤规范 → ✅

### 2026-07-10 Update
> 提交: 0a34cab8
- 网关条件表达式修复: `add_condition()` 从 `{'evaluate': expr}` 改为直接传 `expr`（匹配 BoolRule 原始字符串格式），修复排他网关条件分支始终走默认路径 → ✅
- 驳回流程清理: 驳回后重置 `TicketStatus→WAIT` + 清空 `node_status={}`，防止重新提交时状态残留 → ✅
- 提交流程修复: 移除 `do_in_state()` 提前完成首节点（消除与 engine callback 的竞态），改为统一下批量 `TicketStatus→WAIT` → ✅
- 数字字段兼容: `ItsmFormField.vue` 空字符串 → null（兼容 ElInputNumber）→ ✅
- 设计器边重构: 移除驳回边开关（`isReject`/`direction:'reject'`），改为条件表达式统一管理；`isGatewayEdge` 网关门卫仅对排他/条件并行网关显示边配置；结构化条件预览（`parsedRules`）+ 已有表达式反向解析（`openConditionDialog`）→ ✅
- 审批/会签默认字段清理: `APPROVAL: []` / `SIGN: []`，改为用户通过 FormDesigner 自定义 → ✅
- 条件运算符标准化: `useGraphCanvas.ts` 字符串运算符统一为 BoolRule 兼容（`in`/`notin` 替代 `contains`/`startsWith`/`endsWith`/`regex`）→ ✅
