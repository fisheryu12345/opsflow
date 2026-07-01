# 页面权限配置动态化设计

> 日期: 2026-07-01 | 状态: 草案
> 目标: 所有子产品的 tab/按钮权限配置彻底动态化，前端零硬编码
> 覆盖: OpsFlow / ITSM / CMDB / Monitor / 集成中心

---

## 一、设计目标

1. **前端零硬编码权限** — 所有 tab 名称、图标、权限要求、按钮配置全部从后端 API 获取
2. **动态渲染** — 用户能看到哪些 tab、哪些按钮，完全由 API 返回的 `has_access` 字段决定
3. **i18n 在后端** — 中文/英文标签在后端维护，前端只按语言选择
4. **管理 UI 可配置** — 通过数据库表而非代码管理配置

---

## 二、关键澄清

### 2.1 Project ≠ 权限

OpsFlow 的 **project 是数据隔离概念，不是权限概念**。

```
OpsFlow       project_id=2  → 只看项目2的模板/执行 → 数据过滤 ✅
ITSM          没有 project 概念                      → 不涉及     ✅
CMDB          没有 project 概念                      → 不涉及     ✅

ProjectMember.role (editor/viewer/admin) → 不应该影响任何子产品的按钮权限 ❌
```

**所以：**
- `?project_id=X` 只在 `ProjectFilteredViewSet.get_queryset()` 中做**数据过滤**
- 按钮/tab 的显隐完全由 `IAMPermission` codename 决定，跟 project role 无关
- `v-can.edit` / `v-can.admin` 等旧用法不依赖 `projectStore.currentProject.role`

### 2.2 平台级权限 vs 子产品级权限 — 独立不互扰

```
平台级（系统管理）
  └─ system:user:manage, system:role:manage, system:menu:manage
  └─ 角色: sysadmin（唯一）

子产品级（OpsFlow / ITSM / CMDB / Monitor ...）
  ├─ opsflow_viewer    → 只能看 opsflow 的 dashboard + logs，其他 🔒
  ├─ opsflow_editor    → opsflow 全部 tab + 创建/编辑/执行
  ├─ opsflow_admin     → opsflow 全部 + 删除/发布/取消
  │
  ├─ itsm_viewer       → 只能看 ITSM 的工单/事件等
  ├─ itsm_editor       → ITSM 全部操作（不含管理操作）
  ├─ itsm_admin        → ITSM 全部 + 删除流程/编辑SLA/路由/升级
  │
  ├─ cmdb_viewer       → 只能查看 CMDB 实例
  ├─ cmdb_editor       → CMDB 创建/编辑实例
  └─ cmdb_admin        → CMDB 全部 + 删除实例/管理模型
```

**核心规则：**
- 各 app 的角色**互相独立**。`opsflow_admin` 不影响 ITSM，也不影响 CMDB
- 用户可以有多个 app 的角色：`opsflow_editor` + `itsm_viewer` + `cmdb_admin`
- 平台级 `sysadmin` 是唯一的，拥有所有系统管理权限
- 没有全局的 "super viewer" 或 "super editor" — 每个 app 单独管理

---

## 三、完整权限链路

从数据定义到前端渲染的完整链路：

```
                  ┌─────────────────────────────┐
                  │  1. 定义 IAMPermission       │
                  │  codename: "opsflow:template:create"
                  │  app: "opsflow"             │
                  └──────────┬──────────────────┘
                             │
                  ┌──────────▼──────────────────┐
                  │  2. 定义 PageTab / PageButton │
                  │  tab: key="templates"        │
                  │   required_perm="opsflow:    │
                  │     templates:view"          │
                  │  button: key="create"        │
                  │   required_perm="opsflow:    │
                  │     template:create"         │
                  └──────────┬──────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                   ▼
  ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
  │  3a. IAMRole  │  │  3b. IAMUserRole │  用户直接授权  │
  │ opsflow_editor│  │  user=510976    │  UserDirect   │
  │  permission:  │  │  role=opsflow  │  Permission   │
  │ template:    │  │  _editor       │  template:    │
  │  create      │  └───────┬───────┘  │  create      │
  │  delete      │          │          └──────┬───────┘
  └──────────────┘          │                  │
                             ▼                  ▼
                    ┌───────────────────────────┐
                    │  4. page-permissions API  │
                    │  查询用户权限 → 计算 has_access
                    └──────────┬────────────────┘
                               │
                    ┌──────────▼────────────────┐
                    │  5. 前端渲染              │
                    │  tab.has_access? → 显示/🔒│
                    │  btn.has_access? → 显示/🔒│
                    └───────────────────────────┘
```

