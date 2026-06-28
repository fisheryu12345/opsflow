# 多租户架构实现

> 提交: 64fcc336 | 日期: 2026-06-28
> 涉及 App: iam (主), opsflow, cmdb, itsm, monitor, job_platform, integration, opsagent
> 类型: 功能新增

---

## 背景

OPSflow 平台需要支持企业内部多部门（业务线）的精细数据与权限隔离。原有系统仅有 `OpsProject` 级别的隔离，无法满足：
- 按业务线组织项目
- 按部署环境（dev/staging/prod）控制操作权限
- 分级管理员（Platform → Business → Project）
- 跨子产品（CMDB/ITSM/Monitor 等）的统一权限

## 实现方案

### 核心架构

```
iam app (底座) → 所有子产品统一依赖
  ├── Business (业务线) — 隔离基座
  ├── DeployEnvironment (部署环境) — 全局横切
  ├── Project (项目) — 从 opsflow 迁入
  ├── BusinessMember — 业务线角色，向下继承到 Project
  ├── DeployEnvironmentPermission — 环境操作显式授权
  ├── resolvers.py — 权限解析（数据可见范围 + 角色判断 + 环境门禁）
  └── permissions.py — DRF Permission Backend

opsflow app (消费者)
  └── 6 模型 FK('iam.Project')，TenantPermission + EnvironmentGatePermission

其他子产品 (cmdb/itsm/monitor/job_platform/integration/opsagent)
  └── 核心模型添加 Business FK
```

### 权限解析三层叠加

```
最终权限 = 角色权限 × 数据可见范围 × 环境门禁
```

**角色权限** (TenantPermission)：Business Admin 自动继承下属所有 Project 的 Admin 等效权限。

**数据可见范围** (resolvers.py)：`get_visible_projects(user)` 合并直接 ProjectMember + BusinessMember 间接权限。

**环境门禁** (EnvironmentGatePermission)：即使 Platform Admin 也需要显式授予生产环境执行权限。

### 关键代码

```python
# backend/iam/resolvers.py — 核心权限解析

def get_visible_projects(user) -> set[int]:
    """User's visible project IDs (direct + Business inheritance)"""
    if user.is_superuser:
        return set(Project.objects.values_list('id', flat=True))
    direct = set(ProjectMember.objects.filter(user=user).values_list('project_id', flat=True))
    biz_ids = BusinessMember.objects.filter(user=user).values_list('business_id', flat=True)
    biz_projects = set(Project.objects.filter(business_id__in=biz_ids).values_list('id', flat=True))
    return direct | biz_projects

def has_project_role(user, project_id, min_role='editor') -> bool:
    """Check role (direct ProjectMember or inherited BusinessMember)"""

def can_execute_in_environment(user, environment_id, project_id=None) -> bool:
    """Explicit env permission + high-risk gate for prod"""
```

```python
# backend/iam/permissions.py — DRF 权限后端

class TenantPermission(BasePermission):
    """Write ops require editor+ role on object's project"""

class EnvironmentGatePermission(BasePermission):
    """Execution requires explicit environment can_execute"""
```

### 数据流

```
User → API Request
  → IsAuthenticated
  → TenantPermission → has_project_role(user, project_id, 'editor')
  → EnvironmentGatePermission → can_execute_in_environment(user, env_id, project_id)
  → ProjectFilteredViewSet → get_visible_projects(user) → queryset filter
  → Business Logic
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Project 归属 | 从 opsflow 迁入 iam | 避免所有子产品依赖 opsflow 仅为一个 FK |
| 环境权限 | 不随角色继承，显式授权 | 生产环境操作权不能因职位自动获得 |
| 层级深度 | Business → Project 两级 | 单企业内部三级过深 |
| Public Template | Business-public，废弃 `*` | 跨业务线公开模板泄露运维细节 |
| Dept vs Business | 完全独立 | HR 组织树和 IT 业务线边界不同 |
| dvadmin vs iam | 长期并存 | dvadmin 管后台界面，iam 管运维资源 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/models/tenant.py` | Business/BusinessGroup/DeployEnvironment 模型定义 |
| `backend/iam/models/project.py` | Project/ProjectMember，从 opsflow 迁入 |
| `backend/iam/models/membership.py` | BusinessMember/DeployEnvironmentPermission |
| `backend/iam/resolvers.py` | 权限解析函数，Business 角色继承逻辑 |
| `backend/iam/permissions.py` | TenantPermission/EnvironmentGatePermission Backend |
| `backend/iam/views.py` | BusinessViewSet/DeployEnvironmentViewSet API |
| `backend/iam/routers.py` | TenantDatabaseRouter 物理隔离扩展点 |
| `backend/opsflow/views/base.py:16-92` | ProjectFilteredViewSet 重构为 iam.resolvers |
| `backend/opsflow/views/execution_views.py:33` | EnvironmentGatePermission 接入 |
| `docs/superpowers/specs/2026-06-28-multi-tenant-design.md` | 完整设计规范 |

## 使用方式

### 初始化

```bash
# 1. 创建默认环境
python manage.py seed_deploy_environments

# 2. 为现有用户批量授权 dev+staging
python manage.py grant_default_env_permissions
```

### 日常使用流程

1. **Platform Admin** 登录 → IAM 管理 → 创建 Business（业务线）
2. **Platform Admin** → 为 Business 分配 Business Admin 成员
3. **Business Admin** → 创建 Project，指定归属 Business
4. **Platform Admin** → 环境管理 → 为关键用户授权 prod 环境
5. **普通用户** → 日常运维操作，权限自动按 Business+Project+Environment 三层叠加校验

### API 端点

```
/api/iam/businesses/          — Business CRUD + 成员管理
/api/iam/environments/        — DeployEnvironment CRUD + 权限管理
/api/iam/business-groups/     — BusinessGroup CRUD
/api/iam/projects/            — 从 iam 侧管理 Project
```

### 关联文档

- 设计规范: [2026-06-28-multi-tenant-design.md](../../superpowers/specs/2026-06-28-multi-tenant-design.md)
