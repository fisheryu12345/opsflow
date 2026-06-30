# IAM 企业级 RBAC 闭环 — 设计规范

> 日期: 2026-07-01 | 状态: 设计完成

---

## 1. 背景

IAM 已持有 RBAC 模型（Role/Menu/MenuButton），BusinessMember/ProjectMember 已实现项目级角色。但缺乏统一授权 UI、角色模板、完整的申请/审批闭环，距离企业级 RBAC 仍有差距。

## 2. 目标

构建完整的企业级 RBAC 闭环，覆盖 4 个支柱：
1. 统一授权 UI — Role 权限配置面板（菜单树 + 按钮勾选）
2. 角色模板 — 预定义 + 自定义，新建项目一键套用
3. 审批工作流 — 申请→审批→自动赋权，全链路
4. 多 App 覆盖 — ITSM + OPSflow + CMDB 权限 Key 统一注册

---

## 3. 实施设计

> ⚠️ **i18n 要求**：所有新增前端组件（`RolePermissionPanel.vue`、`MyRequests` 扩展、`ApprovalDashboard` 扩展）的标签、按钮文字、placeholder、提示信息均使用 `$t('message.iam.xxx')` 而非硬编码中文/英文。新增 i18n keys 见 3.3.1 节 key 表。

### 3.1 统一授权 UI — Role 权限配置面板

**当前问题**：Role 管理页"权限"按钮打开 `PermissionComNew` 抽屉，可能因目录移动后路径问题无响应。

**方案**：替换为行内展开面板：

```
┌─────────────────────────────────────────────┐
│ 角色: ITSM Admin          [保存] [取消]      │
├──────────┬──────────────────────────────────┤
│ 📋 菜单   │ ☑ 流程模板                      │
│  ├ ITSM  │   ☑ 新建  ☑ 删除  ☑ 编辑        │
│  │ ├ 流程 │                                  │
│  │ ├ 工单 │ ☑ 工单管理                       │
│  │ └ SLA  │   ☑ 创建  ☑ 审批  ☐ 删除         │
│  ├ OPSflow│                                  │
│  └ CMDB   │ ☑ SLA 策略                       │
│          │   ☑ 编辑                         │
└──────────┴──────────────────────────────────┘
```

- 左侧菜单树（按子产品分组），勾选后出现该菜单的按钮列表
- 右侧展示选中菜单的所有按钮，勾选即绑定
- 顶部一键保存：`POST /api/system/role_menu_button_permission/set_role_premission/`

**关键文件**：
- 新建 `web/src/views/apps/iam/admin/role/components/RolePermissionPanel.vue`
- 后端：复用现有 `role_menu_button_permission.py` 的 `set_role_premission` action

### 3.2 角色模板

**模型**（新增 `iam/models/role_template.py`）：

```python
class RoleTemplate(CoreModel):
    name = CharField          # "ITSM Editor"
    source_role = FK(Role, null=True)  # 来源角色（自定义模板时填充）
    menus = JSONField         # [{menu_id, button_ids: [...]}]
    is_system = BooleanField  # 系统预置 vs 用户自定义
```

**系统预置模板**（seed 创建）：

| 模板名 | 覆盖范围 |
|--------|---------|
| ITSM Admin | 全部 ITSM 菜单 + 按钮 |
| ITSM Editor | 工单/流程模板（无删除/路由/SLA管理） |
| ITSM Viewer | 只读 |
| OPSflow Admin | 全部 OPSflow 菜单 + 按钮 |
| OPSflow Editor | 设计/执行（无删除） |
| CMDB Admin | 全部 CMDB 菜单 + 按钮 |
| CMDB Viewer | 只读 |

**使用流程**：
- 新建项目 → 选择角色模板 → 自动创建 Role + 绑定 Menu/Button
- 管理员在 Role 页面"另存为模板" → 创建自定义模板

### 3.3 审批工作流完善

**权限申请类型扩展**：

