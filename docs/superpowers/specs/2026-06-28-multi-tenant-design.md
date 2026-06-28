# 多租户模型设计 — 按业务/环境精细隔离 + 分级管理员

> **版本:** v1.0  
> **日期:** 2026-06-28  
> **关联文档:** [opsflow_target.md](../../opsflow_target.md)  
> **状态:** 设计完成，待评审

---

## 1. 设计目标与范围

为 OPSflow 平台引入多租户能力，支持按**业务线**和**部署环境**进行精细的数据与权限隔离，满足**分级管理员**需求，预留**物理隔离**架构扩展点。

**适用范围：** 单企业内部多部门使用（非 SaaS 多企业）。物理隔离作为架构扩展点预留，当前不实现。

---

## 2. 核心概念

### 2.1 隔离层级

```
[可选: BusinessGroup 分组容器]          ← 纯视觉分组，无权限含义
  └── Business (业务线)                ← 核心隔离单位，权限基座
       ├── Project (项目)              ← 运维工作空间，归属 iam
       ├── CMDB Resources              ← 资产归属 Business + DeployEnvironment
       └── ITSM Tickets                ← 工单归属 Business

DeployEnvironment (部署环境，全局横切维度)
  ├── Production  (risk_level=100)     ← 高危，需审批 + 显式授权
  ├── Staging     (risk_level=50)      ← 中危
  └── Development (risk_level=0)       ← 低危，默认授权
```

### 2.2 与现有体系的关系

| 现有概念 | 新概念 | 关系 |
|---------|--------|------|
| `dvadmin.system.Dept` (HR部门树) | `iam.Business` (IT业务线) | **完全独立，各管各的**。Dept 管后台界面权限，Business 管运维资源隔离 |
| `dvadmin.system.Role/Menu` (管理后台权限) | `iam.TenantPermission` (运维资源权限) | **长期并存**。dvadmin 管"谁能进哪个页面"，iam 管"谁能操作哪个业务线的资源" |
| `opsflow.OpsProject` | `iam.Project` | **迁入 iam**，从 opsflow 移除 |
| `opsflow.ProjectEnvironmentVariable` | `iam.DeployEnvironment` | **不同概念**。前者是 Pipeline 变量（key-value），后者是部署目标环境（dev/staging/prod） |

### 2.3 关键原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **两层半** | Business → Project 为核心层级，BusinessGroup 可选分组 |
| 2 | **环境全局横切** | 全公司共享同一套 dev/staging/prod 环境定义 |
| 3 | **CMDB 即锚点** | CMDB 资源是所有子产品的数据归属根 |
| 4 | **权限向下继承** | Business Admin 自动拥有下属所有 Project 的 Admin 等效权限 |
| 5 | **环境显式授权** | 环境操作权限不随任何层级继承，必须显式授予 |
| 6 | **跨成员灵活** | 一人可属于多个 Business，权限取并集 |
| 7 | **iam 即底座** | 所有租户/权限模型集中在 `iam` app，Project 从 opsflow 迁入 |
| 8 | **Dept与Business独立** | Dept（HR部门树）和 Business（IT业务线）互不映射，各管各的 |
| 9 | **dvadmin与iam并存** | dvadmin 管后台界面访问，iam 管运维资源操作，长期共存 |

---

## 3. 分级管理员

### 3.1 四级体系

```
Platform Admin     → 全局管控（创建 Business / 系统配置 / 环境定义）
                     映射到 Django is_superuser

Business Admin     → 管理本 Business（创建 Project / 管理业务成员）
                     自动继承下属所有 Project 的 Admin 等效权限

Project Admin      → 管理本 Project（管理项目成员 / 模板发布 / 调度）

Editor             → 日常操作（创建编辑模板 / 执行流程）

Viewer             → 只读（查看执行状态 / 审计日志 / 资源配置）
```

### 3.2 DeployEnvironment 权限（独立于管理员层级）

