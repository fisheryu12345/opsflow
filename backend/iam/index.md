# IAM — 模块索引

> 上次自动更新: 2026-07-05 | 触发提交: 8240cbb1

---

## `根目录/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | —
| `admin.py` | — | `PermissionRequestAdmin`<br>`UserDirectPermissionAdmin`<br>`BusinessGroupAdmin`<br>`BusinessAdmin`<br>`DeployEnvironmentAdmin`
| `apps.py` | IAM app config — multi-tenant infrastructure + RBAC permission management | `IamConfig`
| `permission_backend.py` | Unified DRF permission backend — replaces dvadmin CustomPermission | `IAMPermissionChecker` — Single entry point for all permission checks.<br>`IAMPermissionBackend` — Unified DRF permission backend for all sub-products.
| `permissions.py` | DRF Permission Backends for multi-tenant access control. | `TenantPermission` — Unified multi-tenant permission check for all sub-product ViewSets.<br>`EnvironmentGatePermission` — Environment gate for execution / ticket creation endpoints.
| `resolvers.py` | Permission resolution functions for all sub-products. | `get_visible_projects()` — Return all project IDs visible to the user<br>`get_visible_businesses()` — Return all business IDs visible to the user<br>`get_project_role()` — Return the user's role (admin/editor/viewer) on a project.<br>`has_project_role()` — Check if user has at least min_role on a project<br>`has_business_role()` — Check if user has at least min_role in a business
| `routers.py` | Tenant database router — physical isolation extension point. | `TenantDatabaseRouter` — Routes database operations based on Business.db_alias.
| `serializers.py` | — | `PermissionRequestSerializer`<br>`PermissionRequestCreateSerializer`<br>`PermissionRequestReviewSerializer`<br>`UserDirectPermissionSerializer`<br>`BusinessGroupSerializer`
| `signals.py` | Signal handlers — (deprecated, unified RBAC replaces dvadmin role sync). | —
| `urls.py` | — | —

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | —

## `management/commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | —
| `grant_default_env_permissions.py` | Grant dev + staging DeployEnvironmentPermission to all active users. | `Command`
| `seed_deploy_environments.py` | Seed initial DeployEnvironment records: dev, staging, prod. | `Command`
| `seed_iam_menu.py` | Seed IAMMenu records (snapshot of current DB state). | `Command`
| `seed_iam_page_configs.py` | Seed PageTab + PageButton + IAMPermission + IAMRole config for all apps. | `Command`
| `seed_iam_unified.py` | Seed: initialize IAM permission models (data already migrated, clean one-shot)
Run: python manage.py seed_iam_unified | `Command`

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | IAM app models — multi-tenant infrastructure + RBAC permission requests | —
| `dept.py` | — | `IAMDept`
| `membership.py` | Membership models — BusinessMember, DeployEnvironmentPermission | `BusinessMember` — Business line membership — Admin/Editor roles cascade down to all Projects<br>`DeployEnvironmentPermission` — Explicit per-user execution permission for a deploy environment
| `page_config.py` | Page-level permission config — PageTab + PageButton | `IAMMenu` — 菜单 — 侧边栏导航配置 (replaces dvadmin Menu, maps to legacy DB schema)<br>`PageTab` — Tab 配置 — 每个应用有哪些 tab<br>`PageButton` — 按钮配置 — Tab 内的按钮
| `permission.py` | Unified RBAC models — replaces dvadmin Role/MenuButton/RoleMenuPermission | `IAMPermission` — Unique permission definition — replaces MenuButton<br>`IAMRole` — Unified role — replaces dvadmin Role, pure permission set<br>`IAMRolePermission` — Role-Permission binding — replaces RoleMenuButtonPermission<br>`IAMUserRole` — User-Role binding — replaces user.role M2M
| `project.py` | Project model — migrated from opsflow.models.project | `Project` — Ops workspace — the operational unit for workflow management<br>`ProjectMember` — Project membership — which users belong to which projects
| `rbac.py` | — | `PermissionRequest`<br>`UserDirectPermission`
| `role_template.py` | RoleTemplate — pre-configured Role + Menu/Button bindings for quick project setup. | `RoleTemplate`
| `tenant.py` | Tenant models — BusinessGroup, Business, DeployEnvironment | `BusinessGroup` — Optional visual grouping for businesses — no permission semantics<br>`Business` — Business line — the core isolation unit for all operational resources<br>`DeployEnvironment` — Deployment environment — globally defined, managed by Platform Admin
| `users.py` | — | `CustomUserManager`<br>`IAMUsers` — IAM 用户模型 — replaces dvadmin system.Users

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | —

