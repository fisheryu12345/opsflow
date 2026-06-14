# CMDB 拓扑视图 G6 v4 → v5 迁移重构

> 提交: 4ce858ff | 日期: 2026-06-14
> 涉及 App: cmdb
> 类型: 重构

---

## 动机

旧的拓扑视图基于 G6 v4 (`@antv/g6@4.8.25`) 的 `TreeGraph`，存在以下问题：

1. **API 已废弃** — G6 v4 已停止维护，v5 是完全重写的架构（`Graph` 替代 `TreeGraph`，`treeToGraphData` 替代手动 data 构造）
2. **节点渲染能力弱** — 旧版通过 `label` + `subLabel` 配置，不支持自定义图形组合（状态点、徽章）
3. **展开/折叠不稳定** — 旧版通过 `updateChild` + `layout()` 手动触发展开折叠，多次操作后状态不一致
4. **TypeScript 类型支持差** — G6 v4 没有完整的 TS 类型定义

## 变更要点

> ⚠️ **以下为具体实现细节**

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `TopologyCanvas.vue` | 依赖 G6 v4 `TreeGraph`、`G6.Graph`，手动构造 data 树 | 使用 G6 v5 `Graph`、`treeToGraphData()`、自定义 `Rect` + `Badge` |
| `package.json` | `@antv/g6: 4.8.25` | `@antv/g6: 5.1.1` |
| `index.vue` | `v-if` + 固定高度 560px | `v-show` + `flex: 1` 全高布局 + 演示按钮 |

### 架构对比

**重构前 (G6 v4)：**
```vue
// 旧版 — 直接用 G6 对象
import G6 from '@antv/g6'
const g = new G6.TreeGraph({
  container: containerRef.value,
  data: toTree(),  // 手动构造的 data 对象
  layout: { type: 'compactBox', direction: 'LR', ... },
  modes: { default: ['zoom-canvas', 'drag-canvas'] },
})
// 展开折叠靠修改 model 属性 + 手动 layout
g.on('node:click', (evt) => {
  const model = evt.item.getModel()
  if (model.collapsible) {
    model.collapsed = !model.collapsed
    g.updateChild(model, model.id)
    g.layout()
  }
})
```

**重构后 (G6 v5)：**
```vue
// 新版 — 模块化导入
import { Graph, treeToGraphData, ExtensionCategory, Rect, Badge, register } from '@antv/g6'

// 树数据转换：flat edges → nested tree → graphData
const tree = buildTree()  // 从 flat edges 构建嵌套树
const graphData = treeToGraphData(tree, {
  getNodeData: (datum, depth) => {
    datum.style.collapsed = depth >= 2
    if (!datum.children) return datum
    const { children, ...rest } = datum
    return { ...rest, children: children.map(c => c.id) }
  },
})

// 自定义节点：状态点 + 标签 + 子文本 + 折叠徽章
class CmdbTreeNode extends Rect {
  get data() { return this.context.model.getNodeLikeDatum(this.id) }
  get childrenData() { return this.context.model.getChildrenData(this.id) }
  render(attrs, container) { /* status-dot, label, sub, collapse badage */ }
}
register(ExtensionCategory.NODE, 'cmdb-tree-node', CmdbTreeNode)

// 折叠统一由 graph 级别 node:click 处理
g.on('node:click', (evt) => {
  if (target.id !== 'collapse') return
  const collapsed = g.getNodeData(id).style?.collapsed
  collapsed ? g.expandElement(id) : g.collapseElement(id)
})
```

### 关键类/函数

| 类/函数 | 职责 | 定义位置 |
|---------|------|----------|
| `CmdbTreeNode` | 继承 `Rect` 的自定义树节点，渲染状态点/标签/副文本/折叠徽章 | `TopologyCanvas.vue:101-169` |
| `CmdbTreeNode.getCollapseStyle()` | 返回折叠徽章的 Badge 样式，从 `attrs.collapsed` 读取状态 | `TopologyCanvas.vue:124-135` |
| `CmdbTreeNode.render()` | 每次 G6 触发渲染时绘制所有子形状 | `TopologyCanvas.vue:143-164` |
| `buildTree()` | 从 flat `nodes` + `edges` props 构建嵌套树结构 | `TopologyCanvas.vue:65-98` |
| `makeGraphData()` | 将嵌套树转换为 `treeToGraphData` 格式，应用 `_collapsedMap` | 已移除（回到原生） |

### 数据流

```
props.nodes + props.edges (flat)
  → buildTree() → nested tree object
  → treeToGraphData() → graphData (nodes with children IDs + style.collapsed)
  → new Graph({ data: graphData }) → render
  → node:click → g.getNodeData() → g.expandElement() / g.collapseElement()
  → G6 内部更新 collapsed 状态 → 自动重新 layout
```

### 设计决策

1. **为什么用 `Rect` + `Badge` 而不是纯 DOM 覆盖？**
   - G6 v5 的自定义节点使用 `upsert()` 管理子形状生命周期，性能优于 DOM overlay
   - Badge 形状自带背景圆角、文本居中，适合做折叠徽章

2. **为什么折叠点击放在 graph 级别而非 Badge 上？**
   - Badge 上直接 `addEventListener` 在 v5.1.1 中与 G6 内部状态管理有冲突（多次操作后面包屑状态损坏）
   - graph 级别 `node:click` 检测 `evt.target.id === 'collapse'` 更稳定

3. **为什么从 `compactBox` 改为 `indented` 布局？**
   - `indented` 是 G6 v5 的树形布局，更贴近 CMDB 的 Biz→Set→Module→Host 层级视觉
   - `compactBox` 在 v5 中不再作为默认布局导出

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | G6 v5 自定义树节点组件，全部渲染逻辑 |
| `web/src/views/apps/cmdb/index.vue` | 演示数据、CSS 全高、:key 驱动重建 |
| `web/package.json` | `@antv/g6` 版本升级 4.8.25 → 5.1.1 |

## 当前已知问题

- 折叠/展开徽章的点击处理仍不稳定，`expandElement`/`collapseElement` 在多次操作后可能失效
- 需要在后续迭代中解决

### 关联文档

- 相关功能文档: [拓扑演示数据](features/2026-06-14-topology-demo-data.md)
- 相关配置变更: [G6 版本升级](config/2026-06-14-g6-upgrade-config.md)
