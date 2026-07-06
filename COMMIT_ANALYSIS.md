# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## 0a4a32f3

> 提交日期: 2026-07-07 | 提交信息: feat: ITSM i18n full coverage + name_en fields + Manage Categories dialog

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/models/catalog.py` | 后端 | ServiceCategory + SlaPolicy 新增 name_en |
| `backend/itsm/models/escalation.py` | 后端 | EscalationLevel 新增 name_en |
| `backend/itsm/models/service_item.py` | 后端 | ServiceItem 新增 name_en + description_en |
| `backend/itsm/models/state.py` | 后端 | State 新增 name_en |
| `backend/itsm/models/workflow.py` | 后端 | Workflow 新增 name_en |
| `backend/itsm/migrations/0002_*` | 迁移 | 6 个 name_en 字段迁移 |
| `backend/itsm/serializers/legacy.py` | 后端 | ServiceCategory/SlaPolicy to_representation i18n |
| `backend/itsm/serializers/service_item.py` | 后端 | ServiceItem + category_name i18n |
| `backend/itsm/serializers/workflow_serializers.py` | 后端 | Workflow/WorkflowVersion i18n |
| `backend/itsm/serializers/escalation.py` | 后端 | EscalationLevel i18n |
| `backend/itsm/management/commands/seed_itsm.py` | 后端 | 全量中英双语 seed 数据 |
| `web/src/views/apps/itsm/*.vue` (12 文件) | 前端 | 全页面 i18n 替换 + Manage Categories CRUD 弹窗 |
| `web/src/i18n/pages/itsm/zh-cn.ts` | i18n | 新增 150+ 中文 key |
| `web/src/i18n/pages/itsm/en.ts` | i18n | 对应英文翻译 |

### 解决

- **问题/背景：** ITSM 12 个前端页面硬编码中文违反 i18n first 规则；seed 数据全中文切换英文不生效；分类管理按钮为占位 ElMessage
- **办法：** 3 个 Agent 并行 i18n 替换；6 个模型加 name_en + 序列化器按 ?lang=en 返回；seed 中英双语重写；新增树形 CRUD 分类管理弹窗

### 验证

- 改动类型: feat + refactor
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待推送 ✅

---

## bafc693b

> 提交日期: 2026-07-07 | 提交信息: feat: end-to-end SLA timing + escalation hierarchy — 端到端 SLA 计时与升级层级体系

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/services/itsm_engine.py` | 后端 | SLA 启动移至 ITSMEngine.run() — pipeline 启动时统一 start_ticket_sla() |
| `backend/itsm/models/ticket.py` | 后端 | 移除节点级 SLA start/stop，do_before_exit_state 变为空钩子 |
| `backend/itsm/signals.py` | 后端 | 移除 post_set_state 按节点无条件启动 SLA |
| `backend/itsm/apps.py` | 后端 | APScheduler BackgroundScheduler 替代 Celery Beat，60s 间隔运行 SLA check |
| `backend/itsm/sla_check_job.py` | 后端 | **新建** — 普通函数版 SLA 检查，不依赖 Celery |
| `backend/itsm/services/sla_engine.py` | 后端 | _execute_escalation 新增 notify_sla_violation 超时通知 |
| `backend/itsm/serializers/ticket_serializers.py` | 后端 | TicketSerializer 新增 sla_info 字段暴露 SLA 数据到前端 (+ prefetch_related N+1 消除) |
| `backend/itsm/views/dashboard.py` | 后端 | 超时统计从 7 天硬编码改为 SlaTask.deadline < now |
| `backend/itsm/models/escalation.py` | 后端 | **新建** — EscalationLevel 模型 |
| `backend/itsm/views/escalation_views.py` | 后端 | **新建** — EscalationLevelViewSet CRUD |
| `backend/itsm/urls.py` | 后端 | 注册 escalation-levels 路由 |
| `backend/itsm/models/sla.py` | 后端 | 清理 — 删除 PriorityMatrix(未使用)、cost_seconds(未更新) |
| `backend/itsm/management/commands/seed_itsm.py` | 后端 | 新增 _create_escalation_levels() + --force 更新支持 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 后端 | 注册升级 Tab 页面配置 |
| `web/src/views/apps/itsm/index.vue` | 前端 | 工单表格新增 SLA 列 + 完整升级 Tab(CRUD表格+编辑对话框+用户多选) |
| `web/src/views/apps/itsm/TicketDetail.vue` | 前端 | 新增 SLA 信息卡片(状态/倒计时/截止时间) |
| `web/src/views/apps/itsm/Dashboard.vue` | 前端 | 超时列表改用 overdue_seconds 格式化显示 |
| `web/src/api/itsm/index.ts` | 前端 | 新增 escalationApi |

### 解决

- **问题/背景：** SLA 与 pipeline 协作断裂：双重触发、无定时检查、无超时通知、数据前端不可见、仪表板硬编码 7 天规则
- **办法：** 重构为端到端 SLA（ITSMEngine.run 启动→pipeline 结束停止）；APScheduler 替代 Celery Beat；补全超时通知；新建 EscalationLevel 模型+API+UI；仪表板改 SlaTask.deadline；序列化器暴露 sla_info 到前端

### 文档

- **生成文档：**
  - `docs/itsm/features/2026-07-07-sla-escalation.md`

### 验证

- 改动类型: feat + fix + chore
- 清理乱码: 无
- 子 App index.md 更新: itsm
- 工作区状态: 待提交 ✅

---

## fc3bae8c

> 提交日期: 2026-07-06 | 提交信息: refactor: full ITSM legacy cleanup + 6 bug fixes — 清理遗留模块与修复代码审查发现的 6 个缺陷

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/views/assign_views.py` | 后端 | **删除** — 5 个遗留 ViewSet (SkillGroup/OnDutySchedule/AssignRule/EscalationLevel/TicketTransferLog) |
| `backend/itsm/views/views.py` | 后端 | **重写** — 仅保留 ServiceCategory/SlaPolicy，删除 Incident/Change/ServiceRequest/Problem ViewSet 及 CRUD |
| `backend/itsm/serializers/assign_serializers.py` | 后端 | **删除** |
| `backend/itsm/serializers/legacy.py` | 后端 | **重写** — 仅保留 ServiceCategory/SlaPolicy serializers |
| `backend/itsm/services/assign_engine.py` | 后端 | **删除** — AssignEngine 自动分派引擎（已由节点 processors 驱动替代） |
| `backend/itsm/services/escalation_service.py` | 后端 | **删除** — EscalationService 升级检测 |
| `backend/itsm/management/commands/start_itsm_scheduler.py` | 后端 | **删除** — ITSM 独立调度器 |
| `backend/itsm/models/incident.py` | 后端 | **删除** — Incident/Change/ServiceRequest/Problem 模型（ServiceCategory/SlaPolicy 迁至 catalog.py） |
| `backend/itsm/models/skill_group.py` | 后端 | **删除** — SkillGroup/OnDutySchedule |
| `backend/itsm/models/assign_rule.py` | 后端 | **删除** |
| `backend/itsm/models/escalation.py` | 后端 | **删除** — EscalationLevel |
| `backend/itsm/models/transfer_log.py` | 后端 | **删除** — TicketTransferLog |
| `backend/itsm/models/catalog.py` | 后端 | **新建** — ServiceCategory + SlaPolicy 模型 |
| `backend/itsm/services/role_resolver.py` | 后端修复 | **Bug 1:** _resolve_starter_leader 用 `username=ticket.creator` → `id=ticket.creator` (creator 是 IntegerField) |
| `backend/itsm/pipeline_plugins/components.py` | 后端修复 | **Bug 2:** ItsmSignService 持有 _approval_svc 实例，只在 is_schedule_finished() 为 True 时 finish_schedule() |
| `backend/itsm/services/workflow_builder.py` | 后端修复 | **Bug 3:** `all_node_ids.add(sid_str)` 添加原始 key 使 _collect_condition_refs 能匹配；**Bug 4:** run_salt 12→6 字符确保 element ID 不超 EriNode.node_id(33) |
| `backend/itsm/signals.py` | 后端修复 | **Bug 6:** EndEvent 检测从 JSON 子串匹配改为 json.loads() 解析后检 type 字段 |
| `backend/itsm/views/ticket_views.py` | 后端修复 | **Bug 5:** assign 接口加 int(user_id) 转换和明确错误提示 |
| `backend/itsm/views/service_item.py` | 后端修复 | 保存 pipeline_id + 设置 current_status='running' 使 pipeline 结束信号能匹配 |
| `backend/portal/views/dashboard.py` | 后端 | 移除 Incident/Change 引用，改用 Ticket 统计 |
| `backend/open_api/views/external.py` | 后端 | 移除 create_incident/query_incident 端点 |
| `backend/monitor/adapters/action/itsm.py` | 后端 | Incident → Ticket |
| `backend/monitor/views/alert_views.py` | 后端 | Incident → Ticket |
| `backend/iam/migrations/0003-0005` | 迁移 | 删除 PageTab 记录（3 个迁移） |
| `backend/itsm/migrations/0008-0009` | 迁移 | FK 字段清理 + 10 张 legacy 表删除 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 配置 | 移除 incidents/changes/assign-rules/skill-groups/on-duty/escalation tab 配置 |
| `backend/itsm/management/commands/seed_itsm.py` | 配置 | 清理遗留 seed 数据 |
| `web/src/views/apps/itsm/index.vue` | 前端 | 移除 6 个废弃 tab 组件引用+import+componentMap；移除工单详情 dialog 改用独立页面路由；转派/分派按钮限制 finished/terminated 状态 |
| `web/src/views/apps/itsm/TicketDetail.vue` | 前端 | **新建** 独立详情页（全宽布局、单据信息区、申请内容区、流程图、已完成节点时间线、审批结果标签） |
| `web/src/views/apps/itsm/FlowChart.vue` | 前端 | **新建** X6 只读流程图（dagre 布局、状态着色、zoom in/out/fit、驳回标签） |
| `web/src/api/itsm/index.ts` | 前端 | 移除 legacy API (incidentApi/changeApi/AssignIncident 等) |
| `web/src/router/route.ts` | 前端 | ItsmTicketDetail 路由 |
| `web/src/views/apps/itsm/{AssignRule,EscalationLevel,OnDutySchedule,SkillGroup,TeamDashboard}.vue` | 前端 | **删除** — 5 个废弃组件 |
| `backend/itsm/index.md` | 文档 | 全量重写，移除已删除文件引用 |
| `docs/superpowers/specs/2026-07-06-itsm-flowchart-readonly-design.md` | 文档 | **新建** FlowChart 只读流程设计文档 |

### 解决

- **问题/背景：** 继承多个会话累计改动：ITS 遗留模型/视图/序列化器/服务/测试文件在统一 Ticket 模型后未被清理（6 个废弃 tab）；代码审查发现 6 个严重 bug（STARTER_LEADER 解析、会签提前结束、条件表达式失效等）
- **办法：** 全量清理遗留代码（删除 15+ 后端文件、5 个 Vue 组件、8 张 DB 表）；逐一修复 6 个 confirmed bug；新增 FlowChart 只读流程图替代 el-steps 线性展示；独立详情页全面优化

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-07-06-itsm-flowchart-readonly-design.md`

### 验证

- 改动类型: refactor + fix + feat
- 清理乱码: 有（6 个 shell 残留代码片段文件）
- 子 App index.md 更新: itsm
- 工作区状态: 待提交 ✅

---

## db14a792

> 提交日期: 2026-07-05 | 提交信息: fix: cross-app hero-tab alignment — 全线修复 hero-tab 内容与标题左对齐，全局 mixin + 8 个 app CSS 修正

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/styles/_mixins.scss` | 前端 | 全局 `g-hero-tab` mixin padding 从 `10px 16px` 改为 `10px 16px 10px 0`，移除左侧 padding |
| `web/src/views/apps/cmdb/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/iam/index.vue` | 前端 | hero-tab padding 修复 `10px 16px` → `10px 16px 10px 0`，移除旧 `:first-child` hack |
| `web/src/views/apps/integration/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/itsm/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/job-platform/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/open-api/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/opsagent/index.vue` | 前端 | hero-tab padding 修复 `10px 20px` → `10px 20px 10px 0` |
| `web/src/views/apps/opsflow/index.vue` | 前端 | hero-tab padding 修复 `10px 16px` → `10px 16px 10px 0` |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 后端 | ITSM tab 重新排序，服务市场设为默认首页 (sort=10, is_default=True) |
| `docs/guides/frontend-style-guide.md` | 文档 | 新增约束规则 #5 tab 内容左对齐 |

### 解决

- **问题/背景：** 全局 `g-hero-tab` mixin 定义了 `padding: 10px 16px`，其中 `padding-left` 导致 tab 内容相对于父容器（`padding: 0 24px`）额外偏移 16-20px，tab 内容比标题偏右。ITSM tab 排序不合理，服务市场与后台配置混杂
- **办法：** 所有 hero-tab 移除 `padding-left`（统一为 `padding: 10px Xpx 10px 0`）；ITSM tab 重新按"核心流程 → 后台管理 → 遗留模块"三段式分组

### 文档

- **生成文档：**
  - `docs/opsflow/debug/2026-07-05-hero-tab-alignment.md`
  - `docs/itsm/features/2026-07-05-tab-ordering-optimization.md`

### 验证

- 改动类型: fix + feat
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端 + iam seed）
- 工作区状态: 干净 ✅


## 847774f9

> 提交日期: 2026-07-05 | 提交信息: feat: itsm node_key stable identity + SLA pause/resume enhancement — 节点稳定标识与 SLA 暂停恢复增强

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/models/state.py` | 后端 | **新增** node_key（前端节点标识）、is_builtin 字段，unique_together(workflow, node_key) |
| `backend/itsm/models/transition.py` | 后端 | **新增** from_node_key、to_node_key 字段（连线两端节点标识） |
| `backend/itsm/models/workflow.py` | 后端 | create_version() 快照 key 改用 node_key；START/END 自动补全 safety net；快照含 node_key |
| `backend/itsm/models/ticket.py` | 后端 | get_state() 支持 node_key 查找；节点状态 key 改用 node_key；多处理 null safety |
| `backend/itsm/models/sla.py` | 后端 | SlaTask 新增 paused_at 字段 |
| `backend/itsm/services/workflow_builder.py` | 后端 | build_tree() 优先用 node_key 映射 transition |
| `backend/itsm/services/sla_engine.py` | 后端 | SLA pause/resume 增强：paused_at 记录 + 时长补偿；start 改为 get_or_create 不覆盖 |
| `backend/itsm/services/condition_utils.py` | 后端 | 条件工具微调 |
| `backend/itsm/services/role_resolver.py` | 后端 | 角色解析微调 |
| `backend/itsm/services/state_machine.py` | 后端 | **删除** — 已被新引擎替代 |
| `backend/itsm/views/workflow_views.py` | 后端 | StateSync 按 node_key 差异同步；operator 传 user.id；State 关闭分页 |
| `backend/itsm/views/ticket_views.py` | 后端 | _get_activity_id() 用 node_key 映射 bamboo element ID |
| `backend/itsm/migrations/0004_add_node_key.py` | 迁移 | **新建** node_key 字段迁移 |
| `backend/itsm/migrations/0005_add_sla_paused_at.py` | 迁移 | **新建** paused_at 字段迁移 |
| `backend/common/utils/serializers.py` | 后端 | 序列化器微调 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 后端 | IAM 种子配置修复 |
| `web/src/views/apps/itsm/designer/useDesigner.ts` | 前端 | **大幅重写** node_key 自动生成；连接校验；拖放重构（clone→createNode）；连线数据自动填充 |
| `web/src/views/apps/itsm/designer/shapes.ts` | 前端 | 节点形状适配 node_key |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | 前端 | 配置面板 node_key 展示 |
| `web/src/views/apps/itsm/designer/index.vue` | 前端 | 设计器 layout 微调 |
| `web/src/views/apps/itsm/index.vue` | 前端 | **新增** 工单详情内联填单（NORMAL 节点表单渲染+提交）；从 WorkflowVersion 合并字段定义 |
| `web/src/api/itsm/index.ts` | 前端 | **新增** NodeSubmit、stateApi、transitionApi |
| `.gitignore` | 配置 | 新增 .superpowers/ 忽略规则 |

### 解决

- **问题/背景：** ITSM 引擎重构后，设计器节点缺乏稳定标识，导致保存/加载不一致、Pipeline activity ID 和 node_status key 不匹配、SLA 暂停/恢复计时不准、工单详情无法内联填单
- **办法：** node_key 贯穿设计→快照→运行整条链路做 stable identity；SLA 用 paused_at 做时长补偿；前端设计器全面增强初始化与连接校验

### 文档

- **生成文档：**
  - `docs/itsm/features/2026-07-05-node-key-stable-identity.md`
  - `docs/itsm/features/2026-07-05-sla-pause-resume-enhance.md`
  - `docs/superpowers/specs/2026-07-05-itsm-service-catalog-design.md`

### 验证

- 改动类型: feat + fix
- 清理乱码: 有（2 个 0 字节垃圾文件）
- 工作区状态: 干净 ✅


## 88b61c0f

> 提交日期: 2026-07-05 | 提交信息: feat: itsm service catalog with ServiceItem model + market page — ITSM 服务目录（服务市场+管理后台）

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/models/service_item.py` | 后端 | **新建** ServiceItem 模型 — flow/lightweight 双模式、form_fields、可见性控制 |
| `backend/itsm/serializers/service_item.py` | 后端 | **新建** CRUD + submit 验证序列化器 |
| `backend/itsm/views/service_item.py` | 后端 | **新建** ServiceItemViewSet + submit action（flow/lightweight 双路径） |
| `backend/itsm/urls.py` | 后端 | 注册 service-items 路由 |
| `backend/itsm/migrations/0006_add_service_item.py` | 迁移 | **新建** ServiceItem 数据迁移 |
| `backend/itsm/tests/test_models.py` | 测试 | **新增** 5 个 ServiceItem 单元测试 |
| `backend/itsm/management/commands/seed_itsm.py` | 后端 | **新增** 12 个 Mock 服务项种子数据 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 配置 | **新增** 服务市场/服务目录管理 Tab + itsm:service:admin 权限 |
| `web/src/views/apps/itsm/catalog/ServiceMarket.vue` | 前端 | **新建** 服务市场（分类树+卡片网格+搜索） |
| `web/src/views/apps/itsm/catalog/ServiceDetail.vue` | 前端 | **新建** 服务详情（动态表单+提交申请） |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 前端 | **新建** 服务管理后台（CRUD+编辑弹窗+预览） |
| `web/src/views/apps/itsm/index.vue` | 前端 | 集成 service-market/service-admin 两个新 Tab |
| `web/src/api/itsm/index.ts` | 前端 | 新增 serviceItemApi + SubmitServiceItem |
| `backend/itsm/models/ticket.py` | 后端 | SignTask 通过 TicketStatus pk 查询修复 |
| `backend/itsm/services/sla_engine.py` | 后端 | stopped 状态 SLA 重置支持 |
| `backend/itsm/views/workflow_views.py` | 后端 | rollback node_key 支持；StateSync 保护旧状态；transition 同步增强 |
| `web/src/views/apps/itsm/designer/useDesigner.ts` | 前端 | 清理 console.log；连线数据引用修复 |

### 解决

- **问题/背景：** ITSM 缺少统一服务目录入口，用户创建工单需先理解"流程模板"，体验不友好
- **办法：** 新增 ServiceItem 模型，双模式服务目录（flow 走 Pipeline / lightweight 直接分派），服务市场+管理后台双视图，12 个 Mock 种子数据即时可见

### 文档

- **生成文档：**
  - `docs/itsm/features/2026-07-05-service-catalog.md`
  - `docs/superpowers/specs/2026-07-05-itsm-service-catalog-design.md`

### 验证

- 改动类型: feat + fix
- 清理乱码: 有（6 个 0 字节垃圾文件）
- 工作区状态: 干净 ✅



---

## 1d8ddc88

> 提交日期: 2026-07-04 | 提交信息: feat: itsm engine refactor + three gateway types — ITSM 引擎重构与三种网关支持

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/itsm/services/itsm_engine.py` | 后端 | **新建** ITSMEngine — PipelineWrapper 重构为实例化模式（run/pause/resume/revoke），SLA/暂停/升级统一联动 |
| `backend/itsm/services/workflow_builder.py` | 后端 | **新建** ITSMWorkflowBuilder — 三种网关 + Data/NodeOutput + by_field 条件 + ConvergeGateway 配对 |
| `backend/itsm/services/condition_utils.py` | 后端 | **新建** 条件表达式工具（从 opsflow.core.pipeline_builder.elements 复制，消除跨 app import） |
| `backend/itsm/services/pipeline_wrapper.py` | 后端 | **删除** PipelineWrapper（已由 ITSMEngine 替代） |
| `backend/itsm/signals.py` | 后端 | 新增 post_set_state 信号监听 — bamboo 节点状态变更同步 ITSM 工单状态 |
| `backend/itsm/views/ticket_views.py` | 后端 | PipelineWrapper → ITSMEngine 替换（5 处） |
| `backend/itsm/tasks.py` | 后端 | PipelineWrapper → ITSMEngine 替换 |
| `backend/opsflow/plugins/itsm/update_ticket.py` | 后端 | PipelineWrapper → ITSMEngine 替换 |
| `backend/itsm/models/state.py` | 后端 | TYPE_CHOICES: ROUTER_P → CONDITIONAL_PARALLEL, 新增 EXCLUSIVE/PARALLEL, 移除 WEBHOOK |
| `backend/itsm/models/transition.py` | 后端 | condition_type 增加 choices（default/by_field） |
| `backend/itsm/models/ticket.py` | 后端 | pipeline_id 加 db_index=True |
| `backend/itsm/pipeline_plugins/components.py` | 后端 | ItsmFillForm/ApprovalService 新增 data.set_outputs() — 表单字段输出供网关条件引用 |
| `backend/itsm/views/workflow_views.py` | 后端 | ITSM_NODE_TYPE_MAP 更新 — ROUTER_P → CONDITIONAL_PARALLEL, 新增 PARALLEL |
| `backend/itsm/migrations/0002_ticket_pipeline_id_db_index.py` | 迁移 | pipeline_id db_index |
| `backend/itsm/migrations/0003_gateway_types.py` | 迁移 | ROUTER_P → CONDITIONAL_PARALLEL + choices 更新 |
| `backend/common/utils/layout/` (18 文件) | 后端 | **新建** 从 opsflow/core/layout/ 复制（零修改） |
| `backend/scripts/patch_eri_migration.py` | 脚本 | **新建** eri.0006 RenameIndex → AddIndex 补丁脚本 |
| `docs/guides/eri-migration-fix.md` | 文档 | **新建** ERI 迁移修复指南 |
| `web/src/views/apps/itsm/designer/shapes.ts` | 前端 | ITSM_NODE_CONFIG + resolveItsmShape 更新（CONDITIONAL_PARALLEL, PARALLEL） |
| `web/src/views/apps/itsm/designer/useDesigner.ts` | 前端 | Stencil 网关配置更新 + validateWorkflow 排他网关出边校验 + COVERAGE 配对 |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | 前端 | 网关类型提示更新 + 条件编辑 by_field 支持 |
| `web/src/views/apps/itsm/tests/test_workflow_builder.py` | 测试 | **新建** 11 个测试（排他/并行/条件并行网关 + by_field 条件 + converge 配对） |
| `web/src/views/apps/itsm/tests/test_itsm_engine.py` | 测试 | **新建** 8 个引擎测试 |
| `web/src/views/apps/itsm/tests/test_layout.py` | 测试 | **新建** 3 个 layout 测试 |

### 解决

- **问题/背景：** ITSM 只实现了 ROUTER_P（条件并行）一种网关，缺少排他/纯并行网关；PipelineWrapper 为 stateless 模式未与 FlowEngine 对齐；组件不输出表单字段导致网关条件运行时死引用；bamboo-pipeline eri.0006 在 SQLite 测试环境失败
- **办法：** 命名与 opsflow 对齐（ROUTER_P→CONDITIONAL_PARALLEL, 新增 EXCLUSIVE/PARALLEL）；Builder 增加三种网关、Data/NodeOutput 注册、by_field 结构化条件、ConvergeGateway 自动配对；组件加 data.set_outputs()；eri migration RenameIndex→AddIndex；前端设计器同步更新

### 验证

- 改动类型: feat + refactor + fix + chore
- 清理乱码: 无
- 子 App index.md 更新: itsm
- 工作区状态: 干净 ✅

---


> 提交日期: 2026-07-03 | 提交信息: refactor: cleanup common/utils + remove dead code — 公共工具代码清理

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/common/utils/crud_mixin.py` | 后端 | 删除 FastCrudMixin（零引用，遗留代码） |
| `backend/common/utils/viewset.py` | 后端 | 剥离 ImportExportMixin，移除 import_field_dict/export_field_label |
| `backend/common/utils/exception.py` | 后端 | 清理 @author 样板 docstring |
| `backend/common/utils/json_response.py` | 后端 | 清理 @author 样板 docstring |
| `backend/common/utils/models.py` | 后端 | 清理 @author 样板 docstring |
| `backend/common/utils/pagination.py` | 后端 | 清理 @author 样板 docstring |
| `backend/common/utils/serializers.py` | 后端 | 清理 @author 样板 docstring |
| `backend/common/utils/validator.py` | 后端 | 清理 @author 样板 docstring |
| `backend/iam/views/user.py` | 后端 | 直接继承 ImportSerializerMixin, ExportSerializerMixin |
| `backend/iam/views/dept.py` | 后端 | 直接继承 ImportSerializerMixin，清理空 docstring |
| `backend/application/settings.py` | 配置 | 移除 LOCALE_PATHS |
| `backend/locale/en/LC_MESSAGES/django.po` | 配置 | 删除未使用的语言翻译文件 |
| `backend/scripts/generate_pdf.py` | 脚本 | 删除未使用的 PDF 生成脚本 |
| `docs/opsflow/architecture/06-deployment-notes.md` | 文档 | 删除（内容已合并至 deployment-guide.md） |

### 解决

- **问题/背景：** common/utils/ 目录积累了大量遗留代码（FastCrudMixin 零引用、ImportExportMixin 仅 IAM 使用却被所有 ViewSet 继承、@author 样板 docstring 不符项目规范）
- **办法：** 删除无引用代码、将 ImportExportMixin 从基类剥离为按需继承、清理所有 @author 头部注释为单行英文描述

### 验证

- 改动类型: refactor/chore
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 0861c07c

> 提交日期: 2026-07-03 | 提交信息: docs: doc restructure + seed_iam_menu — 文档重组与导航菜单种子命令

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/management/commands/seed_iam_menu.py` | 后端 | 新增 IAMMenu 种子命令（基于当前 DB 快照 13 条记录，幂等） |
| `backend/common/management/commands/seed_all.py` | 后端 | L1 依赖链加入 seed_iam_menu、seed_iam_page_configs |
| `docs/guides/deployment-guide.md` | 文档 | 修复明文密码泄露；修正默认凭据 superadmin → opsflowadmin；MySQL 创建用户独立为 3.2 节 |
| `docs/opsflow/architecture/04-frontend.md` | 文档 | 补充 12 个子产品页面注册表、全局共享组件、跨 App composable |
| `docs/opsflow/architecture/06-deployment-notes.md` | 文档 | 更新 API 端点表/WebSocket 路由/Celery 任务表/路由配置/部署清单 |
| `docs/guides/quick-start.md` | 文档 | 从 docs/opsflow/guides/ 迁移至 docs/guides/ |
| `docs/guides/link_rules.md` | 文档 | 从 docs/opsflow/reference/ 迁移至 docs/guides/ |
| `docs/guides/notes.md` | 文档 | 从 docs/guides/注意事项.md 重命名 |
| `backend/scripts/generate_pdf.py` | 后端 | 从 docs/opsflow/reference/ 迁移至 backend/scripts/ |
| `docs/TODO.md`, `docs/TODO.html` | 文档 | 删除（已被各 App implementation.md 替代） |
| `backend/conf/env_base.py` | 配置 | 配置项更新 |
| `backend/requirements.txt` | 配置 | 依赖项更新 |
| `backend/job_platform/services/dangerous_detector.py` | 后端修复 | bug 修复 |
| `backend/opsflow/apps.py` | 后端修复 | ready() 方法清理 |
| `backend/job_platform/apps.py` | 后端修复 | ready() 方法清理 |
| `backend/*/migrations/` | 迁移 | 各 App 自动生成迁移文件同步 |

### 解决

- **问题/背景：** 文档结构有过多散乱文件，导航菜单种子命令缺失导致新建环境无法正常渲染前端路由
- **办法：** 文档归类迁移（代码→backend/scripts/，全局指南→docs/guides/），新增 seed_iam_menu 命令并加入 seed_all；修复部署指南中明文密码和过时凭据

### 文档

- **生成/更新文档：**
  - `docs/guides/deployment-guide.md`
  - `docs/opsflow/architecture/04-frontend.md`
  - `docs/opsflow/architecture/06-deployment-notes.md`

### 验证

- 改动类型: docs/feat/chore/fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 已提交

---

## dacd322e

> 提交日期: 2026-07-03 | 提交信息: docs: add spacing after deployment guide frontmatter — 部署指南添加格式间距

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/guides/deployment-guide.md` | 文档 | frontmatter 分隔线后添加 2 个空行，改善排版可读性 |

