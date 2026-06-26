# 模板公开转换 — 设计文档

> 日期: 2026-06-26 | 类型: 功能设计 | 涉及 App: opsflow

---

## 目标

项目管理员能将项目模板转换为公共模板，选择对哪些项目可见。全站用户可在指定项目范围内查看和使用该模板。

## 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 权限 | Project Admin（非仅 superuser） | superuser 不可能管理所有项目的模板公开需求 |
| 可见范围 | 可选项目列表（非全站） | 企业场景下模板可能涉及敏感逻辑，需要限制可见范围 |
| 审批 | 无审批 | 轻量方案，信任项目管理员 |
| UI | 弹窗（非独立页面） | 操作简单，不需要额外导航 |
| 数据库 | 零变更 | 复用 is_public + project_scope |

## 实现方案

### 1. 后端 — make_public API 端点

**文件**: `backend/opsflow/views/template_views.py`

新增 `make_public` action：

```python
@action(detail=True, methods=['post'], url_path='make-public')
def make_public(self, request, pk=None):
    template = self.get_object()
    user = request.user

    # 权限：project admin 或 superuser
    if not user.is_superuser:
        if not template.project:
            raise PermissionDenied('Template has no project')
        from opsflow.models import ProjectMember
        is_admin = ProjectMember.objects.filter(
            project=template.project, user=user, role='admin'
        ).exists()
        if not is_admin:
            raise PermissionDenied('Only project admin can make template public')

    # 模板必须已发布（非草稿）
    if template.is_draft:
        return ErrorResponse(msg='Publish the template first before making it public')

    # project_scope: ['*'] 全站，或具体项目 ID 列表
    scope = request.data.get('project_scope', ['*'])

    template.is_public = True
    template.project = None
    template.project_scope = scope
    template.save(update_fields=['is_public', 'project', 'project_scope'])

    return DetailResponse(data=FlowTemplateSerializer(template).data, msg='Template is now public')
```

**放宽 update() 中 is_public 的权限**：

```python
# 现有（仅 superuser）:
if request.data.get('is_public') and not request.user.is_superuser:
    return ErrorResponse(...)

# 改为（superuser 或 project admin）:
if request.data.get('is_public') and not request.user.is_superuser:
    if not instance.project:
        return ErrorResponse(...)
    is_admin = ProjectMember.objects.filter(
        project=instance.project, user=request.user, role='admin'
    ).exists()
    if not is_admin:
        return ErrorResponse(...)
```

### 2. 前端 — 公开按钮 + 弹窗

**触发位置**: 模板列表页或设计画布工具栏

**显示条件**: `!template.is_public && !template.is_draft && (isProjectAdmin || isSuperuser)`

**按钮**: Globe 图标 + "Public" 文本

**弹窗**: 项目多选下拉框
- 默认选中当前模板所在项目
- 支持「所有项目」选项（勾选后其他项置灰）
- [取消] [确认公开] 按钮

**调用**: `POST /api/opsflow/templates/{id}/make-public/` → `{project_scope: ["1","3"]}`

**成功后**: 刷新模板列表，模板卡片显示 Public 标签（Globe 图标 + "Public"）

### 3. 公开后的行为（无需改动）

| 场景 | 行为 | 已有实现 |
|------|------|----------|
| 列表查询 | 按 project_id 过滤 + 返回对应的 public 模板 | `ProjectFilteredViewSet._add_public_q()` |
| 全项目可见 | `project_scope: ["*"]` → 所有项目 | `project_scope__contains='*'` |
| 指定项目 | `project_scope: ["1","3"]` → 仅项目1和3 | `project_scope__contains=str(pid)` |
| 编辑权限 | 仅 superuser 可编辑 | 已有 update() 检查 |
| 删除权限 | 仅 superuser 可删除 | 已有 destroy() 检查 |
| 收藏 | 全站可收藏 | 已有 TemplateCollect |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/views/template_views.py` | 新增 `make_public` action + 放宽 `update` 中 is_public 权限 |
| `web/src/views/apps/opsflow/api/templates.ts` | 新增 `MakeTemplatePublic(id, data)` |
| `web/src/views/apps/opsflow/components/.../TemplateToolbar.vue` | 公开按钮 + 弹窗 |
| `web/src/i18n/pages/opsflow/{en,zh-cn}.ts` | 相关文案（~5 key） |

## 不涉及

- 数据库模型变更
- 序列化器修改
- `ProjectFilteredViewSet` 修改
- 路由新增
- 审批流程
- 模板市场/浏览页面

## 验证

1. Project Admin 点击「公开」→ 选择项目 → 确认 → 模板标记为 public → 其他项目可见
2. 非 Admin（Editor/Viewer）→ 不显示公开按钮
3. 草稿模板 → 不显示公开按钮（需先发布）
4. Superuser → 仍可公开任意模板
5. 公开后选择「所有项目」→ 任意项目都能在模板列表中看到
6. 公开后选「项目A、项目B」→ 只有 A 和 B 能看到

## 后续扩展（非本期）

- 撤销公开（转回项目模板）：新增 `make_private` action
- 公开模板编辑历史与版本对比
- 模板使用次数统计
- 模板审批流