## `sync/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Identity Sync Engine — department & user sync from LDAP/AD/SAML | —
| `backends.py` | LDAP/AD Bind authentication backend | `LDAPBackend` — LDAP/AD Bind 认证后端
| `differ.py` | Diff algorithms for identity sync — Dept tree diff and user list diff | `DeptNode` — A department node from the remote directory<br>`UserEntry` — A user entry from the remote directory<br>`DeptDiff` — Diff result for departments<br>`UserDiff` — Diff result for users<br>`Differ` — Pure diff logic — no DB queries, no I/O
| `jobs.py` | APScheduler job registration for identity sync | `register_sync_jobs()` — Register identity sync cron jobs for all enabled LDAP/AD instances
| `models.py` | — | `DeptMapping` — 部门映射：追踪 LDAP DN → 本地 Dept 的关联<br>`UserMapping` — 用户映射：追踪 LDAP/AD 用户 → 本地 Users 的关联
| `provider.py` | Identity sync provider — orchestrate full sync from LDAP/AD to local Dept & Users | `SyncStats` — Sync execution statistics<br>`SyncResult` — Result of a sync run<br>`BaseSyncProvider` — Abstract base for identity sync providers<br>`LDAPSyncProvider` — Sync provider for LDAP/AD directories
| `serializers.py` | Serializers for identity sync — sync trigger, status, mappings | `SyncTriggerSerializer` — 手动触发同步请求（无必填参数）<br>`SyncStatusSerializer` — 同步状态概览<br>`SyncResultSerializer` — 同步结果
| `urls.py` | URL configuration for iam sync module — /api/iam/sync/ | —
| `views.py` | Identity sync API views — sync trigger, status, SAML ACS | `trigger_sync()` — 手动触发指定连接器实例的全量同步<br>`sync_status()` — 返回所有启用的 LDAP/AD 连接器实例的同步概览<br>`test_connection()` — 测试 LDAP 连接器实例的连接<br>`sync_history()` — 获取指定实例的同步历史记录<br>`saml_login()` — SAML SP-initiated login — 生成 AuthnRequest 并重定向到 IdP

## `tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | — | —
| `test_backends.py` | LDAPBackend 认证后端测试 — mock LDAP 连接器实例 | `TestLDAPBackend` — LDAPBackend 认证后端测试
| `test_differ.py` | Differ 单元测试 — DeptDiff / UserDiff 算法 | `TestDeptDiff` — 部门树 Diff 算法测试<br>`TestUserDiff` — 用户列表 Diff 算法测试
| `test_my_permissions.py` | IAM my_permissions endpoint tests | `TestMyPermissions` — my_permissions endpoint — role resolution + page visibility
| `test_rbac.py` | IAM RBAC integration tests — 权限申请/审批/赋权 全链路 | `TestPermissionRequestModel` — PermissionRequest 模型测试<br>`TestRoleTemplate` — RoleTemplate 模型测试<br>`TestMyPermissionsAPI` — my_permissions API 端点测试
| `test_signals.py` | IAM signal handler tests — dvadmin Role auto-sync | `TestRoleSyncSignals` — BusinessMember/ProjectMember save/delete → dvadmin Role sync

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | IAM views package — RBAC + permission management views. | —
| `dept.py` | Department management views | `DeptSerializer` — 部门-序列化器<br>`DeptImportSerializer` — 部门-导入-序列化器<br>`DeptCreateUpdateSerializer` — 部门管理 创建/更新时的列化器<br>`DeptViewSet` — 部门管理接口
| `login.py` | — | `CaptchaView`<br>`LoginSerializer` — 登录的序列化器:<br>`LoginView` — 登录接口<br>`LoginTokenSerializer` — 登录的序列化器:<br>`LoginTokenView` — 登录获取token接口
| `menu.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/1 001 22:38
@Remark: 菜单模块 — using IAMMenu (migrated from dvadmi | `MenuSerializer`<br>`MenuCreateSerializer`<br>`WebRouterSerializer`<br>`MenuViewSet`
| `oauth.py` | OAuth2/SSO 登录视图
OAuth2/SSO Login Views | `OAuthLoginView` — OAuth2 登录入口 — 跳转到授权页面<br>`OAuthCallbackView` — OAuth2 回调处理 — 获取token并创建/绑定用户
| `permission_views.py` | IAM permission views — PermissionRequest, DirectPermission, Business, Project, etc. | `PermissionRequestViewSet`<br>`UserDirectPermissionViewSet`<br>`BusinessGroupViewSet` — BusinessGroup CRUD — superuser only<br>`BusinessViewSet` — Business CRUD + member management<br>`DeployEnvironmentViewSet` — DeployEnvironment CRUD + permission management — superuser for write
| `role.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 角色管理 — using IAMRole (new unified role mode | `RoleSerializer` — 角色-序列化器<br>`RoleCreateUpdateSerializer`<br>`RoleViewSet` — 角色管理接口
| `user.py` | — | `UserSerializer` — 用户管理-序列化器<br>`UserCreateSerializer` — 用户新增-序列化器<br>`UserUpdateSerializer` — 用户修改-序列化器<br>`UserInfoUpdateSerializer` — 用户修改-序列化器<br>`ExportUserProfileSerializer` — 用户导出 序列化器
