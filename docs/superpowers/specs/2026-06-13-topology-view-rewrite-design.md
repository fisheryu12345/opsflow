# CMDB 拓扑视图重写设计 / CMDB Topology View Rewrite

> 创建日期: 2026-06-12
> 状态: 设计草案
> 涉及 App: cmdb

---

## 1. 背景

TopologyCanvas.vue（CMDB 拓扑视图 tab）在 G6 4.x → 5.x 升级过程中被反复修改，目前无法正常工作。表现为：
- `props.edges` undefined 导致 `for...of` 崩溃
- `walk()` 返回 undefined 导致 `.slice(0,20)` 崩溃
- `v-show`/`v-if` 切换导致 DOM 不一致
- `fitView` 在容器高度为 0 时溢出

需要完全重写，放弃所有 G6 4.x 遗留代码（TreeGraph、`evt.item.getModel()`、`g.getCanvasByClient(x, y)` 等），用 G6 5.x 的推荐 API 重新实现。

---

## 2. 技术方案

### 2.1 数据流

```
CMDB API (/api/cmdb/instances/...) 
  → index.vue 中的 fetchTopology()
    → store.topology {nodes, edges}
      → TopologyCanvas props {nodes, edges}
        → buildTree() 构建嵌套树
          → flattenTree() 转为 {nodes, edges} 扁平数据
            → G6Graph.setData() + render()
```

### 2.2 关键 API 映射

| 功能 | G6 4.x | G6 5.x |
|------|--------|--------|
| 导入 | `import G6 from '@antv/g6'` | `import { Graph as G6Graph } from '@antv/g6'` |
| 创建图 | `new G6.TreeGraph({...})` | `new G6Graph({layout: {type:'dendrogram'}, ...})` |
| 设置数据 | `g.data(treeData); g.render()` | `g.setData(flatData); g.render()` |
| 自适应 | `fitView: true, fitViewPadding: [x]` | `autoFit: {type:'view', options:{padding:[x]}}` |
| 交互模式 | `modes: {default: [...]}` | `behaviors: [...]` |
| 默认样式 | `defaultEdge: {...}` | `edge: {style: {...}}` |
| 动画 | `animate: true` | `animation: true` |
| 缩放 | `g.zoom(1.25)` | `g.zoomBy(1.25)` |
| 改变尺寸 | `g.changeSize(w, h)` | `g.resize(w, h)` |
| 获取节点位置 | `evt.item.getModel()` | `g.getNodeData(evt.targetId)` |
| 画布坐标 | `g.getCanvasByClient(x, y)` | `g.getCanvasByClient({x, y})` |
| 更新数据 | `g.data(d); g.render()` | `g.setData(d); g.render()` |

### 2.3 折叠/展开

不使用 G6 内置的 `collapsed` 属性（5.x 不支持 TreeGraph），改为：

```typescript
const collapsedSet = ref(new Set<string>())

// 点击节点时切换
function toggleCollapse(id: string) {
  const s = new Set(collapsedSet.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  collapsedSet.value = s
  
  // 重建扁平数据
  const tree = buildTree()
  const flat = flattenTree(tree, collapsedSet.value)
  graph.value.setData(flat)
  graph.value.render()
  graph.value.fitView()
}
```

`flattenTree()` 在遍历时遇到 `collapsedSet` 中的节点就跳过其 children。

### 2.4 右键菜单

```typescript
g.on('node:contextmenu', (evt) => {
  const id = evt.targetId
  if (!id) return
  const nd = g.getNodeData(id)
  ctxNode.value = nd  // 显示 context menu div
  const cp = g.getCanvasByClient({x: evt.clientX, y: evt.clientY})
  ctxPos.value = {x: Math.min(cp.x+10, w-260), y: Math.min(cp.y-10, h-200)}
})
g.on('canvas:click', () => { ctxNode.value = null })
```

### 2.5 节点样式

```typescript
// 所有节点使用内置 circle 类型，style 中定义全部样式
{
  id: 'xxx',
  type: 'rect',
  data: { label: 'Biz-Name', attrs: {...} },
  style: {
    fill: '#1890ff',
    stroke: '#fff',
    lineWidth: 2,
    cursor: 'pointer',
    size: [110, 28],
    radius: 4,
    labelText: 'Biz-Name',     // 显示在节点内部
    labelFontSize: 10,
    labelFontWeight: 600,
    labelFill: '#fff',
    labelPlacement: 'center',
  },
}
```

### 2.6 状态样式

```typescript
node: {
  state: {
    hover: {
      lineWidth: 3,
      stroke: '#ffd666',
      shadowColor: '#ffd666',
      shadowBlur: 10,
    },
  },
},
```

---

## 3. 组件结构

```
TopologyCanvas.vue (约 220 行)
├── template: 工具栏 + G6 容器 + 右键菜单
├── script:
│   ├── buildTree()        — props.nodes/edges → 嵌套树对象
│   ├── flattenTree()      — 嵌套树 + collapsedSet → {nodes, edges}
│   ├── init()             — 创建 G6Graph 并渲染
│   ├── toggleCollapse()   — 折叠/展开逻辑
│   ├── zoomIn/Out/Fit     — 缩放控制
│   └── resetExpand()      — 全部展开
└── style: 容器 flex 布局 + 右键菜单样式
```

---

## 4. 涉及文件

| 文件 | 操作 |
|------|------|
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | **重写** — 完全删除现有代码，按设计重建 |

仅改一个文件。

---

## 5. 未纳入范围

- ❌ DR 拓扑改进（DrTopologyCanvas 不动）
- ❌ 自定义节点（不使用 register('node')）
- ❌ 节点拖拽（drag-element 不引入）
- ❌ G6 版本变更（保持 5.1.1）