- 通过 `DeployEnvironmentPermission` 模型单独管理，不随任何角色继承
- 即使是 Platform Admin，也必须显式获得生产环境的 `can_execute` 才能执行
- 新成员默认自动获得 dev + staging 环境权限
- 生产环境权限需 Business Admin 手动授予

---

## 4. 数据模型

### 4.1 App 边界

```
iam app — 多租户权限基础设施（底座）
  ├── models/
  │   ├── tenant.py          # Business, BusinessGroup, DeployEnvironment
  │   ├── project.py         # Project (从 opsflow 迁入), ProjectMember
  │   └── membership.py      # BusinessMember, DeployEnvironmentPermission
  ├── resolvers.py           # 权限解析函数 (get_visible_* / has_*_role)
  ├── permissions.py         # DRF Permission Backend (TenantPermission / EnvironmentGatePermission)
  └── routers.py             # TenantDatabaseRouter (物理隔离扩展点，当前骨架)

opsflow app — 流程编辑器 + 流程执行器
  └── 不承载任何租户模型，通过 FK('iam.Project') 引用
  └── 权限过滤调用 iam.resolvers 和 iam.permissions

其他子产品 (itsm / monitor / cmdb / job_platform / integration / opsagent)
  └── 通过 FK 引用 iam.Business / iam.Project，同理调用 iam 权限层
```

### 4.2 iam 新增模型

```python
# ============== backend/iam/models/tenant.py ==============

class BusinessGroup(models.Model):
    """Optional visual grouping for businesses, no permission meaning"""
    name = models.CharField(max_length=128, unique=True)
    code = models.SlugField(max_length=32, unique=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'iam_business_group'


class Business(models.Model):
    """Business line — core isolation unit"""
    name = models.CharField(max_length=128, unique=True)
    code = models.SlugField(max_length=32, unique=True)
    group = models.ForeignKey(BusinessGroup, null=True, blank=True,
                               on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    db_alias = models.CharField(
        max_length=32, null=True, blank=True,
        help_text="Physical isolation extension point: Django DATABASES key. "
                  "Null means use 'default'."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'iam_business'


class DeployEnvironment(models.Model):
    """Deploy environment — globally defined, managed by Platform Admin"""
    name = models.CharField(max_length=64)              # Production / Staging / Development
    code = models.CharField(max_length=16, unique=True)  # prod / staging / dev
    risk_level = models.IntegerField(default=0)          # 0=dev, 50=staging, 100=prod
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'iam_deploy_environment'
```

```python
# ============== backend/iam/models/project.py ==============
# Migrated from opsflow/models/project.py

class Project(models.Model):
    """Project — ops workspace, migrated from opsflow.OpsProject"""
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255, blank=True)
    business = models.ForeignKey(
        Business, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='projects'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    max_schedule_plans = models.IntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'iam_project'


class ProjectMember(models.Model):
    """Project member — migrated from opsflow, role choices unchanged"""
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EDITOR = 'editor', 'Editor'
        VIEWER = 'viewer', 'Viewer'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EDITOR)
    joined_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'iam_project_member'
        unique_together = [('project', 'user')]
```

```python
# ============== backend/iam/models/membership.py ==============

class BusinessMember(models.Model):
    """Business member — Admin/Editor roles cascade down to all Projects"""
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EDITOR = 'editor', 'Editor'
        VIEWER = 'viewer', 'Viewer'

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EDITOR)
    joined_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'iam_business_member'
        unique_together = [('business', 'user')]


class DeployEnvironmentPermission(models.Model):
    """Deploy env execution permission — NOT inherited from any role level"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    environment = models.ForeignKey(DeployEnvironment, on_delete=models.CASCADE)
    can_execute = models.BooleanField(default=False)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='env_permissions_granted'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'iam_deploy_env_permission'
        unique_together = [('user', 'environment')]
```

### 4.3 opsflow 模型改动

**6 个模型 FK 指向 iam.Project：**

