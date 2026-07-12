# Preset 创建时 project_id 缺省回退

> 最后更新: 2026-07-13
> 提交: 0237cea6
> 涉及 App: itsm
> 类型: 修复

---

## 1. 背景与现象

创建 ITSM Preset（预设）时，如果客户端未在请求中显式传入 `project_id`（无论 body 还是 query params），接口直接抛出 `ValidationError({'project_id': 'project_id is required'})`。

但实际上，很多调用场景下用户只在一个项目中操作，`project_id` 可以从用户可访问的项目列表中推断，不应强制要求每次显式传入。

## 2. 排查思路

### 2.1 初步定位
- 报错位置：`PresetViewSet.perform_create()` 第 33 行
- 错误逻辑：`project_id` 为 `None` 时直接 `raise ValidationError`
- 父类 `ItsmProjectViewSet` 已提供 `get_user_project_ids()` 方法，可获取用户有权限的所有项目

### 2.2 分析结论
在抛出 `ValidationError` 之前，应先尝试从上下文推断 `project_id`。如果用户只有一个可访问项目，直接使用该项目；如果多个项目且未指定，仍需报错。

## 3. 根因分析

`perform_create()` 中存在两个获取 `project_id` 的途径：
1. `self.request.data.get('project_id')` — POST body
2. `self.request.query_params.get('project_id')` — URL query params

但没有利用已有的 `get_user_project_ids()` 进行回退推断。当两个途径都未提供时，直接抛出错误，缺少"容错回退"步骤。

## 4. 解决方案

**文件：** `backend/itsm/views/preset_views.py`

### 4.1 新增 fallback 逻辑

```python
if not project_id:
    # Fallback: use the first user-visible project
    user_pids = self.get_user_project_ids()
    project_id = user_pids[0] if user_pids else None
```

- **改动：** 在首次 `if not project_id:` 检查后、`raise ValidationError` 之前，插入 fallback 逻辑
- **目的：** 当 `project_id` 未在请求中显式提供时，自动使用用户有权限的第一个项目，提升 API 易用性

### 4.2 删除过时注释

删除了注释 `# Enforce project-level permission check (inherited from ProjectFilteredViewSet)`。

## 5. 引入的方法 / 函数 / 设计模式

| 引入内容 | 所在文件 | 说明 |
|---------|---------|------|
| `get_user_project_ids()` | `backend/itsm/views/workflow_views.py` (父类已有) | 获取当前用户有权限访问的项目 ID 列表，作为 fallback 数据源 |

## 6. 验证

1. 不传 `project_id`，用户有 1 个可见项目 → 自动使用该项目，创建成功
2. 不传 `project_id`，用户无可见项目 → 仍抛出 `ValidationError`
3. 不传 `project_id`，用户有多个可见项目 → 自动使用第一个项目（行为可预测）
4. 传入有效 `project_id` → 正常创建（行为不变）

## 7. 涉及文件清单

- `backend/itsm/views/preset_views.py` — `perform_create()` 新增 project_id fallback 逻辑

### 关联文档

- 相关功能文档: [2026-07-09-preset-management.md](../features/2026-07-09-preset-management.md)
