# ITSM 接入 IAM 多租户体系 — 改造设计

**日期**: 2026-06-30  
**状态**: 设计完成，待实施  
**依赖**: IAM 多租户体系（Phase 1-2 已完成）

---

## 1. 背景与问题

### 1.1 现状

IAM 模块已实现完整的多租户体系（Business → Project 两级隔离 + DeployEnvironment 横向维度），详见 `docs/superpowers/specs/2026-06-28-multi-tenant-design.md`。opsflow、cmdb、monitor 等子产品已通过 `ProjectFilteredViewSet` + `TenantPermission` 接入。

**ITSM 模块完全未接入**，具体差距：

| 层次 | IAM 设计 | ITSM 现状 | 差距 |
|------|----------|-----------|------|
| View 基类 | `ProjectFilteredViewSet`（集成 iam resolvers） | `CustomModelViewSet`（dvadmin 框架） | ❌ 不同隔离机制 |
| 权限后端 | `TenantPermission` + `EnvironmentGatePermission` | `DataLevelPermissionsFilter`（部门级） | ❌ 用 dvadmin RBAC，不是 iam |
| 隔离维度 | `Business` FK + `Project` FK | `dept_belong_id`（HR 部门树） | ❌ 设计原则 #8：Dept ≠ Business |
| 服务层 | 服务感知租户上下文 | AssignEngine/SlaEngine/Escalation 全盲 | ❌ 可能跨租户泄露 |

### 1.2 目标

将 ITSM 模块完整对齐到 IAM 多租户体系，使 ITSM 工单、流程模板、SLA、分派规则等资源按 Business/Project 隔离。

---

## 2. Model 层变更

### 2.1 新增 FK 字段

所有字段 `null=True, blank=True, on_delete=SET_NULL`，兼容存量数据。

| 模型 | 新增字段 | 说明 |
|------|---------|------|
| `Workflow` | `project` FK → `iam.Project`, `related_name='itsm_workflows'` | 流程模板归属项目 |
| `Ticket` | `project` FK → `iam.Project`, `related_name='itsm_tickets'` | 工单归属项目 |
| `Incident` | `project` FK → `iam.Project`, `related_name='itsm_incidents'` | 事件工单归属项目 |
| `Change` | `project` FK → `iam.Project`, `related_name='itsm_changes'` | 变更申请归属项目 |
| `ServiceRequest` | `project` FK → `iam.Project`, `related_name='itsm_requests'` | 服务请求归属项目 |
| `Problem` | `project` FK → `iam.Project`, `related_name='itsm_problems'` | 问题归属项目 |
| `ServiceCategory` | `project` FK → `iam.Project`, `related_name='itsm_categories'` | 分类归属（nullable，可跨项目共享） |
| `SlaPolicy` | `project` FK → `iam.Project`, `related_name='itsm_sla_policies'` | SLA 策略归属项目 |
| `SkillGroup` | `business` FK → `iam.Business`, `related_name='itsm_skill_groups'` | 技能组归属业务线 |
| `AssignRule` | `project` FK → `iam.Project`, `related_name='itsm_assign_rules'` | 分派规则归属项目 |
| `EscalationLevel` | `project` FK → `iam.Project`, `related_name='itsm_escalations'` | 升级规则归属项目 |
| `OnDutySchedule` | `project` FK → `iam.Project`, `related_name='itsm_schedules'` | 排班归属项目 |

### 2.2 不需要直接加 project FK 的子表

以下通过父表级联归属，无需单独加 project：
- `State`、`Transition`、`Field` → 通过 `Workflow` 级联
- `TicketStatus`、`SignTask`、`TicketTransferLog` → 通过 `Ticket` 级联
- `WorkflowVersion` → 通过 `Workflow` 级联

### 2.3 Ticket.business 自动填充

`Ticket.business` FK 已存在（migration 0007），改造后在 `TicketViewSet.perform_create()` 中从 `project.business` 自动填充：

```python
def perform_create(self, serializer):
    instance = super().perform_create(serializer)
    if instance.project and instance.project.business_id:
        instance.business = instance.project.business
        instance.save(update_fields=['business'])
```