| 模型 | 文件 | 改动 |
|------|------|------|
| `FlowTemplate` | `opsflow/models/template.py` | `project` FK → `FK('iam.Project')` |
| `FlowExecution` | `opsflow/models/execution.py` | `project` FK → `FK('iam.Project')` |
| `ExecutionScheme` | `opsflow/models/execution.py` | `project` FK → `FK('iam.Project')` |
| `SchedulePlan` | `opsflow/models/schedule.py` | `project` FK → `FK('iam.Project')` |
| `OpsKnowledge` | `opsflow/models/knowledge.py` | `project` FK → `FK('iam.Project')` |
| `ProjectEnvironmentVariable` | `opsflow/models/env.py` | `project` FK → `FK('iam.Project')` |

**无需改动的：**
- `PluginMeta.allowed_projects` — JSON 数组存 project_id，ID 值不变
- `TemplateNode` / `ExecutionNode` 等 — 无直接 Project FK
- `FlowTemplate.is_public` / `project_scope` — 逻辑保留，project_id 不变

**改名：** `opsflow.ProjectEnvironmentVariable` 保持原名不变（它是 Pipeline 变量，与 iam.DeployEnvironment 是不同概念）。

### 4.4 审计与 API Token 增强

```python
# backend/opsflow/models/audit.py — OperationRecord 新增字段

class OperationRecord(models.Model):
    # ... 现有字段不变 ...
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business'
    )  # 新增 — 冗余，用于 Business Admin 可见性过滤
    project = models.ForeignKey(
        'iam.Project', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Project'
    )  # 新增 — 冗余，用于 Project Admin 可见性过滤
```

```python
# backend/opsflow/models/auth.py — ApiToken 新增绑定

class ApiToken(models.Model):
    # ... 现有字段不变 ...
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business'
    )  # 新增 — 限定此 Token 可操作的 Business
    environment = models.ForeignKey(
        'iam.DeployEnvironment', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Deploy Environment'
    )  # 新增 — 限定此 Token 可操作的环境
    # allowed_actions 保持不变，描述具体的操作类型列表
```

### 4.5 Public Template 可见范围

当前 `FlowTemplate.is_public=True` 且 `project_scope` 支持 `"*"`（全平台可见）。新模型下：

- **Platform-public（`"*"`）**: 废弃，不再支持
- **Business-public**: 同 Business 内所有 Project 可见，通过 `project_scope` 存 project_id 列表实现
- `project_scope` 存的是 project_id，Project 迁到 iam 后 ID 不变，**不受影响**

### 4.6 非模型文件改动（~10 个）

需更新 import 路径的文件：`opsflow/views/base.py`、`project_views.py`、`template_views.py`、`execution_views.py`、`schedule_views.py`、`opsflow/serializers.py`、`opsflow/apps.py`、`opsflow/models/__init__.py`、`common/management/commands/seed_reference.py`、`common/management/commands/add_mock_data.py`。

---

## 5. 权限解析逻辑

### 5.1 三层叠加模型

```
最终权限 = 角色权限(Membership Level) × 数据可见范围(Data Scope) × 环境门禁(Env Gate)
```

### 5.2 数据可见范围