---

## 四、数据模型

### 4.1 IAMPermission（已有）

已在 `iam/models/permission.py` 中，新增 tab/view 级别的 codename：

```python
# opsflow tab 级别 (新)
IAMPermission(codename='opsflow:designer:view', ...)
IAMPermission(codename='opsflow:templates:view', ...)
IAMPermission(codename='opsflow:executions:view', ...)
# opsflow 动作级别 (已有)
IAMPermission(codename='opsflow:template:create', ...)
IAMPermission(codename='opsflow:template:delete', ...)
IAMPermission(codename='opsflow:execution:run', ...)
```

### 4.2 PageTab — Tab 配置（新建）

```python
class PageTab(models.Model):
    app = models.CharField(max_length=64)
    key = models.CharField(max_length=64)
    label_zh = models.CharField(max_length=128)
    label_en = models.CharField(max_length=128)
    icon = models.CharField(max_length=64)
    sort = models.IntegerField(default=1)
    required_perm = models.CharField(max_length=128, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)

    class Meta:
        unique_together = ('app', 'key')
        ordering = ['app', 'sort']
```

### 4.3 PageButton — 按钮配置（新建）

```python
class PageButton(models.Model):
    tab = models.ForeignKey(PageTab, related_name='buttons', on_delete=CASCADE)
    key = models.CharField(max_length=64)
    label_zh = models.CharField(max_length=128)
    label_en = models.CharField(max_length=128)
    icon = models.CharField(max_length=64, null=True)
    required_perm = models.CharField(max_length=128)
    style = models.CharField(max_length=32, default='default')
    sort = models.IntegerField(default=1)

    class Meta:
        unique_together = ('tab', 'key')
        ordering = ['sort']
```

### 4.4 IAMRole（已有）— 角色 = 权限的集合

```python
# seed 数据 — 每个 app 三个角色
IAMRole(key='opsflow_viewer',  name='OpsFlow Viewer')   # 只读
IAMRole(key='opsflow_editor',  name='OpsFlow Editor')   # 可编辑
IAMRole(key='opsflow_admin',   name='OpsFlow Admin')    # 可管理

# 角色-权限绑定
IAMRolePermission(role=opsflow_viewer, permission=opsflow:access)
IAMRolePermission(role=opsflow_viewer, permission=opsflow:dashboard:view)  # null
IAMRolePermission(role=opsflow_viewer, permission=opsflow:logs:view)       # null

IAMRolePermission(role=opsflow_editor, permission=opsflow:designer:view)
IAMRolePermission(role=opsflow_editor, permission=opsflow:templates:view)
IAMRolePermission(role=opsflow_editor, permission=opsflow:template:create)
IAMRolePermission(role=opsflow_editor, permission=opsflow:executions:view)
IAMRolePermission(role=opsflow_editor, permission=opsflow:execution:run)
...

IAMRolePermission(role=opsflow_admin,  permission=opsflow:template:delete)
IAMRolePermission(role=opsflow_admin,  permission=opsflow:template:publish)
...
```

---

## 五、各环节如何控制

### 5.1 Tab 控制

