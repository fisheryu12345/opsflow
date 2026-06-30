# IAM — 模块索引

> 上次自动更新: 2026-06-30 | 触发提交: 4f73a692

---

## `/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `admin.py` | - | `PermissionRequestAdmin`, `UserDirectPermissionAdmin`, `BusinessGroupAdmin`, `BusinessAdmin` |
| `apps.py` | IAM app config — multi-tenant infrastructure + RBAC permission management | `IamConfig` |
| `permissions.py` | DRF Permission Backends for multi-tenant access control. | `Unified multi-tenant permission check for all sub-product ViewSets.`, `Environment gate for execution / ticket creation endpoints.` |
| `resolvers.py` | Permission resolution functions for all sub-products. | `Return all project IDs visible to the user()`, `Return all business IDs visible to the user()`, `Check if user has at least min_role on a project()`, `Check if user has at least min_role in a business()` |
| `routers.py` | Tenant database router — physical isolation extension point. | `Routes database operations based on Business.db_alias.` |
| `serializers.py` | - | `PermissionRequestSerializer`, `PermissionRequestCreateSerializer`, `PermissionRequestReviewSerializer`, `UserDirectPermissionSerializer` |
| `signals.py` | Signal handlers — auto-sync dvadmin Roles when IAM membership roles change. | `on_business_member_save()()`, `on_business_member_delete()()`, `on_project_member_save()()`, `on_project_member_delete()()` |
| `urls.py` | - | - |

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/__init__.py` | - | - |

## `management/commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/commands/__init__.py` | - | - |
| `management/commands/grant_default_env_permissions.py` | Grant dev + staging DeployEnvironmentPermission to all active users. | `Command` |
| `management/commands/init_iam.py` | Comprehensive IAM initialization — replaces dvadmin `python manage.py init`. | `Command` |
| `management/commands/seed_deploy_environments.py` | Seed initial DeployEnvironment records: dev, staging, prod. | `Command` |
| `management/commands/seed_iam_permissions.py` | Seed complete IAM RBAC — all app MenuButtons + Roles + RoleTemplates. | `Command` |
| `management/commands/seed_itsm_permissions.py` | Seed ITSM permission keys — dvadmin Role + MenuButton + RoleMenuButtonPermission | `Command` |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models/__init__.py` | IAM app models — multi-tenant infrastructure + RBAC permission requests | - |
| `models/membership.py` | Membership models — BusinessMember, DeployEnvironmentPermission | `Business line membership`, `Explicit per-user execution permission for a deploy environment` |
| `models/menu_rbac.py` | IAM RBAC models — Role / Menu / MenuButton / Permission bridges. | `角色 (was dvadmin.system.models.Role)`, `菜单`, `菜单字段`, `字段权限` |
| `models/project.py` | Project model — migrated from opsflow.models.project | `Ops workspace`, `Project membership` |
| `models/rbac.py` | - | `PermissionRequest`, `UserDirectPermission` |
| `models/role_template.py` | RoleTemplate — pre-configured Role + Menu/Button bindings for quick project setup. | `RoleTemplate` |
| `models/tenant.py` | Tenant models — BusinessGroup, Business, DeployEnvironment | `Optional visual grouping for businesses`, `Business line`, `Deployment environment` |

## `sync/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `sync/__init__.py` | Identity Sync Engine — department & user sync from LDAP/AD/SAML | - |
| `sync/backends.py` | LDAP/AD Bind authentication backend | `LDAP/AD Bind 认证后端` |
| `sync/differ.py` | Diff algorithms for identity sync — Dept tree diff and user list diff | `A department node from the remote directory`, `A user entry from the remote directory`, `Diff result for departments`, `Diff result for users` |
| `sync/jobs.py` | APScheduler job registration for identity sync | `Register identity sync cron jobs for all enabled LDAP/AD instances()` |
| `sync/models.py` | Mapping models for identity sync engine | `部门映射：追踪 LDAP DN → 本地 Dept 的关联`, `用户映射：追踪 LDAP/AD 用户 → 本地 Users 的关联` |
| `sync/provider.py` | Identity sync provider — orchestrate full sync from LDAP/AD to local Dept & Users | `Sync execution statistics`, `Result of a sync run`, `Abstract base for identity sync providers`, `Sync provider for LDAP/AD directories` |
| `sync/serializers.py` | Serializers for identity sync — sync trigger, status, mappings | `手动触发同步请求（无必填参数）`, `同步状态概览`, `同步结果` |
| `sync/urls.py` | URL configuration for iam sync module — /api/iam/sync/ | - |
| `sync/views.py` | Identity sync API views — sync trigger, status, SAML ACS | `手动触发指定连接器实例的全量同步()`, `返回所有启用的 LDAP/AD 连接器实例的同步概览()`, `测试 LDAP 连接器实例的连接()`, `获取指定实例的同步历史记录()` |

## `tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `tests/__init__.py` | - | - |
| `tests/test_my_permissions.py` | IAM my_permissions endpoint tests | `my_permissions endpoint` |
| `tests/test_rbac.py` | IAM RBAC integration tests — 权限申请/审批/赋权 全链路 | `PermissionRequest 模型测试`, `RoleTemplate 模型测试`, `my_permissions API 端点测试` |
| `tests/test_signals.py` | IAM signal handler tests — dvadmin Role auto-sync | `BusinessMember/ProjectMember save/delete → dvadmin Role sync` |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views/__init__.py` | IAM views package — RBAC + permission management views. | - |
| `views/menu.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/1 001 22:38
@Remark: 菜单模块 — migrated from dvadmin.system.views  | `菜单表的简单序列化器`, `菜单表的创建序列化器`, `前端菜单路由的简单序列化器`, `菜单管理接口` |
| `views/menu_button.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 菜单按钮管理 — migrated from dvadmin.system.views | `菜单按钮-序列化器`, `初始化菜单按钮-序列化器`, `菜单按钮接口` |
| `views/menu_field.py` | 菜单列权限 — migrated from dvadmin.system.views to iam.views | `列权限序列化器`, `列权限视图集` |
| `views/permission_views.py` | IAM permission views — PermissionRequest, DirectPermission, Business, Project, etc. | `PermissionRequestViewSet`, `UserDirectPermissionViewSet`, `BusinessGroup CRUD`, `Business CRUD + member management` |
| `views/role.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 角色管理 — migrated from dvadmin.system.views t | `角色-序列化器`, `角色管理 创建/更新时的列化器`, `菜单的按钮权限`, `菜单和按钮权限` |
| `views/role_menu.py` | 角色-菜单权限管理 — migrated from dvadmin.system.views to iam.views | `菜单按钮-序列化器`, `初始化菜单按钮-序列化器`, `初始化菜单按钮-序列化器`, `菜单按钮接口` |
| `views/role_menu_button_permission.py` | @author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 角色菜单按钮权限管理 — migrated from dvadmin.system.v | `菜单按钮-序列化器`, `初始化菜单按钮-序列化器`, `角色按钮权限`, `RoleFieldPermissionSerializer` |
