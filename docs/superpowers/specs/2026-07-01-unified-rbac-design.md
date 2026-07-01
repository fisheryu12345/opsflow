# 统一 RBAC 权限模型设计

> 日期: 2026-07-01 | 状态: 草案
> 目标: 企业级 RBAC，完全去除 dvadmin 旧权限体系，统一用 IAM
> 覆盖: IAM / OpsFlow / CMDB / ITSM / Monitor / 集成中心

---

## 一、设计目标

1. **一套权限模型**覆盖所有子产品，不再每个 app 各自写权限匹配
2. **彻底去掉 dvadmin 旧权限体系**：`CustomPermission`、`RoleMenuPermission`、`RoleMenuButtonPermission`、信号桥
3. **平台级 vs 项目级**权限分开管理 — 系统管理页面走平台角色，子产品内走项目角色
4. **OpsFlow 项目隔离保持不变** — `ProjectMember` + `ProjectFilteredViewSet` + `TenantPermission` 不动
5. **前端的 v-can / permissionStore 适配新模型**，不需要大改

---

## 二、数据模型

### 2.1 IAMPermission — 唯一权限定义

取代旧的 `MenuButton`。每个 codename 代表一个原子权限。

```python
class IAMPermission(models.Model):
    codename = models.CharField(unique=True, max_length=128)
    label = models.CharField(max_length=128)
    app = models.CharField(max_length=64)         # "system", "opsflow", "itsm", "cmdb"
    scope = models.CharField(max_length=8, choices=[
        ('platform', '平台级'),   # 系统管理，与项目无关
        ('project', '项目级'),    # 子产品，需要搭配项目角色
    ])
```

### 2.2 IAMRole — 唯一角色

取代旧的 `Role`（dvadmin）。不再有 Menu/API 匹配语义，纯权限集合。

```python
class IAMRole(models.Model):
    name = models.CharField(max_length=64)
    key = models.CharField(unique=True, max_length=64)   # "sysadmin", "opsflow_editor"
    is_system = models.BooleanField(default=False)       # 系统预置不可删除
```

### 2.3 IAMRolePermission — 角色-权限关联

取代 `RoleMenuButtonPermission`。附带的 `min_project_role` 字段用于 project 作用域的权限。

```python
class IAMRolePermission(models.Model):
    role = models.ForeignKey(IAMRole)
    permission = models.ForeignKey(IAMPermission)
    min_project_role = models.CharField(
        max_length=16, null=True, blank=True,
        choices=[('viewer','viewer'), ('editor','editor'), ('admin','admin')],
        help_text="仅 project 作用域有效。用户在该项目中的角色 >= 此值才有权限。"
    )
```

### 2.4 IAMUserRole — 用户-角色关联

取代 `user.role` M2M。用户通过这个表关联到 IAMRole。

```python
class IAMUserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.ForeignKey(IAMRole)
    class Meta:
        unique_together = ('user', 'role')
```

### 2.5 UserDirectPermission — 用户直接授权（保留）

改为关联 `IAMPermission`，不再关联 `Menu` 和 `MenuButton`。

```python
class UserDirectPermission(models.Model):
    user = models.ForeignKey(Users)
    permission = models.ForeignKey(IAMPermission, null=True)
    granted_by = models.ForeignKey(Users, null=True)
    granted_at = models.DateTimeField(auto_now_add=True)
```

### 2.6 PermissionRequest — 权限申请流程（更新 FK）

FK 指向新模型：

```python
class PermissionRequest(models.Model):
    user = models.ForeignKey(Users)
    request_type = models.CharField(choices=[...])
    target_role = models.ForeignKey(IAMRole, null=True)
    target_permission = models.CharField(max_length=128)      # codename 字符串
    target_project = models.ForeignKey(Project, null=True)
    target_project_role = models.CharField(max_length=16, null=True)
    status = models.CharField(choices=['pending','approved','rejected'])
    reason = models.TextField()
    reviewer = models.ForeignKey(Users, null=True, related_name='+')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True)
```

### 2.7 Menu — 导航菜单（精简）

去掉权限语义，只保留纯导航结构。去掉 `is_catalog`、`status` 字段和 `MenuButton` 关联。

