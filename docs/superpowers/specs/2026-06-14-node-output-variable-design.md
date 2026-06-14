# Node Output Variable Visibility in Workflow Editor

**Date:** 2026-06-14
**Status:** Draft
**Author:** AI (Claude)
**Related:** Workflow Engine, Variable System

## Problem Statement

在流程设计画布中，用户为 A 节点（测试原子 `test_print_time`）配置参数后，编辑下游 B 节点的参数时，**VariableBrowser（变量浏览器）的 "Node Outputs" 标签页看不到 A 节点的输出字段**（如 `node_1.test1`）。

ConditionDialog（条件编辑器）中的 VariablePicker 下拉列表同样缺少这些输出字段，导致用户无法在设计时引用 `${node_1.test1}` 作为下游节点输入或条件表达式。

## Root Cause Analysis

问题贯穿 **3 个层级**，形成完整的可见性断裂链：

### L1: 后端 API — 字段 key 映射错误

`backend/opsflow/views/mixins/template_variable.py:106`:

```python
field_key = field.get('tag_code', field.get('key', ''))
```

插件 `get_output_schema()` 返回的 schema 格式为 `{"name": "test1", "type": "integer"}`，使用 `name` 而不是 `key` 或 `tag_code`。`field.get('tag_code')` → `None`，`field.get('key')` → `None`，`field_key` → `''` → 被 `if field_key:` 过滤掉。**所有插件输出字段因此无法显示在 VariableBrowser**。

### L2: 前端 — _outputSchema 未同步到 graph node data

PropertyPanel 加载插件 schema 后，`outputSchema` 是局部 `ref`。`emitUpdate()` 未将 `_outputSchema` 写入 graph node data → `extractNodeOutputFields()` 只能返回硬编码的兜底字段（仅 `test_print_time` 和 `_result`）。

### L3: 前端 — 缺乏上游过滤和内联建议

- `extractAvailableVariables()` 遍历**所有**节点而非仅上游节点
- TagVariableInput 只有 "Browse" 弹窗入口，没有内联变量建议/自动补全
- 用户必须记忆 `${node_id.field}` 精确拼写

### 运行时确认

`resolve_variables()` + `build_execution_context()` 对 `${node_id.field}` 的运行时解析**没有问题**。一旦设计时正确输入了引用，运行时就能正确从 `NodeExecutionTrace.outputs` 取值。**问题集中在设计时的可见性和可发现性**。

## Design

### 架构概览

```
用户编辑B节点参数
  └→ TagVariableInput（参数输入框 + 内联建议） ← L5 新增
      ├→ [Browse] → VariableBrowser 弹窗 → API (template_variable.py)  ← L1 修复
      └→ VariablePicker 下拉 → extractAvailableVariables()            ← L4 上游过滤

PropertyPanel 选择插件
  └→ loadPluginSchema → _outputSchema → emitUpdate → graph node data ← L3 同步

Pipeline 构建时
  └→ elements.py → 注册 output_schema 字段的 NodeOutput              ← L2 注册
```

### L1: API 字段 key 映射修复

**文件：** `backend/opsflow/views/mixins/template_variable.py`

#### 变更 1：修复字段 key 提取

```python
# 第 106 行
# 当前（bug）
field_key = field.get('tag_code', field.get('key', ''))
# 改为
field_key = field.get('tag_code', field.get('key', field.get('name', '')))
```

这样 `output_schema` 中无论字段使用 `name` / `key` / `tag_code`，都能正确映射。

#### 变更 2：标准回退字段

对于未定义 `output_schema` 的插件（如 `shell.py`、`api_call.py` 等 Ansible/HTTP 节点），提供通用回退字段：

```python
# 在第 115-123 行后追加
if not schema or not any(
    field.get('name') or field.get('key') or field.get('tag_code') for field in schema
):
    node_outputs.extend([
        {"key": f"{nid}.stdout", "node_id": nid, "node_label": label,
         "source": "node_output", "description": "Standard output"},
        {"key": f"{nid}.stderr", "node_id": nid, "node_label": label,
         "source": "node_output", "description": "Standard error"},
    ])
```

### L2: pipeline 构建时 NodeOutput 注册

**文件：** `backend/opsflow/core/pipeline_builder/elements.py`

在 `_create_element()` 的默认 atom 分支中，注册 `output_schema` 字段的 `NodeOutput` 引用：

```python
# 在 act 构建完成后（约 line 220），追加：
if plugin_cls and hasattr(plugin_cls, 'get_output_schema'):
    schema = plugin_cls.get_output_schema()
    for field in (schema or []):
        field_key = field.get('name') or field.get('key') or ''
        if field_key:
            _register_node_output(data, f"{nid}_{field_key}", nid, field_key)
```

使 bamboo-engine 在运行时能通过 `${node_X.field}` 的 SPLICE 机制正确传递 ContextValue。

### L3: 前端 — _outputSchema 同步到 graph node

**文件：** `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue`

#### 变更 1：插件选择时同步 _outputSchema

```typescript
async function onPluginChange(code: string) {
    // ... 现有逻辑 ...
    if (code) {
        await loadPluginSchema(code)
        form.value._outputSchema = outputSchema.value  // 新增
    }
    emitUpdate()
}
```

#### 变更 2：表单变更时保持 _outputSchema

```typescript
function onFormChange(data: Record<string, any>) {
    form.value.plugin_params = data
    form.value._outputSchema = outputSchema.value  // 新增保持
    emitUpdate()
}
```

