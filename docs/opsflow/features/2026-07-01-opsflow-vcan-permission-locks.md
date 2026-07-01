# OpsFlow 按钮级权限锁 + Tab 可见性控制

> 提交: 5ad24b89 | 日期: 2026-07-01
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

OpsFlow 页面缺乏前端按钮级权限控制：
- viewer 角色能看到所有 tab 和按钮，点击后才收到后端 403 报错
- 知识库在 API 返回空时回退显示假数据（`mockData`），掩盖了权限问题
- 项目角色（`ProjectMember`）全局共享，ITSM 的 editor 身份会污染 OpsFlow 的权限判断

## 实现方案

### 1. 后端：`my_opsflow_permissions` 独立权限接口

在 `OpsProjectViewSet` 中新增 `my_opsflow_permissions` action：
```python
@action(detail=False, methods=['get'])
def my_opsflow_permissions(self, request):
    """返回当前用户的 opsflow 按钮权限列表"""
    perm_keys = set()
    opsflow_buttons = MenuButton.objects.filter(menu__web_path='/opsflow')
    if user.is_superuser:
        perm_keys = set(opsflow_buttons.values_list('value', flat=True))
    else:
        for r in user.role.filter(status=1):
            for mbp in r.role_menu_button.filter(menu_button__in=opsflow_buttons):
                if mbp.menu_button: perm_keys.add(mbp.menu_button.value)
        for dp in UserDirectPermission.objects.filter(user=user, menu_button__in=opsflow_buttons):
            if dp.menu_button: perm_keys.add(dp.menu_button.value)
    return SuccessResponse(data=sorted(perm_keys))
```

前端在 `onMounted` 时调用此接口替代全局 `permissionStore.canEdit` 来判断 tab 可见性。

### 2. 前端：Tab 可见性控制（`opsflow/index.vue`）

```vue
const opsflowPerms = ref<string[]>([])
const opsflowCanEdit = computed(() => opsflowPerms.value.length > 0)

// Tab 根据权限显示/隐藏
<div class="opsflow-hero-tab" v-if="opsflowCanEdit">Templates</div>
<div class="opsflow-hero-tab" v-if="opsflowCanEdit">Executions</div>
<div class="opsflow-hero-tab">执行日志</div>  <!-- 总是可见 -->
<div class="opsflow-hero-tab">Dashboard</div>   <!-- 总是可见 -->
```

URL 参数绕过防护：如果 URL `?tab=templates` 传了 editor-only tab，自动重定向到 dashboard。

### 3. 前端：`v-can` 按钮锁

利用已有的 `v-can` 指令和 `permissionStore`，在所有 opsflow 页面的按钮上添加：

| 指令 | 作用 | 按钮类型 |
|------|------|---------|
| `v-can.edit` | editor+ 可见 | 编辑、创建、发布、启动、保存 |
| `v-can.admin` | admin 可见 | 删除、暂停、取消、设为公开、拒绝、项目管理 |
| 无（默认） | 所有人可见 | 刷新、查看详情、导出、版本历史 |

当用户权限不足时，按钮显示 🔒 锁，点击弹出 `RequestPermission` 对话框。

### 4. 修复 `permissionStore` 空角色处理

```typescript
// 修复前：null → fallback 'viewer' → canEdit = false → 没问题
// 但项目加载前 undefined !== 'viewer' → canEdit = true → 所有 tab 全显示
const currentRole = computed(() => projectStore.currentProject?.role || null)
const canEdit = computed(() => currentRole.value !== null && currentRole.value !== 'viewer')
```

### 5. 删除知识库 Mock 数据

删除 `opsflow-knowledge/index.vue` 中的 `fallbackMock()` 函数、`mockData` 数组和 `useMock` 状态。API 失败时直接显示空列表。

### 6. 后端：`ProjectFilteredViewSet` 静默处理无权限

```python
# 修改前：抛异常 → 403 → 前端报错
if int(project_id) not in user_project_ids:
    raise exceptions.PermissionDenied('No access to this project')

# 修改后：返回空查询集 → 200 + [] → 前端正常显示空
if int(project_id) not in user_project_ids:
    return qs.none()
```

## 数据流

```
用户进入 OpsFlow 页面
  │
  ├── my_opsflow_permissions/ → ['opsflow:template:create', ...] or []
  │
  ├── opsflowCanEdit = true → 显示所有 tab
  │   └── 按钮按 v-can.edit / v-can.admin 分级显示/锁定
  │
  └── opsflowCanEdit = false → 只显示 Dashboard + 执行日志
      └── URL 绕过 → 自动重定向

用户点击按钮
  ├── viewer → 🔒 锁 → 弹出 RequestPermission 对话框
  ├── editor → v-can.edit 按钮可用 → v-can.admin 按钮 🔒
  └── admin → 全部可用
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/views/project_views.py:164-185` | 新增 `my_opsflow_permissions` 接口 |
| `backend/opsflow/views/base.py:70-71` | `PermissionDenied` → `qs.none()` |
| `web/src/views/apps/opsflow/index.vue` | Tab 权限控制、`my_opsflow_permissions` 集成 |
| `web/src/stores/permission.ts` | `canEdit` 空角色修复 |
| `web/src/views/apps/opsflow-knowledge/index.vue` | 删除 mock 数据回退 |
| 8 个 opsflow 子页面 | `v-can.edit` / `v-can.admin` 权限锁 |

### 关联文档

- 相关调试记录: [2026-07-01-remove-data-level-permissions-filter-refactor.md](../architecture/2026-07-01-remove-data-level-permissions-filter-refactor.md)
