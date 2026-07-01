# IAM RBAC 模型清理 — dvadmin 旧体系归并到 IAM

> 提交: 3ade6b9e | 日期: 2026-07-01
> 涉及 App: iam
> 类型: 重构 + 功能新增 + 破坏性变更

---

## 动机

项目存在两套并行的 RBAC 模型（dvadmin 旧模式和新 IAM），功能重叠、维护成本高。旧模型包括 Role, MenuButton, RoleMenuPermission, RoleMenuButtonPermission 4 个表和对应的 ViewSet。目标：**彻底消除旧模型，只维护一套 IAM 体系**。

## 变更要点

### 删除的模型和文件

| 模型/文件 | 说明 | 替代 |
|-----------|------|------|
| `iam/models/menu_rbac.py` → `Role` | 旧角色模型（platform admin/operator/viewer_only） | `IAMRole`（permission.py） |
| `iam/models/menu_rbac.py` → `MenuButton` | 旧按钮权限模型，含 api/method 字段 | `IAMPermission` |
| `iam/models/menu_rbac.py` → `RoleMenuPermission` | 旧角色-菜单绑定 | `IAMRolePermission` |
| `iam/models/menu_rbac.py` → `RoleMenuButtonPermission` | 旧角色-按钮绑定, 含 `data_range` 废弃字段 | `IAMRolePermission` |
| `iam/views/menu_button.py` | MenuButtonViewSet + menu_button_all_permission | — |
| `iam/views/role_menu.py` | RoleMenuPermissionViewSet 全文件 | — |
| `iam/views/role_menu_button_permission.py` | 400+ 行的全套 RBAC 管理视图 | — |
| `iam/views/menu_field.py` | MenuFieldViewSet（字段权限僵尸代码） | — |
| `dvadmin/utils/field_permission.py` | FieldPermissionMixin（后端无拦截） | — |
| `dvadmin/utils/permission.py` | CustomPermission 旧权限类 | `IAMPermissionBackend` |

### 新增：IAMMenu 导航模型

在 `iam/models/page_config.py` 中新增 `IAMMenu` 类，直接映射 `opsflow_iam_menu` 表：

```python
class IAMMenu(models.Model):
    """侧边栏导航配置，替换 dvadmin Menu"""
    name, icon, sort, web_path, component, component_name  # 路由配置
    is_link, is_catalog, is_iframe, cache, visible, status  # 渲染模式
    description, modifier, create_datetime, update_datetime  # 审计字段
    # db_table = 'opsflow_iam_menu' — 直接复用旧 Menu 表
```

关键区别：IAMMenu 使用 `models.Model` 而非 `CoreModel`（因为旧表缺少 `creator_id` 列），字段精确匹配 DB 结构。

### 核心迁移：PermissionRequest 审批

`permission_views.py:approve` 中 `target_role` 分支被移除，仅保留 `target_iam_role` 分支：

```python
# 重构前
if permission_request.request_type == 'role':
    if permission_request.target_role:
        permission_request.user.role.add(permission_request.target_role)  # 旧 M2M
    elif permission_request.target_iam_role:
        IAMUserRole.objects.create(user=..., role=...)

# 重构后
if permission_request.request_type == 'role' and permission_request.target_iam_role:
    IAMUserRole.objects.get_or_create(user=..., role=...)
```

### 核心迁移：user.role M2M → IAMUserRole

`dvadmin/system/models.py` → Users 模型去掉了 `role = ManyToManyField("iam.Role")`。

8 个文件中的 `user.role.values_list(...)` 批量替换为 `IAMUserRole.objects.filter(user=user).values_list(...)`：

| 文件 | 旧写法 | 新写法 |
|------|--------|--------|
| `iam/views/menu.py:187` | `user.role.values_list('id', ...)` | `IAMUserRole.objects.filter(user=user).values_list('role_id', ...)` |
| `iam/views/permission_views.py:175` | `user.role.add(target_role)` | `IAMUserRole.objects.get_or_create(...)` |
| `dvadmin/system/views/user.py:55` | `instance.role.all()` | `IAMUserRole.objects.filter(user=instance).select_related('role')` |
| `dvadmin/system/models.py:22` | `user.role.add(IamRole.objects.get(...))` | `IAMUserRole.objects.create(user=user, role=...)` |

### admin 管理后台适配

