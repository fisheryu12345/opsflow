# ITSM 工单详情 404 + ProjectFilteredViewSet 过滤修复

> 提交: db5ad6f9 | 日期: 2026-07-07
> 涉及 App: itsm, opsflow
> 类型: 修复

---

## 背景

ITSM 工单创建后点击详情报 400 错误："请求的资源不存在"（原为"接口地址不正确"）。

**根本原因有两个层面：**

### 层面 1：工单创建时 project_id 未赋值

`TicketViewSet.perform_create()` 覆盖了父类 `ProjectFilteredViewSet.perform_create()`，但没有调用 `super()` 也没有自行解析 project。导致工单创建时 `project_id = NULL`。

```python
# 修复前
def perform_create(self, serializer):
    # ... 解析 workflow_version ...
    instance = serializer.save(creator=self.request.user.id)  # ← project_id 未传

# 修复后
def perform_create(self, serializer):
    # ... 解析 workflow_version ...
    kwargs = self.resolve_project_kwargs(self.request)
    kwargs['creator'] = self.request.user.id
    instance = serializer.save(**kwargs)  # ← project_id 正确赋值
```

### 层面 2：Detail 接口被 project_id 过滤

前端 `service.ts` Axios 拦截器全局给所有请求注入 `project_id`（从 `localStorage.opsflow_active_project_id`）。后端 `ProjectFilteredViewSet.get_queryset()` 原本对所有 action 都按该参数过滤：

```sql
-- 修复前：detail 也被 project_id=13 锁死
WHERE project_id = 13 OR project_id IS NULL
-- 工单 project_id=11 → 找不到！
```

**修复**：只在 `list` / `create` action 应用 `project_id` 过滤：

```python
# base.py - get_queryset()
project_id = self.request.query_params.get('project_id') if self.action in ('list', 'create') else None
```

| Action | project_id 过滤 |
|--------|:---:|
| `list`, `create` | ✅ |
| `retrieve`, `update`, `delete` | ❌ |
| `@action(detail=True)` 如 submit, approve, status | ❌ |

### 辅助修复

- `exception.py`: `Http404` 错误消息从误导性的"接口地址不正确"改为"请求的资源不存在"

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/views/base.py` | `get_queryset()` — 只对 list/create 应用 project_id 过滤 |
| `backend/itsm/views/ticket_views.py` | `perform_create()` — 调用 `resolve_project_kwargs()` 赋值 project |
| `backend/common/utils/exception.py` | `Http404` msg 改为"请求的资源不存在" |