```
1. seed 创建 PageTab 记录
2. 用户访问 opsflow 页面
3. 前端调用 /api/iam/page-permissions/?app=opsflow
4. API 查询用户 opsflow 相关 IAMPermission → 计算 tab.has_access
5. 前端循环渲染 tabs
   - has_access=true  → 可见可点击
   - has_access=false → 显示 🔒，点击弹窗申请
```

### 5.2 按钮控制

```
1. seed 创建 PageButton 记录（关联到 PageTab）
2. 用户切换到某 tab
3. API 在 tab 数据中包含 buttons 列表 + 各自的 has_access
4. 前端渲染当前 tab 的 buttons
   - has_access=true  → 正常显示
   - has_access=false → 🔒 + 禁用 + 点击弹窗
```

每个按钮的 `required_perm` 直接对应一个 `IAMPermission.codename`。

### 5.3 角色授权（viewer / editor / admin）

| IAMRole | 拥有的 IAMPermission | 能干什么 |
|---------|---------------------|---------|
| `opsflow_viewer` | `access`, `:view` 类 | 看 dashboard + logs，其他 tab 🔒 |
| `opsflow_editor` | `:view` + `:create` + `:run` | 所有 tab 解锁，能创建/编辑/执行 |
| `opsflow_admin` | 全部包括 `:delete` `:publish` `:cancel` | 所有 tab 解锁 + 删除/发布/取消 |

**用户怎么获得角色？**

```
方式 A → IAMUserRole：给用户分配一个 IAMRole
  IAMUserRole(user=510976, role=opsflow_editor)
  → 用户获得 opsflow_editor 角色的所有权限

方式 B → UserDirectPermission：绕过角色直接给单个权限
  UserDirectPermission(user=510976, permission=opsflow:template:create)
  → 用户即使没有 editor 角色也能创建模板

方式 C → 权限申请审批
  用户点击 🔒 → 提交 PermissionRequest → 管理员审批
  → 创建 UserDirectPermission(permission=请求的 codename)
```

### 5.4 角色 vs 权限的叠加规则

```
用户权限 = 所有 IAMRole 的权限并集 + 所有 UserDirectPermission 并集

例：用户同时有 opsflow_viewer 和 opsflow_editor 两个角色
→ 最终权限 = viewer 的 + editor 的 = editor 级别

例：用户只有 opsflow_viewer，但有 UserDirectPermission(template:create)
→ 最终权限 = viewer 的权限 + 创建模板
```

---

## 六、API 设计

### `GET /api/iam/page-permissions/?app=opsflow`

```json
{
  "app": "opsflow",
  "user_permissions": ["opsflow:designer:view", "opsflow:template:create"],
  "tabs": [
    {
      "key": "dashboard",
      "label_zh": "看板",
      "label_en": "Dashboard",
      "icon": "DataAnalysis",
      "is_default": true,
      "required_perm": null,
      "has_access": true,
      "buttons": []
    },
    {
      "key": "templates",
      "label_zh": "模板中心",
      "label_en": "Templates",
      "icon": "Document",
      "is_default": false,
      "required_perm": "opsflow:templates:view",
      "has_access": true,
      "buttons": [
        {"key": "create", "label_zh": "新建模板", "label_en": "Create",
         "icon": "Plus", "required_perm": "opsflow:template:create",
         "has_access": false, "style": "primary"},
        {"key": "delete", "label_zh": "删除", "label_en": "Delete",
         "icon": "Delete", "required_perm": "opsflow:template:delete",
         "has_access": false, "style": "danger"}
      ]
    }
  ]
}
```

