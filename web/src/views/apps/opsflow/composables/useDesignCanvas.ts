import { ref, onBeforeUnmount, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Graph, Shape } from '@antv/x6'
import { resolveNodeShape } from '../utils/shapes'
import { AiLayout } from '/@/api/opsflow/templates'
import { Stencil } from '@antv/x6-plugin-stencil'
import { History } from '@antv/x6-plugin-history'
import { Snapline } from '@antv/x6-plugin-snapline'
import { Clipboard } from '@antv/x6-plugin-clipboard'
import { Selection } from '@antv/x6-plugin-selection'
import { MiniMap } from '@antv/x6-plugin-minimap'
import { Keyboard } from '@antv/x6-plugin-keyboard'

export function useDesignCanvas(containerId: string, emit?: (event: string, ...args: any[]) => void) {
  const graph = shallowRef<Graph | null>(null)
  const stencil = shallowRef<Stencil | null>(null)
  const selectedNode = ref<any>(null)
  const selectedEdge = ref<any>(null)

  const canUndo = ref(false)
  const canRedo = ref(false)

  /** loading 标志：loadGraphData 期间抑制 node:added 误触发 */
  const isLoading = ref(false)

  /** 通知父组件该未配置的 Task Node 需要选择插件 */
  function needPlugin(nodeId: string) {
    if (emit && !isLoading.value) emit('nodeNeedPlugin', nodeId)
  }

  function initGraph(minimapContainer?: HTMLElement | null) {
    if (graph.value) {
      graph.value.dispose()
    }

    const g = new Graph({
      container: document.getElementById(containerId)!,
      grid: true,
      panning: { enabled: true },
      mousewheel: { enabled: true, zoomAtMousePosition: true },
      connecting: {
        router: { name: 'manhattan', args: { padding: { top: 30, bottom: 30, left: 30, right: 30 }, step: 20, maxLoopCount: 10000 } },
        connector: 'rounded',
        anchor: { name: 'center', args: { dx: 0, dy: 0 } },
        connectionPoint: { name: 'boundary', args: { sticky: true } },
        allowBlank: false,
        allowNode: true,
        allowPort: true,
        allowMulti: true,
        allowLoop: false,
        snap: true,
        highlight: true,
        validateConnection({ sourceMagnet, targetMagnet, sourcePort, targetPort }) {
          if (!sourceMagnet) return false // must start from a port
          if (!targetPort && !targetMagnet) return false // must end at a port
          return true
        },
        createEdge() {
          return new Shape.Edge({
            attrs: {
              line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' },
            },
          })
        },
      },
      highlighting: {
        nodeAvailable: { name: 'stroke', args: { padding: 4, attrs: { stroke: '#409EFF' } } },
      },
    })

    // 插件
    g.use(new History({}))
    g.use(new Snapline({}))
    g.use(new Clipboard({}))
    g.use(new Selection({ rubberband: true, showNodeSelectionBox: true }))
    if (minimapContainer) {
      g.use(new MiniMap({ container: minimapContainer, width: 200, height: 140 }))
    }

    // 事件
    g.on('node:click', ({ node }) => {
      const data = node.getData()
      // 把 X6 的 node.id 合入 data，确保 PropertyPanel 的 form.id 不为空
      selectedNode.value = { ...data, id: data.id || node.id }
      selectedEdge.value = null
      // 未配置 atom_type 的 Task Node → 弹出插件选择器
      if (data?.node_type === 'atom' && !data?.atom_type) {
        needPlugin(node.id)
      }
    })
    g.on('edge:click', ({ edge }) => {
      const source = edge.getSource()
      const target = edge.getTarget()
      const edgeData = edge.getData() || {}
      selectedEdge.value = {
        id: edge.id,
        from: typeof source === 'object' ? source.cell : source,
        to: typeof target === 'object' ? target.cell : target,
        label: edge.getLabels?.()?.[0]?.attrs?.text?.text || '',
        condition: edgeData.condition || '',
      }
      selectedNode.value = null
    })
    g.on('blank:click', () => {
      selectedNode.value = null
      selectedEdge.value = null
    })
    g.on('node:change:data', ({ node }) => {
      if (node.id === selectedNode.value?.id) selectedNode.value = node.getData()
    })
    g.on('node:mouseenter', ({ node }) => {
      node.getPorts().forEach(p => { if (p.id) node.setPortProp(p.id, 'attrs/circle/opacity', 1) })
    })
    g.on('node:mouseleave', ({ node }) => {
      node.getPorts().forEach(p => { if (p.id) node.setPortProp(p.id, 'attrs/circle/opacity', 0) })
    })
    // 历史记录变化同步
    g.on('history:change', () => {
      canUndo.value = g.canUndo()
      canRedo.value = g.canRedo()
    })

    // Task Node 拖入画布回调
    g.on('node:added', ({ node }) => {
      const data = node.getData()
      if (data?.node_type === 'atom') {
        // 从 stencil 拖入的节点尺寸是 stencil 预览尺寸（130×32），恢复为原子节点标准尺寸
        node.setSize({ width: 180, height: 48 })
        if (!data?.atom_type) {
          needPlugin(node.id)
        }
      }
    })

    // 键盘快捷键
    g.use(new Keyboard({ enabled: true }))
    g.bindKey('del', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.bindKey('backspace', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.bindKey('ctrl+c', () => g.copy(g.getSelectedCells()))
    g.bindKey('ctrl+v', () => g.paste({ offset: 32 }))
    g.bindKey('ctrl+z', () => g.undo())
    g.bindKey('ctrl+y', () => g.redo())

    g.on('scale', () => { zoomLevel.value = g.zoom() })

    graph.value = g
  }

  function initStencil(target: HTMLElement) {
    if (!graph.value) return

    const s = new Stencil({
      target: graph.value,
      search: false,
      title: 'Nodes',
      groups: [
        { name: 'basic', label: 'Basic', graphHeight: 130 },
        { name: 'gateway', label: 'Gateways', graphHeight: 170 },
      ],
      stencilGraphWidth: 160,
      layout: (model) => {
        const nodes = model.getNodes()
        const pw = 160
        nodes.forEach((node) => {
          const d = node.getData() || {}
          if (d.node_type === 'start_event')        node.setPosition({ x: 48, y: 12 })
          else if (d.node_type === 'end_event')     node.setPosition({ x: 100, y: 12 })
          else if (d.node_type === 'atom')          node.setPosition({ x: 15, y: 72 })
          else if (d.node_type === 'exclusive_gateway')          node.setPosition({ x: 6, y: 8 })
          else if (d.node_type === 'parallel_gateway')           node.setPosition({ x: 86, y: 8 })
          else if (d.node_type === 'conditional_parallel_gateway') node.setPosition({ x: 6, y: 88 })
          else if (d.node_type === 'converge_gateway')            node.setPosition({ x: 86, y: 88 })
        })
      },
    })

    const base = { width: 130, height: 32 }
    const basicNodes = [
      { shape: 'ops-start-event', ...base, width: 36, height: 36, data: { node_type: 'start_event' } },
      { shape: 'ops-end-event', ...base, width: 36, height: 36, data: { node_type: 'end_event' } },
      { shape: 'ops-atom', label: 'Task Node', ...base, data: { node_type: 'atom' } },
    ]
    const gateH = 70  // 与 shapes.ts 中 gateway 定义一致
    const gatewayNodes = [
      { shape: 'ops-exclusive-gateway', label: 'Condition', width: 68, height: gateH, data: { node_type: 'exclusive_gateway' } },
      { shape: 'ops-parallel-gateway', label: 'Parallel', width: 68, height: gateH, data: { node_type: 'parallel_gateway' } },
      { shape: 'ops-conditional-parallel-gateway', label: 'Cond. Parallel', width: 68, height: gateH, data: { node_type: 'conditional_parallel_gateway' } },
      { shape: 'ops-converge-gateway', label: 'Converge', width: 68, height: gateH, data: { node_type: 'converge_gateway' } },
    ]

    s.load(basicNodes.map(n => graph.value!.createNode(n)), 'basic')
    s.load(gatewayNodes.map(n => graph.value!.createNode(n)), 'gateway')
    target.appendChild(s.container!)
    stencil.value = s
  }

  /** 简易 DAG 分层布局 — 为节点分配 x/y 坐标 */
  function layoutNodes(nodes: any[], edges: { from: string; to: string }[]) {
    // 计算入度 & 邻接表
    const inDeg: Record<string, number> = {}
    const adj: Record<string, string[]> = {}
    for (const n of nodes) { inDeg[n.id] = 0; adj[n.id] = [] }
    for (const e of edges) {
      if (adj[e.from]) adj[e.from].push(e.to)
      if (inDeg[e.to] != null) inDeg[e.to]++
    }

    // BFS 分层
    const level: Record<string, number> = {}
    const queue: string[] = []
    for (const n of nodes) {
      if (inDeg[n.id] === 0) { level[n.id] = 0; queue.push(n.id) }
    }
    let maxLevel = 0
    while (queue.length) {
      const id = queue.shift()!
      if (!adj[id]) continue
      for (const next of adj[id]) {
        const lv = level[id] + 1
        if ((level[next] ?? Infinity) > lv) {
          level[next] = lv
          maxLevel = Math.max(maxLevel, lv)
          queue.push(next)
        }
      }
    }
    // 若有孤立节点未分层
    for (const n of nodes) {
      if (level[n.id] == null) { level[n.id] = 0 }
    }

    // 按层分组
    const layers: Record<number, string[]> = {}
    for (const n of nodes) {
      const lv = level[n.id]
      if (!layers[lv]) layers[lv] = []
      layers[lv].push(n.id)
    }

    // 分配坐标
    const LAYER_GAP = 250
    const NODE_GAP = 120
    const START_X = 50
    const START_Y = 40
    const positions: Record<string, { x: number; y: number }> = {}

    for (let lv = 0; lv <= maxLevel; lv++) {
      const ids = layers[lv] || []
      const totalH = (ids.length - 1) * NODE_GAP
      ids.forEach((id, i) => {
        positions[id] = {
          x: START_X + lv * LAYER_GAP,
          y: START_Y + (totalH / 2) + i * NODE_GAP,
        }
      })
    }

    return positions
  }

  function loadGraphData(data: { nodes: any[]; edges: any[] }) {
    if (!graph.value) return
    if (!data || typeof data !== 'object') return

    const nodesList = data.nodes || []
    const edgesList = data.edges || []

    console.log(`[loadGraphData] nodes=${nodesList.length}, edges=${edgesList.length}`, nodesList, edgesList)

    // 检测是否已有开始/结束节点
    const startFromData = nodesList.find(n => n.node_type === 'start_event')
    const endFromData = nodesList.find(n => n.node_type === 'end_event')

    // 内容节点（剔除开始/结束）
    const contentNodes = nodesList.filter(n =>
      n.node_type !== 'start_event' && n.node_type !== 'end_event'
    )
    const contentEdges = edgesList.filter((e: any) =>
      contentNodes.some(n => n.id === e.from) &&
      contentNodes.some(n => n.id === e.to)
    )

    // 使用固化位置（如 x/y 已存在）或 BFS 布局
    const hasSavedPositions = nodesList.some(n => n.x != null && n.y != null)
    const positions = hasSavedPositions
      ? Object.fromEntries(
          nodesList
            .filter(n => n.x != null && n.y != null)
            .map(n => [n.id, { x: n.x, y: n.y }])
        )
      : layoutNodes(contentNodes, contentEdges)
    const cells: any[] = []

    // 计算内容节点的根节点和叶子节点
    const toIds = new Set(contentEdges.map(e => e.to))
    const fromIds = new Set(contentEdges.map(e => e.from))
    const roots = contentNodes.filter(n => !toIds.has(n.id))
    const leaves = contentNodes.filter(n => !fromIds.has(n.id))

    // 计算所有内容节点 Y 的中心值，使开始/结束节点水平高度一致
    const allY = contentNodes.map(n => positions[n.id]?.y ?? 40)
    const centerY = allY.length > 0
      ? (Math.min(...allY) + Math.max(...allY)) / 2
      : 40

    // ---- 开始节点 ----
    const startId = startFromData?.id || '__start__'
    cells.push(graph.value!.createNode({
      shape: 'ops-start-event',
      id: startId,
      x: startFromData ? (positions[startId]?.x ?? 10) : 10,
      y: startFromData ? (positions[startId]?.y ?? centerY) : centerY,
      data: startFromData || { id: startId, node_type: 'start_event' },
    }))
    // 自动连接开始 → 根节点
    if (!startFromData) {
      for (const root of roots) {
        cells.push(graph.value!.createEdge({
          source: { cell: startId, port: 'out' }, target: { cell: root.id, port: 'left' },
          attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        }))
      }
    }

    /** Returns default label for node type */
    function defaultLabel(nodeType: string): string {
      const map: Record<string, string> = {
        exclusive_gateway: 'Condition?',
        parallel_gateway: 'Parallel',
        conditional_parallel_gateway: 'Cond. Parallel',
        converge_gateway: 'Converge',
        start_event: 'Start',
        end_event: 'End',
      }
      return map[nodeType] || ''
    }

    // ---- 内容节点 ----
    for (const node of contentNodes) {
      const pos = positions[node.id] || { x: 0, y: 0 }
      const nodeLabel = node.label || defaultLabel(node.node_type)
      cells.push(graph.value!.createNode({
        shape: resolveNodeShape(node),
        id: node.id, x: pos.x, y: pos.y,
        label: nodeLabel,
        attrs: { label: { text: nodeLabel } },
        data: node,
      }))
    }

    // ---- 连线 ----
    for (const edge of edgesList) {
      if (!edge.from || !edge.to) continue
      cells.push(graph.value!.createEdge({
        source: { cell: edge.from, port: edge.sourcePort || 'right' },
        target: { cell: edge.to, port: edge.targetPort || 'left' },
        labels: edge.label ? [{ attrs: { text: { text: edge.label } } }] : undefined,
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        data: { condition: edge.condition || '' },
      }))
    }

    // ---- 结束节点 ----
    const endId = endFromData?.id || '__end__'
    const maxContentX = contentNodes.length > 0
      ? Math.max(...contentNodes.map(n => positions[n.id]?.x ?? 50))
      : 50
    cells.push(graph.value!.createNode({
      shape: 'ops-end-event',
      id: endId,
      x: endFromData ? (positions[endId]?.x ?? maxContentX + 250) : maxContentX + 250,
      y: endFromData ? (positions[endId]?.y ?? centerY) : centerY,
      data: endFromData || { id: endId, node_type: 'end_event' },
    }))
    // 自动连接叶子节点 → 结束
    if (!endFromData) {
      for (const leaf of leaves) {
        cells.push(graph.value!.createEdge({
          source: { cell: leaf.id, port: 'right' }, target: { cell: endId, port: 'in' },
          attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        }))
      }
    }

    // 空画布时连接开始→结束
    if (!startFromData && !endFromData && contentNodes.length === 0) {
      cells.push(graph.value!.createEdge({
        source: { cell: startId, port: 'out' }, target: { cell: endId, port: 'in' },
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
      }))
    }

    console.log(`[loadGraphData] creating ${cells.length} cells total`)
    // NOTE: 不能使用 { silent: true } — 会阻止 X6 视图层渲染 DOM，导致画布空白
    isLoading.value = true
    graph.value!.resetCells(cells)
    isLoading.value = false
    // 清除历史快照，避免初始加载成为 undo 入口
    graph.value!.clearHistory?.()
    console.log('[loadGraphData] resetCells done, now centerContent')
    graph.value!.centerContent()
    console.log('[loadGraphData] centerContent done, graph zoom:', graph.value?.zoom(), 'graph size:', graph.value?.getContentArea())
  }

  function getGraphData(): { nodes: any[]; edges: any[] } {
    if (!graph.value) return { nodes: [], edges: [] }
    const cells = graph.value.getCells()
    const nodes: any[] = []
    const edges: any[] = []

    for (const cell of cells) {
      if (cell.isNode()) {
        const data = cell.getData() || {}
        const pos = cell.getPosition()
        nodes.push({ ...data, id: data.id || cell.id, x: pos.x, y: pos.y })
      } else if (cell.isEdge()) {
        const source = cell.getSource()
        const target = cell.getTarget()
        const labels = cell.getLabels?.() || []
        const edgeData = cell.getData?.() || {}
        edges.push({
          from: typeof source === 'object' ? source.cell : source,
          to: typeof target === 'object' ? target.cell : target,
          sourcePort: typeof source === 'object' ? source.port : undefined,
          targetPort: typeof target === 'object' ? target.port : undefined,
          label: labels.length ? (labels[0].attrs?.text?.text || '') : '',
          condition: edgeData.condition || '',
        })
      }
    }

    return { nodes, edges }
  }

  /** 调用 AI 进行布局优化 */
  async function aiLayout() {
    if (!graph.value) return
    const { nodes, edges } = getGraphData()
    if (nodes.length === 0) {
      ElMessage.warning('Canvas is empty')
      return
    }
    try {
      const res = await AiLayout({ nodes, edges })
      const data = res.data?.data || res.data
      const positions = data?.positions || []
      if (!positions.length) {
        ElMessage.warning('AI returned no layout')
        return
      }
      for (const pos of positions) {
        const cell = graph.value!.getCellById(pos.id)
        if (cell && cell.isNode()) {
          cell.setPosition(pos.x, pos.y)
        }
      }
      graph.value!.centerContent()
      ElMessage.success('AI layout complete')
    } catch {
      ElMessage.error('AI layout failed')
    }
  }

  function undo() {
    graph.value?.undo()
  }

  function redo() {
    graph.value?.redo()
  }

  const zoomLevel = ref(1)

  function zoomIn() { graph.value?.zoom(0.15); zoomLevel.value = graph.value?.zoom() || 1 }
  function zoomOut() { graph.value?.zoom(-0.15); zoomLevel.value = graph.value?.zoom() || 1 }
  function fitCanvas() {
    graph.value?.centerContent()
    graph.value?.zoomToFit({ padding: 40 })
    zoomLevel.value = graph.value?.zoom() || 1
  }

  /** Task Node 点击回调用（由父组件直接监听 @nodeNeedPlugin 事件） */
  // onTaskNodeDropped 保留为 null 占位，避免外部 ref 访问报错
  const onTaskNodeDropped = ref<((nodeId: string) => void) | null>(null)

  function destroy() {
    if (graph.value) {
      graph.value.dispose()
      graph.value = null
    }
  }

  onBeforeUnmount(() => destroy())

  return {
    graph, stencil, selectedNode, selectedEdge,
    initGraph, initStencil, loadGraphData, getGraphData,
    aiLayout, onTaskNodeDropped,
    zoomIn, zoomOut, fitCanvas, zoomLevel,
    undo, redo, canUndo, canRedo, destroy,
  }
}