```python
class Menu(models.Model):
    parent = models.ForeignKey('self', null=True, on_delete=CASCADE, db_constraint=False)
    app = models.CharField(max_length=64)         # 关联 IAMPermission.app
    icon = models.CharField(max_length=64, null=True)
    name = models.CharField(max_length=64)
    name_en = models.CharField(max_length=128, null=True)
    sort = models.IntegerField(default=1)
    web_path = models.CharField(max_length=128)
    component = models.CharField(max_length=128)
    component_name = models.CharField(max_length=50)
    visible = models.BooleanField(default=True)
    cache = models.BooleanField(default=False)
    is_iframe = models.BooleanField(default=False)
    is_affix = models.BooleanField(default=False)
    is_link = models.BooleanField(default=False)
    link_url = models.CharField(max_length=255, null=True)
```

### 2.8 默认角色

所有用户创建后自动分配一个默认 `IAMRole`（如 `key='authenticated'`）。该角色包含基础的必要权限，使用户能够登录并看到仪表盘、个人设置等基础页面。

```python
# seed 数据
IAMRole.objects.get_or_create(key='authenticated', defaults={
    'name': 'Authenticated User',
    'is_system': True,
})
```

### 2.9 保留不变的模型

- `Project` / `ProjectMember` / `BusinessMember` / `Business` — 项目隔离不变
- `DeployEnvironment` / `DeployEnvironmentPermission` — 环境权限不变

### 2.10 替换关系一览

| 旧模型 | 新模型 | 操作 |
|--------|--------|------|
| `MenuButton` | `IAMPermission` | 迁移 |
| `Role` (dvadmin) | `IAMRole` | 迁移 |
| `RoleMenuPermission` | 自动从 IAMPermission.app 推导 | 删除 |
| `RoleMenuButtonPermission` | `IAMRolePermission` | 迁移 |
| `user.role` M2M | `IAMUserRole` | 迁移 |
| `MenuField` / `FieldPermission` | (不需要) | 删除 |
| `MenuButton.api` + method | ViewSet 声明式 `required_permission` | 删除 |
| 信号桥 `_sync_dvadmin_role` | (不需要) | 删除 |
| `CustomPermission` | `IAMPermissionBackend` | 替换 |

---

## 三、API 权限检查

### 3.1 辅助函数

```python
ROLE_ORDER = {'viewer': 0, 'editor': 1, 'admin': 2}

def _meets_min_role(user_role: str | None, min_role: str | None) -> bool:
    """检查用户角色是否达到最低要求"""
    if not min_role:
        return True
    return ROLE_ORDER.get(user_role, -1) >= ROLE_ORDER.get(min_role, 0)
```

### 3.2 IAMPermissionChecker — 统一权限判定入口

```python
class IAMPermissionChecker:
    """所有权限判定的单一入口"""

    @staticmethod
    def has_perm(user, codename, request=None):
        """用户是否有这个 codename 权限？"""
        perm = IAMPermission.objects.get(codename=codename)
        
        if user.is_superuser:
            return True
        
        if UserDirectPermission.objects.filter(
            user=user, permission__codename=codename
        ).exists():
            return True
        
        role_perm = IAMRolePermission.objects.filter(
            role__iamuserrole__user=user,
            permission__codename=codename,
        ).first()
        if not role_perm:
            return False
        
        if perm.scope == 'platform':
            return True
        
        project_id = request.query_params.get('project_id') if request else None
        if not project_id:
            return False
        user_role = get_project_role(user, project_id)
        return _meets_min_role(user_role, role_perm.min_project_role)
```

### 3.3 IAMPermissionBackend — 统一 DRF 权限后端

```python
class IAMPermissionBackend(BasePermission):
    """统一权限检查后端 — 所有子产品共用。"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        perm = getattr(view, 'required_permission', None)
        if not perm:
            return True
        return IAMPermissionChecker.has_perm(request.user, perm, request)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            project_id = getattr(obj, 'project_id', None)
            if project_id:
                return has_project_role(request.user, project_id, 'editor')
        return True
```

### 3.4 TenantPermission（保留）

不变。保持现有的项目写入权限检查。

```python
class TenantPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            project_id = getattr(obj, 'project_id', None)
            if project_id:
                return has_project_role(request.user, project_id, 'editor')
        return True
```

### 3.5 各子产品 ViewSet 使用方式