### 后端实现

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def page_permissions(request):
    app = request.query_params.get('app')
    if not app:
        return ErrorResponse(msg='app required')

    user = request.user

    # 1. 获取用户该 app 下的所有权限 codename
    user_perms = set()
    if user.is_superuser:
        user_perms = set(IAMPermission.objects.filter(app=app).values_list('codename', flat=True))
    else:
        for rp in IAMRolePermission.objects.filter(
            role__user_roles__user=user, permission__app=app
        ).select_related('permission'):
            user_perms.add(rp.permission.codename)
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__app=app
        ).select_related('permission'):
            if dp.permission:
                user_perms.add(dp.permission.codename)

    # 2. 构建 tab 数据（含按钮）
    tabs_data = []
    for tab in PageTab.objects.filter(app=app, visible=True).order_by('sort'):
        tab_has_access = not tab.required_perm or tab.required_perm in user_perms
        buttons_data = []
        for btn in PageButton.objects.filter(tab=tab).order_by('sort'):
            buttons_data.append({
                'key': btn.key,
                'label_zh': btn.label_zh,
                'label_en': btn.label_en,
                'icon': btn.icon,
                'required_perm': btn.required_perm,
                'has_access': btn.required_perm in user_perms,
                'style': btn.style,
            })
        tabs_data.append({
            'key': tab.key,
            'label_zh': tab.label_zh,
            'label_en': tab.label_en,
            'icon': tab.icon,
            'is_default': tab.is_default,
            'required_perm': tab.required_perm,
            'has_access': tab_has_access,
            'buttons': buttons_data,
        })

    return SuccessResponse(data={
        'app': app,
        'user_permissions': sorted(user_perms),
        'tabs': tabs_data,
    })
```

---

## 七、前端改造

### 7.1 opsflow/index.vue — 完全数据驱动

```vue
<!-- 数据加载 -->
const pageConfig = ref<any>(null)
async function loadPageConfig() {
  const res = await request({ url: '/api/iam/page-permissions/', params: { app: 'opsflow' } })
  pageConfig.value = res.data
  // 设置默认 tab
  const defaultTab = res.data.tabs.find((t: any) => t.is_default) || res.data.tabs[0]
  activeTab.value = defaultTab.key
}

<!-- Hero tabs — 完全由 API 数据驱动 -->
<div class="opsflow-hero-tabs">
  <div v-for="tab in pageConfig?.tabs" :key="tab.key"
    class="opsflow-hero-tab"
    :class="{ active: activeTab === tab.key, locked: !tab.has_access }"
    @click="onTabClick(tab)">
    <el-icon><component :is="iconMap[tab.icon]" /></el-icon>
    {{ isEn ? tab.label_en : tab.label_zh }}
    <span v-if="!tab.has_access" class="tab-lock">🔒</span>
  </div>
</div>

<!-- Body — 数据驱动 -->
<template v-if="pageConfig">
  <div v-for="tab in pageConfig.tabs" :key="tab.key" v-show="activeTab === tab.key"
    class="opsflow-section g-fade-in-up" v-if="tab.has_access">
    <component :is="componentMap[tab.key]" embedded />
  </div>
