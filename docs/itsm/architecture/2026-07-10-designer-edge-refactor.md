# Designer 边配置简化 — 移除驳回边 + 审批/会签默认字段清理

> 提交: f689e639 | 日期: 2026-07-10
> 涉及 App: itsm
> 类型: 重构

---

## 动机

1. **驳回边机制冗余** — 驳回本质上是一个带条件的流转边，不需要独立的 `isReject` 开关和方向标记。统一用条件表达式 `condition` 区分分支，简化数据模型。
2. **审批/会签默认字段僵化** — `APPROVAL` 和 `SIGN` 节点的预设字段（`approval_opinion`、`approval_result`、`sign_opinion`、`sign_result`）无法满足不同业务的审批表单需求，改为完全由用户通过 FormDesigner 自定义。
3. **边配置面板缺乏网关门卫** — 所有边点击都弹出配置面板，非网关边（如普通流转）不应显示条件编辑。

---

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `DesignerConfigPanel.vue` | 边配置无网关判别；驳回开关独立；条件预览为纯文本 | `isGatewayEdge` guard：仅 EXCLUSIVE/CONDITIONAL_PARALLEL 显示边配置；移除驳回开关；结构化条件预览 |
| `useDesigner.ts` | 边数据含 `isReject`、`direction: 'reject'`；无边选中自动同步到画布 | 移除 `isReject`、`direction` 始终 `'forward'`；新增 `watch(selectedEdge)` 自动同步 label/condition 到 X6 cell |
| `shapes.ts` | `DEFAULT_NODE_FIELDS.APPROVAL` 含 2 个预设字段；`SIGN` 含 2 个预设字段 | `APPROVAL: []`、`SIGN: []`，用户通过 FormDesigner 自定义 |
| `shapes.ts` | `DEFAULT_EDGE_ATTRS.line.stroke: '#DCDFE6'` | `stroke: '#E6A23C'` 统一金色强调 |
| `FlowChart.vue` | 边颜色根据 `isReject`/`condition` 动态变化 | 统一 `#E6A23C` |

### 代码对比

#### 边配置面板 — 网关门卫

```typescript
// 重构前 — 所有边都可配置，非网关边出现无意义的条件编辑区
const configVisible = computed(() => props.node || props.edge)

// 重构后 — 仅网关边显示
const configVisible = computed(() => props.node || (props.edge && isGatewayEdge.value))
const isGatewayEdge = computed(() => {
  const t = props.edge?._from_state_type || ''
  return t === 'EXCLUSIVE' || t === 'CONDITIONAL_PARALLEL'
})
```

#### 边数据结构 — 移除驳回

```typescript
// 重构前
data: {
  ...t,
  isReject,                    // 冗余布尔标记
  label: edgeLabel,
  direction: e.isReject ? 'reject' : 'forward',  // 驳回＝特殊方向
}

// 重构后
data: {
  ...t,
  label: edgeLabel,            // 用户自定义标签或条件文本
  direction: 'forward',        // 统一前向，驳回通过条件表达式表达
}
```

#### 条件预览 — 结构化解析

```html
<!-- 重构前：纯文本展示 -->
<div v-if="edge.condition" style="...word-break:break-all">
  {{ edge.condition }}
</div>

<!-- 重构后：opsflow-style 结构化渲染 -->
<div v-if="edge.condition" class="itsm-cond-preview">
  <div v-for="(r, i) in parsedRules" :key="i" class="cond-rule-line">
    <span v-if="r.logic" class="cond-logic-tag">{{ r.logic }}</span>
    <span class="cond-rule-ref">{{ r.source }}.{{ r.field }}</span>
    <span class="cond-rule-op">{{ r.op }}</span>
    <span class="cond-rule-val">{{ r.value }}</span>
  </div>
</div>
```

#### 审批/会签默认字段 — 清空

```typescript
// 重构前 — 硬编码预设字段
APPROVAL: [
  { key: 'approval_opinion', name: '审批意见', type: 'TEXT', ... },
  { key: 'approval_result', name: '审批结果', type: 'SELECT', ... },
],

// 重构后 — 用户自定义
APPROVAL: [],   // user defines via FormDesigner
```

### 新增能力

#### `parsedRules` computed — 条件表达式结构化解析

解析 OpsFlow 格式 `${node.field} op value` 的条件字符串：

```typescript
const parsedRules = computed(() => {
  const c = (props.edge?.condition || '')
  if (!c || typeof c !== 'string' || !c.trim()) return []
  const RULE_PAT = /^\$\{([^.]+)\.([^}]+)\}\s*(>=|<=|!=|==|>|<|in|notin)\s*(.+)$/
  // 按 AND/OR 分割，逐段匹配并提取 source/field/op/value
  // 返回结构化数组用于预览渲染
})
```

#### `watch(selectedEdge)` — 边选中自动同步画布

```typescript
watch(selectedEdge, (se) => {
  if (!se?._x6Id) return
  const cell = graph.value?.getCellById(se._x6Id)
  if (!cell || !cell.isEdge()) return
  // 同步 label → setLabels()
  // 同步 condition → cellData.condition
}, { deep: true })
```

#### `openConditionDialog()` — 已有条件表达式反向解析

```typescript
function openConditionDialog() {
  const raw = props.edge?.condition || ''
  // 按 AND/OR 分割 → 逐段正则匹配 → 还原为 struct { logic, rules[] }
  // 支持重新编辑已有的多规则条件
}
```

### 设计决策

1. **为什么移除驳回边而不是增强它？** — 驳回本质是"条件不满足时的流转"，用条件表达式 `condition` 表达更灵活（多条件驳回 vs 单一驳回标记）。保留独立 `direction` 字段会导致 UI 和数据模型双重维护成本。

2. **为什么 `APPROVAL`/`SIGN` 默认字段改为空数组？** — 实际审批场景中字段差异巨大（有的只需"通过/驳回"，有的要加"审批意见"、"加签人"、"转办说明"等）。硬编码字段既不够用又占位，改为 FormDesigner 自定义后更灵活。

3. **为什么边颜色统一为 `#E6A23C`？** — 橙色在 OpsFlow 中约定为"条件边"的视觉标识。统一后用户一目了然哪些边是条件分支，无需依赖 `isReject` 的颜色区分。

4. **为什么用 `watch` 而不是双向绑定同步画布？** — X6 图编辑器基于事件驱动，cell 数据变更不会自动反映到画布。`watch(selectedEdge)` 是响应式边界上最直接的同步方式。

## 迁移说明

- **已有工作流：** 之前配置的驳回边将作为普通边保留，条件表达式不变
- **新建工作流：** 不再有"驳回"开关，所有网关分支统一通过条件表达式区分
- **审批字段：** 已有工单的审批数据不受影响（字段存储在 `ticket.meta` 中）；新建审批节点需要通过 FormDesigner 添加所需字段

---

### 关联文档

- 相关调试记录: [2026-07-10-exclusive-gateway-fix.md](debug/2026-07-10-exclusive-gateway-fix.md)
