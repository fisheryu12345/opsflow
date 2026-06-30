# ITSM — 开发进度跟踪

> 最后更新: 2026-06-30 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐☆ (4.5/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | AI 生成器未用真实 LLM，双向 OpsFlow 审批集成未完成，服务目录未建 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 工作流模板引擎 | P0 | ✅ | Workflow/State/Transition/Field 管理 | 完整 CRUD + deploy 版本快照 + 版本回滚 |
| 工单生命周期 | P0 | ✅ | Ticket CRUD + 流转 | submit/node_submit/approve/reject/suspend/resume/close + assign/auto_assign |
| Pipeline 驱动执行 | P0 | ✅ | Bamboo-engine DAG 驱动 | PipelineWrapper(build_tree/run/pause/resume/revoke/callback) |
| 4 种节点类型 | P0 | ✅ | 填单/审批/会签/自动任务 | ItsmFillForm/ItsmApproval/ItsmSign/ItsmAutoTask 组件 |
| 多级审批/会签 | P0 | ✅ | 多审批人/顺序/并行 | SignTask + RoleResolver(6种解析) + delegation |
| 可视化表单设计器 | P1 | ✅ | 拖拽设计工单表单 | FormDesigner.vue 三栏可视化拖拽(vuedraggable)，14种字段+Section+COL布局 |
| 智能分派体系 | P1 | ✅ | 技能组+排班+路由+升级 | SkillGroup/OnDuty/AssignRule/EscalationLevel/TransferLog + AssignEngine + EscalationService |
| SLA 引擎 | P1 | ✅ | 超时升级 | SlaEngine + EscalationService 多级升级(L1→L2→L3) + APScheduler 每分钟检测 |
| 通知渠道 | P1 | ✅ | 钉钉/企微/邮件/IntegrationHub | 4 个 channel 实现 |
| 审批委托 | P1 | ✅ | 代理审批 | 时间范围+工单类型过滤 |
| 传统 ITSM 模型 | P1 | ✅ | Incident/Change/Problem/ServiceRequest | 完整 CRUD + 状态转换 |
| OpsFlow 集成 | P1 | ✅ | 审批后触发 OpsFlow 执行 | TicketOpsflowConfig + on_ticket_approved 完整 |
| 仪表盘 | P1 | ✅ | 工单统计(含 assigned/receiving) | summary/my_tasks/trend/status_dist/overdue |
| 工单分派/转派 | P1 | ✅ | 手动+自动分派 | assign/auto_assign API + 前端对话框(技能组筛选) |
| i18n 国际化 | P1 | ✅ | 中英文翻译 | itsm/zh-cn.ts + en.ts，SkillGroup/OnDutySchedule/AssignRule/EscalationLevel 完成 |
| DevOps 测试 | P1 | ✅ | 26 个单元测试 | test_models(14) + test_views(4) + test_services(8) |
| 多租户对齐 | P1 | ✅ | Project/Business FK 隔离 | ITSM 核心模型注入 project/business FK，ViewSet 继承 ItsmProjectViewSet |
| SlaPolicy 模型 | P1 | ✅ | SLA 策略定义 | PriorityMatrix + SLA 策略 |
| AI 智能生成 | P2 | 🔄 | LLM 生成工作流 | AIGenerator：内置关键词模板引擎，<b>未接入真实 DeepSeek</b> |
| 服务目录 | P2 | 📅 | 可请求的 IT 服务项 | ServiceCategory 模型存在，但无完整服务项+履行流程 |
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
