import { ref, shallowRef, onBeforeUnmount } from 'vue'
import { Graph, Shape } from '@antv/x6'
import type { OutputField, VariableOption, ConditionRule, ConditionStruct } from '../utils/shapes'
import { DEFAULT_OUTPUT_FIELDS, SYSTEM_VARIABLES } from '../utils/shapes'

/** 通用 Graph 选项 — 设计/监控/预览模式通过 mode 区分 */
export interface GraphCanvasOptions {
  mode: 'design' | 'monitor' | 'preview'
  /** 是否允许交互（监控模式为 false） */
  interacting?: boolean
  /** 用户开始从端口拖拽连线时的回调 */
  onConnectStart?: () => void
}

/** 创建通用 Graph 实例的共享配置 */
function createDefaultGraph(
  container: HTMLElement,
  options: GraphCanvasOptions,
): Graph {
  const isDesign = options.mode === 'design'
  return new Graph({
    container,
    grid: true,
    panning: { enabled: options.mode !== 'preview' },
    mousewheel: { enabled: true, zoomAtMousePosition: true },
    interacting: options.interacting ?? isDesign,
    connecting: {
      router: {
        name: 'manhattan',
        args: { padding: { top: 30, bottom: 30, left: 30, right: 30 }, step: 20, maxLoopCount: 10000 },
      },
      connector: 'rounded',
      ...(isDesign ? {
        anchor: { name: 'center', args: { dx: 0, dy: 0 } },
        connectionPoint: { name: 'boundary', args: { sticky: true } },
        allowBlank: false,
        allowNode: true,
        allowPort: true,
        allowMulti: true,
        allowLoop: false,
        snap: true,
        highlight: true,
        validateConnection({ sourceCell, targetCell, sourceMagnet, targetMagnet, sourcePort, targetPort }) {
          if (!sourceMagnet) return false
          if (!targetPort && !targetMagnet) return false
          // 禁止从 end_event 连出（end_event 只能有入边）
          if (sourceCell?.getData()?.node_type === 'end_event') return false
          // 禁止连向 start_event（start_event 只能有出边）
          if (targetCell?.getData()?.node_type === 'start_event') return false
          return true
        },
        createEdge() {
          options.onConnectStart?.()
          return new Shape.Edge({
            attrs: {
              line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' },
            },
          })
        },
      } : {}),
    },
    highlighting: isDesign ? {
      nodeAvailable: { name: 'stroke', args: { padding: 4, attrs: { stroke: '#409EFF' } } },
    } : undefined,
  })
}

