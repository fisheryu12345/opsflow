import { ref, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
import { resolveNodeShape, updateAtomNode, refreshPortStates, showNodePorts, PORT_DOT_RADIUS, CARD_WIDTH, CARD_HEIGHT } from '../utils/shapes'

export function useDesignCanvas(containerId: string, emit?: (event: string, ...args: any[]) => void) {
  // 使用通用 Graph composable（设计模式）
  const {
    graph, zoomLevel,
    initGraph: baseInitGraph,
    zoomIn, zoomOut, fitCanvas,
    getGraphData: baseGetGraphData,
    enableResize, enableVisibilityRefresh,
    destroy,
  } = useGraphCanvas(containerId, {
    mode: 'design',
    onConnectStart: () => { _isConnecting.value = true },
  })

  const stencil = shallowRef<Stencil | null>(null)
  const selectedNode = ref<any>(null)
  const selectedEdge = ref<any>(null)

  const canUndo = ref(false)
  const canRedo = ref(false)

  /** 是否正在拖拽连线（连接桩在拖拽期间保持显示） */
  const _isConnecting = ref(false)

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
    g.on('node:click', ({ node, e }) => {
      // 检查是否点击了删除按钮（X6 自动为 markup 元素设置 data-tag 属性）
      const target = e.target as SVGElement | null
      const tag = target?.getAttribute?.('data-tag') || ''
      if (tag === 'del-btn-bg' || tag === 'del-btn-icon') {
        const data = node.getData()
        const isProtected = data?.node_type === 'start_event' || data?.node_type === 'end_event'
        if (!isProtected) node.remove()
        return
      }
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
      if (node.shape === 'ops-atom') updateAtomNode(node)
    })
    g.on('node:mouseenter', ({ node }) => {
      // 参考案例：hover 显示所有端口
      showNodePorts(node, true)
      // 放大端口圆点便于点击
      node.getPorts().forEach(p => {
        if (p.id) {
          node.setPortProp(p.id, 'attrs/circle/r', 6)
          node.setPortProp(p.id, 'attrs/circle/strokeWidth', 2)
        }
      })
      // 为 ops-atom / ops-subprocess 显示删除按钮
      if (node.shape === 'ops-atom' || node.shape === 'ops-subprocess') {
        const data = node.getData()
        const isProtected = data?.node_type === 'start_event' || data?.node_type === 'end_event'
        if (!isProtected) {
          node.setAttrs({ 'del-btn-bg': { visibility: 'visible' }, 'del-btn-icon': { visibility: 'visible' } })
        }
      }
    })
    g.on('node:mouseleave', ({ node }) => {
      // 拖拽连线时保持所有连接桩显示
      if (_isConnecting.value) return
      // 参考案例：已连接的端口保持蓝色可见，未连接的隐藏
      showNodePorts(node, false)
      // 恢复端口大小
      node.getPorts().forEach(p => {
        if (p.id) {
          node.setPortProp(p.id, 'attrs/circle/r', PORT_DOT_RADIUS)
          node.setPortProp(p.id, 'attrs/circle/strokeWidth', 1)
        }
      })
      // 隐藏删除按钮
      if (node.shape === 'ops-atom' || node.shape === 'ops-subprocess') {
        node.setAttrs({ 'del-btn-bg': { visibility: 'hidden' }, 'del-btn-icon': { visibility: 'hidden' } })
      }
    })
    g.on('edge:removed', ({ edge }) => {
      _isConnecting.value = false
      if (isLoading.value) return
      // 刷新两端节点的 port 状态
      const src = edge.getSourceCell()
      const tgt = edge.getTargetCell()
      if (src?.isNode()) refreshPortStates(src as Node)
      if (tgt?.isNode()) refreshPortStates(tgt as Node)
    })
    g.on('history:change', () => {
      canUndo.value = g.canUndo()
      canRedo.value = g.canRedo()
    })
    g.on('node:added', ({ node }) => {
      // 限制 node_id ≤ 32 字符（bamboo-engine MySQL 字段 max_length=33）
      // 自动生成 node_{N+1} 格式，与 AI 生成的 ID 一致
      // X6 Node 无 setId 方法，用 setTimeout 异步替换
      const oldId = node.id
      if (oldId.length > 32 || /^node_\d+$/.test(oldId) === false) {
        setTimeout(() => {
          let maxN = 0
          for (const cell of g.getNodes()) {
            const m = cell.id.match(/^node_(\d+)$/)
            if (m) maxN = Math.max(maxN, parseInt(m[1], 10))
          }
          const newId = `node_${maxN + 1}`
          const data = node.getData() || {}
          const pos = node.getPosition()
          const size = node.getSize()
          const json = node.toJSON()
          // stencil 紧凑形状 → 画布标准形状
          if (json.shape === 'ops-atom-stencil') json.shape = 'ops-atom'
          if (json.shape === 'ops-subprocess-stencil') json.shape = 'ops-subprocess'
          const ports = json.ports || node.getPorts()
          g.removeCell(node.id)
          const newNode = g.addNode({
            shape: json.shape,
            id: newId,
            x: pos.x, y: pos.y,
            width: size.width, height: size.height,
            data: { ...data, id: newId },
            attrs: json.attrs,
            ports: ports,
          })
          // 修复引用旧 ID 的边
          g.getEdges().forEach(edge => {
            const src = edge.getSource()
            const tgt = edge.getTarget()
            if (typeof src === 'object' && src.cell === oldId) edge.setSource({ ...src, cell: newId })
            if (typeof tgt === 'object' && tgt.cell === oldId) edge.setTarget({ ...tgt, cell: newId })
          })
          if (data?.node_type === 'atom') {
            // 强制使用标准卡片尺寸（从调色板拖入时尺寸可能不对）
            if (data?.atom_type) updateAtomNode(newNode)
            else needPlugin(newId)
            newNode.resize(CARD_WIDTH, CARD_HEIGHT)
          }
          if (data?.node_type === 'subprocess') {
            newNode.resize(CARD_WIDTH, CARD_HEIGHT)
          }
          // ID 重建后刷新 port 连接状态
          refreshPortStates(newNode)
        }, 0)
        return
      }
      const data = node.getData()
      const isAtomLike = data?.node_type === 'atom' || data?.node_type === 'subprocess' || data?.node_type === undefined
      if (isAtomLike) {
        // stencil 紧凑形状 → 画布标准形状
        const stencilToReal: Record<string, { shape: string; width: number; height: number }> = {
          'ops-atom-stencil': { shape: 'ops-atom', width: CARD_WIDTH, height: CARD_HEIGHT },
          'ops-subprocess-stencil': { shape: 'ops-subprocess', width: 200, height: 56 },
        }
        const real = stencilToReal[node.shape]
        if (real) {
          const pos = node.getPosition()
          const edges = g.getEdges().filter(e => e.getSourceCellId() === node.id || e.getTargetCellId() === node.id)
          g.removeCell(node.id)
          const realNode = g.addNode({
            shape: real.shape,
            id: data.id || node.id,
            x: pos.x, y: pos.y,
            width: real.width, height: real.height,
            data: { ...data, id: data.id || node.id },
            ports: node.getPorts(),
          })
          // 重连边
          edges.forEach(edge => {
            const src = edge.getSource()
            const tgt = edge.getTarget()
            if (typeof src === 'object' && src.cell === (data.id || node.id)) edge.setSource({ ...src, cell: realNode.id })
            if (typeof tgt === 'object' && tgt.cell === (data.id || node.id)) edge.setTarget({ ...tgt, cell: realNode.id })
          })
          if (data?.atom_type) updateAtomNode(realNode)
          else if (data?.node_type === 'atom') needPlugin(realNode.id)
          return
        }
        // 强制使用标准卡片尺寸（从调色板拖入时尺寸可能不对）
        if (data?.node_type === 'atom') {
          node.resize(CARD_WIDTH, CARD_HEIGHT)
          if (data?.atom_type) updateAtomNode(node)
          else needPlugin(node.id)
        }
      }
    })
    // 连线完成后执行校验：出度约束 + 标签检查 + 网关 Prompt
    g.on('edge:connected', ({ edge }) => {
      _isConnecting.value = false
      const source = edge.getSourceCell()
      if (!source || !source.isNode()) return
      const sourceData = source.getData()
      const sourceType = sourceData?.node_type

      // ── 度约束校验 ──
      const outEdges = g.getEdges().filter(e => {
        const src = e.getSourceCell()
        return src && src.id === source.id
      })

      // atom / '' 出度 ≤ 2
      if (!sourceType || sourceType === 'atom') {
        if (outEdges.length > 2) {
          ElMessage.error(`活动节点 "${sourceData?.label || source.id}" 最多允许 2 条出边（success/failure）`)
          g.removeEdge(edge.id)
          return
        }
        if (outEdges.length === 2) {
          const labels = new Set(outEdges.map(e => e.getLabels?.()?.[0]?.attrs?.text?.text || ''))
          if (labels.size < 2 || !labels.has('success') || !labels.has('failure')) {
            setTimeout(() => ElMessage.warning(`活动节点 "${sourceData?.label || source.id}" 的两条出边标签应为 success 和 failure`), 300)
          }
        }
      }

      // 汇聚网关出度 ≤ 1
      if (sourceType === 'converge_gateway') {
        if (outEdges.length > 1) {
          ElMessage.error(`汇聚网关 "${sourceData?.label || source.id}" 最多允许 1 条出边`)
          g.removeEdge(edge.id)
          return
        }
        // 入边 < 2 提示建议改为直连（检查目标节点入度）
        const target = edge.getTargetCell()
        if (target && target.isNode()) {
          const targetData = target.getData()
          if (targetData?.node_type === 'converge_gateway') {
            const inEdges = g.getEdges().filter(e => {
              const tgt = e.getTargetCell()
              return tgt && tgt.id === target.id
            })
            if (inEdges.length < 2) {
              setTimeout(() => ElMessage.info(`汇聚网关 "${targetData?.label || target.id}" 入边少于 2 条，建议改用直接连接`), 300)
            }
          }
        }
      }

      // ── 排他/条件并行网关：连接后 Prompt 选标签 ──
      const needLabel = sourceType === 'exclusive_gateway' || sourceType === 'conditional_parallel_gateway'
      if (!needLabel) {
        // 非网关连接：刷新两端端口连接状态
        const target = edge.getTargetCell()
        if (target?.isNode()) refreshPortStates(target as Node)
        refreshPortStates(source as Node)
        return
      }
      const labels = edge.getLabels?.() || []
      if (labels.length > 0 && labels[0]?.attrs?.text?.text) {
        // 已有标签的边：刷新端口状态
        const target = edge.getTargetCell()
        if (target?.isNode()) refreshPortStates(target as Node)
        refreshPortStates(source as Node)
        return
      }

      // 刷新两端端口状态（即使 Prompt 未关闭，端口已显示连接态）
      { const target = edge.getTargetCell(); if (target?.isNode()) refreshPortStates(target as Node) }
      refreshPortStates(source as Node)

      ElMessageBox.prompt('请选择分支类型', '分支', {
        inputType: 'select',
        inputOptions: [
          { value: 'success', label: 'success（成功路径）' },
          { value: 'failure', label: 'failure（失败路径）' },
          { value: 'custom', label: '自定义条件' },
        ],
        inputValue: 'success',
        confirmButtonText: '确定',
        cancelButtonText: '取消（删除边）',
        closeOnClickModal: false,
      }).then(({ value }) => {
        if (value === 'custom') {
          ElMessageBox.prompt('请输入条件表达式（如 ${node_1.cpu} > 80）', '自定义条件', {
            inputValue: '${_result} == True',
            inputPlaceholder: '例如: ${node_1.cpu} > 80',
            confirmButtonText: '确定',
            cancelButtonText: '取消（删除边）',
          }).then(({ value: expr }) => {
            edge.setLabels([{ attrs: { text: { text: 'custom' } } }])
            edge.setData({ condition: expr })
          }).catch(() => {
            g.removeEdge(edge.id)
          })
        } else {
          edge.setLabels([{ attrs: { text: { text: value } } }])
        }
      }).catch(() => {
        g.removeEdge(edge.id)
      })
    })

    // 程序化添加边时更新两端 port 状态（isLoading 期间由 loadGraphData 统一管理 port）
    g.on('edge:added', ({ edge }) => {
      if (isLoading.value) return
      const srcCell = edge.getSourceCell()
      const tgtCell = edge.getTargetCell()
      if (srcCell?.isNode()) refreshPortStates(srcCell as Node)
      if (tgtCell?.isNode()) refreshPortStates(tgtCell as Node)
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
      groups: [{ name: 'gateway', label: 'FlowNode', graphHeight: 650 }],
      stencilGraphWidth: 200,
      layout: (model) => {
        const nodes = model.getNodes()
        const d = (n: any) => n.getData() || {}
        nodes.forEach((n) => {
          const t = d(n).node_type
          if (t === 'start_event')                n.setPosition({ x: 26, y: 8 })
          else if (t === 'end_event')             n.setPosition({ x: 110, y: 8 })
          else if (t === 'exclusive_gateway')     n.setPosition({ x: 14, y: 100 })
          else if (t === 'parallel_gateway')      n.setPosition({ x: 110, y: 100 })
          else if (t === 'conditional_parallel_gateway') n.setPosition({ x: 14, y: 184 })
          else if (t === 'converge_gateway')      n.setPosition({ x: 110, y: 184 })
          else if (t === 'approval')              n.setPosition({ x: 63, y: 284 })
          else if (t === 'subprocess')            n.setPosition({ x: 4, y: 388 })
          else if (t === 'atom')                  n.setPosition({ x: 4, y: 446 })
        })
      },
    })

    const stencilNodes = [
      { shape: 'ops-start-event', label: 'Start', width: 56, height: 82, attrs: { label: { text: 'Start', visibility: 'visible', refY: 80 } }, data: { node_type: 'start_event' } },
      { shape: 'ops-end-event', label: 'End', width: 56, height: 82, attrs: { label: { text: 'End', visibility: 'visible', refY: 80 } }, data: { node_type: 'end_event' } },
      { shape: 'ops-exclusive-gateway', label: 'Exclusive', width: 70, height: 92, attrs: { label: { text: 'Exclusive', visibility: 'visible' } }, data: { node_type: 'exclusive_gateway' } },
      { shape: 'ops-parallel-gateway', label: 'Parallel', width: 70, height: 92, attrs: { label: { text: 'Parallel', visibility: 'visible' } }, data: { node_type: 'parallel_gateway' } },
      { shape: 'ops-conditional-parallel-gateway', label: 'Conditional', width: 70, height: 92, attrs: { label: { text: 'Conditional', visibility: 'visible' } }, data: { node_type: 'conditional_parallel_gateway' } },
      { shape: 'ops-converge-gateway', label: 'Converge', width: 70, height: 92, attrs: { label: { text: 'Converge', visibility: 'visible' } }, data: { node_type: 'converge_gateway' } },
      { shape: 'ops-approval', label: 'Approval', width: 70, height: 92, attrs: { label: { text: 'Approval', visibility: 'visible' } }, data: { node_type: 'approval' } },
      { shape: 'ops-subprocess-stencil', label: 'Subprocess', width: 168, height: 48, attrs: { iconLabel: { text: 'S' }, title: { text: 'Subprocess' } }, data: { node_type: 'subprocess' } } as any,
      { shape: 'ops-atom-stencil', label: 'Task Node', width: 168, height: 48, attrs: { iconLabel: { text: 'T' }, title: { text: 'Task Node' } }, data: { node_type: 'atom' } } as any,
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
      label: 'Start',
      attrs: { label: { text: 'Start' } },
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
      const x6Node = graph.value.createNode({
        shape: resolveNodeShape(node),
        id: node.id, x: pos.x, y: pos.y,
        label: nodeLabel,
        attrs: { label: { text: nodeLabel } },
        data: node,
      })
      // 对 ops-atom / ops-subprocess 节点应用卡片样式
      if (x6Node.shape === 'ops-atom') {
        updateAtomNode(x6Node)
        x6Node.resize(CARD_WIDTH, CARD_HEIGHT)
      }
      if (x6Node.shape === 'ops-subprocess') {
        x6Node.resize(CARD_WIDTH, CARD_HEIGHT)
      }
      cells.push(x6Node)
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
      x: endFromData ? (positions[endId]?.x ?? maxContentX + 320) : maxContentX + 320,
      y: endFromData ? (positions[endId]?.y ?? centerY) : centerY,
      label: 'End',
      attrs: { label: { text: 'End' } },
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
    // 加载完成后刷新所有节点的 port 连接状态
    graph.value.getNodes().forEach(n => refreshPortStates(n))
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