### 解决

- **问题/背景：** 部署指南 frontmatter 后缺少间距，排版紧凑
- **办法：** 添加 2 个空行分隔，同时清理编码错乱的空文件

### 验证

- 改动类型: docs
- 清理乱码: 有（编码错乱产生的 0 字节空文件）
- 子 App index.md 更新: 无（纯文档改动）
- 工作区状态: 干净 ✅

---

## 7a839e6b

> 提交日期: 2026-07-02 | 提交信息: refactor: role management search bar restructure + IAM page padding tweak

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/views/apps/iam/admin/role/index.vue` | 前端 | 搜索栏从列头内联筛选改为独立搜索行（Name/Status/Reset），移除列头筛选样式，简化布局 |
| `web/src/views/apps/iam/index.vue` | 前端 | hero-tab 第一个 padding-left 归零，body padding 20px→24px |

### 解决

- **问题/背景：** 角色管理列头筛选占用表头空间、与排序交互冲突；IAM 页面 tab 间距不对称
- **办法：** 拆出独立搜索行 + 弹性布局，统一间距

### 验证

- 改动类型: refactor + style
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端改动）
- 工作区状态: 干净 ✅

---

## 8a2fabec

> 提交日期: 2026-07-02 | 提交信息: feat: IAM menu detail panel, OpsAgent tab + perms, v-can lock fix, ITSM button perms

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/views/menu.py` | 后端 | MenuSerializer 新增 parent/name_display/hasChild 字段，修复 list 方法支持 ?parent= 懒加载 |
| `backend/iam/views/permission_views.py` | 后端 | permission_catalog 改用动态 PageTab 查询替代写死 app 列表 |
| `backend/common/utils/serializers.py` | 后端 | SlagRelatedField → SerializerMethodField 修复 IAMMenu 无 creator 属性报错 |
| `backend/common/utils/middleware.py` | 后端 | creator: user → user.id 修复 IntegerField 类型不匹配 |
| `backend/common/utils/request_util.py` | 后端 | creator_id → creator 修复 LoginLog 传参错误 |
| `backend/common/views/operation_log.py` | 后端 | creator=self.request.user → user.id 修复 IntegerField 类型错误 |
| `backend/common/urls.py` | 后端 | 注册 DeptViewSet 修复 /api/system/dept/ 404 |
| `backend/iam/models/page_config.py` | 后端 | 补充 IAMMenu 字段（is_affix/name_en/app） |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 后端 | 新增 OpsAgent 权限码/tab/button/角色绑定 |
| `web/src/views/apps/iam/admin/menu/components/MenuDetailPanel/index.vue` | 前端 | **新建** IAM Menu 详情面板（内联开关/图标选择/排序按钮） |
| `web/src/views/apps/iam/admin/menu/index.vue` | 前端 | 右侧空面板替换为 MenuDetailPanel |
| `web/src/views/apps/iam/admin/menu/components/MenuFormCom/index.vue` | 前端 | 移除 icon 选择（入口统一到详情面板） |
| `web/src/views/apps/opsagent/index.vue` | 前端 | **新建** 参考 ITSM 布局的 tab 页面 + 权限感知 |
| `web/src/views/apps/opsagent/Console.vue` | 前端 | 修复嵌入式布局，添加 btnPerms 按钮权限控制 |
| `web/src/views/apps/opsagent/Sessions.vue` | 前端 | 修复嵌入式布局（移除 position:absolute） |
| `web/src/directive/iamPermission.ts` | 前端 | 修复 v-can 支持 modifier 模式（v-can.edit/admin），移除 disabled 属性使点击可穿透 |
| `web/src/views/apps/itsm/index.vue` | 前端 | ITSM 按钮补充 v-can（提交/转派/关闭/分派/批准/驳回/SLA编辑） |
| `web/src/views/apps/itsm/SkillGroup.vue` | 前端 | 按钮补充 v-can="itsm:skillgroup:manage" |
| `web/src/views/apps/itsm/Delegation.vue` | 前端 | 按钮补充 v-can="itsm:ticket:assign" |
| `web/src/views/apps/itsm/OnDutySchedule.vue` | 前端 | 按钮补充 v-can="itsm:duty:manage" |
| `web/src/views/apps/itsm/AssignRule.vue` | 前端 | 按钮补充 v-can="itsm:rule:manage" |
| `web/src/views/apps/itsm/EscalationLevel.vue` | 前端 | 按钮补充 v-can="itsm:escalation:manage" |
| `web/src/views/apps/iam/admin/role/index.vue` | 前端 | 修复 `{{ viewForm.key }}` Vue 保留属性编译错误 |
| `web/src/theme/iconSelector.scss` | 前端 | 图标选择弹窗标题/tabs 布局修复（绝对定位 → 块级布局） |
| `web/src/components/iconSelector/list.vue` | 前端 | 图标列表高度 230→320px |
| `web/src/i18n/lang/zh-cn.ts` | 前端 | 新增 menuPage 14 个 + opsagent 4 个 i18n 键 |
| `web/src/i18n/lang/en.ts` | 前端 | 新增 menuPage 14 个 + opsagent 4 个 i18n 键 |