### L4: 上游拓扑过滤

**文件：** `web/src/views/apps/opsflow/composables/useGraphCanvas.ts`

修改 `extractAvailableVariables()` 的签名，支持按当前节点过滤上游变量：

```typescript
export function extractAvailableVariables(
    nodes: { id: string; node_type: string; label: string; [key: string]: any }[],
    store?: any,
    options?: {
        currentNodeId?: string
        edges?: { from: string; to: string }[]
    },
): VariableOption[] {
```

上游 BFS 反向遍历算法：

```typescript
const upstreamIds = new Set<string>()
if (options?.currentNodeId && options?.edges?.length) {
    const queue = [options.currentNodeId]
    const visited = new Set<string>()
    while (queue.length) {
        const nid = queue.shift()!
        for (const e of options.edges) {
            if (e.to === nid && !visited.has(e.from)) {
                visited.add(e.from)
                queue.push(e.from)
                upstreamIds.add(e.from)
            }
        }
    }
}
```

当 `currentNodeId` 和 `edges` 都传入时，只返回 `upstreamIds` 中的节点输出；否则回退为显示全部节点（向后兼容）。

**使用处：** PropertyPanel (`openConditionDialog` 中调用时传入当前选中节点 `form.id`) 和 TagVariableInput。

### L5: 内联变量建议

**文件：** `web/src/components/RenderForm/tags/TagVariableInput.vue`

将 `<el-input>` 替换为 `<el-autocomplete>`，从 `availableVars` 中提取建议：

```vue
<el-autocomplete
  v-model="val"
  :fetch-suggestions="queryVariableSuggestions"
  :placeholder="placeholder"
  :disabled="disabled"
  size="small"
  @select="onSuggestionSelect"
/>
```

`availableVars` 通过 Provide/Inject 从 PropertyPanel 传递到 RenderForm 环境。实现方式：

1. PropertyPanel 将 `availableVars` 作为 `context` 传递给 RenderForm
2. RenderForm 通过 inject 传递到 TagVariableInput
3. TagVariableInput 的 `queryVariableSuggestions` 方法将变量列表转换为 `{value, label}` 格式

### 数据流转图

```
┌─────────────────────────────────────────────────────┐
│                  DesignCanvas.vue                    │
│  graph node data ——→ PropertyPanel                   │
│     ↑   ↓                 ↓                           │
│     │   │   onNodeUpdate  onPluginChange              │
│     │   │   (写入 _outputSchema)  (加载 schema)      │
│     │   └──────────┬──────────────────┘              │
│     │              │                                 │
│     │    extractAvailableVariables()                 │
│     │    (读取 graph nodes + edges → 上游过滤)      │
│     │              │                                 │
│     │     ┌────────┴────────┐                        │
│     │     ▼                 ▼                        │
│     │  TagVariableInput   ConditionDialog            │
│     │  (内联建议)          (VariablePicker 下拉)     │
│     └──────┘                                         │
│                                                       │
│  VariableBrowser ← GET /api/.../variable-browser/    │
│  (弹窗)              ↑  (L1 修复 key 映射)           │
└─────────────────────────────────────────────────────┘
```

## Error Handling

| 场景 | 处理 |
|------|------|
| 插件 `get_output_schema()` 返回 `None` | `for field in (schema or []):` 安全 |
| pipeline_tree 无节点（新建模板） | `tree or {}` 安全 |
| `currentNodeId` 未传入 | 上游过滤跳过，显示全部节点（向后兼容） |
| BFS 循环引用（A→B→C→A） | `visited` set 保护，不无限循环 |
| `fetch-suggestions` 无匹配 | 返回 `[]`，显示空状态 |
| VariableBrowser 弹窗 loading | `Try-Catch`，静默失败 |

## Testing Strategy

### 后端

1. **API 单元测试：** mock 插件 `get_output_schema()` → 调用 `variable_browser` → 验证 node_outputs 含 `key` 字段
2. **NodeOutput 注册：** 构建含 test_print_time 的 pipeline → 验证 `data.inputs` 含 `${node_1_test1}`

### 前端

1. **`extractAvailableVariables` 单元测试：** A→B→C 串行，选中 C → 只返回 A + B 的输出
2. **PropertyPanel 状态：** 选择插件后验证 `_outputSchema` 被 emit、graph node data 正确接收

## Implementation Order

1. **L1** — `template_variable.py`（最核心，修复后 VariableBrowser 立即显示节点输出）
2. **L3** — `PropertyPanel.vue`（同步 `_outputSchema`，使前端下拉列表有数据）
3. **L4** — `useGraphCanvas.ts`（上游过滤）
4. **L5** — `TagVariableInput.vue`（内联建议）
5. **L2** — `elements.py`（运行时 NodeOutput 注册，优先级最低，当前运行时路径已正确）

## Files Changed

| # | File | Type | Lines |
|---|------|------|-------|
| 1 | `backend/opsflow/views/mixins/template_variable.py` | Backend / Python | +2 |
| 2 | `backend/opsflow/core/pipeline_builder/elements.py` | Backend / Python | +6 |
| 3 | `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | Frontend / Vue | +5 |
| 4 | `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | Frontend / TS | +30 |
| 5 | `web/src/components/RenderForm/tags/TagVariableInput.vue` | Frontend / Vue | +50 |

~100 lines total, 6 files. No model/API structure changes.