```python
# backend/iam/resolvers.py

ROLE_ORDER = {'viewer': 0, 'editor': 1, 'admin': 2}


def get_visible_projects(user) -> set[int]:
    """Return all project IDs visible to the user"""
    if user.is_superuser:
        return set(Project.objects.values_list('id', flat=True))

    direct = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    biz_ids = BusinessMember.objects.filter(user=user).values_list('business_id', flat=True)
    biz_projects = Project.objects.filter(business_id__in=biz_ids).values_list('id', flat=True)
    return set(direct) | set(biz_projects)


def get_visible_businesses(user) -> set[int]:
    """Return all business IDs visible to the user"""
    if user.is_superuser:
        return set(Business.objects.values_list('id', flat=True))
    return set(BusinessMember.objects.filter(user=user).values_list('business_id', flat=True))


def has_project_role(user, project_id, min_role='editor') -> bool:
    """Check if user has at least min_role on a project (includes Business inheritance)"""
    if user.is_superuser:
        return True

    min_level = ROLE_ORDER[min_role]

    pm = ProjectMember.objects.filter(project_id=project_id, user=user).first()
    if pm and ROLE_ORDER.get(pm.role, -1) >= min_level:
        return True

    try:
        project = Project.objects.get(id=project_id)
        if project.business_id:
            bm = BusinessMember.objects.filter(
                business_id=project.business_id, user=user
            ).first()
            if bm and ROLE_ORDER.get(bm.role, -1) >= min_level:
                return True
    except Project.DoesNotExist:
        pass

    return False


def get_visible_operation_records(user):
    """Business Admin sees records of their businesses; superuser sees all"""
    if user.is_superuser:
        return OperationRecord.objects.all()
    biz_ids = get_visible_businesses(user)
    return OperationRecord.objects.filter(business_id__in=biz_ids)
```

### 5.3 环境门禁

```python
def can_execute_in_environment(user, environment_id, project_id) -> bool:
    """Check if user can execute in given env on given project"""
    if not DeployEnvironmentPermission.objects.filter(
        user=user, environment_id=environment_id, can_execute=True
    ).exists():
        return False

    env = DeployEnvironment.objects.get(id=environment_id)
    if env.risk_level >= 100:
        if not has_project_role(user, project_id, min_role='editor'):
            return False

    return True
```

### 5.4 DRF Permission Backend

```python
# backend/iam/permissions.py

class TenantPermission(BasePermission):
    """Unified multi-tenant permission for all sub-product ViewSets"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            return has_project_role(request.user, obj.project_id, min_role='editor')
        return True


class EnvironmentGatePermission(BasePermission):
    """Environment gate for execution / ticket creation endpoints"""

    def has_permission(self, request, view):
        env_id = request.data.get('environment_id')
        project_id = request.data.get('project_id')
        if env_id and project_id:
            return can_execute_in_environment(request.user, int(env_id), int(project_id))
        return True
```

---

## 6. 跨子产品隔离

### 6.1 CMDB — 数据锚点

```python
class CmdbResource(models.Model):
    name = models.CharField(max_length=256)
    resource_type = models.CharField(max_length=64)  # server/network/storage/app/process
    scope_type = models.CharField(
        choices=[('business', 'Single Business'), ('shared', 'Cross-Business Shared')],
        default='business'
    )
    business = models.ForeignKey('iam.Business', null=True, on_delete=models.PROTECT)
    shared_businesses = models.ManyToManyField('iam.Business', blank=True)
    environment = models.ForeignKey('iam.DeployEnvironment', on_delete=models.PROTECT)
    properties = models.JSONField(default=dict)
```

### 6.2 OpsFlow — 执行校验链

```
Pipeline Execution Request
  → has_project_role(user, project_id, 'editor')
  → can_execute_in_environment(user, environment_id, project_id)
  → for each CMDB target host:
      host.business_id in get_visible_businesses(user)
      host.environment_id == environment_id
  → Execute
```

### 6.3 ITSM — Business 级工单

```python
class ItsmTicket(models.Model):
    business = models.ForeignKey('iam.Business', on_delete=models.PROTECT)
    environment = models.ForeignKey('iam.DeployEnvironment', on_delete=models.PROTECT)
    affected_resources = models.ManyToManyField(CmdbResource)
    approval_chain = models.JSONField(default=dict)
```

### 6.4 Monitor — 继承 CMDB 归属

```python
class MonitorAlert(models.Model):
    source_resource = models.ForeignKey(CmdbResource, on_delete=models.CASCADE)
    business = models.ForeignKey('iam.Business', on_delete=models.CASCADE)
    environment = models.ForeignKey('iam.DeployEnvironment', on_delete=models.CASCADE)
    # business + environment auto-inherited from source_resource

class SelfHealingStrategy(models.Model):
    business = models.ForeignKey('iam.Business', on_delete=models.CASCADE)
    opsflow_template = models.ForeignKey('opsflow.FlowTemplate', on_delete=models.PROTECT)
    target_environment = models.ForeignKey('iam.DeployEnvironment', on_delete=models.PROTECT)
```

