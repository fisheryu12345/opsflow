# IAM — My Permissions 端点 + ITSM 角色同步

> 提交: 80f9ed95 | 日期: 2026-06-30
> 涉及 App: iam
> 类型: 功能新增

---

## 背景

ITSM 需要根据用户在当前项目的 IAM 角色（admin/editor/viewer）控制页面 tab 的可见性和操作权限。原来没有统一的"我的权限"查询端点，前端需要分别调多个 API 来拼凑权限信息。

## 实现方案

### 核心架构

三部分协同工作:

```
seed_itsm_permissions → dvadmin Role + MenuButton + RoleMenuButtonPermission
                             ↓
signals.py → 监听 BusinessMember/ProjectMember 变更 → 同步 dvadmin Role
                             ↓
my_permissions API → 返回当前用户的 role + pages + permissions
```

### 关键代码

**1. `my_permissions` 端点** — `backend/iam/views.py:329+`:

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_permissions(request):
    """Return current user's ITSM permissions for a given project."""
    project_id = int(request.query_params['project_id'])
    
    # 1. Determine IAM role (ProjectMember → fallback BusinessMember)
    role = 'viewer'
    pm = ProjectMember.objects.filter(project_id=project_id, user=user).first()
    if pm:
        role = pm.role
    else:
        bm = BusinessMember.objects.filter(business_id=project.business_id, user=user).first()
        if bm: role = bm.role
    
    # 2. Compute visible ITSM pages by role
    is_admin = role == 'admin'; is_editor = role == 'editor'
    pages = []
    for key, label_en, label_zh in ITSM_PAGE_DEFS:
        visible = True
        if key in ('skill-groups', 'on-duty'):
            visible = is_admin or is_editor
        elif key in ('assign-rules', 'escalation'):
            visible = is_admin
        pages.append({key, label_en, label_zh, visible})
    
    # 3. Collect dvadmin permission keys (itsm:*)
    perm_keys = set()
    if user.is_superuser:
        perm_keys = set(MenuButton.objects.filter(value__startswith='itsm:').values_list('value', flat=True))
    else:
        for role in user.role.filter(status=1):
            for mbp in role.role_menu_button.all():
                if mbp.menu_button.value.startswith('itsm:'):
                    perm_keys.add(mbp.menu_button.value)
    
    return DetailResponse(data={role, project_id, pages, permissions: sorted(perm_keys)})
```

**2. 信号自动同步** — `backend/iam/signals.py`:

```python
IAM_TO_DVADMIN_ROLE = {
    'admin': 'itsm_admin',
    'editor': 'itsm_editor',
    'viewer': 'itsm_viewer',
}

@receiver([post_save, post_delete], sender=BusinessMember)
@receiver([post_save, post_delete], sender=ProjectMember)
def _sync_dvadmin_role(sender, instance, **kwargs):
    """IAM 成员角色变更 → 自动分配/移除对应 dvadmin Role"""
    _sync_dvadmin_role(instance.user)

def _sync_dvadmin_role(user):
    """计算用户在所有 Business/Project 中的最高 IAM 角色 → 分配对应 dvadmin Role"""
    # 收集用户所有 IAM membership 的角色
    # 取最高角色 → 分配对应 dvadmin role
    # 移除不再匹配的 role
```

**3. 权限种子** — `backend/iam/management/commands/seed_itsm_permissions.py`:

```
python manage.py seed_itsm_permissions
```

创建 11 个 `itsm:*` MenuButton + 3 个 Role (ITSM Admin/Editor/Viewer) + RoleMenuButtonPermission。

### 数据流

```
IAM membership 变更 (BusinessMember/ProjectMember)
  → Django signal (post_save/post_delete)
  → _sync_dvadmin_role(user)
  → 计算最高 IAM role
  → 分配/移除 dvadmin Role (itsm_admin/editor/viewer)
  → RoleMenuButtonPermission 自动控制菜单按钮可见性

前端调用:
  GET /api/iam/my_permissions/?project_id=X
  → my_permissions(request)
  → 查 ProjectMember/BusinessMember → 确定 role
  → 查 User.role → RoleMenuButtonPermission → itsm:* keys
  → 返回 { role, pages, permissions }
```

### 设计决策

1. **信号同步而非中间件** — 角色变更即时生效，不依赖请求路径。信号在 save/delete 时触发，一次计算、结果持久化到 DB。
2. **最高角色优先** — 用户可能同时是多个 Business 的 member（不同角色），取最高角色分配 dvadmin Role，确保权限不丢失。
3. **Role 映射而非直接权限** — IAM role → dvadmin Role → MenuButton permissions，复用 dvadmin 现有的 RBAC 体系。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/views.py` | my_permissions 端点 (行 329-427) |
| `backend/iam/signals.py` | BusinessMember/ProjectMember 信号处理，自动同步 dvadmin Role |
| `backend/iam/apps.py` | ready() 中 import signals 注册信号 |
| `backend/iam/urls.py` | 新增 `/my_permissions/` 路由 |
| `backend/iam/management/commands/seed_itsm_permissions.py` | ITSM 权限种子命令 |

## 使用方式

```bash
# 种子权限数据
python manage.py seed_itsm_permissions

# API 调用
curl -H "Authorization: Token xxx" \
  "http://localhost:8000/api/iam/my_permissions/?project_id=1"

# Response
{
  "role": "admin",
  "project_id": 1,
  "pages": [
    {"key": "tickets", "label_en": "My Tickets", "label_zh": "我的工单", "visible": true},
    {"key": "assign-rules", "label_en": "Assign Rules", "label_zh": "路由", "visible": true},
    ...
  ],
  "permissions": ["itsm:ticket:create", "itsm:ticket:approve", ...]
}
```
