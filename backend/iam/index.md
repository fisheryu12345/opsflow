# iam - Module Index

> Auto-updated: 2026-06-28 | Trigger commit: 64fcc336

## `./`

| File | Purpose | Key Components |
|------|---------|----------------|
| `__init__.py` |  | - |
| `admin.py` |  | PermissionRequestAdmin; UserDirectPermissionAdmin; BusinessGroupAdmin |
| `apps.py` | IAM app config — multi-tenant infrastructure + RBAC permission management | IamConfig |
| `permissions.py` | DRF Permission Backends for multi-tenant access control. | TenantPermission - Unified multi-tenant permission check for all sub-product ViewSets.; EnvironmentGatePermission - Environment gate for execution / ticket creation endpoints. |
| `resolvers.py` | Permission resolution functions for all sub-products. | get_visible_projects() - Return all project IDs visible to the user; get_visible_businesses() - Return all business IDs visible to the user; has_project_role() - Check if user has at least min_role on |
| `routers.py` | Tenant database router — physical isolation extension point. | TenantDatabaseRouter - Routes database operations based on Business.db_alias. |
| `serializers.py` |  | PermissionRequestSerializer; PermissionRequestCreateSerializer; PermissionRequestReviewSerializer |
| `urls.py` |  | - |
| `views.py` |  | PermissionRequestViewSet; UserDirectPermissionViewSet; BusinessGroupViewSet - BusinessGroup CRUD — superuser only |

## `management/`

| File | Purpose | Key Components |
|------|---------|----------------|
| `management/__init__.py` |  | - |

## `management\commands/`

| File | Purpose | Key Components |
|------|---------|----------------|
| `management/commands/__init__.py` |  | - |
| `management/commands/grant_default_env_permissions.py` | Grant dev + staging DeployEnvironmentPermission to all active users. | Command |
| `management/commands/seed_deploy_environments.py` | Seed initial DeployEnvironment records: dev, staging, prod. | Command |

## `models/`

| File | Purpose | Key Components |
|------|---------|----------------|
| `models/__init__.py` | IAM app models — multi-tenant infrastructure + RBAC permission requests | - |
| `models/membership.py` | Membership models — BusinessMember, DeployEnvironmentPermission | BusinessMember - Business line membership — Admin/Editor roles cascade down to all Projects; DeployEnvironmentPermission - Explicit per-user execution permission for a deploy environment |
| `models/project.py` | Project model — migrated from opsflow.models.project | Project - Ops workspace — the operational unit for workflow management; ProjectMember - Project membership — which users belong to which projects |
| `models/rbac.py` |  | PermissionRequest; UserDirectPermission |
| `models/tenant.py` | Tenant models — BusinessGroup, Business, DeployEnvironment | BusinessGroup - Optional visual grouping for businesses — no permission semantics; Business - Business line — the core isolation unit for all operational resources; DeployEnvironment - Deployment envi |