### 6.5 Job Platform — 双层约束

```python
class JobScript(models.Model):
    project = models.ForeignKey('iam.Project', on_delete=models.CASCADE)
    business = models.ForeignKey('iam.Business', on_delete=models.CASCADE)
    allowed_environments = models.ManyToManyField('iam.DeployEnvironment')

class JobExecution(models.Model):
    script = models.ForeignKey(JobScript, on_delete=models.CASCADE)
    target_hosts = models.ManyToManyField(CmdbResource)
    environment = models.ForeignKey('iam.DeployEnvironment', on_delete=models.PROTECT)
```

### 6.6 Integration Hub — 连接器作用域

```python
class Connector(models.Model):
    scope_type = models.CharField(
        choices=[('business', 'Business Level'), ('project', 'Project Level')],
        default='business'
    )
    business = models.ForeignKey('iam.Business', null=True, blank=True, on_delete=models.CASCADE)
    project = models.ForeignKey('iam.Project', null=True, blank=True, on_delete=models.CASCADE)
```

### 6.7 OpsAgent — 权限投影

AI 不额外授权。每个 ToolCall 在执行前调用对应子产品的 Permission Backend。Operator 权限即 AI 权限上限。

### 6.8 归属矩阵汇总

| 子产品 | 数据归属 | 操作边界 | 环境约束 |
|--------|---------|---------|---------|
| CMDB | Business + DeployEnvironment + scope_type | 资源 CRUD | 环境标签区分 |
| OpsFlow | Project (→Business) | 模板/执行 | Environment Gate |
| ITSM | Business | 工单/变更/审批 | 变更环境 + 审批门禁 |
| Monitor | 继承 CMDB 资源的 Business+Env | 告警/自愈策略 | 告警源 → 自愈执行 |
| Job Platform | Project + CMDB Host | 脚本分发/执行 | Host env × 操作者 env |
| Integration Hub | Business/Project 级连接器 | 连接器/凭据 CRUD | 无 |
| OpsAgent | 用户 × 上述各维度投影 | 自然语言操作 | 继承被操作对象的约束 |

---

## 7. i18n 约定

- **前端** Phase 5 创建 `web/src/i18n/pages/iam/en.ts` 和 `zh-cn.ts`，所有 Vue 模板使用 `$t()`，禁止硬编码中文
- **后端** 模型 verbose_name 英文、TextChoices label 用英文 key、API 错误消息英文，前端 i18n 字典映射为中文展示
- **禁止** 前端硬编码中文、模型 choices 中文 label、API msg 中文

---

## 8. 渐进迁移路径

### Phase 1: 数据底座搭建 + Project 迁入（1-2 周）

- 新建 `backend/iam/` 完整目录结构
- 新增 `Business`, `BusinessGroup`, `DeployEnvironment`, `BusinessMember`, `DeployEnvironmentPermission` 模型
- `OpsProject` → `iam.Project` 数据迁移
- `ProjectMember` → `iam.ProjectMember` 数据迁移
- opsflow 内 6 个模型 FK 改为 `FK('iam.Project')`
- ~10 个文件 import 路径更新
- `OperationRecord` 新增 `business_id` + `project_id` 字段
- `ApiToken` 新增 `business_id` + `environment_id` 字段
- `DeployEnvironment` 种子数据: prod / staging / dev

**验收：** `business=null` 时行为完全不变，零破坏。

### Phase 2: iam 权限层接管 OpsFlow（1 周）

- `ProjectFilteredViewSet` 调用 `iam.resolvers`
- ViewSet `permission_classes` 加入 `[TenantPermission]`
- `ProjectMember.role` / `BusinessMember.role` 首次在 views 强制校验
- 移除分散的内联权限检查