---

## 3. View 层变更

### 3.1 切换基类

以下 ViewSet 从 `CustomModelViewSet` → `ProjectFilteredViewSet`，添加 `TenantPermission`：

| ViewSet | project_field | permission_classes |
|---------|--------------|-------------------|
| `WorkflowViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `TicketViewSet` | `project` | `IsAuthenticated, TenantPermission, EnvironmentGatePermission` |
| `IncidentViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `ChangeViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `SlaPolicyViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `AssignRuleViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `EscalationLevelViewSet` | `project` | `IsAuthenticated, TenantPermission` |
| `OnDutyScheduleViewSet` | `project` | `IsAuthenticated, TenantPermission` |

### 3.2 保留 CustomModelViewSet 的 ViewSet

- `WorkflowVersionViewSet` — 通过 workflow 级联，内部使用
- `StateViewSet`、`TransitionViewSet`、`FieldViewSet` — sync action 内部使用
- `TicketStatusViewSet`、`SignTaskViewSet` — 通过 ticket 嵌套访问
- `DelegationViewSet` — 用户级，非项目级隔离
- `SkillGroupViewSet` — 按 business 过滤（自建 get_queryset 逻辑，不适用 ProjectFilteredViewSet）

### 3.3 响应格式兼容

`ProjectFilteredViewSet` 继承 DRF `ModelViewSet`，不继承 `CustomModelViewSet`。需要确保 ITSM ViewSet 的 action 方法返回格式与前端期望一致（当前前端期望 `{code, data, msg}` 格式的 `DetailResponse`）。

方案：在切换后的 ViewSet 中显式调用 `DetailResponse` / `SuccessResponse` 包装返回值。

---

## 4. Service 层变更

### 4.1 AssignEngine

```python
# 改造前
engine = AssignEngine(ticket)

# 改造后
engine = AssignEngine(ticket, project_id=ticket.project_id)