| 组件 | 重构前 | 重构后 |
|------|--------|--------|
| `role.py` RoleViewSet | `Role.objects.all()` | `IAMRole.objects.all()` |
| `role/index.vue` | `v-if="colPerm(...)"` 10+ 处字段权限控制 | 全部移除，默认全部可见 |
| `PermissionComNew/index.vue` | Menu→MenuButton→MenuField 三层树形选择 | App→Tab→Button 选择器，复用 `permission-catalog` API |
| `RolePermissionPanel.vue` | `/role_menu_button_permission/*` 旧 API | `/api/iam/role/{id}/permissions/` 新 API（IAMRolePermission） |
| `MenuButtonCom/` | 整体删除（按钮管理页面） | 迁移到角色权限分配 |

### 新增后端 API

- `GET/POST /api/iam/role/{id}/permissions/` — 读取/批量设置角色的 IAMRolePermission

### 前端 i18n 改造

IAM 三个核心页面全部改为 i18n：`iam/index.vue`（我的权限）、`MyRequests/index.vue`（申请）、`ApprovalDashboard/index.vue`（审批）。
新增 30+ 个 i18n 中英文键值对。

### ApprovalDashboard 批量审批

新增批量选择、批量批准/驳回功能，复用已存在的 `ApproveRequest`/`RejectRequest` API。

## 设计决策

1. **不删除 DB 表** — 旧模型对应表（`opsflow_iam_role` 等）保留，仅用 `managed = False` 标记，防止意外数据丢失
2. **IAMMenu 用 `models.Model` 而非 `CoreModel`** — 旧表结构字段与 CoreModel 不完全匹配（缺 `creator_id`）
3. **`PermissionRequest.target_role` 和 `UserDirectPermission.menu_button` 改为 IntegerField** — 保留 DB 列但不建立 FK 约束，避免 Django 跨模型依赖
4. **迁移使用 `SeparateDatabaseAndState`** — 仅更新 Django 模型状态，不操作 DB DDL，兼容已有表结构

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/models/page_config.py` | IAMMenu 新增（L12-L65） |
| `backend/iam/models/rbac.py` | PermissionRequest/UserDirectPermission FK 改为 IntegerField |
| `backend/iam/models/__init__.py` | 删除旧模型导入 |
| `backend/iam/views/permission_views.py` | approve 去旧 branch, available_roles 仅 IAMRole, 通知简化 |
| `backend/iam/views/role.py` | 重写为 IAMRole CRUD + permissions action |
| `backend/iam/views/menu.py` | IAMMenu 适配，web_router 简化 |
| `backend/iam/urls.py` | 删除 3 行旧 ViewSet 注册 |
| `backend/dvadmin/system/models.py` | 删除 user.role M2M |
| `backend/dvadmin/system/views/user.py` | get_role_info 改 IAMUserRole |
| `backend/dvadmin/system/views/dept.py` | 删除 data_range 过滤 |
| `web/src/views/apps/iam/admin/role/components/RolePermissionPanel.vue` | 重写为 IAM 权限分配 UI |
| `web/src/views/apps/iam/admin/role/index.vue` | 删除 colPerm 全部引用 |
| `web/src/views/apps/iam/admin/menu/index.vue` | 删除 MenuButtonCom/MenuFieldCom tab |
| `web/src/views/apps/iam/ApprovalDashboard/index.vue` | 批量审批 + i18n |
| `web/src/views/apps/iam/MyRequests/index.vue` | 角色选择简化 + i18n + checkbox-group 修复 |
| `web/src/views/apps/iam/index.vue` | 权限展示重写 + i18n |
| `web/src/i18n/pages/iam/zh-cn.ts` | 新增 30+ i18n 键 |
| `web/src/i18n/pages/iam/en.ts` | 同步英文翻译 |

## 迁移说明

此变更是破坏性的，因为：
1. 旧 `Role`/`MenuButton` 等模型类已被删除，引用 `iam.models.menu_rbac.Role` 的代码会报错（已在 commit 中同步更新所有引用）
2. `user.role` M2M 字段已移除，使用 `user.role` 的代码需改为 `IAMUserRole` 查询
3. 旧 API 端点 `/api/iam/menu_button/`, `/api/iam/role_menu_permission/`, `/api/iam/role_menu_button_permission/` 已移除

数据迁移：
- `python manage.py migrate`（fake + 状态迁移）已在开发环境验证
- 旧数据保留在 MySQL 表中未删
