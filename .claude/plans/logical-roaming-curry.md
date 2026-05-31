# IAM 权限申请与审批模块

## Context

当前系统使用 RBAC（用户 ↔ 角色 ↔ 菜单权限），由系统管理员在后台配置。这种模式的问题是：用户需要权限时必须联系管理员手动操作，缺乏自助申请流程。

需要实现一个 IAM (Identity and Access Management) 模块，让用户可以自助申请权限，管理员可以审批。

---

## Architecture

### 数据模型

**1. PermissionRequest** - 权限申请记录
- `user` (FK → Users) - 申请人
- `request_type` (choice: `role` / `menu` / `menu_button`) - 申请类型
- `target_role` (FK → Role, nullable) - 申请加入的角色
- `target_menu` (FK → Menu, nullable) - 申请访问的菜单/页面
- `target_menu_button` (FK → MenuButton, nullable) - 申请的按钮权限
- `status` (choice: `pending` / `approved` / `rejected`) - 状态
- `reason` (TextField) - 申请理由
- `reviewer` (FK → Users, nullable) - 审批人
- `review_comment` (TextField, nullable) - 审批意见
- `reviewed_at` (DateTimeField, nullable) - 审批时间
- 继承 `CoreModel`（自动记录 create_datetime、creator 等）

**2. UserDirectPermission** - 用户直接授权记录（绕过 Role，直接授予）
- `user` (FK → Users)
- `menu` (FK → Menu, nullable) - 直接授权的菜单
- `menu_button` (FK → MenuButton, nullable) - 直接授权的按钮
- `granted_at` (DateTimeField, auto)
- `granted_by` (FK → Users)

### 审批逻辑

审批通过时：
- `request_type == 'role'` → `user.role.add(target_role)` → 用户直接获得角色的所有菜单/按钮权限
- `request_type == 'menu'` → 创建 `UserDirectPermission` 记录 → 修改 `web_router` 端点使其包含直授权限菜单
- `request_type == 'menu_button'` → 创建 `UserDirectPermission` 记录 → 修改 `menu_button_all_permission` 端点使其包含直授权限按钮

### 权限检查集成

修改系统菜单路由 API (`MenuViewSet.web_router`)，非超级用户时额外查询 `UserDirectPermission` 中直接授予的菜单；修改 `MenuButtonViewSet.menu_button_all_permission` 类似处理。这样用户获得批准后无需登出即可看到新菜单。

---

## Files to Create/Modify

### Backend

| File | Action | Purpose |
|------|--------|---------|
| `backend/iam/__init__.py` | CREATE | 空文件 |
| `backend/iam/apps.py` | CREATE | App config |
| `backend/iam/models.py` | CREATE | PermissionRequest + UserDirectPermission |
| `backend/iam/serializers.py` | CREATE | Serializers for both models |
| `backend/iam/views.py` | CREATE | ViewSet: list/create/approve/reject |
| `backend/iam/urls.py` | CREATE | Router registration |
| `backend/iam/admin.py` | CREATE | Admin registration |
| `backend/application/settings.py` | MODIFY | Add `'iam'` to INSTALLED_APPS |
| `backend/application/urls.py` | MODIFY | Add `path("api/iam/", include("iam.urls"))` |
| `backend/dvadmin/system/views/menu.py` | MODIFY | `web_router` action: include menus from `UserDirectPermission` |
| `backend/dvadmin/system/views/menu_button.py` | MODIFY | `menu_button_all_permission` action: include buttons from `UserDirectPermission` |

### Frontend

| File | Action | Purpose |
|------|--------|---------|
| `web/src/api/iam/requests.ts` | CREATE | API functions: GetRequests, CreateRequest, ApproveRequest, RejectRequest |
| `web/src/api/iam/permissions.ts` | CREATE | API functions: GetAvailableRoles, GetAvailableMenus |
| `web/src/views/apps/iam/MyRequests/index.vue` | CREATE | User-facing: request list + "New Request" dialog form |
| `web/src/views/apps/iam/ApprovalDashboard/index.vue` | CREATE | Admin-facing: pending requests table + approve/reject actions |
| `web/src/views/apps/iam/index.vue` | CREATE | Container with el-tabs: My Requests \| Approval Dashboard |
| `web/src/router/route.ts` | MODIFY | Add `/iam` route entry |

---

## API Design

All endpoints under `/api/iam/`:

```
GET    /api/iam/requests/              # 列表：用户看自己的，超级用户看全部
POST   /api/iam/requests/              # 创建申请 { request_type, target_role, target_menu, reason }
GET    /api/iam/requests/{id}/         # 详情
POST   /api/iam/requests/{id}/approve/ # 审批通过 { review_comment }
POST   /api/iam/requests/{id}/reject/  # 驳回 { review_comment }

GET    /api/iam/available-roles/       # 可申请的角色列表
GET    /api/iam/available-menus/       # 可申请的菜单列表
GET    /api/iam/direct-permissions/    # 用户的直接授权记录
DELETE /api/iam/direct-permissions/{id}/  # 撤销直接授权
```

---

## Frontend Detail

### MyRequests (`/iam` → "My Requests" tab)

**顶部**: 搜索/筛选栏 + "New Request" 按钮

**申请对话框**:
1. 选择申请类型: 角色 / 菜单
2. 选择目标: 根据类型动态显示角色下拉或菜单树选择
3. 填写申请理由
4. 提交

**申请列表**: el-table 显示所有申请记录，包含类型、目标、状态、时间、审批意见等列，支持分页

### ApprovalDashboard (`/iam` → "Approval" tab)

仅超级管理员可访问（`user.is_superuser` 判断）

**筛选栏**: 按申请类型、状态筛选

**审批列表**: el-table
- 行显示申请人、类型、目标、理由、申请时间
- 操作列: "Approve" + "Reject" 按钮
- 点击审批弹对话框，可填写审批意见

---

## Key Backend Views Details

**PermissionRequestViewSet** (`views.py`):
- `list`: 过滤当前用户的请求（非超级用户只能看自己的；超级用户可看全部，支持 `?status=pending` 筛选）
- `create`: 创建请求，自动关联当前用户为 `creator`
- `approve`: 超级用户操作，更新状态 + 执行业务逻辑（加角色/创建直接授权）
- `reject`: 超级用户操作，更新状态 + 记录审批意见

**AvailableRoles/Menus**:
- `available_roles`: 返回所有启用的角色（Role.objects.filter(status=True)）
- `available_menus`: 返回所有可见菜单（Menu.objects.filter(status=1, visible=1)）

---

## Modified System Views

**`menu.py` - `web_router` action**: 非超级用户时，额外查询 `UserDirectPermission.objects.filter(user=user, menu__isnull=False).values_list('menu_id', flat=True)` 并与 `RoleMenuPermission` 结果合并。

**`menu_button.py` - `menu_button_all_permission` action**: 非超级用户时，额外查询 `UserDirectPermission.objects.filter(user=user, menu_button__isnull=False).values_list('menu_button__value', flat=True)` 并与 `RoleMenuButtonPermission` 结果合并。

---

## Verification

1. `python manage.py makemigrations iam && python manage.py migrate`
2. 重启后端服务
3. 以普通用户登录 → 访问 IAM → 提交角色/菜单申请
4. 以超级管理员登录 → 访问 IAM 审批页 → 审批通过/驳回
5. 确认审批通过后，用户获得相应权限（角色加入或菜单可见）
6. 确认 `web_router` 和 `menu_button_all_permission` 返回了直授权限
