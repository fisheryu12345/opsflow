import { ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Graph } from '@antv/x6'
import { Stencil } from '@antv/x6-plugin-stencil'
import { History } from '@antv/x6-plugin-history'
import { Snapline } from '@antv/x6-plugin-snapline'
import { Clipboard } from '@antv/x6-plugin-clipboard'
import { Selection } from '@antv/x6-plugin-selection'
import { MiniMap } from '@antv/x6-plugin-minimap'
import { Keyboard } from '@antv/x6-plugin-keyboard'
import { AiLayout } from '/@/api/opsflow/templates'
import { useGraphCanvas, layoutNodes, defaultNodeLabel } from './useGraphCanvas'
import { resolveNodeShape } from '../utils/shapes'

export function useDesignCanvas(containerId: string, emit?: (event: string, ...args: any[]) => void) {
  // 使用通用 Graph composable（设计模式）
  const {
    graph, zoomLevel,
    initGraph: baseInitGraph,
    zoomIn, zoomOut, fitCanvas,
    getGraphData: baseGetGraphData,
    enableResize, enableVisibilityRefresh,
    destroy,
  } = useGraphCanvas(containerId, { mode: 'design' })

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

  // ── 增强版 initGraph ──

  function initGraph(minimapContainer?: HTMLElement | null) {
    baseInitGraph()
    const g = graph.value
    if (!g) return

    // 设计模式额外插件
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
      selectedNode.value = { ...data, id: data.id || node.id }
      selectedEdge.value = null
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
    g.on('history:change', () => {
      canUndo.value = g.canUndo()
      canRedo.value = g.canRedo()
    })
    g.on('node:added', ({ node }) => {
      const data = node.getData()
      if (data?.node_type === 'atom') {
        node.setSize({ width: 180, height: 48 })
        if (!data?.atom_type) needPlugin(node.id)
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
  }

  // ── Stencil ──

  function initStencil(target: HTMLElement) {
    if (!graph.value) return
    const s = new Stencil({
      target: graph.value,
      search: false,
      title: 'FlowNode',
      groups: [{ name: 'gateway', label: 'FlowNode', graphHeight: 500 }],
      stencilGraphWidth: 200,
      layout: (model) => {
        const nodes = model.getNodes()
        const d = (n: any) => n.getData() || {}
        nodes.forEach((n) => {
          const t = d(n).node_type
          if (t === 'start_event')                n.setPosition({ x: 26, y: 8 })
          else if (t === 'end_event')             n.setPosition({ x: 110, y: 8 })
          else if (t === 'exclusive_gateway')     n.setPosition({ x: 14, y: 106 })
          else if (t === 'parallel_gateway')      n.setPosition({ x: 110, y: 106 })
          else if (t === 'conditional_parallel_gateway') n.setPosition({ x: 14, y: 208 })
          else if (t === 'converge_gateway')      n.setPosition({ x: 110, y: 208 })
          else if (t === 'approval')              n.setPosition({ x: 63, y: 312 })
          else if (t === 'subprocess')            n.setPosition({ x: 27, y: 416 })
          else if (t === 'atom')                  n.setPosition({ x: 27, y: 474 })
        })
      },
    })

    const stencilNodes = [
      { shape: 'ops-start-event', label: 'Start', width: 56, height: 80, attrs: { label: { text: 'Start', refY: 76 } }, data: { node_type: 'start_event' } },
      { shape: 'ops-end-event', label: 'End', width: 56, height: 80, attrs: { label: { text: 'End', refY: 76 } }, data: { node_type: 'end_event' } },
      { shape: 'ops-exclusive-gateway', label: 'Condition', width: 70, height: 92, attrs: { label: { text: 'Condition' } }, data: { node_type: 'exclusive_gateway' } },
      { shape: 'ops-parallel-gateway', label: 'Parallel', width: 70, height: 92, attrs: { label: { text: 'Parallel' } }, data: { node_type: 'parallel_gateway' } },
      { shape: 'ops-conditional-parallel-gateway', label: 'Cond. Parallel', width: 70, height: 92, attrs: { label: { text: 'Cond. Parallel' } }, data: { node_type: 'conditional_parallel_gateway' } },
      { shape: 'ops-converge-gateway', label: 'Converge', width: 70, height: 92, attrs: { label: { text: 'Converge' } }, data: { node_type: 'converge_gateway' } },
      { shape: 'ops-approval', label: 'Approval', width: 70, height: 92, attrs: { label: { text: 'Approval' } }, data: { node_type: 'approval' } },
      { shape: 'ops-subprocess', label: 'Subprocess', width: 145, height: 48, attrs: { label: { text: 'Subprocess' } }, data: { node_type: 'subprocess' } },
      { shape: 'ops-atom', label: 'Task Node', width: 145, height: 48, attrs: { label: { text: 'Task Node' } }, data: { node_type: 'atom' } },
    ]

    s.load(stencilNodes.map(n => graph.value!.createNode(n)), 'gateway')
    target.appendChild(s.container!)
    stencil.value = s
  }

  // ── 画布加载（设计模式特有：自动创建 start/end 节点） ──

  function loadGraphData(data: { nodes: any[]; edges: any[] }) {
    if (!graph.value) return
    if (!data || typeof data !== 'object') return

    const nodesList = data.nodes || []
    const edgesList = data.edges || []
    console.log(`[loadGraphData] nodes=${nodesList.length}, edges=${edgesList.length}`)

    const startFromData = nodesList.find(n => n.node_type === 'start_event')
    const endFromData = nodesList.find(n => n.node_type === 'end_event')
    const contentNodes = nodesList.filter(n =>
      n.node_type !== 'start_event' && n.node_type !== 'end_event'
    )
    const contentEdges = edgesList.filter((e: any) =>
      contentNodes.some(n => n.id === e.from) &&
      contentNodes.some(n => n.id === e.to)
    )

    const hasSavedPositions = nodesList.some(n => n.x != null && n.y != null)
    const positions = hasSavedPositions
      ? Object.fromEntries(
          nodesList.filter(n => n.x != null && n.y != null).map(n => [n.id, { x: n.x, y: n.y }]),
        )
      : layoutNodes(contentNodes, contentEdges)

    const cells: any[] = []

    const toIds = new Set(contentEdges.map(e => e.to))
    const fromIds = new Set(contentEdges.map(e => e.from))
    const roots = contentNodes.filter(n => !toIds.has(n.id))
    const leaves = contentNodes.filter(n => !fromIds.has(n.id))

    const allY = contentNodes.map(n => positions[n.id]?.y ?? 40)
    const centerY = allY.length > 0
      ? (Math.min(...allY) + Math.max(...allY)) / 2
      : 40

    // Start 节点
    const startId = startFromData?.id || '__start__'
    cells.push(graph.value.createNode({
      shape: 'ops-start-event',
      id: startId,
      x: startFromData ? (positions[startId]?.x ?? 10) : 10,
      y: startFromData ? (positions[startId]?.y ?? centerY) : centerY,
      data: startFromData || { id: startId, node_type: 'start_event' },
    }))
    if (!startFromData) {
      for (const root of roots) {
        cells.push(graph.value.createEdge({
          source: { cell: startId, port: 'out' }, target: { cell: root.id, port: 'left' },
          attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        }))
      }
    }

    // 内容节点
    for (const node of contentNodes) {
      const pos = positions[node.id] || { x: 0, y: 0 }
      const nodeLabel = node.label || defaultNodeLabel(node.node_type)
      cells.push(graph.value.createNode({
        shape: resolveNodeShape(node),
        id: node.id, x: pos.x, y: pos.y,
        label: nodeLabel,
        attrs: { label: { text: nodeLabel } },
        data: node,
      }))
    }

    // 连线
    for (const edge of edgesList) {
      if (!edge.from || !edge.to) continue
      cells.push(graph.value.createEdge({
        source: { cell: edge.from, port: edge.sourcePort || 'right' },
        target: { cell: edge.to, port: edge.targetPort || 'left' },
        labels: edge.label ? [{ attrs: { text: { text: edge.label } } }] : undefined,
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        data: { condition: edge.condition || '' },
      }))
    }

    // End 节点
    const endId = endFromData?.id || '__end__'
    const maxContentX = contentNodes.length > 0
      ? Math.max(...contentNodes.map(n => positions[n.id]?.x ?? 50))
      : 50
    cells.push(graph.value.createNode({
      shape: 'ops-end-event',
      id: endId,
      x: endFromData ? (positions[endId]?.x ?? maxContentX + 250) : maxContentX + 250,
      y: endFromData ? (positions[endId]?.y ?? centerY) : centerY,
      data: endFromData || { id: endId, node_type: 'end_event' },
    }))
    if (!endFromData) {
      for (const leaf of leaves) {
        cells.push(graph.value.createEdge({
          source: { cell: leaf.id, port: 'right' }, target: { cell: endId, port: 'in' },
          attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
        }))
      }
    }

    // 空画布连接 start→end
    if (!startFromData && !endFromData && contentNodes.length === 0) {
      cells.push(graph.value.createEdge({
        source: { cell: startId, port: 'out' }, target: { cell: endId, port: 'in' },
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
      }))
    }

    console.log(`[loadGraphData] creating ${cells.length} cells`)
    isLoading.value = true
    graph.value.resetCells(cells)
    isLoading.value = false
    graph.value.clearHistory?.()
    graph.value.centerContent()
    console.log('[loadGraphData] done, zoom:', graph.value?.zoom())
  }

  // ── AI 布局 ──

  async function aiLayout() {
    if (!graph.value) return
    const { nodes, edges } = baseGetGraphData()
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
        if (cell && cell.isNode()) cell.setPosition(pos.x, pos.y)
      }
      graph.value!.centerContent()
      ElMessage.success('AI layout complete')
    } catch {
      ElMessage.error('AI layout failed')
    }
  }

  function undo() { graph.value?.undo() }
  function redo() { graph.value?.redo() }

  const onTaskNodeDropped = ref<((nodeId: string) => void) | null>(null)

  return {
    graph, stencil, selectedNode, selectedEdge,
    initGraph, initStencil, loadGraphData,
    getGraphData: baseGetGraphData,
    aiLayout, onTaskNodeDropped,
    zoomIn, zoomOut, fitCanvas, zoomLevel,
    undo, redo, canUndo, canRedo, enableResize, enableVisibilityRefresh,
    destroy,
  }
}