```python
# PermissionRequest 新增字段
target_project = FK(Project, null=True)        # 申请项目角色时的目标项目
target_project_role = CharField(choices=[admin/editor/viewer], null=True)
```

**申请类型**（`request_type`）：
| 类型 | 描述 | 前端表单 |
|------|------|---------|
| `role` | 申请平台级 Role（已有） | 选择 Role |
| `menu` | 申请菜单访问（已有） | 选择 Menu |
| `project_role` | **新增** 申请项目角色 | 选择项目 + 角色 |

**审批逻辑**：

```python
# 审批人判断：superuser OR 目标项目的 Business Admin
def can_approve(user, request):
    if user.is_superuser: return True
    if request.target_project and request.target_project.business_id:
        return has_business_role(user, request.target_project.business_id, 'admin')
    return False
```

**审批通过后自动赋权**：
1. `project_role` 类型 → 创建 `ProjectMember(project, user, role)`
2. `iam/signals.py` 自动触发 → IAM Role 同步 → 用户获得 MenuButton 权限
3. 站内信通知申请人和审批人（见 3.3.1）

**3.3.1 审批通知（中英双语）**

利用现有 `MessageCenter` 模型（`dvadmin/system/models.py`），审批结果通过站内信实时通知。
通知内容同时存储中英文，前端根据当前语言显示：

```python
# MessageCenter 扩展 — title_en / content_en 字段（或使用 JSON meta 存储双语）
def notify_approval_result(request, approved: bool, comment: str = ""):
    is_en = request.user.language == 'en'  # 用户语言偏好
    
    if approved:
        title_zh = "权限申请已通过"
        title_en = "Permission Request Approved"
        content_zh = f"项目 [{project.name}] {role_label} 角色已获批"
        content_en = f"Role [{role_label}] for project [{project.name}] has been approved"
    else:
        title_zh = "权限申请已拒绝"
        title_en = "Permission Request Rejected"
        content_zh = f"项目 [{project.name}] {role_label} 申请已拒绝。原因: {comment}"
        content_en = f"Role [{role_label}] for project [{project.name}] was rejected. Reason: {comment}"

    MessageCenter.objects.create(
        title=title_zh if not is_en else title_en,
        content=content_zh if not is_en else content_en,
        # 或将双语都存入 meta: {title_zh, title_en, content_zh, content_en}
        target_user=request.user,
    )
```

前端消息列表通过 `$t()` 或语言变量渲染，导航栏消息铃铛自动感知未读。

**新增 i18n keys**（`web/src/i18n/pages/iam/zh-cn.ts` + `en.ts`）：

| Key | 中文 | English |
|-----|------|---------|
| `message.iam.notifyApproved` | 权限申请已通过 | Permission Request Approved |
| `message.iam.notifyRejected` | 权限申请已拒绝 | Permission Request Rejected |
| `message.iam.notifyNewRequest` | 新的权限申请待审批 | New Permission Request Pending |
| `message.iam.notifyApprovedContent` | 项目 {project} {role} 角色已获批 | Role {role} for project {project} has been approved |
| `message.iam.notifyRejectedContent` | 项目 {project} {role} 申请已拒绝 | Role {role} for project {project} was rejected |
| `message.iam.notifyNewContent` | {user} 申请加入项目 {project} 为 {role} | {user} requested {role} role for project {project} |
| `message.iam.requestTypeProjectRole` | 项目角色申请 | Project Role Request |
| `message.iam.targetProject` | 目标项目 | Target Project |
| `message.iam.targetRole` | 目标角色 | Target Role |
| `message.iam.roleAdmin` | 管理员 | Admin |
| `message.iam.roleEditor` | 编辑者 | Editor |
| `message.iam.roleViewer` | 只读 | Viewer |
| `message.iam.permissionConfig` | 权限配置 | Permission Configuration |
| `message.iam.saveMenuAuth` | 保存菜单授权 | Save Menu Authorization |
| `message.iam.selectAll` | 全选 | Select All |
| `message.iam.noPermissionData` | 暂无权限数据 | No permission data |