</template>
```

### 7.2 组件映射（唯一的前端硬编码）

```typescript
const componentMap: Record<string, any> = {
  templates: OpsflowTemplate,
  executions: OpsflowExecution,
  approvals: OpsflowApproval,
  knowledge: OpsflowKnowledge,
  logs: OpsflowLog,
  webhooks: OpsflowWebhook,
  dashboard: OpsflowDashboard,
  project: OpsflowProject,
}
```

### 7.3 v-can 指令改造

```typescript
// directive/iamPermission.ts
function can(actionOrCodename: string): boolean {
  if (actionOrCodename.includes(':')) {
    return store.hasPerm(actionOrCodename)     // 精确 codename 匹配
  }
  if (actionOrCodename === 'admin') return store.isAdmin
  if (actionOrCodename === 'edit') return store.canEdit
  return true
}
```

### 7.4 Tab 点击处理

```typescript
function onTabClick(tab: any) {
  if (!tab.has_access) {
    permissionStore.requestPerm(tab.label_zh, tab.required_perm)
    return
  }
  activeTab.value = tab.key
}
```

---

## 八、种子数据管理

### 8.1 seed 脚本设计

```python
# backend/iam/management/commands/seed_iam_page_configs.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        self._create_tabs_and_buttons()
        self._create_roles()
        self.stdout.write("Page configs seeded!")

    def _create_tabs_and_buttons(self):
        """幂等创建 PageTab + PageButton — 已存在则跳过，不覆盖"""
        OPSFLOW_CONFIG = {
            'app': 'opsflow',
            'tabs': [
                {
                    'key': 'dashboard', 'label_zh': '看板', 'label_en': 'Dashboard',
                    'icon': 'DataAnalysis', 'sort': 1, 'required_perm': None, 'is_default': True,
                    'buttons': []
                },
                {
                    'key': 'templates', 'label_zh': '模板中心', 'label_en': 'Templates',
                    'icon': 'Document', 'sort': 2, 'required_perm': 'opsflow:templates:view',
                    'buttons': [
                        {'key': 'create', 'label_zh': '新建模板', 'label_en': 'Create',
                         'icon': 'Plus', 'required_perm': 'opsflow:template:create', 'style': 'primary'},
                        {'key': 'delete', 'label_zh': '删除', 'label_en': 'Delete',
                         'icon': 'Delete', 'required_perm': 'opsflow:template:delete', 'style': 'danger'},
                    ]
                },
                ...
            ]
        }

        for tab_data in OPSFLOW_CONFIG['tabs']:
            tab, created = PageTab.objects.get_or_create(
                app='opsflow', key=tab_data['key'],
                defaults={k: v for k, v in tab_data.items() if k != 'buttons'}
            )
            if created:
                for btn_data in tab_data.get('buttons', []):
                    PageButton.objects.get_or_create(tab=tab, key=btn_data['key'], defaults=btn_data)

    def _create_roles(self):
        """幂等创建 IAMRole + IAMRolePermission"""
        viewer_perms = ['opsflow:access', ...]  # :view 类
        editor_perms = viewer_perms + ['opsflow:template:create', 'opsflow:execution:run', ...]
        admin_perms  = editor_perms + ['opsflow:template:delete', 'opsflow:template:publish', ...]

        for key, name, perm_list in [
            ('opsflow_viewer', 'OpsFlow Viewer', viewer_perms),
            ('opsflow_editor', 'OpsFlow Editor', editor_perms),
            ('opsflow_admin', 'OpsFlow Admin', admin_perms),
        ]:
            role, _ = IAMRole.objects.get_or_create(key=key, defaults={'name': name, 'is_system': True})
            for codename in perm_list:
                perm = IAMPermission.objects.filter(codename=codename).first()
                if perm:
                    IAMRolePermission.objects.get_or_create(role=role, permission=perm)