**验收：** viewer 角色限制生效，现有功能不变。

### Phase 3: 环境门禁生效（1 周）

- 现有用户自动获得 dev + staging 的 `can_execute`
- prod 权限需手动授予
- `FlowExecution` 新增 `environment` FK
- 执行 API 强制校验 `EnvironmentGatePermission`
- `ApiToken` 也受 Environment Gate 约束

**验收：** 无 prod 权限的用户被拒绝。

### Phase 4: 扩展到其他子产品（2-3 周，独立 PR）

4a CMDB → 4b ITSM → 4c Monitor → 4d Job Platform → 4e Integration Hub → 4f OpsAgent

### Phase 5: 管理界面 + 扩展点（1-2 周）

```
web/src/views/apps/iam/
├── BusinessManage.vue / EnvironmentManage.vue / BusinessGroupManage.vue
└── components/ (MemberRoleEditor.vue / EnvironmentGate.vue)

web/src/i18n/pages/iam/
├── en.ts / zh-cn.ts
```

---

## 9. 关键场景权限路径

| 场景 | 校验链 |
|------|--------|
| 执行部署到生产环境 | Project role ≥ editor → Env Gate (prod) → CMDB 主机可见 → 执行 |
| 告警自动触发自愈 | Alert(business+env) → Strategy → OpsFlow → Env Gate |
| ITSM 审批后变更实施 | Ticket(business,env) → 审批通过 → OpsFlow → project.business == ticket.business → Env Gate |
| AI 操作生产资源 | OpsAgent → ToolCall → 复用对应子产品 Permission Backend |
| 跨业务批量作业 | 操作者 A-Editor + B-Viewer → B 业务主机被过滤 |
| 外部 API Token 触发执行 | Token.business 范围 + Token.environment 匹配 + allowed_actions 校验 |
| Business Admin 查看审计 | get_visible_operation_records(user) → 过滤到所属 business |

---

## 10. 设计决策记录

| # | 决策 | 选择 | 理由 |
|---|------|------|------|
| 1 | 层级深度 | Business → Project 两级 + Group 可选 | 单企业内部三级过深 |
| 2 | 环境归属 | 全局定义，不挂 Business | 同一套 dev/staging/prod 全公司通用 |
| 3 | 上级递延 | Business Admin → 下属所有 Project Admin | 否则管理员看不到自己创建的项目 |
| 4 | 环境继承 | 不继承，显式授权 | 生产环境操作权不能因职位自动获得 |
| 5 | CMDB 归属 | single + shared 两种模式 | 基础设施跨业务共享是常态 |
| 6 | 跨业务成员 | 允许，权限取并集 | IT 运维跨业务负责是常态 |
| 7 | Project 归属 | 从 opsflow 迁入 iam | 避免所有子产品依赖 opsflow 仅为 FK |
| 8 | 新模型归属 | 全部放入 iam | 租户是基础设施，不应与流程引擎耦合 |
| 9 | 迁移策略 | 五阶段渐进 | 不破坏现有功能，可验证 |
| 10 | 物理隔离 | 预留扩展点，不实现 | 当前不需要，架构上做准备 |
| 11 | Dept vs Business | 完全独立，不映射 | HR 组织和 IT 边界本就不一一对应 |
| 12 | dvadmin vs iam | 长期并存 | dvadmin 管后台界面，iam 管运维资源，边界清晰 |
| 13 | Public Template | Business-public，废弃 `*` | 跨业务线公开模板泄露运维细节 |
| 14 | ApiToken | 绑定 Business + Environment | 细粒度控制外部 API 的资源和环境范围 |
| 15 | OperationRecord | 新增 business_id + project_id | Business Admin 只看自己业务线的审计记录 |
| 16 | 命名冲突 | iam.Environment → DeployEnvironment | 与 opsflow.ProjectEnvironmentVariable 区分 |
| 17 | i18n | 前端 iam 页面 i18n-first，后端英文+双语注释 | 与项目规范一致，避免后续整改 |