### 3.4 多 App 权限 Key 注册

所有子产品的权限 Key 格式：`<app>:<resource>:<action>`

| App | 权限 Key | 说明 |
|-----|---------|------|
| ITSM | `itsm:workflow:create` | 创建流程 |
| | `itsm:workflow:delete` | 删除流程 |
| | `itsm:ticket:create` | 创建工单 |
| | `itsm:ticket:approve` | 审批 |
| | `itsm:ticket:assign` | 分派 |
| | `itsm:ticket:close` | 关闭 |
| | `itsm:sla:edit` | 编辑 SLA |
| | `itsm:skillgroup:manage` | 管理技能组 |
| | `itsm:duty:manage` | 管理排班 |
| | `itsm:rule:manage` | 管理路由 |
| | `itsm:escalation:manage` | 管理升级 |
| OPSflow | `opsflow:template:create` | 创建模板 |
| | `opsflow:template:delete` | 删除模板 |
| | `opsflow:template:publish` | 发布模板 |
| | `opsflow:execution:run` | 执行流程 |
| | `opsflow:execution:cancel` | 取消执行 |
| | `opsflow:schedule:manage` | 管理调度 |
| | `opsflow:webhook:manage` | 管理 Webhook |
| CMDB | `cmdb:model:create` | 创建模型 |
| | `cmdb:model:delete` | 删除模型 |
| | `cmdb:instance:create` | 创建实例 |
| | `cmdb:instance:delete` | 删除实例 |
| | `cmdb:instance:edit` | 编辑实例 |

**Seed 命令**：`backend/iam/management/commands/seed_rbac_permissions.py`（新建，统一注册所有 App 的 MenuButton + Role + RoleTemplate）

---

## 4. 数据流

```
管理员创建 RoleTemplate → seed 预置 Role + MenuButton 绑定
  └→ 用户申请权限（MyRequests）
       ├→ 申请 IAM Role（平台级：菜单可见性 + 按钮）
       ├→ 申请 Menu（特定菜单访问）
       └→ 申请 Project Role（项目级：admin/editor/viewer）
            └→ 业务线管理员/超级管理员审批（ApprovalDashboard）
                 ├→ user.role.add(iam_role)  →  MenuButton 权限生效
                 ├→ ProjectMember.create()   →  项目操作权限生效
                 └→ 站内信通知申请人
```

## 5. 关键文件

| 文件 | 改动 |
|------|------|
| `iam/models/rbac.py` | `PermissionRequest` 加 `target_project`, `target_project_role` |
| `iam/models/role_template.py` | **新建** — `RoleTemplate` 模型 |
| `iam/views.py` | `approve` action：新增 project_role 处理 + 审批人判断改为 business admin 检查 |
| `iam/management/commands/seed_rbac_permissions.py` | **新建** — 全 App 权限 Key seed |
| `web/src/views/apps/iam/admin/role/components/RolePermissionPanel.vue` | **新建** — 行内权限配置面板 |
| `web/src/views/apps/iam/MyRequests/index.vue` | 申请表单加"项目角色"类型 + 项目选择器 |
| `web/src/views/apps/iam/ApprovalDashboard/index.vue` | 审批列表加 business admin 可见性 |

## 6. 实施顺序

```
Phase 1: 后端模型 + Seed
  ├── PermissionRequest 加字段 + migration
  ├── RoleTemplate 模型 + migration
  ├── seed_rbac_permissions（OPSflow + CMDB 权限 Key + Role + RoleTemplate）
  └── 审批逻辑增强（business admin 可审批 + project_role 赋权）

Phase 2: 前端
  ├── RolePermissionPanel.vue（统一授权 UI）
  ├── MyRequests 表单扩展（project_role 类型 + 项目选择器）
  ├── ApprovalDashboard 扩展（business admin 可见 + project_role 展示）
  └── ITSM/OPSflow 页面接入 v-can 指令（按钮级权限控制）
```