### 解决

- **问题/背景：** 两轮对话遗留问题：IAM Menu tab 右侧面板空白、OpsAgent 页面 tab 不显示、v-can modifier 模式永久锁住按钮、ITSM 多个子组件按钮无权限锁、creator IntegerField 类型不匹配导致 500 错误
- **办法：** 新建 MenuDetailPanel 组件替代空白面板，重写 OpsAgent 父页面为 ITSM 风格，修复 v-can 指令逻辑并移除 disabled，ITSM 6 个组件 18+ 按钮补齐 v-can，后端 8 处 IntegerField 类型修复

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-07-02-iam-menu-detail-panel-design.md`

### 验证

- 改动类型: feat + fix + refactor
- 清理乱码: 有（{, 和 , 两个 shell 残留文件）
- 子 App index.md 更新: iam, itsm, opsagent
- 工作区状态: 干净 ✅

---

## c14e45c4

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `*/migrations/0001_initial.py` (12 files) | 后端 | 迁移文件 Squash — 从 96+ 个文件压缩到 12 个 0001_initial |
| `iam/commands/seed_iam_permissions.py` | 后端 | 删除（引用已删除的旧模型） |
| `iam/commands/seed_iam_page_configs.py` | 后端 | 新增 4 个 system 权限 + system_admin 角色 |
| `iam/commands/init_iam.py, seed_itsm_permissions.py` | 后端 | 删除（功能已被覆盖） |
| `opsflow/commands/seed_opsflow.py` | 后端 | 修复重复的 Command 类（删除第 1 个） |
| `opsflow/commands/` (6 文件) | 后端 | 删除过时的一次性命令 & 合入管理命令 |
| `common/commands/bootstrap.py, add_*mock*.py` | 后端 | 删除（bootstrap 过时，mock 已拆分） |
| `common/commands/seed_all.py` | 后端 | 更新为新的 seed 命令列表 |
| `cmdb/commands/seed_cmdb_mock.py` | 后端 | 删除（mock 合入 seed_cmdb） |
| `opsagent/commands/` (2 文件) | 后端 | 删除（过时） |
| `common/utils/models.py` | 后端 | CoreModel.creator 加 db_column='creator_id' 兼容旧表 |

### 解决

- **问题/背景：** 96+ 个迁移文件过于庞大，管理命令 31 个含大量过时代码，IAM seed 缺少 system 权限
- **办法：** 全量 squash + 清理 14+ 个命令 + 补全 4 个 system 权限 + system_admin 角色

### 文档

- **生成文档：** 无（chore + refactor 类型，已有架构文档覆盖）

### 验证

- 改动类型: refactor + chore
- 清理乱码: 有（30+ 个管理命令删除）
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---


## 58f68b5d

> 提交日期: 2026-07-02 | 提交信息: refactor: migrate dvadmin to common/ + iam/, rename agent_app to agent_backend

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `dvadmin/utils/ → common/utils/` (14 文件) | 后端 | 工具代码迁移 — json_response, CoreModel, viewset 等 |
| `dvadmin/system/models → iam/ IAMUsers/IAMDept` | 后端 | 用户+部门模型迁入 iam，重命名 IAMUsers/IAMDept |
| `dvadmin/system/views/ → iam/views/` | 后端 | login, user, dept, oauth 视图迁移 |
| `common/models/` | 后端 | OperationLog, LoginLog, FileList, SystemConfig, MessageCenter |
| `dvadmin/system/views/ → common/views/` | 后端 | operation_log, login_log, message_center 等 |
| `itsm/models/` (11 文件) | 后端 | system.Users FK → settings.AUTH_USER_MODEL |
| `opsflow/plugins/loader.py, registry.py` | 后端 | 日志英文化, 跳过 _tower_base, 修复 vv1.0 |
| `opsflow/plugins/registry.py` | 后端 | sync_plugin_meta_to_db 跳过内部基类 |
| `opsflow/tests/test_layout.py` | 修复 | 修复语法错误 |
| `job_platform` | 修复 | 补齐 dangerous_cmd_rule creator 列 |
| `agent_app → agent_backend` | 配置 | 应用重命名 |
| `application/dispatch.py` | 修复 | SystemConfig 表名变更兼容 |
| `docs/opsflow/config/2026-07-02-conf-db-table-rename-config.md` | 文档 | 数据库表名迁移配置变更文档 |

### 解决

- **问题/背景：** dvadmin 遗留代码与 IAM 体系重复，Users/Dept 模型在 dvadmin 中、所有工具函数依赖 dvadmin.utils 
- **办法：** 一步到位迁移：utils → common, 模型 → iam/common, 137+ import 路径更新, ALTER TABLE 表重命名

### 文档

- **生成文档：**
  - `docs/opsflow/config/2026-07-02-conf-db-table-rename-config.md`

### 验证

- 改动类型: refactor + fix + chore + BREAKING CHANGE
- 清理乱码: 有（删除 agent-py 目录）
- 子 App index.md 更新: iam, common
- 工作区状态: 待提交 ✅

---


## 76e42387

> 提交日期: 2026-07-01 | 提交信息: chore: unify Redis config with conf/env + common/utils/redis_helper

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `conf/env.py` + `conf/env_base.py` | 后端 | 分层配置系统：base 定义默认值，env_{dev,uat,prod}.py 按环境覆写 |
| `application/components/database.py` | 后端 | CACHES LOCATION 改为 f"{REDIS_URL}/1" |
| `application/components/channels.py` | 后端 | CHANNEL_LAYERS hosts 改为 (REDIS_HOST, REDIS_PORT) |
| `application/components/celery.py` | 后端 | CELERY_BROKER_URL/RESULT_BACKEND 改为 f"{REDIS_URL}/0/1" |
| `common/utils/redis_helper.py` | 后端 | 新增 get_redis() 通用 Redis 连接函数 |
| `opsflow/signals/timeout.py` | 后端 | 硬编码 → get_redis(db=0) |
| `opsflow/core/node_timeout_strategy.py` | 后端 | 硬编码 → get_redis(db=0) |
| `opsflow/apps.py` | 后端 | 硬编码 → get_redis(db=0, decode=False) |
| `opsflow/management/commands/start_opsflow_scheduler.py` | 后端 | 硬编码 → get_redis(db=0, decode=False) |
| `itsm/management/commands/start_itsm_scheduler.py` | 后端 | 硬编码 → get_redis(db=0, decode=False) |
| `docs/opsflow/config/2026-07-01-conf-env-design-config.md` | 文档 | 配置系统设计文档 |

### 解决

- **问题/背景：** Redis 地址在 11 个文件中硬编码 127.0.0.1:6379，改地址需逐文件修改，无法按环境切换
- **办法：** conf/env 分层配置 + common/utils/redis_helper 统一连接函数

### 文档

- **生成文档：**
  - `docs/opsflow/config/2026-07-01-conf-env-design-config.md`

### 验证

- 改动类型: chore
- 清理乱码: 无
- 子 App index.md 更新: opsflow, common
- 工作区状态: 待提交 ✅

---


## 3ade6b9e

> 提交日期: 2026-07-01 | 提交信息: refactor: migrate dvadmin RBAC to IAM single system + feat: IAMMenu + i18n

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/models/menu_rbac.py` | 后端 | 删除旧 Role, MenuButton, RoleMenuPermission, RoleMenuButtonPermission |
| `backend/iam/models/page_config.py` | 后端 | 新增 IAMMenu 导航模型（映射 opsflow_iam_menu 表） |
| `backend/iam/models/rbac.py` | 后端 | 旧 FK 改为 IntegerField，Users.role M2M 删除 |
| `backend/iam/views/role.py` | 后端 | RoleViewSet 重写为 IAMRole CRUD + permissions action |
| `backend/iam/views/menu.py` | 后端 | 适配 IAMMenu, web_router 简化 |
| `backend/iam/views/*.py` | 后端 | 删除 menu_button, role_menu, role_menu_button_permission, menu_field |
| `backend/iam/views/permission_views.py` | 后端 | approve 去 target_role, available_roles 仅 IAMRole |
| `backend/dvadmin/system/models.py` | 后端 | 删除 Users.role M2M, MessageCenter.target_role → IAMRole |
| `backend/dvadmin/system/views/user.py` | 后端 | get_role_info/user_info 改用 IAMUserRole |
| `backend/dvadmin/system/views/dept.py` | 后端 | 删除 data_range 过滤 |
| `backend/dvadmin/utils/field_permission.py` | 后端 | 文件删除（僵尸代码） |
| `backend/dvadmin/utils/viewset.py` | 后端 | 删除 get_menu_field 死代码 |
| `web/src/views/apps/iam/admin/` | 前端 | 删除 MenuButtonCom/MenuFieldCom/PermissionComNew |
| `web/src/views/apps/iam/admin/role/` | 前端 | RolePermissionPanel 重写为 IAM 权限分配 |
| `web/src/views/apps/iam/index.vue` | 前端 | 权限展示重写 + 全 i18n |
| `web/src/views/apps/iam/MyRequests/index.vue` | 前端 | 角色选择简化 + checkbox-group 修复 + 全 i18n |
| `web/src/views/apps/iam/ApprovalDashboard/index.vue` | 前端 | 批量审批 + 全 i18n |
| `web/src/i18n/pages/iam/` | 前端 | 新增 30+ i18n 键值对 |
| `docs/` | 文档 | 架构重构 + 迁移指南文档 |