```python
# 系统管理 — 需要声明 required_permission
class UserViewSet(CustomModelViewSet):
    required_permission = 'system:user:manage'
    permission_classes = [IAMPermissionBackend]

class RoleViewSet(CustomModelViewSet):
    required_permission = 'system:role:manage'
    permission_classes = [IAMPermissionBackend]

class DeptViewSet(CustomModelViewSet):
    required_permission = 'system:dept:manage'
    permission_classes = [IAMPermissionBackend]

# 子产品 — 项目隔离为主，permission 可选
class FlowTemplateViewSet(ProjectFilteredViewSet):
    permission_classes = [IsAuthenticated, IAMPermissionBackend, TenantPermission]
    # 不设 required_permission → 不额外检查，只靠 TenantPermission + 项目隔离

    @action(methods=['POST'], detail=False, required_permission='opsflow:template:create')
    def create(self, request): ...

    @action(methods=['DELETE'], detail=True, required_permission='opsflow:template:delete')
    def destroy(self, request, pk=None): ...

class FlowExecutionViewSet(ProjectFilteredViewSet):
    permission_classes = [IsAuthenticated, IAMPermissionBackend, TenantPermission, EnvironmentGatePermission]

    @action(methods=['POST'], detail=True, required_permission='opsflow:execution:run')
    def start(self, request, pk=None): ...

# CMDB
class InstanceViewSet(ProjectFilteredViewSet):
    permission_classes = [IsAuthenticated, IAMPermissionBackend, TenantPermission]

# ITSM
class TicketViewSet(ProjectFilteredViewSet):
    permission_classes = [IsAuthenticated, IAMPermissionBackend, TenantPermission, EnvironmentGatePermission]

# Monitor
class AlertViewSet(ProjectFilteredViewSet):
    permission_classes = [IsAuthenticated, IAMPermissionBackend, TenantPermission]
```

### 3.6 `required_permission` 声明规则

以 opsflow 为例，展示了 operation 级别的 permission 粒度选择：

| ViewSet | required_permission (class 级) | action 覆盖 | 说明 |
|---------|-------------------------------|-------------|------|
| `FlowTemplateViewSet` | 不设置 (靠项目隔离) | create → `opsflow:template:create`, destroy → `opsflow:template:delete` | 读写分离，delete 需要单独权限 |
| `FlowExecutionViewSet` | 不设置 (靠项目隔离) | start → `opsflow:execution:run`, cancel → `opsflow:execution:cancel` | 执行操作需显式权限 |
| `SchedulePlanViewSet` | `opsflow:schedule:manage` | — | 全部操作统一权限 |
| `OpsKnowledgeViewSet` | 不设置 | create → `opsflow:knowledge:create`, destroy → `opsflow:knowledge:delete` | 读开放，写控制 |
| `OpsWebhookViewSet` | `opsflow:webhook:manage` | — | 全部操作统一权限 |
| `FlowTemplateViewSet.make_public` | — | action → `opsflow:template:publish` | 特殊操作 |

规则总结：
- **CRUD 全一样** → 类级 `required_permission` 就够了
- **读写分离** → 不设类级，在 create/update/destroy 上单独声明
- **特殊操作** → 在 `@action` 上声明

### 3.7 `/api/iam/my-full-permissions/` 接口

返回当前用户的所有**平台级** IAMPermission codename 列表（项目级权限由前端通过 projectStore 动态判断）。

```python
@action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
def my_full_permissions(self, request):
    """返回当前用户的全部平台级权限 codename"""
    user = request.user
    if user.is_superuser:
        perms = IAMPermission.objects.values_list('codename', flat=True)
    else:
        perms = set()
        for role in IAMUserRole.objects.filter(user=user):
            for rp in IAMRolePermission.objects.filter(role=role.role).select_related('permission'):
                if rp.permission.scope == 'platform':
                    perms.add(rp.permission.codename)
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__scope='platform'
        ).select_related('permission'):
            perms.add(dp.permission.codename)
    return SuccessResponse(data=sorted(perms))
```

---

## 四、web_router — 侧边栏菜单生成

用户能看到某个 app 的菜单 → 用户有该 app 下的任一 permission。

```python
@action(methods=['GET'], detail=False, permission_classes=[])
def web_router(self, request):
    user = request.user
    if user.is_superuser:
        menus = Menu.objects.filter(visible=True)
    else:
        perm_apps = set()
        for role in IAMUserRole.objects.filter(user=user):
            apps = IAMRolePermission.objects.filter(
                role=role.role
            ).values_list('permission__app', flat=True).distinct()
            perm_apps.update(apps)
        for dp in UserDirectPermission.objects.filter(user=user, permission__isnull=False):
            perm_apps.add(dp.permission.app)
        menus = Menu.objects.filter(visible=True, app__in=perm_apps)
    
    serializer = MenuSerializer(menus, many=True)
    return SuccessResponse(data=serializer.data)
```

不再需要 `RoleMenuPermission` 表。

---

## 五、前端适配

### 5.1 permissionStore 改造