# 内部查询加隔离
AssignRule.objects.filter(project_id=project_id, is_active=True)
SkillGroup.objects.filter(business_id=ticket.business_id)
```

### 4.2 SlaEngine

```python
# 筛选 SlaPolicy 加 project_id 过滤
SlaPolicy.objects.filter(project_id=project_id, is_active=True)
```

### 4.3 EscalationService

```python
# 筛选 EscalationLevel 加 project_id 过滤
EscalationLevel.objects.filter(project_id=project_id, is_active=True)
```

### 4.4 NotificationService

通知接收人限定当前业务线成员范围。

### 4.5 PipelineWrapper / OpsflowTriggerService

PipelineWrapper 无状态封装层，无需改动。OpsflowTriggerService 触发执行时传递 `project_id` 到 opsflow。

---

## 5. 前端变更

### 5.1 全局 Project 选择器（一次性调整）

**5.1.1 新建 `stores/project.ts`**（全局 Pinia store）

从 `views/apps/opsflow/stores/opsflowStore.ts` 提升以下状态到全局：
- `currentProjectId: number | null`
- `myProjects: MyProject[]`
- `fetchMyProjects()` — 调 `/api/opsflow/projects/my_projects/`
- `setCurrentProjectId(id)` — 设置当前项目 + localStorage + dispatchEvent

**5.1.2 `layout/navBars/index.vue`** — 嵌入 ProjectSwitcher

在折叠按钮右侧、TagsView 左侧插入 `<ProjectSwitcher />`（light 模式），始终可见。

**5.1.3 `api/request.ts`** — 全局 API 自动注入 `project_id`

全局 request 拦截器读取 `stores/project.ts` 的 `currentProjectId`，自动附加 `project_id` 参数。

**5.1.4 移除 8 个 opsflow 子页面的本地 ProjectSwitcher**

以下文件的 Hero 区域移除 `<ProjectSwitcher>`，改为从全局 store 读取：
- `views/apps/opsflow-template/index.vue`
- `views/apps/opsflow-webhook/index.vue`
- `views/apps/opsflow-log/index.vue`
- `views/apps/opsflow-knowledge/index.vue`
- `views/apps/opsflow-approval/index.vue`
- `views/apps/opsflow-execution/components/ExecutionList.vue`
- `views/apps/opsflow-template/schedule.vue`
- `views/apps/opsflow/components/canvas/DesignCanvas.vue`

**5.1.5 更新 `stores/opsflowStore.ts`**

移除 `currentProjectId` / `myProjects` / `setCurrentProjectId` / `fetchMyProjects`，改为从全局 `stores/project.ts` 读取。

### 5.2 ITSM 页面接入

**5.2.1 `views/apps/itsm/index.vue`**

- `onMounted` 中监听 `window.addEventListener('project-changed', ...)`，切换项目时重新加载所有数据
- API 调用自动携带 `project_id`（通过全局 request 注入），无需手动传参
- 去掉 ITSM 页面 Hero 区域的统计数字（tickets/incidents/changes 数量），或改为按当前项目过滤

**5.2.2 Designer (`views/apps/itsm/designer/`)**

- 创建 Workflow 时自动关联当前 `project_id`
- 加载和保存无需改动（基于 workflow 级联）

**5.2.3 API 层 (`api/itsm/index.ts`)**

`createCrudApi` 无需改动，全局 request 自动注入 `project_id`。

---

## 6. 数据迁移与 Seeder

### 6.1 Migration

新增 `itsm/migrations/0008_add_project_fk.py`，所有新增 FK 字段 `null=True, blank=True`。

存量数据的 `project_id` 为 NULL，查询不会丢失（`ProjectFilteredViewSet` 对 `project_id=None` 的记录，由 `TenantPermission.has_object_permission()` 放行）。

### 6.2 Seeder 更新

`management/commands/seed_itsm.py`：
- 读取第一个 `iam.Project`（fallback：没有则跳过创建）
- 为所有种子数据设置 `project_id`
- `Ticket.business` 从 `project.business` 填充

---

## 7. 实施顺序

```
Phase 1: 后端 Model 层
  ├── 所有涉及模型加 project / business FK
  ├── Migration 文件
  └── 验证 migrate + 存量数据兼容

Phase 2: 后端 View 层
  ├── WorkflowViewSet 切换 ProjectFilteredViewSet
  ├── TicketViewSet 切换 + business 自动填充
  ├── Incident / Change / ServiceRequest / Problem / ServiceCategory / SlaPolicy 切换
  └── SkillGroup / AssignRule / Escalation / OnDuty 切换

Phase 3: 后端 Service 层
  ├── AssignEngine 加 project_id / business_id 过滤
  ├── SlaEngine 加 project_id 过滤
  ├── EscalationService 加 project_id 过滤
  └── NotificationService 限定业务线成员范围

Phase 4: 前端全局 Project 选择器
  ├── stores/project.ts（全局 Pinia store）
  ├── navBars 嵌入 ProjectSwitcher
  ├── api/request.ts 自动注入 project_id
  ├── 8 个 opsflow 子页面移除本地 ProjectSwitcher
  └── stores/opsflowStore.ts 去重

Phase 5: 前端 ITSM 接入
  ├── ITSM 页面监听 project-changed 事件
  ├── API 调用自动带 project_id（全局注入）
  └── Seeder 更新 + 验证
```

---

## 8. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 存量数据 `project_id=NULL` 导致查询遗漏 | FK 全部 nullable；superuser/superadmin 不受 queryset 过滤限制，可手动补齐 |
| `CustomModelViewSet` → `ProjectFilteredViewSet` 返回格式不兼容 | 显式用 `DetailResponse`/`SuccessResponse` 包装 |
| 全局 ProjectSwitcher 波及 8 个页面 | `project-changed` 事件机制不变，共存过渡，逐个页面移除 |
| 非超级用户突然看不到之前的数据 | 预期行为 — 需要 admin 为各 Business/Project 配置成员权限 |
| Migration 锁表 | MySQL 添加 nullable FK 通常瞬间完成；如数据量大需分批 |
