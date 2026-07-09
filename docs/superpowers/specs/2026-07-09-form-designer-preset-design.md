# Form Designer 预设引用 — 设计文档

## Context

Form Designer 中 SELECT / RADIO / CHECKBOX / MULTISELECT 字段的选项列表只能逐条手动输入。Preset 已有 `options` 类型但未集成。本设计将 Preset 引入 Form Designer，支持从预设选择选项，改一处处处生效。

## Design: 混合模式

字段同时存储展开后的 `choice` 和可选的 `preset_id`。运行时只读 `choice`，修改预设时级联同步 `choice`。选预设 → 展开 → 快照，删预设不丢数据。

## Scope

存在两条字段数据路径，这次全部覆盖：

| 路径 | 编辑器 | 存储 | 状态 |
|------|--------|------|------|
| A | FormDesigner.vue | `State.fields` JSON 内嵌数组 | 在用 |
| B | FieldEditorDialog.vue | `Field` 模型独立记录 | 废弃，本次删除 |

## Backend

### 1. Field 模型新增 preset FK

`backend/itsm/models/field.py`：

```python
preset = models.ForeignKey(
    'itsm.Preset', null=True, blank=True, on_delete=models.SET_NULL,
    related_name='field_defs', verbose_name="关联预设",
)
```

Migration: `0004_field_preset.py`

### 2. StateViewSet.sync() 展开字段级 preset（路径 A）

在 `_expand_preset_processors` 中追加字段级扩展。收集 `s['fields']` 中每个 field 对象的 `preset_id`，查 Preset → 展开 value → 写入 field 的 `choice`：

```python
# After existing state-level expansion, add field-level:
for s in states:
    for f in (s.get('fields') or []):
        fid = f.get('preset_id')
        if fid and int(fid) in presets:
            f['choice'] = presets[int(fid)].value
```

### 3. FieldViewSet.batch_update() 展开字段级 preset（路径 B）

在 `batch_update` 循环中，`_filter_model_fields` 调用前：

```python
for f in fields:
    if f.get('preset_id'):
        preset = Preset.objects.filter(id=f['preset_id']).first()
        if preset and preset.preset_type == 'options':
            f['choice'] = preset.value
```

### 4. PresetSerializer 新增字段级联同步

**4a. Field 模型级联** — `_sync_referencing_fields()`：

```python
@staticmethod
def _sync_referencing_fields(preset):
    from itsm.models.field import Field
    fields = Field.objects.filter(preset=preset)
    for field in fields:
        field.choice = preset.value
        field.save(update_fields=['choice'])
```

**4b. State.fields JSON 内嵌级联** — `_sync_referencing_state_fields()`：

```python
@staticmethod
def _sync_referencing_state_fields(preset):
    from itsm.models.state import State
    states = State.objects.filter(fields__contains=[{"preset_id": preset.id}])
    for state in states:
        for f in state.fields:
            if f.get('preset_id') == preset.id:
                f['choice'] = preset.value
        state.save(update_fields=['fields'])
```

**update() 中触发：**

```python
if old_value != new_value or old_type != new_type:
    self._sync_referencing_states(instance)       # existing: State.processors
    if instance.preset_type == 'options':
        self._sync_referencing_state_fields(instance)   # new: State.fields JSON
        self._sync_referencing_fields(instance)         # new: Field model records
```

### 5. _filter_model_fields

`preset` 已在 `fk_names` 中，无需修改。`preset_id` 会自动通过 Field 模型校验。

## Frontend

### FormDesigner.vue

1. **加载预设**：`onMounted` 中 `presetApi.list({preset_type: 'options'})`
2. **属性面板新增"选项来源"**：radio 切换"手动输入" / "从预设选择"
3. **预设模式**：`el-select` 下拉（过滤 options 类型），选中后 `field.choice = preset.value`，`field.preset_id = preset.id`
4. **切回手动**：`field.preset_id = null`，`choice` 保留不丢
5. **保存**：field 对象含 `choice` + `preset_id`，存入 `node.fields` → `State.fields` JSON

### FieldEditorDialog.vue

删除。无引用、无使用。

## Data Flow

```
FormDesigner 选 options 预设
  │ field.choice = preset.value
  │ field.preset_id = preset.id
  │ emit save → node.fields
  ↓
StateViewSet.sync()
  │ _expand_preset_processors: expand field-level preset_id → choice in s['fields']
  │ save State.fields JSON
  ↓
Preset update 触发
  │ _sync_referencing_state_fields()  → update State.fields JSON
  │ _sync_referencing_fields()        → update Field.choice rows
  │ _sync_referencing_states()        → update State.processors (existing)
  ↓
Runtime rendering
  │ ItsmFormRenderer reads field.choice (no preset dependency)
```

## Files Changed

| File | Change |
|------|--------|
| `backend/itsm/models/field.py` | Add `preset` FK |
| `backend/itsm/views/workflow_views.py` | `_expand_preset_processors` add field-level + `batch_update` expand |
| `backend/itsm/serializers/preset.py` | Add `_sync_referencing_fields()` and `_sync_referencing_state_fields()` |
| `backend/itsm/migrations/0004_field_preset.py` | New migration |
| `web/src/views/apps/itsm/designer/FormDesigner.vue` | Add source toggle + preset dropdown + load presets |
| `web/src/views/apps/itsm/designer/FieldEditorDialog.vue` | Delete |

## Verification

1. 预设管理创建 `options` 预设 "变更分类"
2. 工作流设计器 → NORMAL 节点 → Form Designer
3. 拖入 SELECT 字段 → "从预设选择" → 选 "变更分类" → choice 自动填充
4. 保存/重新打开 → choice + preset_id 正确回显
5. 修改预设内容 → 回到设计器查看，choice 已更新
6. 删除预设 → 字段 choice 保留，preset_id 清空
7. 部署 → 创建工单 → 表单下拉正确显示
