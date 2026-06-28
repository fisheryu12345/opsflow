# Pipeline 执行修复 + 条件编辑器重构

> 提交: beabfcbb | 日期: 2026-06-28
> 涉及 App: opsflow
> 类型: fix + refactor

---

## 背景

本次提交修复了 4 个 pre-existing bug 并重构了条件编辑器 UI：

1. **Pipeline 图有环验证失败** — `_has_loop_edges` 接收了错误格式的 pipeline
2. **排他网关自定义条件不生效** — `_gwcond_` 变量名不被 bamboo-engine whitelist 识别
3. **PropertyPanel Loop Config 崩溃** — Vue 3 `v-if` 优先级高于 `v-for` 导致 crash
4. **条件编辑 Edit 无法加载已有规则** — `conditionStruct` 缓存设计不当
5. **条件预览可读性差** — 多规则显示为一行字符串

## 实现方案

### Fix 1: pipeline graph has circle

```python
# backend/opsflow/core/flow_engine.py:227-228
# 修复前 — 传入已格式化的 bamboo pipeline dict
has_loop = _has_loop_edges(pipeline)
# 修复后 — 传入原始 nodes/edges 格式
has_loop = _has_loop_edges(frozen_tree) if frozen_tree else False
```

`_has_loop_edges` 期望 `{nodes: [...], edges: [...]}` 格式，但传入的是 `{activities: {...}, gateways: {...}, flows: {...}}` 格式，回环检测永远返回 False。

### Fix 2: 自定义条件 whitelist 拒绝

```python
# backend/opsflow/core/pipeline_builder/elements.py:70
# 修复前 — 合成 _gwcond_ 变量名，引擎不认识
var_name = f"_gwcond_{node_id}_{key}"

# 修复后 — 使用 {node_id}_{key}，匹配 output_schema 注册名
var_name = f"{node_id}_{key}"
```

bamboo-engine 的 `_promote_results` 输出 schema 字段注册为 `${nid}_{field}`。`_gwcond_` 前缀的变量引擎不会自动 promotion，导致 whitelist 拒绝。改成 `${node_id}_{key}` 后路径畅通。

### Fix 3: _find_predecessor_activity 类型错误

```python
# 修复前 — 把整个 edge dict 当 node_id 用
for e in in_edges.get(gateway_id, []):
    q.append(e)  # e is dict {from, to, label}

# 修复后 — 从 dict 中提取 from
for e in in_edges.get(gateway_id, []):
    pred_id = e.get('from') if isinstance(e, dict) else e
```

### Fix 4: 条件编辑器重构

**问题链：**
1. `onLoopChange` 函数不存在 → Vue warning
2. `<el-option v-for="item in ..." v-if="item.type === ...">` → Vue 3 `v-if` 优先级高于 `v-for` → `item` 未定义 → crash
3. `conditionStruct` 独立 ref → 边切换时丢失 → Edit 空对话框
4. 多次尝试加缓存（Map、模块级 Map、merged to edgeForm）都因各种原因失败

**最终方案：** 从条件字符串反解析：

```typescript
const _exprPattern = /^\${([^.]+)\.([^}]+)}\s*(>=|<=|!=|==|>|<)\s*(.+)$/

function _parseConditionExpr(expr: string): ConditionStruct | null {
  const lines = expr.split(/\s+(?:AND|OR)\s+/).filter(Boolean)
  const rules = lines.map(line => {
    const m = line.match(_exprPattern)
    if (!m) return null
    return { source: m[1], field: m[2], op: m[3], value: m[4], ... }
  }).filter(Boolean)
  return { logic: expr.includes(' OR ') ? 'OR' : 'AND', rules }
}
```

每次点 Edit 时如果 `conditionStruct` 不在内存，就从 `edgeForm.condition` 反解析。不需要缓存。

### Fix 5: 边 label 丢失

三个位置全部修复：

| 位置 | 问题 | 修复 |
|------|------|------|
| `loadGraphData` | 边创建时不保存 label | `data: { label: edge.label || '' }` |
| `aiLayout` 移除边 | 只捕获 data，没看 X6 labels | `edge.getLabels()` 合并到 data |
| `aiLayout` 恢复边 | addEdge 没有 labels 属性 | 新增 `labels: [...]` |
| `getGraphData` | 只读 X6 labels，没读 data | `edgeData.label || labels` |

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/flow_engine.py:227` | `_has_loop_edges` 传入正确的 frozen_tree |
| `backend/opsflow/core/pipeline_builder/elements.py:68-73` | `_gwcond_` → `{node_id}_{key}` 修复 whitelist |
| `backend/opsflow/core/pipeline_builder/elements.py:24-38` | `_find_predecessor_activity` 处理 dict edge |
| `web/.../PropertyPanel.vue:88-116` | Loop Config UI（移除 onLoopChange） |
| `web/.../PropertyPanel.vue:102` | `v-if+v-for` → `loopVarOptions` computed |
| `web/.../PropertyPanel.vue:755-781` | `_parseConditionExpr` 反解析 + openConditionDialog |
| `web/.../useDesignCanvas.ts:536-551` | 边创建保留 label，仅网关出边显示 label |
| `web/.../useDesignCanvas.ts:612-658` | aiLayout 循环边保留 label |
| `web/.../index.vue:295-322` | onSelectTemplate 自动 layout |

---

## 2026-06-28 Update

> 提交: 5124f0b0

### 变更内容

新增 loop_iteration 字段到 NodeExecutionTrace，支持循环/回环场景下的多迭代追踪：

- `NodeExecutionTrace` 新增 `loop_iteration` 字段，`unique_together` 改为 `(execution, node_id, retry_count, loop_iteration)`
- `_resolve_loop_iteration()` 检测上次迭代状态为 completed/failed 时自动递增 li
- 前端表格新增 Iteration 列显示 `#1` `#2` `#3`
- Traces tab 溢出滚动修复（el-tabs flex 布局）

### 原因

loop 场景下节点执行多次，但 NodeExecutionTrace 只有一行(retry_count=0, loop_iteration=0)，后续迭代的 outputs 被覆盖。每个迭代的输入输出无法查看。