### 解决

- **问题/背景：** 两套 RBAC 模型（dvadmin 旧 + IAM 新）功能重叠，维护成本高。旧模型 Role/MenuButton/RoleMenuPermission/RoleMenuButtonPermission 4 表 + 对应 ViewSet 需要清理
- **办法：** 删除旧模型代码和 ViewSet（保留 DB 表），IAMMenu 迁移到 page_config.py，用户角色绑定从 user.role M2M 改为 IAMUserRole，PermissionRequest 审批仅用 target_iam_role

### 文档

- **生成文档：**
  - `docs/iam/architecture/2026-07-01-rbac-cleanup-refactor.md`
  - `docs/iam/migration/2026-07-01-rbac-cleanup-migration.md`

### 验证

- 改动类型: refactor + feat + BREAKING CHANGE
- 清理乱码: 有（删除 permission.py.bak）
- 子 App index.md 更新: iam
- 工作区状态: 待提交 ✅

---


## e3761d79

> 提交日期: 2026-07-01 | 提交信息: feat: opsflow v-can permission locks + dvadmin cleanup — OpsFlow 按钮权限锁和废弃代码清理

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/dvadmin/utils/filters.py` | 后端 | 删除废弃 DataLevelPermissionsFilter（129 行 → 14 行） |
| `backend/dvadmin/utils/viewset.py` | 后端 | 移除 extra_filter_class，filter_queryset 用 getattr 安全读取 |
| `backend/dvadmin/system/views/dept.py` | 后端 | 去除 @action 上多余的 extra_filter_class=[] 参数 |
| `backend/iam/management/commands/init_iam.py` | 后端 | 修复 6 个菜单 component 路径（去掉 views/ 前缀） |
| `backend/iam/views/permission_views.py` | 后端 | 消息中心申请确认通知和 M2M 写入修复 |
| `backend/opsflow/views/base.py` | 后端 | PermissionDenied → qs.none() 静默无权限 |
| `backend/opsflow/views/project_views.py` | 后端 | 新增 my_opsflow_permissions 接口 |
| `web/src/stores/permission.ts` | 前端 | 修复 currentRole null 时 canEdit 误判 |
| `web/src/views/apps/opsflow/index.vue` | 前端 | Tab 级别权限控制 + my_opsflow_permissions 集成 |
| `web/src/views/apps/opsflow-*/*.vue` (8 个文件) | 前端 | v-can.edit/v-can.admin 按钮权限锁 |
| `web/src/views/apps/opsflow-knowledge/index.vue` | 前端 | 删除 mock 数据回退 |

### 解决

- **问题/背景：** 消息中心普通用户白屏、OpsFlow 页面无前端权限锁导致 viewer 看到所有 tab 和按钮、dvadmin 废弃 DataLevelPermissionsFilter 导致 NameError
- **办法：** 删除 DataLevelPermissionsFilter 整套废弃代码，修复 init_iam component 路径并新增消息中心按钮，新增 my_opsflow_permissions 接口，给所有 opsflow 页面加 v-can 权限锁和 tab 可见性控制，删除知识库 mock 数据回退

### 文档

- **生成文档：**
  - `docs/iam/features/2026-07-01-message-center-button-permissions.md`
  - `docs/iam/architecture/2026-07-01-remove-data-level-permissions-filter-refactor.md`
  - `docs/opsflow/features/2026-07-01-opsflow-vcan-permission-locks.md`

### 验证

- 改动类型: feat + fix + refactor
- 清理乱码: 无
- 前端构建: ✓ built in 5.6s
- 后端检查: System check identified no issues (0 silenced)
- 工作区状态: 待提交文档

---

## f2b67052

> 提交日期: 2026-06-30 | 提交信息: feat: LDAP/AD identity sync engine + SAML SSO — 身份同步引擎与认证集成

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/sync/` | 后端 | 身份同步引擎（DeptMapping/UserMapping/Differ/Provider/Backend） |
| `backend/integration/adapters/auth/ldap.py` | 后端 | LDAPConnector 适配器（health_check + search） |
| `backend/integration/adapters/auth/saml.py` | 后端 | SAMLConnector 适配器（metadata 验证） |
| `backend/application/` | 配置 | 路由注册 + auth 认证链 |
| `backend/opsflow/seed_opsflow.py` | 配置 | 注册 ldap/saml 连接器定义 |
| `backend/requirements.txt` | 配置 | 新增 ldap3, python3-saml 依赖 |
| `web/src/views/apps/integration/` | 前端 | 新增身份同步 Tab（identity-sync.vue） |
| `web/src/views/system/login/` | 前端 | SAML SSO 登录按钮 |
| `web/src/i18n/` | 前端 | 身份同步中英文文案 |
| `docs/` | 文档 | 配置指南 + 设计文档 + 功能文档 |

### 解决

- **问题/背景：** 企业需要从 LDAP/AD/SAML 同步组织架构和用户数据到系统，支持 LDAP Bind 认证和 SAML SSO 登录
- **办法：** 复用集成中心连接器体系，新增 iam/sync 同步引擎（映射模型+Diff算法+同步执行器+认证后端），新增身份同步前端 Tab

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-30-identity-sync-design.md`
  - `docs/iam/features/2026-06-30-identity-sync-engine.md`
  - `docs/integration/features/2026-06-30-ldap-saml-connectors.md`
  - `docs/guides/identity-sync-setup.md`

### 验证

- 改动类型: feat + chore
- 清理乱码: 有 (`,+`, `false)`)
- 子 App index.md 更新: iam, integration
- 工作区状态: 待提交 ✅

---

## 42309410

> 提交日期: 2026-06-30 | 提交信息: feat: opsflow default tab dashboard — 默认 tab 改为 dashboard，Hero 样式压缩

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/views/apps/opsflow/index.vue` | 前端 | 默认 tab 从 templates 改为 dashboard |
| `web/src/views/apps/opsflow/index.vue` | 前端 | Hero 区域样式压缩 (padding/font-size/gap) |

### 解决

- **问题/背景：** Tab 合并后用户进入 /opsflow 默认显示"模板中心"，但仪表盘作为首页入口更合理；合并后的 Hero 区域视觉松散
- **办法：** 切换默认 tab 至 dashboard；压缩 Hero 内边距和字号

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-30-opsflow-tab-consolidation.md` (追加更新)

### 验证

- 改动类型: feat
- 清理乱码: 有 (`,+`, `false)` )
- 子 App index.md 更新: 无需 (纯前端)
- 工作区状态: 干净 ✅

---

## 80f9ed95

> 提交日期: 2026-06-30 | 提交信息: feat: OPSflow UI tab consolidation — 合并6+子页面为单一路由 tab 页面

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| web/src/views/apps/opsflow/index.vue | 前端 | 重写为统一 tab 容器 — hero + 8 tabs + 7 子页面嵌入 |
| web/src/views/apps/opsflow-*/index.vue (7 files) | 前端 | 新增 embedded prop, 嵌入时隐藏 hero |
| web/src/views/apps/opsflow/DesignCanvas.vue | 前端 | 新增 showBack prop + back emit, 返回按钮集成到 toolbar |
| backend/opsflow/management/commands/seed_opsflow.py | 后端 | 菜单种子从 6 独立 leaf 合并为 /opsflow |
| web/src/views/apps/itsm/index.vue | 前端 | 修复 showCreateTicket const ref 赋值错误 |
| backend/iam/views.py | 后端 | 新增 my_permissions 端点 (95 lines) |
| backend/iam/signals.py | 后端 | 新增信号处理, IAM member 变更自动同步 dvadmin Role |
| backend/iam/apps.py | 后端 | ready() 中注册 iam.signals |
| backend/iam/urls.py | 后端 | 注册 /my_permissions/ 路由 |
| backend/iam/management/commands/seed_itsm_permissions.py | 后端 | ITSM 权限种子命令 |