/** BFS 分层布局 — 为节点分配 x/y 坐标 */
export function layoutNodes(
  nodes: any[],
  edges: { from: string; to: string }[],
  options?: { layerGap?: number; nodeGap?: number; startX?: number; startY?: number },
): Record<string, { x: number; y: number }> {
  const LAYER_GAP = options?.layerGap ?? 480
  const NODE_GAP = options?.nodeGap ?? 120
  const START_X = options?.startX ?? 50
  const START_Y = options?.startY ?? 40

  // 计算入度 & 邻接表
  const inDeg: Record<string, number> = {}
  const adj: Record<string, string[]> = {}
  for (const n of nodes) { inDeg[n.id] = 0; adj[n.id] = [] }
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    if (adj[f]) adj[f].push(t)
    if (inDeg[t] != null) inDeg[t]++
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
  // 孤立节点归入第 0 层
  for (const n of nodes) {
    if (level[n.id] == null) level[n.id] = 0
  }

  // 按层分组
  const layers: Record<number, string[]> = {}
  for (const n of nodes) {
    const lv = level[n.id]
    if (!layers[lv]) layers[lv] = []
    layers[lv].push(n.id)
  }

  // 分配坐标
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

/** 条件运算符列表（模块级导出，供外部直接引用） */
export const CONDITION_OPS = ['==', '!=', '>', '<', '>=', '<=', 'contains', 'not contains', 'startsWith', 'endsWith', 'regex'] as const

/** 根据字段类型过滤可用运算符 */
export function opsForType(fieldType: 'string' | 'number' | 'boolean'): string[] {
  if (fieldType === 'boolean') return ['==', '!=']
  if (fieldType === 'number') return ['==', '!=', '>', '<', '>=', '<=']
  return ['==', '!=', 'contains', 'not contains', 'startsWith', 'endsWith', 'regex']
}

/**
 * 结构化条件 → ${...} 表达式字符串
 *
 * 规则:
 *   {source: "node_1", field: "cpu", op: ">", value: "80"}
 *   → "${node_1.cpu} > 80"
 *
 * 字符串值自动加引号:
 *   {fieldType: "string", value: "ok"}
 *   → "${node_1.status} == \"ok\""
 *
 * 多条件 AND/OR 连接:
 *   [{...}, {...}] with logic "AND"
 *   → "${node_1.cpu} > 80 AND ${node_1.mem} < 50"
 */
export function generateConditionExpr(rules: ConditionRule[], logic: 'AND' | 'OR'): string {
  if (!rules || rules.length === 0) return ''

  const parts = rules.map((r) => {
    const ref = `\${${r.source}.${r.field}}`

    // 字符串值需要加引号（boolean 和 number 不加）
    let val = r.value
    if (r.fieldType === 'string' || (r.valueType === 'string' && r.fieldType !== 'boolean' && r.fieldType !== 'number')) {
      val = `"${r.value.replace(/"/g, '\\"')}"`
    }

    return `${ref} ${r.op} ${val}`
  })

  return parts.join(` ${logic} `)
}

/**
 * 提取指定节点的输出字段列表（纯函数版本，不依赖 composable）
 */
export function extractNodeOutputFields(
  nodeData: any,
  nodeType: string,
): OutputField[] {
  if (nodeData._outputSchema && Array.isArray(nodeData._outputSchema)) {
    return nodeData._outputSchema.map((f: any) => ({
      key: f.key || f.name,
      label: f.name || f.key,
      type: f.type || 'string',
      description: f.description || '',
    }))
  }
  // 按原子类型返回（插件定义的 output_schema 未同步到前端时的兜底）
  const atomDefaults: Record<string, OutputField[]> = {
    test_print_time: [
      { key: 'test1', label: 'test1', type: 'number', description: '随机数值 1-10' },
    ],
  }
  if (nodeData.atom_type && atomDefaults[nodeData.atom_type]) {
    return atomDefaults[nodeData.atom_type]
  }
  const defaults = DEFAULT_OUTPUT_FIELDS[nodeType]
  if (defaults && defaults.length > 0) return defaults
  return [{ key: '_result', label: '_result', type: 'boolean', description: '执行结果' }]
}

/**
 * 从画布节点列表提取所有可用变量（纯函数版本）
 *
 * @param nodes 画布节点列表（从 getGraphData 获取）
 * @param store 可选的 Pinia store
 */
export function extractAvailableVariables(
  nodes: { id: string; node_type: string; label: string; [key: string]: any }[],
  store?: any,
): VariableOption[] {
  const result: VariableOption[] = []

  // 上游节点输出
  for (const n of nodes) {
    if (n.node_type === 'end_event') continue
    const label = n.label || n.id
    const fields = extractNodeOutputFields(n, n.node_type)
    for (const f of fields) {
      result.push({
        source: n.id,
        sourceLabel: `${n.id} (${label})`,
        sourceType: 'node',
        field: f.key,
        fieldLabel: `${n.id}.${f.key} (${f.type})`,
        fieldType: f.type,
      })
    }
  }

  // 全局变量
  const globalVars = store?.globalVariables || {}
  for (const [key, val] of Object.entries<any>(globalVars)) {
    let varType: 'string' | 'number' | 'boolean' = 'string'
    if (val?.type === 'int' || val?.type === 'float') varType = 'number'
    else if (val?.type === 'bool') varType = 'boolean'
    result.push({
      source: 'global', sourceLabel: 'Global Variables', sourceType: 'global',
      field: key, fieldLabel: `${key} (${varType})`, fieldType: varType,
    })
  }

  // 项目环境变量
  const projectVars = store?.projectEnvVars || {}
  for (const [key] of Object.entries<any>(projectVars)) {
    result.push({
      source: 'project', sourceLabel: 'Project Env Vars', sourceType: 'project',
      field: key, fieldLabel: `${key} (string)`, fieldType: 'string',
    })
  }

  // 系统变量
  for (const sv of SYSTEM_VARIABLES) {
    result.push({
      source: '_system', sourceLabel: 'System Variables', sourceType: 'system',
      field: sv.key, fieldLabel: `${sv.key} (${sv.type})`, fieldType: sv.type,
    })
  }

  return result
}

/**
 * 校验条件表达式
 *
 * 检查项:
 *   1. ${...} 括号匹配
 *   2. 引号匹配
 *   3. node_id 引用存在性（需传入 nodeId 集合）
 */
export function validateConditionExpr(
  conditionString: string,
  nodeIds?: Set<string>,
): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  if (!conditionString.trim()) return { valid: true, errors: [] }

  // 检查 ${...} 括号匹配
  let depth = 0
  for (const ch of conditionString) {
    if (ch === '{') depth++
    if (ch === '}') depth--
    if (depth < 0) {
      errors.push('多余的关闭括号 "}"')
      return { valid: false, errors }
    }
  }
  if (depth !== 0) {
    errors.push('${...} 括号不匹配')
    return { valid: false, errors }
  }

  // 检查引号匹配
  let quoteCount = 0
  for (const ch of conditionString) {
    if (ch === '"' || ch === "'") quoteCount++
  }
  if (quoteCount % 2 !== 0) {
    errors.push('引号不匹配')
  }

  // 检查 node_id 引用存在性
  if (nodeIds && nodeIds.size > 0) {
    const EXPR_PATTERN = /\$\{([^}]*)\}/g
    const VAR_REF_PATTERN = /([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)/g
    let match: RegExpExecArray | null
    while ((match = EXPR_PATTERN.exec(conditionString)) !== null) {
      const expr = match[1]
      let varMatch: RegExpExecArray | null
      VAR_REF_PATTERN.lastIndex = 0
      while ((varMatch = VAR_REF_PATTERN.exec(expr)) !== null) {
        const refNodeId = varMatch[1]
        // 跳过 global/project/_system 前缀
        if (['global', 'project', '_system'].includes(refNodeId)) continue
        if (!nodeIds.has(refNodeId)) {
          errors.push(`引用的节点 '${refNodeId}' 不存在`)
        }
      }
    }
  }

  return { valid: errors.length === 0, errors }
}

