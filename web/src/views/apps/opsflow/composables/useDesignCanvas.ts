import { ref, onBeforeUnmount, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Graph, Shape, Node } from '@antv/x6'
import { AiLayout } from '/@/api/opsflow/templates'
import { Stencil } from '@antv/x6-plugin-stencil'
import { History } from '@antv/x6-plugin-history'
import { Snapline } from '@antv/x6-plugin-snapline'
import { Clipboard } from '@antv/x6-plugin-clipboard'
import { Selection } from '@antv/x6-plugin-selection'
import { MiniMap } from '@antv/x6-plugin-minimap'
import { Keyboard } from '@antv/x6-plugin-keyboard'

// 注册自定义节点形状

// 原子操作节点
Shape.Rect.define({
  shape: 'ops-atom',
  width: 180,
  height: 48,
  attrs: {
    body: { fill: '#FFF', stroke: '#409EFF', strokeWidth: 1.5, rx: 6, ry: 6 },
    label: { fill: '#333', fontSize: 13, fontFamily: 'Microsoft YaHei' },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

// 开始事件 — 绿色圆
Shape.Circle.define({
  shape: 'ops-start-event',
  width: 56,
  height: 56,
  attrs: {
    body: { fill: '#E1F3D8', stroke: '#67C23A', strokeWidth: 2.5 },
    label: { fill: '#333', fontSize: 12, fontFamily: 'Microsoft YaHei', textAnchor: 'middle', refY: 62 },
  },
  ports: {
    groups: {
      out: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#67C23A', opacity: 0 } } },
    },
    items: [
      { id: 'out', group: 'out' },
    ],
  },
})

// 结束事件 — 红色圆
Shape.Circle.define({
  shape: 'ops-end-event',
  width: 56,
  height: 56,
  attrs: {
    body: { fill: '#FDE2E2', stroke: '#F56C6C', strokeWidth: 2.5 },
    label: { fill: '#333', fontSize: 12, fontFamily: 'Microsoft YaHei', textAnchor: 'middle', refY: 62 },
  },
  ports: {
    groups: {
      in: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#F56C6C', opacity: 0 } } },
    },
    items: [
      { id: 'in', group: 'in' },
    ],
  },
})

// 排他网关 — 菱形（橙色 X）
Node.define({
  shape: 'ops-exclusive-gateway',
  width: 70,
  height: 70,
  markup: [
    { tagName: 'path', selector: 'body' },
    { tagName: 'text', selector: 'icon' },
    { tagName: 'text', selector: 'label' },
  ],
  attrs: {
    body: {
      d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z',
      fill: '#FFF',
      stroke: '#E6A23C',
      strokeWidth: 2,
    },
    icon: {
      text: '×',
      fill: '#E6A23C',
      fontSize: 24,
      fontWeight: 'bold',
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      refX: 35,
      refY: 33,
    },
    label: {
      fill: '#333',
      fontSize: 11,
      fontFamily: 'Microsoft YaHei',
      textAnchor: 'middle',
      refX: 35,
      refY: 80,
    },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: 4, magnet: true, fill: '#E6A23C', opacity: 0 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: 4, magnet: true, fill: '#E6A23C', opacity: 0 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#E6A23C', opacity: 0 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#E6A23C', opacity: 0 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

// 并行网关 — 菱形（蓝色 +）
Node.define({
  shape: 'ops-parallel-gateway',
  width: 70,
  height: 70,
  markup: [
    { tagName: 'path', selector: 'body' },
    { tagName: 'text', selector: 'icon' },
    { tagName: 'text', selector: 'label' },
  ],
  attrs: {
    body: {
      d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z',
      fill: '#FFF',
      stroke: '#409EFF',
      strokeWidth: 2,
    },
    icon: {
      text: '+',
      fill: '#409EFF',
      fontSize: 28,
      fontWeight: 'bold',
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      refX: 35,
      refY: 33,
    },
    label: {
      fill: '#333',
      fontSize: 11,
      fontFamily: 'Microsoft YaHei',
      textAnchor: 'middle',
      refX: 35,
      refY: 80,
    },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#409EFF', opacity: 0 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

// 条件并行网关 — 菱形（青色 ✓）
Node.define({
  shape: 'ops-conditional-parallel-gateway',
  width: 70,
  height: 70,
  markup: [
    { tagName: 'path', selector: 'body' },
    { tagName: 'text', selector: 'icon' },
    { tagName: 'text', selector: 'label' },
  ],
  attrs: {
    body: {
      d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z',
      fill: '#FFF',
      stroke: '#5CADFF',
      strokeWidth: 2,
    },
    icon: {
      text: '✓',
      fill: '#5CADFF',
      fontSize: 24,
      fontWeight: 'bold',
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      refX: 35,
      refY: 33,
    },
    label: {
      fill: '#333',
      fontSize: 11,
      fontFamily: 'Microsoft YaHei',
      textAnchor: 'middle',
      refX: 35,
      refY: 80,
    },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: 4, magnet: true, fill: '#5CADFF', opacity: 0 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: 4, magnet: true, fill: '#5CADFF', opacity: 0 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#5CADFF', opacity: 0 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#5CADFF', opacity: 0 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

// 汇聚网关 — 菱形（紫色）
Node.define({
  shape: 'ops-converge-gateway',
  width: 70,
  height: 70,
  markup: [
    { tagName: 'path', selector: 'body' },
    { tagName: 'text', selector: 'icon' },
    { tagName: 'text', selector: 'label' },
  ],
  attrs: {
    body: {
      d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z',
      fill: '#FFF',
      stroke: '#909399',
      strokeWidth: 2,
    },
    icon: {
      text: '⨁',
      fill: '#909399',
      fontSize: 22,
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      refX: 35,
      refY: 33,
    },
    label: {
      fill: '#333',
      fontSize: 11,
      fontFamily: 'Microsoft YaHei',
      textAnchor: 'middle',
      refX: 35,
      refY: 80,
    },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: 4, magnet: true, fill: '#909399', opacity: 0 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: 4, magnet: true, fill: '#909399', opacity: 0 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: 4, magnet: true, fill: '#909399', opacity: 0 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: 4, magnet: true, fill: '#909399', opacity: 0 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

export function useDesignCanvas(containerId: string) {
  const graph = shallowRef<Graph | null>(null)
  const stencil = shallowRef<Stencil | null>(null)
  const selectedNode = ref<any>(null)

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
        router: 'manhattan',
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
    // 小视窗（Minimap）
    if (minimapContainer) {
      g.use(new MiniMap({
        container: minimapContainer,
        width: 200,
        height: 140,
      }))
    }

    // 事件
    g.on('node:click', ({ node }) => {
      selectedNode.value = node.getData()
    })
    g.on('blank:click', () => {
      selectedNode.value = null
    })
    g.on('node:change:data', ({ node }) => {
      if (node.id === selectedNode.value?.id) {
        selectedNode.value = node.getData()
      }
    })

    // 连接桩 hover 显示/隐藏
    g.on('node:mouseenter', ({ node }) => {
      node.getPorts().forEach(p => {
        if (p.id) node.setPortProp(p.id, 'attrs/circle/opacity', 1)
      })
    })
    g.on('node:mouseleave', ({ node }) => {
      node.getPorts().forEach(p => {
        if (p.id) node.setPortProp(p.id, 'attrs/circle/opacity', 0)
      })
    })

    // 键盘快捷键
    g.use(new Keyboard({ enabled: true }))
    g.bindKey('del', () => {
      const cells = g.getSelectedCells()
      if (cells.length) g.removeCells(cells)
    })
    g.bindKey('backspace', () => {
      const cells = g.getSelectedCells()
      if (cells.length) g.removeCells(cells)
    })
    g.bindKey('ctrl+c', () => g.copy(g.getSelectedCells()))
    g.bindKey('ctrl+v', () => g.paste({ offset: 32 }))
    g.bindKey('ctrl+z', () => g.undo())
    g.bindKey('ctrl+y', () => g.redo())

    graph.value = g
  }

  function initStencil(target: HTMLElement) {
    if (!graph.value) return
    const s = new Stencil({
      target: graph.value,
      search: true,
      title: 'Components',
      groups: [
        { name: 'check', label: 'Check', graphHeight: 110 },
        { name: 'action', label: 'Action', graphHeight: 220 },
        { name: 'control', label: 'Control', graphHeight: 70 },
        { name: 'gateway', label: 'Gateway/Event', graphHeight: 300 },
      ],
      layout: (model) => {
        const nodes = model.getNodes()
        const cols = 2
        nodes.forEach((node, i) => {
          const col = i % cols
          const row = Math.floor(i / cols)
          const h = node.getSize()?.height || 36
          node.setPosition({ x: 10 + col * 85, y: row * (h + 18) + 8 })
        })
      },
      stencilGraphWidth: 180,
    })

    // 注册原子模板（与 ansible_atoms/meta_index.json 同步）
    const atoms = [
      { shape: 'ops-atom', label: 'Disk Check', data: { atom_type: 'disk_check', risk_level: 'low', group: 'check' } },
      { shape: 'ops-atom', label: 'Ping Test', data: { atom_type: 'ping_test', risk_level: 'low', group: 'check' } },
      { shape: 'ops-atom', label: 'Health Check', data: { atom_type: 'health_check', risk_level: 'low', group: 'check' } },
      { shape: 'ops-atom', label: 'Shell', data: { atom_type: 'shell', risk_level: 'medium', group: 'action' } },
      { shape: 'ops-atom', label: 'Upload File', data: { atom_type: 'upload_file', risk_level: 'medium', group: 'action' } },
      { shape: 'ops-atom', label: 'Copy File', data: { atom_type: 'file_copy', risk_level: 'medium', group: 'action' } },
      { shape: 'ops-atom', label: 'Run Script', data: { atom_type: 'script_exec', risk_level: 'medium', group: 'action' } },
      { shape: 'ops-atom', label: 'Backup File', data: { atom_type: 'backup_file', risk_level: 'low', group: 'action' } },
      { shape: 'ops-atom', label: 'Deploy App', data: { atom_type: 'java_deploy', risk_level: 'high', group: 'action' } },
      { shape: 'ops-atom', label: 'Docker Deploy', data: { atom_type: 'docker_deploy', risk_level: 'high', group: 'action' } },
      { shape: 'ops-atom', label: 'Nginx Reload', data: { atom_type: 'nginx_reload', risk_level: 'medium', group: 'action' } },
      { shape: 'ops-atom', label: 'Service Control', data: { atom_type: 'service_control', risk_level: 'high', group: 'control' } },
      { shape: 'ops-atom', label: 'Send Alert', data: { atom_type: 'send_alert', risk_level: 'low', group: 'control' } },
    ]

    // 网关/事件节点
    const gatewayNodes = [
      { shape: 'ops-start-event', label: 'Start', data: { node_type: 'start_event', group: 'gateway' } },
      { shape: 'ops-end-event', label: 'End', data: { node_type: 'end_event', group: 'gateway' } },
      { shape: 'ops-exclusive-gateway', label: 'Condition?', data: { node_type: 'exclusive_gateway', group: 'gateway' } },
      { shape: 'ops-parallel-gateway', label: 'Parallel', data: { node_type: 'parallel_gateway', group: 'gateway' } },
      { shape: 'ops-conditional-parallel-gateway', label: 'Cond. Parallel', data: { node_type: 'conditional_parallel_gateway', group: 'gateway' } },
      { shape: 'ops-converge-gateway', label: 'Converge', data: { node_type: 'converge_gateway', group: 'gateway' } },
    ]

    // 按分组添加（原子节点缩小到 75x36 以适配 2 列布局）
    const atomOpts = { width: 75, height: 36 }
    const checkNodes = atoms.filter(a => a.data.group === 'check').map(a => graph.value!.createNode({ ...a, ...atomOpts }))
    const actionNodes = atoms.filter(a => a.data.group === 'action').map(a => graph.value!.createNode({ ...a, ...atomOpts }))
    const controlNodes = atoms.filter(a => a.data.group === 'control').map(a => graph.value!.createNode({ ...a, ...atomOpts }))
    const gatewayStencilNodes = gatewayNodes.map(a => graph.value!.createNode(a))

    s.load(checkNodes, 'check')
    s.load(actionNodes, 'action')
    s.load(controlNodes, 'control')
    s.load(gatewayStencilNodes, 'gateway')

    // 将 Stencil 容器挂载到目标 DOM 元素
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
    const NODE_GAP = 80
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

  /** 根据节点类型映射到 X6 shape 名称 */
  function resolveNodeShape(node: any): string {
    const typeMap: Record<string, string> = {
      start_event: 'ops-start-event',
      end_event: 'ops-end-event',
      exclusive_gateway: 'ops-exclusive-gateway',
      parallel_gateway: 'ops-parallel-gateway',
      conditional_parallel_gateway: 'ops-conditional-parallel-gateway',
      converge_gateway: 'ops-converge-gateway',
    }
    return typeMap[node.node_type] || 'ops-atom'
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

    // 布局内容节点
    const positions = layoutNodes(contentNodes, contentEdges)
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
      label: startFromData?.label || 'Start',
      data: startFromData || { id: startId, label: 'Start', node_type: 'start_event' },
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
      label: endFromData?.label || 'End',
      data: endFromData || { id: endId, label: 'End', node_type: 'end_event' },
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

    graph.value!.resetCells(cells)
    graph.value!.centerContent()
  }

  function getGraphData(): { nodes: any[]; edges: any[] } {
    if (!graph.value) return { nodes: [], edges: [] }
    const cells = graph.value.getCells()
    const nodes: any[] = []
    const edges: any[] = []

    for (const cell of cells) {
      if (cell.isNode()) {
        const data = cell.getData() || {}
        nodes.push({ ...data, id: data.id || cell.id })
      } else if (cell.isEdge()) {
        const source = cell.getSource()
        const target = cell.getTarget()
        const labels = cell.getLabels?.() || []
        edges.push({
          from: typeof source === 'object' ? source.cell : source,
          to: typeof target === 'object' ? target.cell : target,
          sourcePort: typeof source === 'object' ? source.port : undefined,
          targetPort: typeof target === 'object' ? target.port : undefined,
          label: labels.length ? (labels[0].attrs?.text?.text || '') : '',
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

  function canUndo() {
    return graph.value?.canUndo() ?? false
  }

  function canRedo() {
    return graph.value?.canRedo() ?? false
  }

  function destroy() {
    if (graph.value) {
      graph.value.dispose()
      graph.value = null
    }
  }

  onBeforeUnmount(() => destroy())

  return {
    graph, stencil, selectedNode,
    initGraph, initStencil, loadGraphData, getGraphData,
    aiLayout,
    undo, redo, canUndo, canRedo, destroy,
  }
}
