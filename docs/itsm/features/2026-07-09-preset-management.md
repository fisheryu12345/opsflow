# ITSM 预设管理 — 可复用处理器/字段选项预设

> 提交: 34b64ce6 | 日期: 2026-07-09
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

ITSM 审批/处理节点配置处理人、角色、部门时每次都需要重新输入。SELECT/RADIO/CHECKBOX 字段的选项列表也需要逐个手敲 label/value。新增 Preset 模型统一管理这些可复用的预定义值，支持一处定义、处处引用、改一处全局生效。

## 实现方案

### 核心架构

**混合模式引用**：字段同时存储展开后的快照值（`choice`/`processors`）和可选的 `preset_id` 引用。运行时只读快照，修改预设时级联同步快照。

**预设类型**：

| 类型 | 用途 | 值格式 |
|------|------|--------|
| `user_list` | 用户列表 | `["user1","user2"]` |
| `role_list` | 角色列表 | `["admin","dev"]` |
| `dept_list` | 部门列表 | `["ops","qa"]` |
| `text` | 文本 | `"some text"` |
| `options` | 选项列表 | `[{label,value}]` |

### 数据流

```
前端选择预设 → field.processors/choice 填入预设值 + preset_id
    ↓
StateViewSet.sync() 或 FieldViewSet.batch_update()
    │ _expand_preset_processors(): 展开 state 级 preset_id → processors
    │ 展开 field 级 preset_id → choice（内嵌 JSON 和 DB 记录两条路径）
    ↓
PresetSerializer.update() 值变化时
    │ _sync_referencing_states()       → 更新 State.processors（已有）
    │ _sync_referencing_state_fields() → 更新 State.fields JSON 内嵌字段
    │ _sync_referencing_fields()       → 更新 Field 模型记录
    ↓
ItsmFormRenderer 只读 field.choice（零依赖，与现有逻辑兼容）
```

### 关键代码

**Preset 模型** (`backend/itsm/models/preset.py`):
```python
class Preset(CoreModel):
    name = CharField(max_length=128)
    preset_type = CharField(max_length=32, choices=[user_list, role_list, dept_list, text, options])
    value = JSONField(default=list)
    project = ForeignKey('iam.Project', null=True, blank=True, db_constraint=False)
    sort = IntegerField(default=1)
```

**PresetViewSet** (`backend/itsm/views/preset_views.py`):
- 继承 `ItsmProjectViewSet`，支持 `?preset_type=` 过滤
- `perform_create` 含项目权限校验 + `creator=self.request.user.id`

**_expand_preset_processors** (`backend/itsm/views/workflow_views.py`):
- 收集 state 级 `preset_id` + field 级 `preset_id`（JSON 内嵌）
- 批量查 Preset，按 workflow.project_id 范围过滤
- `int()` 带 try/except 防止非数值输入崩溃
- options 类型写 `choice`，其他类型写 `processors`

**PresetSerializer.update() 级联** (`backend/itsm/serializers/preset.py`):
- value 或 preset_type 变化时触发三级同步
- `_sync_referencing_state_fields()`: `State.objects.filter(fields__contains=[{"preset_id": id}])` → 逐个 state 遍历内嵌 JSON 更新 choice
- `_sync_referencing_fields()`: `Field.objects.filter(preset=preset)` → 逐个 field.save() 更新 choice

### 设计决策

| 决策 | 原因 |
|------|------|
| 快照模式（展开存储 choice） | 运行时零依赖预设表，已部署工单完全独立；删除预设不丢数据 |
| State.fields JSON + Field 模型双路径 | FormDesigner 写 JSON，后续可能用 FieldEditorDialog 写 DB 记录 |
| Preset 不在 DesignerConfigPanel 与 FormDesigner 间共享 | 两者在不同 Dialog，独立加载更简单，避免 props 穿透 |
| 预设切换时清空对立模式数据 | 防止手动编辑被预设覆盖（前端清除）或预设被手动值覆盖 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/preset.py` | Preset 模型（5 种类型，CoreModel 基类） |
| `backend/itsm/serializers/preset.py` | PresetSerializer + 三级级联同步 |
| `backend/itsm/views/preset_views.py` | PresetViewSet CRUD + 项目权限 |
| `backend/itsm/views/workflow_views.py` | `_expand_preset_processors()` 展开逻辑 |
| `backend/itsm/models/field.py` | Field 模型新增 preset FK |
| `web/src/views/apps/itsm/components/PresetList.vue` | 预设管理 Tab 页（CRUD + 类型筛选） |
| `web/src/views/apps/itsm/designer/components/PresetProcessorInput.vue` | 预设/手动切换共享组件 |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | 工作流节点处理器集成预设 |
| `web/src/views/apps/itsm/designer/FormDesigner.vue` | 表单字段选项集成预设 |
| `web/src/api/itsm/index.ts` | presetApi 导出 |

## 使用方式

1. **创建预设**: ITSM → 预设管理 Tab → 新建 → 选择类型 → 填写值 → 保存
2. **工作流节点引用**: 设计器 → 点击审批/会签/自动任务节点 → 处理人类型选 PERSON/ROLE/ORGANIZATION → 点击"从预设选择" → 下拉选预设
3. **表单字段引用**: 设计器 → NORMAL 节点 → 表单设计 → 拖入 SELECT/RADIO/CHECKBOX → 属性面板"从预设选择" → 下拉选 options 类型预设
4. **修改同步**: 修改预设值 → 所有引用该预设的节点和字段自动更新