/** 默认节点 label 映射 */
export function defaultNodeLabel(nodeType: string): string {
  const map: Record<string, string> = {
    exclusive_gateway: 'Exclusive',
    parallel_gateway: 'Parallel',
    conditional_parallel_gateway: 'Conditional',
    converge_gateway: 'Converge',
    approval: 'Approval',
    subprocess: 'SubProcess',
    atom: 'Task',
  }
  return map[nodeType] || ''
}

/**
 * useGraphCanvas — 通用 X6 Graph composable
 *
 * 提供 Graph 初始化、BFS 布局、缩放、自适应、生命周期管理等共享逻辑。
 * 设计模式（design）差异：stencil/history/clipboard/selection/keyboard 等插件由
 * useDesignCanvas 附加；监控模式（monitor）差异由 MonitorCanvas 自行控制。
 */
export function useGraphCanvas(containerId: string, options: GraphCanvasOptions) {
  const graph = shallowRef<Graph | null>(null)
  const zoomLevel = ref(1)

  /** 初始化 Graph（基础共享配置） */
  function initGraph() {
    const container = document.getElementById(containerId)
    if (!container) return

    if (graph.value) {
      graph.value.dispose()
    }

    graph.value = createDefaultGraph(container, options)

    graph.value.on('scale', () => {
      zoomLevel.value = graph.value?.zoom() || 1
    })
  }

  // ── 缩放控制 ──

  function zoomIn() {
    graph.value?.zoom(0.15)
    zoomLevel.value = graph.value?.zoom() || 1
  }

  function zoomOut() {
    graph.value?.zoom(-0.15)
    zoomLevel.value = graph.value?.zoom() || 1
  }

  function fitCanvas() {
    graph.value?.centerContent()
    graph.value?.zoomToFit({ padding: 40 })
    zoomLevel.value = graph.value?.zoom() || 1
  }

  // ── 自适应 ──

  let resizeObserver: ResizeObserver | null = null

  function enableResize() {
    const container = document.getElementById(containerId)
    if (!container) return
    resizeObserver = new ResizeObserver(() => {
      if (graph.value) {
        const w = container.clientWidth
        const h = container.clientHeight
        if (w > 0 && h > 0) graph.value.resize(w, h)
      }
    })
    resizeObserver.observe(container)
  }

  let visibilityHandler: (() => void) | null = null

  function enableVisibilityRefresh() {
    visibilityHandler = () => {
      if (document.visibilityState === 'visible' && graph.value) {
        const container = document.getElementById(containerId)
        if (container) {
          const w = container.clientWidth
          const h = container.clientHeight
          if (w > 0 && h > 0) {
            graph.value.resize(w, h)
            graph.value.centerContent()
          }
        }
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)
  }

  // ── 导出 Graph 数据（通用格式） ──

  function getGraphData(): { nodes: any[]; edges: any[] } {
    if (!graph.value) return { nodes: [], edges: [] }
    const cells = graph.value.getCells()
    const nodes: any[] = []
    const edges: any[] = []

    for (const cell of cells) {
      if (cell.isNode()) {
        const data = cell.getData() || {}
        const pos = cell.getPosition()
        // Ensure label is present — X6 stores it on attrs, not in getData()
        if (!data.label) {
          const nodeLabels = cell.getLabels?.() || []
          data.label = nodeLabels[0]?.attrs?.text?.text || ''
        }
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

  // ── 生命周期 ──

  function destroy() {
    resizeObserver?.disconnect()
    resizeObserver = null
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler)
      visibilityHandler = null
    }
    if (graph.value) {
      graph.value.dispose()
      graph.value = null
    }
  }

  onBeforeUnmount(() => destroy())

  return {
    graph,
    zoomLevel,
    initGraph,
    zoomIn,
    zoomOut,
    fitCanvas,
    getGraphData,
    enableResize,
    enableVisibilityRefresh,
    destroy,
  }
}
