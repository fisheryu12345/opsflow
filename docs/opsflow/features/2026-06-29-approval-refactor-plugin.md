# Approval 原子重构 — 从特殊节点到标准插件

> 提交: (待提交) | 日期: 2026-06-29
> 涉及 App: opsflow + iam
> 类型: 功能新增 + 重构

---

## 背景

原有的 approval 节点是一个"伪节点"——elements.py 中创建 ServiceActivity(`_atom_type='approval'`)，但 `get_plugin('approval')` 找不到对应插件，每次执行都打印 ERROR 日志。暂停也依赖信号处理器走弯路过。现重构为标准 `ApprovalPlugin`，与 manual_pause 相同模式：PluginService 直接触发暂停。

## 实现方案

### 核心架构

```
执行链：
  ManualPausePlugin.execute() → 返回 success
  → PluginService 检测到 manual_pause → 直接 FlowEngine.pause()
  → 前端 context._pause_reason === 'manual_pause' → 蓝色提示

  ApprovalPlugin.execute() → 返回 success
  → PluginService 检测到 approval → 直接 FlowEngine.pause()
  → 前端 context._pause_reason === 'approval' → 审批 banner + Approve/Reject 按钮
```

### 关键代码

#### ApprovalPlugin

`opsflow/plugins/approval/approval.py`

```python
class ApprovalPlugin(BasePlugin):
    code = "approval"
    group = "流程控制"
    icon = "Clock"
    color = "#9B59B6"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(tag_code="approvers", type="async_select",
                     attrs={"api_endpoint": "/api/iam/users/search/",
                            "multiple": True, "searchable": True}),
        ]

    def execute(self, approvers=None, **kwargs):
        if not approvers:
            return {"success": False, "error": "请选择审批人"}
        return {"success": True, "data": {"approvers": approvers}}
```

#### PluginService 直接暂停

`plugin_service_adapter.py` — 与 manual_pause 并列：

```python
if atom_type == 'manual_pause':
    ... 直接 pause ...
if atom_type == 'approval':
    execution.context['_pause_reason'] = 'approval'
    execution.context['_approvers'] = approvers
    FlowEngine(execution).pause()
```

#### 用户搜索 API

`iam/views.py` — 新增 `search_users` 端点供 async_select 使用：

```python
@api_view(['GET'])
def search_users(request):
    q = request.query_params.get('search', '')
    users = Users.objects.filter(is_active=True)
    if q: users = users.filter(username__icontains=q) | users.filter(name__icontains=q)
    return SuccessResponse(data=[{'value': u.id, 'label': f"{u.name} ({u.username})"} for u in users[:50]])
```

### 删除的旧代码

| 文件 | 删除内容 |
|------|----------|
| `elements.py` | approval 特殊分支（插件自动发现替代） |
| `helpers.py` | `_is_approval_node()` 函数 |
| `trace.py` | approval import + pause 分支 |
| `pipeline_schema.py` | `"approval"` 枚举值 |
| `shapes.ts` | `ops-approval` 菱形图标注册、typeMap 映射 |
| `useDesignCanvas.ts` | GATEWAY_TYPES 中的 approval、stencil 中 ops-approval 节点 |

### Stencil 布局调整

删除 approval 菱形图标后，subprocess 和 atom 节点在 stencil 中上移。

### 前端 ExecutionDetail

审批暂停判断由 `_is_approval_node` API 调用改为 `context._pause_reason === 'approval'`。

### 审批页面跳转

`opsflow-approval/index.vue` 新增 View 按钮，通过 `window.open('/#/opsflow-execution?id=' + row.id)` 跳转到执行详情。执行页面通过 `route.query.id` 自动加载对应 execution。

### TowerBasePlugin 修复

基类 `code = "_tower_base"` 避免空 code 被注册到 `PLUGIN_REGISTRY`，防止 `get_plugin('')` 错误返回 Tower 插件。

### IAM 用户搜索 API

路由 `GET /api/iam/users/search/`。

## 数据流

```
用户拖入 Task Node → 选择 Approval 插件 → async_select 选择审批人 → 保存
→ pipeline_tree 中存储 atom_type='approval', params={approvers: [id1, id2]}
→ 执行时 PluginService 检测到 approval → _pause_reason='approval' → pause
→ 前端显示审批 banner → 用户 Approve/Reject → API → resume
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/plugins/approval/approval.py` | ApprovalPlugin 插件 |
| `backend/opsflow/core/plugin_service_adapter.py` | PluginService 批准暂停分支 |
| `backend/iam/views.py` | search_users 用户搜索 API |
| `backend/iam/urls.py` | 用户搜索路由 |
| `backend/opsflow/plugins/ansible/tower_backend/base_plugin.py` | TowerBasePlugin code 修复 |
| `web/src/views/apps/opsflow-approval/index.vue` | View 跳转按钮 |
| `web/src/views/apps/opsflow-execution/index.vue` | execution id query 参数支持 |

## 使用方式

1. 在 Pipeline 设计器中拖入 Task Node
2. 在 PropertyPanel 选择「流程控制 → Approval」插件
3. 在审批人下拉中搜索并选择审批人（支持多选）
4. 执行流程，到达审批节点后自动暂停
5. 在审批中心或 ExecutionDetail 页面点击 Approve/Reject 继续