```

### 8.2 后续配置变更

| 场景 | 操作 |
|------|------|
| 新增一个 tab | 在 seed 脚本中添加 tab 定义 → 重新运行 seed |
| 新增一个按钮 | 在 seed 脚本对应 tab 下添加 button → 重新运行 seed |
| 新增一个权限 codename | 在 seed 脚本中添加 perm → 重新运行 seed |
| 修改标签/图标 | 直接更新 DB（后续可通过 IAM 管理 UI） |
| 角色权限变了 | 更新 `_create_roles` 中的 perm_list → 重新运行 seed |

所有 `get_or_create` 保证幂等，重复运行 seed 不会创建重复数据。

### 8.3 seed 数据初始内容

#### opsflow

| key | label_zh | icon | required_perm | default |
|-----|----------|------|---------------|---------|
| dashboard | 看板 | DataAnalysis | null | ✅ |
| templates | 模板中心 | Document | opsflow:templates:view | |
| executions | 任务执行 | VideoPlay | opsflow:executions:view | |
| approvals | 审批 | Clock | opsflow:approvals:view | |
| knowledge | 知识库 | Collection | opsflow:knowledge:view | |
| logs | 执行日志 | List | null | |
| webhooks | Webhook | Link | opsflow:webhooks:view | |
| project | 项目管理 | Setting | opsflow:project:view | |

#### ITSM

| key | label_zh | icon | required_perm | default |
|-----|----------|------|---------------|---------|
| dashboard | 看板 | DataAnalysis | null | |
| tickets | 工单 | List | null | ✅ |
| workflows | 流程模板 | Setting | itsm:workflows:view | |
| incidents | 事件 | WarningFilled | null | |
| changes | 变更 | Edit | null | |
| sla | SLA | Clock | null | |
| delegation | 委托 | User | null | |
| skill-groups | 技能组 | Collection | itsm:skill_groups:view | |
| on-duty | 排班 | Clock | itsm:on_duty:view | |
| assign-rules | 路由 | Setting | itsm:assign_rules:view | |
| escalation | 升级 | WarningFilled | itsm:escalation:view | |

#### CMDB

| key | label_zh | icon | required_perm | default |
|-----|----------|------|---------------|---------|
| schema | 模型 | Collection | cmdb:schema:view | ✅ |
| instances | 实例 | List | null | |
| sync | 同步 | Refresh | cmdb:sync:view | |
| events | 事件 | Bell | cmdb:events:view | |

#### 角色权限矩阵

| IAMPermission | viewer | editor | admin |
|--------------|--------|--------|-------|
| opsflow:dashboard:view | ✅（null） | ✅（null） | ✅（null） |
| opsflow:logs:view | ✅（null） | ✅（null） | ✅（null） |
| opsflow:designer:view | | ✅ | ✅ |
| opsflow:templates:view | | ✅ | ✅ |
| opsflow:template:create | | ✅ | ✅ |
| opsflow:template:delete | | | ✅ |
| opsflow:template:publish | | | ✅ |
| opsflow:executions:view | | ✅ | ✅ |
| opsflow:execution:run | | ✅ | ✅ |
| opsflow:execution:cancel | | | ✅ |
| opsflow:approvals:view | | ✅ | ✅ |
| opsflow:knowledge:view | | ✅ | ✅ |
| opsflow:knowledge:create | | ✅ | ✅ |
| opsflow:knowledge:delete | | | ✅ |
| opsflow:schedule:manage | | | ✅ |
| opsflow:webhooks:view | | ✅ | ✅ |
| opsflow:webhook:manage | | | ✅ |
| opsflow:project:view | | | ✅ |

> 注意：`opsflow:access` 已移除。`web_router` 改为检查用户是否有任一 `opsflow:*` 权限。viewer 只看到 dashboard + logs（它们 `required_perm=null`）。

---

## 九、迁移计划

### P1：建表 + 接口 + seed
- 创建 `PageTab`、`PageButton` 模型 + migration
- 创建 `seed_iam_page_configs` 命令（含 PageTab/PageButton + IAMRole + IAMRolePermission）
- 实现 `page_permissions` API
- 注册路由 `/api/iam/page-permissions/`

### P2：OpsFlow 前端改造
- opsflow/index.vue 改为数据驱动渲染
- 删除 `TAB_PERMS`、`TAB_NAMES`、`canAccessTab`
- `v-can` 指令支持 codename 检查
- 删除 `v-can.edit` / `v-can.admin` 中对项目角色的依赖

### P3：ITSM、CMDB 前端改造
- 同样改为数据驱动
- 删除所有硬编码的 tab/按钮权限

### P4：管理 UI（可选）
- IAM 管理页面增加 Tab/Button 配置管理
- 超级管理员可直接增删改 tab/按钮/权限要求

---

## 十、验证

1. 运行 seed 脚本后 PageTab/PageButton/IAMRole/IAMRolePermission 数据正确
2. 调用 `/api/iam/page-permissions/?app=opsflow` 返回正确结构
3. viewer 用户只有 `:view` 权限，看到开放 tab + 其他 🔒
4. editor 用户能创建模板等
5. admin 用户能删除/发布
6. 按钮 `has_access` 随权限变化
7. i18n 中文/英文正确切换
8. ITSM、CMDB 同样工作
9. ProjectMember.role 不影响任何按钮/tab 显示
10. seed 脚本可重复运行，不会产生重复数据