```typescript
// stores/permission.ts
export const usePermissionStore = defineStore('permission', () => {
  const perms = ref<string[]>([])
  const loaded = ref(false)

  async function fetchPermissions() {
    const res = await request({ url: '/api/iam/my-full-permissions/', method: 'get' })
    perms.value = res.data || []
    loaded.value = true
  }

  function hasPerm(codename: string): boolean {
    return perms.value.includes(codename)
  }

  // 项目角色（独立维度，从 projectStore 读取）
  const projectStore = useProjectStore()
  const currentRole = computed(() => projectStore.currentProject?.role || null)
  const canEdit = computed(() => currentRole.value !== null && currentRole.value !== 'viewer')
  const isAdmin = computed(() => currentRole.value === 'admin')

  return { perms, loaded, fetchPermissions, hasPerm, currentRole, canEdit, isAdmin }
})
```

### 5.2 v-can 行为

| 写法 | 检查方式 |
|------|---------|
| `v-can="'user:create'"` | `permissionStore.hasPerm('user:create')` |
| `v-can.edit` | `permissionStore.canEdit` |
| `v-can.admin` | `permissionStore.isAdmin` |

### 5.3 消息中心等旧页面迁移

全部统一到 IAM 框架。消息中心不再使用 `@fast-crud/fast-crud` + `crud.tsx`，改为 Vue3 直接编写，使用 `v-can="'message_center:search'"` 控制按钮权限。

### 5.4 Tab 可见性控制（opsflow）

当前方案不变 — 调用 `/api/opsflow/projects/my_opsflow_permissions/`。长期可以替换为统一的 `/api/iam/my-full-permissions/`。

---

## 六、IAM 管理页面的调整

原来的"菜单管理"tab 改为"权限管理"。新的 "IAM" 下的 tab 为：

| tab | 内容 |
|-----|------|
| 用户管理 | 用户 CRUD + 角色分配 |
| 角色管理 | IAMRole CRUD |
| 权限管理 | IAMPermission 查看 + 角色-权限绑定 |
| 部门管理 | 部门维护 |
| 操作日志 | 审计日志 |

管理内容：
1. **IAMPermission 列表** — 查看所有 codename，标记 scope
2. **IAMRole 管理** — 创建/编辑系统角色
3. **角色-权限绑定** — 设置角色有哪些权限，project 权限的最低角色要求
4. **用户-角色分配** — 给用户分配角色

不再管理：
- ❌ Menu 层级（导航结构属于 UI 配置）
- ❌ MenuButton api + method
- ❌ MenuField / FieldPermission
- ❌ data_range

---

## 七、迁移计划

### P1：新模型建表（兼容运行）
- 创建 `IAMPermission`、`IAMRole`、`IAMRolePermission`、`IAMUserRole`
- 精简 `Menu` 保留 app 字段
- 修改 `UserDirectPermission` 加 `permission` FK
- 修改 `PermissionRequest` FK 指向

### P2：数据迁移脚本
- `MenuButton` → `IAMPermission`
- `Role` (dvadmin) → `IAMRole`
- `RoleMenuButtonPermission` → `IAMRolePermission`
- `user.role` M2M → `IAMUserRole`
- 创建默认 `authenticated` 角色并分配给所有已有用户

### P3：IAMPermissionBackend 上线
- `CustomPermission` 指向新后端（并行运行）
- ViewSet 逐个声明 `required_permission`
- 测试通过后切换

### P4：web_router 切换到新逻辑
- 菜单 → app → IAMPermission 推导
- 删除 `RoleMenuPermission` 数据

### P5：清理旧代码
- 删除 `_sync_dvadmin_role`（信号桥）
- 删除 `RoleMenuPermission`、`RoleMenuButtonPermission`、`MenuButton`
- 删除 `MenuField`、`FieldPermission`
- 删除旧 `Role` 表（非 IAMRole）
- 删除 `CustomPermission`（确认无引用后）
- 删除消息中心的 `crud.tsx`，替换为 Vue3 原生组件

---

## 八、验证

1. 迁移后所有子产品的 API 正常工作
2. 系统管理页面（用户/角色/菜单）按平台级权限控制
3. OpsFlow/ITSM/CMDB 按项目隔离 + project role 控制
4. 侧边栏菜单根据用户权限自动显示/隐藏
5. 前端 v-can 按 codename 控制按钮可见性
6. 权限申请流程（PermissionRequest）正常工作
7. 默认角色确保新用户能登录和看到基础页面
8. 旧表数据全部迁移完成，无遗漏