### 解决

- **问题/背景:** OPSflow 6+ 个独立路由导致菜单臃肿; ITSM 新建工单按钮报 TypeError; IAM 缺少统一权限查询
- **办法:** OPSflow 合并为 ITSM 式单路由 tab 页面; 修复 ref 赋值; 新增 my_permissions + 角色同步信号

### 文档

- **生成文档:**
  - docs/opsflow/features/2026-06-30-opsflow-tab-consolidation.md
  - docs/itsm/debug/2026-06-30-fix-showCreateTicket-const.md
  - docs/iam/features/2026-06-30-iam-my-permissions.md

### 验证

- 改动类型: feat + fix
- 清理乱码: 无
- 工作区状态: 干净 ✓

---

## c46945dd

> 提交日期: 2026-06-30 | 提交信息: feat: ITSM multi-tenant alignment + global project selector + bug fixes

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| backend/itsm/models/* (6 files) | 后端 | 12个模型加 project/business FK — Workflow/Ticket/Incident/Change/ServiceRequest/Problem/ServiceCategory/SlaPolicy/AssignRule/EscalationLevel/OnDutySchedule/SkillGroup |
| backend/itsm/migrations/0010_add_project_business_fk.py | 后端 | Migration: 12 字段新增 |
| backend/itsm/views/workflow_views.py | 后端 | 新增 ItsmProjectViewSet 基类 (ProjectFilteredViewSet+TenantPermission+dvadmin响应+NULL兼容+dept_belong_id allow_null) |
| backend/itsm/views/ticket_views.py | 后端 | TicketViewSet 切 ItsmProjectViewSet + EnvironmentGatePermission + business自动填充 |
| backend/itsm/views/views.py | 后端 | Incident/Change/ServiceRequest/Problem/ServiceCategory/SlaPolicy 6个ViewSet切换 |
| backend/itsm/views/assign_views.py | 后端 | AssignRule/Escalation/OnDuty 切换; SkillGroup 加 business queryset过滤 |
| backend/itsm/services/* (3 files) | 后端 | AssignEngine/SlaEngine/EscalationService 加 project_id 租户过滤 |
| backend/dvadmin/utils/serializers.py | 后端 | dept_belong_id IntegerField 加 allow_null=True |
| backend/itsm/serializers/assign_serializers.py | 后端 | 补 leader_name/target_group_name/match_category_name/group_name/user_name |
| backend/itsm/serializers/delegation.py | 后端 | DelegationCreateUpdateSerializer user设read_only; 补user_name/delegate_to_name |
| backend/itsm/serializers/workflow_serializers.py | 后端 | WorkflowVersionSerializer 加 workflow_name |
| backend/itsm/management/commands/seed_itsm.py | 后端 | 完整种子数据重写 (Workflows/SkillGroups/AssignRules/Escalations/OnDuty+duty) |
| backend/itsm/tests/test_services.py | 测试 | 补齐测试 |
| web/src/stores/project.ts | 前端 | **新建** 全局 Project Pinia store (currentProjectId/myProjects/fetchMyProjects) |
| web/src/layout/navBars/GlobalProjectSwitcher.vue | 前端 | **新建** 导航栏全局项目选择器 (loading/disabled/暗色模式) |
| web/src/layout/navBars/index.vue | 前端 | 嵌入 GlobalProjectSwitcher 到 navbars-right-area (classic/transverse/defaults) |
| web/src/utils/service.ts | 前端 | 全局 request 拦截器从 localStorage 自动注入 project_id |
| web/src/views/apps/opsflow/stores/opsflowStore.ts | 前端 | 项目状态委托给全局 stores/project.ts |
| web/src/views/apps/opsflow*/index.vue (8 files) | 前端 | 移除本地 ProjectSwitcher 组件+import |
| web/src/layout/navBars/breadcrumb/setings.vue | 前端 | 移除布局切换卡片(defaults/classic/transverse/columns) |
| web/src/views/apps/itsm/index.vue | 前端 | 流程模板删除+图标; SLA编辑弹窗; 事件新建工单; 监听project-changed; onBeforeUnmount |
| web/src/views/apps/itsm/*.vue (5 files) | 前端 | 所有dialog加 append-to-body; Delegation补Check import; OnDuty el-radio label→value |
| docs/superpowers/specs/2026-06-30-itsm-multi-tenant-alignment.md | 文档 | **新建** ITSM多租户对齐完整设计规范 |

### 解决

- **问题/背景:** ITSM模块完全未接入IAM多租户体系; 缺少全局项目选择器; dept_belong_id null校验失败; 流程模板无删除; SLA无编辑; 弹窗被遮罩覆盖等18个bug/功能缺口
- **办法:** 5阶段实施: Model层加FK→View层切ProjectFilteredViewSet→Service层加租户过滤→前端全局ProjectSelector→ITSM页面接入+seeder+修复

### 文档

- **生成文档:**
  - docs/superpowers/specs/2026-06-30-itsm-multi-tenant-alignment.md

### 验证

- 改动类型: feat + fix + refactor
- 清理乱码: 无
- 工作区状态: 干净 ✅
- 测试: itsm.tests 通过 ✅

---

## 0d0a3be9

> 提交日期: 2026-06-30 | 提交信息: feat: ITSM assignment redesign + drag-drop form designer + i18n

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| backend/itsm/models/skill_group.py | 后端 | 新增 SkillGroup + OnDutySchedule |
| backend/itsm/models/assign_rule.py | 后端 | 新增 AssignRule 路由规则 |
| backend/itsm/models/escalation.py | 后端 | 新增 EscalationLevel 升级级别 |
| backend/itsm/models/transfer_log.py | 后端 | 新增 TicketTransferLog 转派审计 |
| backend/itsm/services/assign_engine.py | 后端 | 新增 AssignEngine 自动分派引擎 |
| backend/itsm/services/escalation_service.py | 后端 | 新增 EscalationService 多级升级 |
| backend/itsm/management/commands/start_itsm_scheduler.py | 后端 | 新增独立 APScheduler 进程 |
| backend/itsm/models/ticket.py | 后端 | 新增 category FK, 扩展 STATUS_CHOICES |
| backend/itsm/models/field.py | 后端 | LAYOUT_CHOICES 扩展 COL_8/COL_4/COL_3 |
| backend/itsm/models/incident.py | 后端 | ServiceCategory 扩展, SlaPolicy 移除 escalate_minutes |
| backend/itsm/views/dashboard.py | 后端 | 看板状态筛选改为 assigned/receiving/running |
| backend/itsm/tasks.py | 后端 | 修复 auto_resolve 用 set_status() |
| web/src/views/apps/itsm/designer/ | 前端 | 新增三栏可视化拖拽 FormDesigner.vue |
| web/src/views/apps/itsm/SkillGroup.vue | 前端 | 新增技能组管理 CRUD |
| web/src/views/apps/itsm/OnDutySchedule.vue | 前端 | 新增值班排班管理 |
| web/src/views/apps/itsm/AssignRule.vue | 前端 | 新增分派规则管理 |
| web/src/views/apps/itsm/EscalationLevel.vue | 前端 | 新增升级级别管理 |
| web/src/views/apps/itsm/TeamDashboard.vue | 前端 | 新增团队看板 |
| web/src/i18n/pages/itsm/ | 前端 | 新增 ITSM i18n 中文/英文翻译 |

### 解决

- **问题/背景:** ITSM 分派系统缺失,表单字段编辑体验差,无 i18n 支持
- **办法:** 完整的技能组+排班+路由规则+多级升级体系;三栏拖拽可视化表单设计器;i18n 翻译文件+管理页面改造

### 验证

- 改动类型: feat + fix
- 清理乱码: 删除 index.vue.bak
- 工作区状态: 干净 ✅

---

## ac661951

> 提交日期: 2026-06-29 | 提交信息: docs: fix placeholder hash in manual-pause feature doc

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| docs/opsflow/features/2026-06-29-manual-pause-atom.md | 文档 | `(待提交)` → `6e23a2f0` |
| COMMIT_ANALYSIS.md | 文档 | 修正 amend 后的 hash |

### 解决

- **问题/背景：** amend 后 commit hash 变更
- **办法：** 替换为实际 hash

### 验证

- 改动类型: docs
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅

---

## 6e23a2f0

> 提交日期: 2026-06-29 | 提交信息: feat: add manual_pause atom + fix optional skip integration

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `plugins/common/manual_pause.py` | 后端 | **新建** ManualPausePlugin，零参数，execute() 立即返回 success |
| `core/pipeline_builder/elements.py` | 后端 | 注册 manual_pause 节点类型 |
| `core/plugin_service_adapter.py` | 后端 | 拦截 manual_pause 原子直接 FlowEngine.pause() |
| `signals/handlers.py` | 后端 | 补全 FAILED 分支中 _check_optional_skip() 集成 |
| `tests/test_manual_pause.py` | 测试 | 5 个测试（PluginService 暂停 + ManualPausePlugin 元数据）|
| `ExecutionDetail.vue` | 前端 | 新增 isManualPause 计算属性 + 蓝色暂停提示横幅 |
| `en.ts` / `zh-cn.ts` | 前端 | 新增 manualPause.title/description 共 4 个 key |
| `docs/opsflow/features/2026-06-29-manual-pause-atom.md` | 文档 | 新建功能文档 |

### 解决

- **问题/背景：** Pipeline 缺乏「执行到此处暂停」的能力，只能借审批原子变通且语义不符；Optional 跳过集成代码在之前的 hook 提交中漏掉了 FAILED 分支
- **办法：** 新建 manual_pause 原子（PluginService 直接暂停不走信号）；补全 handlers.py 中的 _check_optional_skip 集成

### 文档

- **生成文档：**
  - docs/opsflow/features/2026-06-29-manual-pause-atom.md

### 验证

- 改动类型: feat + fix
- 清理乱码: 有（空文件 `0`）
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## cda6e382

> 提交日期: 2026-06-29 | 提交信息: chore: add version field to agent and ansible plugins

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| plugins/agent/*.py (7 files) | 后端 | 添加 version = "v1.0" |
| plugins/ansible/*.py (9 files) | 后端 | 添加 version = "v1.0" |
| docs/superpowers/specs/2026-06-28-manual-pause-atom-design.md | 文档 | 新建设计规范 |
| COMMIT_ANALYSIS.md | 文档 | 修正上条记录 hash |

### 解决

- **问题/背景：** Agent 和 Ansible 插件缺少 version 字段，未注册到插件注册表
- **办法：** 16 个插件在 group 后插入 version = "v1.0"

### 文档

- **生成文档：** 无（chore 类型跳过）

### 验证

- 改动类型: chore
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## 59fe80a2

> 提交日期: 2026-06-29 | 提交信息: feat: complete i18n fields for agent/aliyun/ansible plugins

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| plugins/agent/*.py (5 files) | 后端 | FormItem 添加 name_en + placeholder_en |
| plugins/aliyun_ecs/*.py (8 files) | 后端 | FormItem 添加 name_en + placeholder_en，类补齐 icon + color |
| plugins/ansible/*.py (9 files) | 后端 | 类补齐 name_en + icon + color，FormItem 添加 name_en + placeholder_en |

### 解决

- **问题/背景：** Agent/Aliyun/Aliyun ECS/Ansible 三类插件共 22 个文件缺少英文标签（name_en/placeholder_en）和前端展示图标（icon/color），导致英文模式下标签缺失、节点图标空白
- **办法：** 逐文件补齐 FormItem 的 name_en 和 placeholder_en；类级别补齐 name_en、icon、color

### 文档

- **生成文档：** 无（非功能新增，跳过）

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## 8716aefe

> 提交日期: 2026-06-28 | 提交信息: docs: fix placeholder hash in optional-skip feature doc

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| docs/opsflow/features/2026-06-28-optional-skip-on-fail.md | 文档 | `(待提交)` → `bae59bcc` |

### 解决

- **问题/背景：** feature 文档中有未替换的 `(待提交)` 占位符
- **办法：** 替换为实际 commit hash bae59bcc

### 验证

- 改动类型: docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## bae59bcc

> 提交日期: 2026-06-28 | 提交信息: test: add optional skip unit + integration tests — Optional 节点跳过测试 + 功能文档

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| backend/opsflow/tests/test_optional_skip.py | 测试 | 10 个测试覆盖 _check_optional_skip（7 单元）+ 信号集成（3） |
| docs/opsflow/features/2026-06-28-optional-skip-on-fail.md | 文档 | Optional 节点失败自动跳过功能文档 |
| docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md | 文档 | 修复 merge conflict 残留 |
| COMMIT_ANALYSIS.md | 文档 | 更新 8e58d2cb 条目补全改动描述 |

### 解决

- **问题/背景：** Optional skip-on-fail 代码已提交（8e58d2cb），但配套测试和功能文档缺失
- **办法：** 补齐 10 个测试 + feature 文档

### 文档

- **生成文档：**
  - docs/opsflow/features/2026-06-28-optional-skip-on-fail.md

### 验证

- 改动类型: test + docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 8e58d2cb

> 提交日期: 2026-06-28 | 提交信息: fix: enable clearable for async_select dropdown

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| web/src/components/RenderForm/tags/TagAsyncSelect.vue | 前端 | clearable 默认值 false→true |
| backend/opsflow/signals/handlers.py | 后端 | 新增 _check_optional_skip() + FAILED 分支集成，Optional 节点失败自动跳过 |
| web/src/views/apps/opsflow/components/panels/PropertyPanel.vue | 前端 | Optional/max_retries 互斥，retry 开启时 optional 禁用，反之亦然 |
| docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md | 文档 | 新建调试文档 |

### 解决

- **问题/背景：** async_select 下拉选中后无法清除；Optional 开关只在冲突检测中有效，实际执行无 skip-on-fail 功能；前端 Optional 和 Retry 同时启用语义矛盾
- **办法：** TagAsyncSelect clearable=true；signal handler 中拦截 FAILED 检查 optional 标志自动调 FlowEngine.skip()；前端 :disabled 双向互斥

### 文档

- **生成文档：**
  - docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端组件 + 文档）
- 工作区状态: 干净 ✅

---

## 4fbb2c87

> 提交日期: 2026-06-28 | 提交信息: refactor: remove execution rollback functionality — 移除所有执行回滚代码

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| core/flow_engine.py | 后端 | 删除 rollback_failed_nodes()、_trigger_plugin_rollback()，简化 _fail_execution() |
| core/plugin_service_adapter.py | 后端 | 删除 PluginService.rollback() 方法 |
| signals/handlers.py | 后端 | 删除 FAILED 分支中的 rollback 触发 |
| plugins/base.py | 后端 | 删除 BasePlugin.rollback() 默认实现 |
| plugins/esxi/*.py (8个) | 后端 | 删除各插件 rollback() 方法 |
| plugins/aliyun_ecs/*.py (4个) | 后端 | 删除各插件 rollback() 方法 |
| plugins/ansible/tower_backend/base_plugin.py | 后端 | 删除 rollback() 方法及 docstring 引用 |
| tests/test_flow_engine.py | 后端 | 删除 3 个 rollback 测试用例；修复 mock 路径 |
| tests/test_node_timeout_strategy.py | 后端 | 修复 mock 导入路径 |
| apps.py | 后端 | 插件注册异常捕获改为 debug 日志 |
| docs/architecture/2026-06-28-remove-execution-rollback-refactor.md | 文档 | 新建架构重构文档 |
| docs/superpowers/specs/2026-06-28-remove-execution-rollback-design.md | 文档 | 新建设计规范文档 |

### 解决

- **问题/背景：** 执行回滚功能（节点失败后的补偿操作）不再需要，涉及 FlowEngine、PluginService、信号处理器和所有插件共计 18 个文件中的 rollback 代码
- **办法：** 删除所有执行回滚相关代码：核心引擎 rollback 调度、服务适配器 PluginService.rollback()、插件基类和所有子类的 rollback() 方法、信号处理器中的 rollback 触发、对应的测试用例。保留模板版本回滚和安全校验中的 rollback 路径检查

### 文档

- **生成文档：**
  - docs/opsflow/architecture/2026-06-28-remove-execution-rollback-refactor.md
  - docs/superpowers/specs/2026-06-28-remove-execution-rollback-design.md

### 验证

- 改动类型: refactor + fix (test mock paths)
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 待提交 ✅

---

## e345baa5

> 提交日期: 2026-06-28 | 提交信息: fix: loop config i18n + switch click event bubble fix — Loop Configuration 区域 i18n 替换 + 滑块点击无响应修复

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| PropertyPanel.vue | 前端 | 9 处硬编码标签/placeholder/radio 替换为 $t()；移除父 div @click 改为 span @click.stop 修复事件冒泡 |
| en.ts | 前端 | 新增 9 个 i18n keys (loopConfig/maxIterations/loopVariable/loopValues/...) |
| zh-cn.ts | 前端 | 新增对应 9 个中文翻译 |
| docs/opsflow/debug/2026-06-28-loop-config-i18n-switch-fix.md | 文档 | 新建调试文档 |

### 解决

- **问题/背景：** Loop Configuration 区域所有标签为硬编码英文，el-switch 滑块因事件冒泡双重触发导致点击无响应
- **办法：** 父 div 移除 @click，文字改为 span @click.stop 单独控制；全部标签替换为 $t()

### 文档

- **生成文档：**
  - docs/opsflow/debug/2026-06-28-loop-config-i18n-switch-fix.md

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端改动）
- 工作区状态: 干净 ✅

---

## 8145f0fb

> 提交日期: 2026-06-28 | 提交信息: docs: fix commit hash references in analysis log and arch doc — 修正 COMMIT_ANALYSIS.md 和架构文档中的 commit hash 引用

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| COMMIT_ANALYSIS.md | 文档 | 修正上条记录中的 commit hash 为 4fbb2c87 |
| docs/opsflow/architecture/2026-06-28-remove-execution-rollback-refactor.md | 文档 | 修正文档中 commit hash 为 4fbb2c87 |

### 解决

- **问题/背景：** 上轮 amend 后 commit hash 变更，遗留的 COMMIT_ANALYSIS.md 和架构文档中仍引用旧 hash 4852cbce，导致链接失效
- **办法：** 将两处引用更新为实际的 commit hash 4fbb2c87

### 文档

- **生成文档：** 无（docs 类型跳过）

### 验证

- 改动类型: docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## d7c0716c

> 提交日期: 2026-06-28 | 提交信息: fix: add aiSuggestions i18n key + widen AI dialog

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| web/src/i18n/pages/opsflow/zh-cn.ts | 前端 | 新增 opsflowPage.aiSuggestions 键 |
| web/src/i18n/pages/opsflow/en.ts | 前端 | 新增 opsflowPage.aiSuggestions 键 |
| web/src/views/apps/opsflow/index.vue | 前端 | AI 分析弹窗宽度 740px->960px |

### 解决

- **问题/背景：** aiSuggestions 在 index.vue 中被引用，但 i18n 文件中缺少该键；AI 分析弹窗内容太多放不下
- **办法：** 补齐中英文键；弹窗宽度扩大 1/3

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 5ea3fd8e

> 提交日期: 2026-06-28 | 提交信息: fix: correct i18n key references in opsflow sub-pages

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/api/opsflow/dashboard.ts` | 前端 | API 路径修正 |
| `web/src/views/apps/{integration,itsm,open-api}/index.vue` | 前端 | i18n 键引用修正 (3 files) |
| `web/src/views/apps/opsflow-{approval,dashboard,execution,log,template}/index.vue` | 前端 | i18n 键引用修正 (5 files) |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue` | 前端 | 条件标签修正 |

### 解决

- **问题/背景：** 多个子页面 i18n 键引用使用错误的前缀格式
- **办法：** 统一修正为正确的 i18n 键路径

### 验证

- 改动类型: fix
- 清理乱码: 有（1 个 garbled file）
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 28122657

> 提交日期: 2026-06-28 | 提交信息: feat: unify IAM as identity management center + portal i18n

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/views/apps/iam/index.vue` | 前端 | 新增 5 个 dvadmin 系统管理 tab（Users/Roles/Menus/Depts/OperationLog） |
| `web/i18n/pages/iam/en.ts` | 前端 | 新增 users/roles/menus/depts/operationLog 标签 |
| `web/i18n/pages/iam/zh-cn.ts` | 前端 | 同上中文翻译 |
| `web/views/apps/portal/index.vue` | 前端 | 28+ 处硬编码替换为 message.portal.* i18n |
| `web/i18n/pages/portal/en.ts` | 前端 | 新建 30+ key 英文翻译 |
| `web/i18n/pages/portal/zh-cn.ts` | 前端 | 新建 30+ key 中文翻译 |

### 解决

- **问题/背景：** dvadmin 和 IAM 各管一方，IAM 缺少用户/角色/菜单管理入口；Portal 全部硬编码中文无法国际化
- **办法：** Phase 1 前端入口统一：IAM 直接嵌入 dvadmin 组件无需后端改动；Portal 全量 i18n 替换

### 文档

- **生成文档：** 无（纯前端改动）

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 5124f0b0

> 提交日期: 2026-06-28 | 提交信息: feat: add loop_iteration to NodeExecutionTrace for loop/cycle iteration tracking

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/models/execution.py` | 后端 | NodeExecutionTrace 新增 loop_iteration 字段，unique_together 改为 (execution, node_id, retry_count, loop_iteration) |
| `backend/opsflow/serializers.py` | 后端 | trace_summary 返回 loop_iteration |
| `backend/opsflow/signals/trace.py` | 后端 | 新增 _resolve_loop_iteration() — 检查上次迭代状态为 completed/failed 时自动递增 |
| `web/.../ExecutionDetail.vue` | 前端 | 行 key + Iteration 列 + tab 区域 overflow 滚动修复 |
| `docs/superpowers/specs/2026-06-28-loop-trace-iteration-design.md` | 文档 | 设计规范 |

### 解决

- **问题/背景：** loop 场景下节点执行多次，但 NodeExecutionTrace 只有一行(retry_count=0,loop_iteration=0)，后续迭代的 outputs 被覆盖
- **办法：** 新增 loop_iteration 字段 + _resolve_loop_iteration 按 DB 状态自动递增；Django migration 更新 unique_together

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-28-loop-trace-iteration-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## beabfcbb

> 提交日期: 2026-06-28 | 提交信息: fix: pipeline execution bugs + PropertyPanel condition editor overhaul

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | _find_predecessor_activity 处理 dict edge；_gwcond_ → {node_id}_{key} 修复 whitelist |
| `backend/opsflow/core/flow_engine.py` | 后端 | _has_loop_edges 传入原始 frozen_tree |
| `web/.../PropertyPanel.vue` | 前端 | Loop Config 修复（onLoopChange + v-if+v-for crash）；条件预览多行显示+Delete按钮+反解析Edit |
| `web/.../useDesignCanvas.ts` | 前端 | 边 label 保留；label 仅网关边显示；aiLayout 循环边恢复 label |
| `web/.../useGraphCanvas.ts` | 前端 | getGraphData 优先读 edgeData.label |
| `web/.../index.vue` | 前端 | onSelectTemplate 自动跑 AI layout |

### 解决

- **问题/背景：** Pipeline 执行因回环检测格式错误、自定义条件 whitelist 拒绝、前驱查找类型错误而失败；PropertyPanel Loop Config/条件编辑器因 Vue3 v-if+v-for 顺序、conditionStruct 状态管理不当而崩溃/无法编辑
- **办法：** 统一用 frozen_tree 格式检测回环；去掉 _gwcond_ 前缀；兼容 dict edge 前驱查找；loopVarOptions computed 替代 v-if+v-for；_parseConditionExpr 从字符串反解析；边 label 全线修复。共修复 5 个 bug

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-28-pipeline-bugfix-condition-editor.md`

### 验证

- 改动类型: fix+refactor
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 64fcc336

> 提交日期: 2026-06-28 | 提交信息: feat: implement multi-tenant architecture with Business/Environment isolation

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/models/{tenant,project,membership,rbac}.py` | 后端 | iam app 重构为 models/ 包，新增 Business/BusinessGroup/DeployEnvironment/Project/ProjectMember/BusinessMember/DeployEnvironmentPermission 7 个模型 |
| `backend/iam/resolvers.py` | 后端 | 权限解析核心：get_visible_projects/has_project_role/can_execute_in_environment，Business 角色向下继承 |
| `backend/iam/permissions.py` | 后端 | TenantPermission/EnvironmentGatePermission DRF Backend |
| `backend/iam/routers.py` | 后端 | TenantDatabaseRouter 物理隔离扩展点（当前返回 default） |
| `backend/iam/views.py` | 后端 | BusinessViewSet/DeployEnvironmentViewSet/IamProjectViewSet 管理 API |
| `backend/iam/serializers.py` | 后端 | 全部 tenant 序列化器 |
| `backend/iam/urls.py` | 后端 | /api/iam/businesses/ /api/iam/environments/ /api/iam/projects/ 路由 |
| `backend/iam/management/commands/` | 后端 | seed_deploy_environments + grant_default_env_permissions 命令 |
| `backend/opsflow/models/` | 后端 | 6 模型 FK('iam.Project')，OperationRecord+ApiToken 增强，FlowExecution.environment FK，旧 OpsProject/ProjectMember 删除 |
| `backend/opsflow/views/base.py` | 后端 | ProjectFilteredViewSet 接入 iam.resolvers（get_visible_projects 含 Business 继承） |
| `backend/opsflow/views/{template,execution,project,schedule,knowledge,scheme}_views.py` | 后端 | 6 ViewSet 添加 TenantPermission，执行 ViewSet 添加 EnvironmentGatePermission |
| `backend/{cmdb,itsm,monitor,job_platform,integration,opsagent}/models/` | 后端 | 6 个子产品核心模型各添加 Business FK |
| `web/src/views/apps/iam/index.vue` | 前端 | 全新 hero + tabs 布局，Business 和 Environment 管理 tab |
| `web/src/views/apps/iam/{BusinessManage,EnvironmentManage}.vue` | 前端 | 业务线 CRUD + 成员管理，部署环境 CRUD + 权限管理 |
| `web/src/views/apps/iam/{MyRequests,ApprovalDashboard}/index.vue` | 前端 | 全部硬编码英文改为 i18n，统一 opsflow 卡片+表格+弹窗样式 |
| `web/src/i18n/pages/iam/{en,zh-cn}.ts` | 前端 | 90+ 中英文翻译 key |
| `docs/superpowers/specs/2026-06-28-multi-tenant-design.md` | 文档 | 17 条设计决策 + 完整实现方案 |

### 解决

- **问题/背景：** OPSflow 仅支持 OpsProject 级别隔离，无法满足企业按业务线和部署环境细粒度控制权限的需求，且 CMDB/ITSM/Monitor 等子产品缺少统一的权限底座
- **办法：** 新建 iam app 作为多租户基础设施；Project 从 opsflow 迁入 iam 避免循环依赖；权限解析分三层叠加；5 阶段渐进迁移不破坏现有功能；18/18 tests 全程通过

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-28-multi-tenant-design.md`
  - `docs/iam/features/2026-06-28-multi-tenant-implementation.md`

### 验证

- 改动类型: feat
- 清理乱码: 有（.bak 残留清理）
- 子 App index.md 更新: iam, opsflow, cmdb, itsm, monitor, job_platform, integration, opsagent
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 4e0cbf74

> 提交日期: 2026-06-26 | 提交信息: feat: add template presets for AI quick-start

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/models/template.py` | 后端 | 新增 TemplatePreset 模型 |
| `backend/opsflow/views/template_views.py` | 后端 | GET /templates/presets/ 端点 |
| `backend/opsflow/management/commands/seed_template_presets.py` | 后端 | 10 个中英双语预设提示词 seed |
| `web/.../CreateTemplateWizard.vue` | 前端 | AI 输入框下方预设标签 |
| `web/.../api/templates.ts` | 前端 | GetTemplatePresets API |

### 解决

- **问题/背景：** 新用户不知道怎么写 AI 提示词，需要预制常见 IT 运维场景快速上手
- **办法：** TemplatePreset 模型存储中英双语提示词 + API 返回 + 前端预设标签 10 个场景覆盖串行/并行/网关/循环全部机制

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-template-presets-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 有
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## aecd282b

> 提交日期: 2026-06-26 | 提交信息: feat: implement pipeline loop mechanism A+B

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/bamboo_validator.py` | 后端 | 新增回环边检测，环检测跳过合法回环边 |
| `backend/opsflow/core/flow_engine.py` | 后端 | run() 传递 cycle_tolerate |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | 拓扑排序容忍回环边 + loop_config 注入 |
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | ServiceActivity loop_var SPLICE 绑定 |
| `backend/opsflow/core/layout/layout_adapter.py` | 后端 | canvas_width 自适应 + 每行最多 8 节点 |
| `backend/opsflow/core/llm_service.py` | 后端 | LLM 提示词追加 Loop Mechanisms |
| `web/.../PropertyPanel.vue` | 前端 | Loop Configuration UI |
| `web/.../useDesignCanvas.ts` | 前端 | AI Layout 去环-布局-恢复 + 回环边样式 |
| `web/.../useGraphCanvas.ts` | 前端 | layoutNodes 排除回环边 + orth 路由 |
| `web/.../useGraphValidator.ts` | 前端 | checkCycle 容忍排他网关回环边 |
| `backend/opsflow/tests/test_bamboo_builder.py` | 测试 | 8 个循环机制测试 |

### 解决

- **问题/背景：** OpsFlow 基于 DAG 引擎，不支持循环。IT 运维场景需要两种循环：批量执行（同操作不同参数）和条件轮询（等待状态满足）
- **办法：** 机制 A（节点级 loop_config）实现批量循环；机制 B（排他网关回环边）实现条件驱动轮询；前后端+校验+布局+AI 提示词全链路支持

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-loop-mechanism-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 26699e30

> 提交日期: 2026-06-26 | 提交信息: feat: template public conversion + VariableBrowser simplify + remove output promote

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/views/template_views.py` | 后端 | 新增 make_public action + project admin is_public 权限 |
| `web/.../opsflow-template/index.vue` | 前端 | Make Public 按钮 + 项目选择弹窗 |
| `web/.../api/templates.ts` | 前端 | MakeTemplatePublic API 函数 |
| `web/.../PropertyPanel.vue` | 前端 | 全局 Vars 按钮 + VariableBrowser + focus 焦点跟踪插入 |
| `web/.../VariableBrowser.vue` | 前端 | 移除 Add/Drawer/CRUD；新增只读信息卡 + Delete + DOM 光标插入 |
| `web/.../TagInput.vue, TagTextarea.vue` | 前端 | 移除内置 VariableBrowser（精简） |
| `web/.../OutputParamSection.vue` | 前端 | 移除 Output Promote 按钮 |

### 解决

- **问题/背景：** 模板无法转为公共模板供跨项目使用；VariableBrowser 功能混乱（手动 Add + Drawer 编辑与 Promote 入口冲突）；Output Promote 创建别名变量无实际价值
- **办法：** 新增 make_public API + 前端按钮弹窗；VariableBrowser 变为纯浏览/插入引用/删除工具；移除 Output Promote

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-template-public-conversion-design.md`
  - `docs/superpowers/specs/2026-06-26-variable-browser-simplify-design.md`

### 验证

- 改动类型: feat+refactor
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端+少量后端改动）
- 工作区状态: 干净 ✅

---

## 3f8184af

> 提交日期: 2026-06-26 | 提交信息: feat: add 7 more SubmitWizard types + doc

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/.../SubmitWizardDialog.vue` | 前端 | 新增 switch/checkbox/radio/cascader/slider/host_selector/ip_selector 渲染 |
| `web/.../SubmitWizardDialog.vue` | 前端 | 修复多选下拉初始值类型（string->array） |
| `web/.../SubmitWizardDialog.vue` | 前端 | 修复 slider 初始值为数字类型 |
| `docs/.../2026-06-26-...md` | 文档 | 追加 FormItem 类型全景分析章节 + 更新记录 |

### 解决

- **问题/背景：** SubmitWizard Step 3 只覆盖了 9 种变量类型，缺少 switch/checkbox/radio/cascader/slider/host_selector/ip_selector 等 IT 运维常用类型；多选下拉和 slider 的初始值类型错误
- **办法：** Template 中为每种类型添加 v-else-if 分支渲染对应的 Element Plus 组件；loadVars() 中根据 meta.multiple 和 type 做类型转换

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md`（追加更新）

### 验证

- 改动类型: feat+docs+fix
- 清理乱码: 有（鎻愪氦 0字节）
- 子 App index.md 更新: 无（纯前端+文档改动）
- 工作区状态: 干净 ✅

---

## b67fff40

> 提交日期: 2026-06-26 | 提交信息: feat: node input promote + type-aware SubmitWizard — 原子节点输入参数提权全局变量 + SubmitWizard 类型感知渲染

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/variable_resolver.py` | 后端 | normalize_global_vars 添加 meta 字段 |
| `backend/opsflow/serializers.py` | 后端 | get_global_variable_list 返回 meta |
| `backend/opsflow/views/aliyun_views.py` | 后端 | _is_template_ref 拦截模板引用透传 + describe_disk_categories 修复 error code |
| `backend/opsflow/views/mixins/template_variable.py` | 后端 | hook_variable 增加 promote_type=input 支持 |
| `web/src/components/RenderForm/FormItem.vue` | 前端 | 输入框右侧添加 Promote 按钮 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 前端 | promoteInput 提权函数 + context.onPromote |
| `web/src/views/apps/opsflow/api/templates.ts` | 前端 | HookVariable 接口扩展 |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue` | 前端 | 类型感知渲染 + async_select 级联加载 + flex 2 列布局 |
| `web/src/views/apps/opsflow/components/panels/GlobalVariablePanel.vue` | 前端 | select 选项编辑器 + show_type 保留 + 代码重构 |
| `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md` | 文档 | 功能实现详细文档 |

### 解决

- **问题/背景：** 原子节点 input 参数无法一键提权为全局变量；SubmitWizard Step 3 所有变量统一渲染为 `<el-input>`，丢失 UI 类型信息；提权后的 async_select 变量没有级联下拉加载功能
- **办法：** FormItem 添加 Promote 按钮 → promoteInput 提权函数 → HookVariable(promote_type=input) 存储 type/meta；SubmitWizard 根据 templateVars.type 渲染对应组件（select/async_select/int/float/datetime/date/time）；async_select 实时 API 加载 + watch 级联依赖

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md`

### 验证

- 改动类型: feat+fix+refactor
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅

---

## b4ce0afd

> 提交日期: 2026-06-22 | 提交信息: feat: implement Aliyun ECS CMDB sync + refactor all 8 atoms

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/cloud_sync.py` | 后端 | 实时同步模块，Pipeline 执行后自动同步 ECS 到 CMDB |
| `backend/opsflow/core/plugin_service_adapter.py` | 后端 | execute 成功后调用 cloud_sync hook |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 30 分钟周期全量同步，修复闭包序列化 |
| `backend/cmdb/services/sync_service.py` | 后端 | AliyunSync 全地域分页查询 + 状态映射 |
| `backend/cmdb/services/import_service.py` | 后端 | 保留 instance_id 系统字段，修复 null MERGE |
| `backend/opsflow/plugins/aliyun_ecs/_client.py` | 后端 | resolve_cmdb_region() 工具函数 |
| `backend/opsflow/plugins/aliyun_ecs/*.py` | 后端 | 8 个原子统一改造：region async_select + instance_id CMDB 选择 + switch |
| `backend/opsflow/views/aliyun_views.py` | 后端 | 新增 describe_cmdb_instances API + 页面视图 |
| `backend/opsflow/urls.py` | 后端 | 注册 cmdb-instances 等 8 个路由 |
| `backend/common/management/commands/seed_reference.py` | 后端 | Host 模型加 cloud_instance_id 等 3 个字段 |
| `web/src/components/RenderForm/FormGroup.vue` | 前端 | formData 传递修复 |
| `web/src/components/RenderForm/FormItem.vue` | 前端 | TAG_MAP 注册 TagSwitch + formData |
| `web/src/components/RenderForm/RenderForm.vue` | 前端 | formData 传递修复 |
| `web/src/components/RenderForm/tags/TagSwitch.vue` | 前端 | 新增 switch 类型组件 |
| `web/src/components/RenderForm/tags/TagSlider.vue` | 前端 | 新增滑块组件（自定义标签） |
| `web/src/components/RenderForm/tags/index.ts` | 前端 | 导出 TagSwitch |
| `web/src/views/apps/integration/index.vue` | 前端 | 集成中心页面优化 |
| `docs/opsflow/features/` | 文档 | ECS CMDB 同步功能文档 |
| `docs/superpowers/specs/` | 文档 | ECS CMDB 同步设计文档 |

### 解决

- **问题/背景：** 阿里云 ECS 实例创建/删除/启停后不会更新 CMDB，Pipeline 执行完操作后实例在 CMDB 不可见；8 个原子 region 硬编码、instance_id 手动输入、无级联选择
- **办法：** 实时同步（cloud_sync.sync_after_execution）+ 周期同步（AliyunSync 全地域 30min）；所有原子改用 async_select 级联表单 + CMDB 实例选择 + switch 开关

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md`
  - `docs/superpowers/specs/2026-06-22-ecs-cmdb-sync-design.md`

### 验证

- 改动类型: feat+refactor+fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 97397ecb

> 提交日期: 2026-06-23 | 提交信息: feat: implement Cloud Asset Sync management UI and sync logging — 云资产同步管理

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/models/cloud_sync_log.py` | 后端 | CloudSyncLog 同步日志持久化模型（provider/status/errors/triggered_by） |
| `backend/cmdb/views/cloud_sync_views.py` | 后端 | 云同步 API 4 端点 + 卡死记录自动检测（15min 超时重置） |
| `backend/cmdb/services/sync_service.py` | 后端 | BaseCloudSync 重构，sync() 自动写入 CloudSyncLog + try/except 兜底 |
| `backend/cmdb/urls.py` | 后端 | 注册 cloud-sync/providers/status/trigger/history 路由 |
| `backend/cmdb/models/__init__.py` | 后端 | 导出 CloudSyncLog |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 定时同步传入 triggered_by="schedule" |
| `web/src/views/apps/integration/cloud-sync.vue` | 前端 | 云同步管理组件（厂商卡片+操作工具栏+同步历史表格） |
| `web/src/views/apps/integration/index.vue` | 前端 | 集成中心新增云同步标签页 |
| `web/src/i18n/pages/integration/en.ts` | 前端 | 云同步英文文案（18 个 key） |
| `web/src/i18n/pages/integration/zh-cn.ts` | 前端 | 云同步中文文案（18 个 key） |
| `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md` | 文档 | 追加 CloudSyncLog/管理页面/数据修复 更新 |

### 解决

- **问题/背景：** 云同步只有后端无界面，用户无法查看同步状态、触发同步或排查同步错误；daemon thread 进程重启后同步状态永远卡在 running
- **办法：** 新增 CloudSyncLog 模型持久化同步记录；list_providers/sync_status/trigger_sync/sync_history 4 个 API；前端集成中心「云同步」标签页（厂商卡片 + 同步历史表格）；自动检测超 15 分钟卡死的 running 记录并重置

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md`（追加更新）

### 验证

- 改动类型: feat+fix
- 清理乱码: 有（backend/reset 空文件）
- 子 App index.md 更新: cmdb
- 工作区状态: 干净 ✅

---

## df82a1c9

> 提交日期: 2026-06-17 | 提交信息: feat: implement CMDB hierarchy refactor — Service→Application→Process model

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | 后端 | 新增 Application ModelDefinition + HAS_PROCESS/PROTECTED_BY 关联/模型关联种子数据 |
| `backend/agent_app/internal_views.py` | 后端 | `_sync_applications()` 同步 Application 节点 + HAS_PROCESS; `_match_calls_topology()` 建立 Application 级 CALLS |
| `backend/agent_app/apps.py` | 后端 | 实现 `get_registry_pids()` 修复死代码 |
| `backend/opsflow/services/dr_service.py` | 后端 | DR 拓扑查询改为 Application 级; neighbors_to_pipeline() 使用 Application 名 + host_ip |
| `backend/opsflow/views/mixins/template_dr.py` | 后端 | 修复 `_get_llm_client()` 解包错误 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | DR 拓扑改为选中 Group 后才加载; 边过滤新增 PROTECTED_BY/HAS_PROCESS |
| `docs/cmdb/features/` | 文档 | Application 模型层次重构文档 |
| `docs/opsflow/features/` | 文档 | DR Pipeline 适配文档 |
| `backend/seed_monitor_dr.py` | 脚本 | 监控业务 DR mock 数据种子脚本 |
| `backend/clean_neo4j.py` | 脚本 | Neo4j 无效数据清理脚本 |
| `.gitignore` | 配置 | 忽略 backend/logs/ |

### 解决

- **问题/背景：** CMDB 模型扁平化在 Process(PID)级，DrGroup 直接关联 Process，CALLS 在 4 个 nginx worker 间毫无意义；缺少 Application 层承载启停语义和 DR 拓扑
- **办法：** 新增 `:Application` Neo4j 节点 + HAS_PROCESS/PROTECTED_BY 关系，将 CALLS 和 DR 关联提升到 Application 层；修复 LLM 客户端调用；前端 DR 拓扑改为 Group 选择后才加载

### 文档

- **生成文档：**
  - `docs/cmdb/features/2026-06-17-application-model-hierarchy.md`
  - `docs/opsflow/features/2026-06-17-dr-pipeline-adapter.md`

### 验证

- 改动类型: feat+refactor+fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## ed7cb503

> 提交日期: 2026-06-15 | 提交信息: feat: implement opsflow-agent system — Go Agent + Server + Django integration

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/agent/` | 后端 | Go Agent Server + Agent daemon 核心实现（14个Go包） |
| `backend/agent_app/` | 后端 | Django App（6个模型，ViewSets，内部API） |
| `backend/opsflow/plugins/agent/` | 后端 | OpsFlow原子插件（3个：exec_cmd/file_push/file_pull） |
| `backend/job_platform/` | 后端 | AgentExecutor远程执行通道替代SSH |
| `backend/application/` | 后端 | 注册agent_app到Django |
| `backend/common/` | 后端 | Agent管理菜单seed数据 |
| `backend/agent-py/` | 后端 | Python Agent备份（重命名） |
| `web/src/views/apps/agent/` | 前端 | Agent管理页面（列表/安装/执行/文件推送） |
| `web/src/api/agent/` | 前端 | Agent API客户端 |
| `web/src/i18n/lang/` | 前端 | Agent页国际化（中/英各97个key） |
| `docs/superpowers/specs/` | 文档 | Agent设计文档 |

### 解决

- **问题/背景：** OpsFlow缺少远程Agent基础设施，远程执行依赖SSH（paramiko），无法做到指令推送、实时结果流、文件传输和主机端数据采集
- **办法：** 用Go实现类蓝鲸GSE的Agent组件体系（Server + Agent + Gateway三层架构），替换SSH成为远程执行首选通道

### 验证

- 改动类型: feat
- 清理乱码: 有（build/目录下的二进制exe文件）
- 子App index.md 更新: agent_app（需要时更新）
- 工作区状态: 干净 ✅
