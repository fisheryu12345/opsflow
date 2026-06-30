# iam — Module Index / 模块索引

> Last auto-update: 2026-06-30 | Trigger commit: 80f9ed95

---

## Root

| File | Purpose / 用途 | Core Components / 核心组件 |
|------|----------------|---------------------------|
| `__init__.py` | — | — |
| `admin.py` | — | PermissionRequestAdmin — , UserDirectPermissionAdmin — , BusinessGroupAdmin —  |
| `apps.py` | IAM app config — multi-tenant infrastructure + RBAC permission management | IamConfig —  |
| `permissions.py` | DRF Permission Backends for multi-tenant access control. | TenantPermission — Unified multi-tenant permission check for all sub-product ViewSets., EnvironmentGatePermission — Environment gate for execution / ticket creation endpoints. |
| `resolvers.py` | Permission resolution functions for all sub-products. | get_visible_projects() — Return all project IDs visible to the user, get_visible_businesses() — Return all business IDs visible to the user, has_project_role() — Check if user has at least min_role on a project |
| `routers.py` | Tenant database router — physical isolation extension point. | TenantDatabaseRouter — Routes database operations based on Business.db_alias. |
| `serializers.py` | — | PermissionRequestSerializer — , PermissionRequestCreateSerializer — , PermissionRequestReviewSerializer —  |
| `signals.py` | Signal handlers — auto-sync dvadmin Roles when IAM membership roles change. | on_business_member_save() — , on_business_member_delete() — , on_project_member_save() —  |
| `urls.py` | — | — |
| `views.py` | — | search_users() — 搜索用户，返回 async_select 格式 {data: [{value: id, label: username}]}, my_permissions() — Return current user's ITSM permissions for a given project., PermissionRequestViewSet — , UserDirectPermissionViewSet — , BusinessGroupViewSet — BusinessGroup CRUD — superuser only |

## `management/`

| File | Purpose / 用途 | Core Components / 核心组件 |
|------|----------------|---------------------------|
| `__init__.py` | — | — |

## `management\commands/`

| File | Purpose / 用途 | Core Components / 核心组件 |
|------|----------------|---------------------------|
| `__init__.py` | — | — |
| `grant_default_env_permissions.py` | Grant dev + staging DeployEnvironmentPermission to all active users. | Command —  |
| `seed_deploy_environments.py` | Seed initial DeployEnvironment records: dev, staging, prod. | Command —  |
| `seed_itsm_permissions.py` | Seed ITSM permission keys — dvadmin Role + MenuButton + RoleMenuButtonPermission | Command —  |

## `models/`

| File | Purpose / 用途 | Core Components / 核心组件 |
|------|----------------|---------------------------|
| `__init__.py` | IAM app models — multi-tenant infrastructure + RBAC permission requests | — |
| `membership.py` | Membership models — BusinessMember, DeployEnvironmentPermission | BusinessMember — Business line membership — Admin/Editor roles cascade down to all Projects, DeployEnvironmentPermission — Explicit per-user execution permission for a deploy environment |
| `menu_rbac.py` | IAM RBAC models — Role / Menu / MenuButton / Permission bridges. | Role — 角色 (was dvadmin.system.models.Role), Menu — 菜单 — hierarchical navigation (was dvadmin.system.models.Menu), MenuField — 菜单字段 — column-level permission target |
| `project.py` | Project model — migrated from opsflow.models.project | Project — Ops workspace — the operational unit for workflow management, ProjectMember — Project membership — which users belong to which projects |
| `rbac.py` | — | PermissionRequest — , UserDirectPermission —  |
| `tenant.py` | Tenant models — BusinessGroup, Business, DeployEnvironment | BusinessGroup — Optional visual grouping for businesses — no permission semantics, Business — Business line — the core isolation unit for all operational resources, DeployEnvironment — Deployment environment — globally defined, managed by Platform Admin |
