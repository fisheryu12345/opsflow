import { Graph, Shape, Node } from '@antv/x6'

// ── HMR 防重复注册 ──

function registerOnce(name: string, config: any) {
  try {
    Shape.Rect.define({ shape: name, ...config })
  } catch {
    // HMR 热更新时已注册，忽略
  }
}

function registerNodeOnce(name: string, config: any) {
  try {
    Node.define({ shape: name, ...config })
  } catch {
    // HMR 热更新时已注册，忽略
  }
}

function registerCircleOnce(name: string, config: any) {
  try {
    Shape.Circle.define({ shape: name, ...config })
  } catch {
    // HMR 热更新时已注册，忽略
  }
}

function registerGraphOnce(name: string, config: any) {
  try {
    Graph.registerNode(name, config, true)
  } catch {
    // HMR 热更新时已注册，忽略
  }
}

// ============================================================
// 参考案例样式：agent-card 卡片设计（260×96）
//   .agent-card { border:1px solid #5F95FF; border-radius:8px;
//                 padding:12px; background:#fff; width:260px; height:96px }
//   .header { display:flex; align-items:center; gap:12px }
//   .icon   { width:32px; height:32px; border-radius:8px; display:flex;
//             align-items:center; justify-content:center; font-weight:600 }
//   .title  { font-size:16px; font-weight:600 }
//   .desc   { font-size:13px; color:rgba(0,0,0,0.65) }
//   .actions { margin-left:auto }
// ============================================================

export const CARD_WIDTH = 208
export const CARD_HEIGHT = 56

// ── 端口常量 ──
export const PORT_DOT_RADIUS = 4
const COLOR_PORT_GRAY = '#C2C8D5'
const COLOR_PORT_BLUE = '#5F95FF'

// ── Group → icon/color 映射（后端不存 emoji，前端维护映射表） ──

const GROUP_CONFIG: Record<string, { icon: string; color: string }> = {
  '通用工具':  { icon: '⚙', color: '#409EFF' },
  'HTTP':      { icon: '↔', color: '#67C23A' },
  'Ansible':   { icon: '▶', color: '#E6A23C' },
  'Monitor':   { icon: '◉', color: '#F56C6C' },
  'ESXi':      { icon: '☰', color: '#9B59B6' },
  'Redfish':   { icon: '≈', color: '#00BCD4' },
  'ServiceNow':{ icon: '✉', color: '#FF9800' },
  'NetApp':    { icon: '◇', color: '#607D8B' },
  'Pmax':      { icon: '▲', color: '#795548' },
  '验证工具':  { icon: '✓', color: '#67C23A' },
}

const DEFAULT_COLOR = '#409EFF'
const DEFAULT_ICON = '◇'

function resolveGroup(group: string) {
  const cfg = GROUP_CONFIG[group]
  return cfg || { icon: DEFAULT_ICON, color: DEFAULT_COLOR }
}

// ── 端口群组定义（参考案例：visibility 控制显隐） ──

const PORT_ATTRS = {
  r: PORT_DOT_RADIUS,
  magnet: true,
  stroke: COLOR_PORT_GRAY,
  strokeWidth: 1,
  fill: COLOR_PORT_GRAY,
  style: { visibility: 'hidden' as const },
}

const PORT_GROUPS = {
  top:    { position: { name: 'top' },    attrs: { circle: { ...PORT_ATTRS } } },
  right:  { position: { name: 'right' },  attrs: { circle: { ...PORT_ATTRS } } },
  bottom: { position: { name: 'bottom' }, attrs: { circle: { ...PORT_ATTRS } } },
  left:   { position: { name: 'left' },   attrs: { circle: { ...PORT_ATTRS } } },
}
const PORT_ITEMS = [
  { id: 'top', group: 'top' },
  { id: 'right', group: 'right' },
  { id: 'bottom', group: 'bottom' },
  { id: 'left', group: 'left' },
]

// ── 端口工具函数（参考案例：isPortConnected → setPortDot → showNodePorts） ──

/** 判断节点的某个端口是否有已连接的边 */
export function isPortConnected(node: Node, portId: string): boolean {
  const model = node.model
  if (!model) return false
  const edges = model.getConnectedEdges(node)
  return edges.some(
    (e) =>
      (e.getSourceCellId() === node.id && e.getSourcePortId() === portId) ||
      (e.getTargetCellId() === node.id && e.getTargetPortId() === portId),
  )
}

/** 设置端口显隐 */
function setPortVisible(node: Node, portId: string, visible: boolean) {
  node.setPortProp(portId, 'attrs/circle/style/visibility', visible ? 'visible' : 'hidden')
}

/** 设置端口颜色 */
function setPortColor(node: Node, portId: string, color: string) {
  node.setPortProp(portId, 'attrs/circle/fill', color)
  node.setPortProp(portId, 'attrs/circle/stroke', color)
}

/** 设置端口显隐+颜色 */
function setPortDot(node: Node, portId: string, visible: boolean, color?: string) {
  setPortVisible(node, portId, visible)
  if (color) setPortColor(node, portId, color)
}

/** 控制节点所有端口的显隐（参考案例：showNodePorts） */
export function showNodePorts(node: Node, show: boolean) {
  const ps = node.getPorts()
  for (let i = 0; i < ps.length; i += 1) {
    const id = ps[i].id as string
    if (show) {
      setPortVisible(node, id, true)
    } else {
      const connected = isPortConnected(node, id)
      setPortDot(node, id, connected, connected ? COLOR_PORT_BLUE : COLOR_PORT_GRAY)
    }
  }
}

/** 刷新节点所有端口的连接状态样式 */
export function refreshPortStates(node: Node) {
  const ps = node.getPorts()
  for (let i = 0; i < ps.length; i += 1) {
    const id = ps[i].id as string
    const connected = isPortConnected(node, id)
    setPortDot(node, id, connected, connected ? COLOR_PORT_BLUE : COLOR_PORT_GRAY)
  }
}

// ── 生成原子卡片 attrs（参考案例 card 布局，紧凑版 208×70） ──
//
//   ┌── Card 208×70, rx:8 ────────────────────────────┐
//   │                                                    │
//   │  ┌── icon ──┐  Title 15px                  [×]     │  y:8～36
//   │  │  28×28   │                                       │
//   │  └──────────┘                                       │
//   │  Description 12px                                   │  y:40～60
//   │                                              ●      │  status-dot
//   └────────────────────────────────────────────────────┘

export function makeAtomAttrs(
  color: string,
  icon: string,
  label: string,
  desc: string,
  configured?: boolean,
) {
  const c = color || DEFAULT_COLOR
  // icon 背景色：color 18% 透明度填充 + 30% 描边
  const iconBg = `${c}18`
  const iconStroke = `${c}30`
  const iconText = c

  return {
    // 背景阴影
    shadow: { fill: 'rgba(0,0,0,0.06)', x: 2, y: 2, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8 },
    // 卡片主体（border 使用分组色）
    body: { fill: '#FFF', stroke: c, strokeWidth: 1, x: 0, y: 0, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8 },
    // 图标背景（28×28 圆角矩形，紧凑版）
    'icon-bg': { fill: iconBg, stroke: iconStroke, strokeWidth: 1, x: 10, y: 3, width: 28, height: 28, rx: 6 },
    // 图标文字
    icon: { text: icon || DEFAULT_ICON, fill: iconText, fontSize: 13, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 24, refY: 17 },
    // 标题
    label: { text: label, fill: '#303133', fontSize: 14, fontWeight: 600, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'middle', refX: 48, refY: 17 },
    // 描述（靠底对齐）
    desc: { text: desc || '', fill: 'rgba(0,0,0,0.65)', fontSize: 12, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'bottom', refX: 10, refY: 56 },
    // 删除按钮（默认隐藏，hover 显示）
    'del-btn-bg': { fill: '#FF4D4F', cx: 196, cy: 12, r: 10, cursor: 'pointer', visibility: 'hidden' as const },
    'del-btn-icon': { text: '✕', fill: '#FFF', fontSize: 12, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 196, refY: 13, cursor: 'pointer', visibility: 'hidden' as const },
    // 状态点：绿=已配置, 橙=待配置, 透明=默认
    'status-dot': {
      fill: configured === true ? '#67C23A' : configured === false ? '#E6A23C' : 'transparent',
      cx: 200, cy: 50, r: 4, stroke: 'none',
    },
  }
}

/** 运行时根据节点 data 更新原子卡片视觉 */
export function updateAtomNode(node: Node) {
  const data = node.getData() || {}
  const groupName = data.group || ''
  const groupCfg = resolveGroup(groupName)
  const label = data.label || '未命名节点'
  const risk = data.risk_level || ''
  const desc = groupName ? `${groupName}${risk ? ' · ' + risk : ''}` : (data.atom_type ? `[${data.atom_type}]` : '')
  const configured = !!data.atom_type
  node.setAttrs(makeAtomAttrs(groupCfg.color, groupCfg.icon, label, desc, configured))
}

// ── ops-atom: 卡片式原子节点（208×64，参考案例 card 设计） ──

const atomMarkup = [
  { tagName: 'rect', selector: 'shadow' },
  { tagName: 'rect', selector: 'body' },
  { tagName: 'rect', selector: 'icon-bg' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
  { tagName: 'text', selector: 'desc' },
  { tagName: 'circle', selector: 'del-btn-bg' },
  { tagName: 'text', selector: 'del-btn-icon' },
  { tagName: 'circle', selector: 'status-dot' },
]

registerOnce('ops-atom', {
  width: CARD_WIDTH,
  height: CARD_HEIGHT,
  markup: atomMarkup,
  attrs: makeAtomAttrs(DEFAULT_COLOR, DEFAULT_ICON, '选择插件', '', false),
  ports: { groups: PORT_GROUPS, items: PORT_ITEMS },
})

// ── ops-atom-stencil: 调色板用图标+标题预览 ──

const stencilMarkup = [
  { tagName: 'rect', selector: 'body' },
  { tagName: 'rect', selector: 'iconRect' },
  { tagName: 'text', selector: 'iconLabel' },
  { tagName: 'text', selector: 'title' },
]

registerGraphOnce('ops-atom-stencil', {
  inherit: 'rect',
  width: 168,
  height: 48,
  markup: stencilMarkup,
  attrs: {
    body: { fill: '#FFF', stroke: '#5F95FF', strokeWidth: 1, rx: 8, ry: 8 },
    iconRect: { width: 28, height: 28, rx: 6, ry: 6, refX: 10, refY: 10, fill: '#F0F5FF' },
    iconLabel: { refX: 24, refY: 24, textAnchor: 'middle', textVerticalAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: '#1D39C4' },
    title: { refX: 46, refY: 24, textAnchor: 'start', textVerticalAnchor: 'middle', fontSize: 13, fontWeight: 600, fill: '#141414' },
  },
  ports: { groups: PORT_GROUPS, items: PORT_ITEMS },
})

// ── ops-subprocess-stencil: 调色板用图标+标题预览（虚边 + S） ──

registerGraphOnce('ops-subprocess-stencil', {
  inherit: 'rect',
  width: 168,
  height: 48,
  markup: stencilMarkup,
  attrs: {
    body: { fill: '#EBF5FB', stroke: '#2980B9', strokeWidth: 1.5, rx: 8, ry: 8, strokeDasharray: '5 3' },
    iconRect: { width: 28, height: 28, rx: 6, ry: 6, refX: 10, refY: 10, fill: '#D6EAF8' },
    iconLabel: { refX: 24, refY: 24, textAnchor: 'middle', textVerticalAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: '#2980B9' },
    title: { refX: 46, refY: 24, textAnchor: 'start', textVerticalAnchor: 'middle', fontSize: 13, fontWeight: 600, fill: '#2C3E50' },
  },
  ports: { groups: PORT_GROUPS, items: PORT_ITEMS },
})

/** 创建调色板预览节点配置 */
export function createStencilNode(cfg: { iconText?: string; title?: string }) {
  return {
    shape: 'ops-atom-stencil',
    width: 168,
    height: 48,
    attrs: {
      iconRect: { fill: '#F0F5FF' },
      iconLabel: { text: cfg.iconText || '' },
      title: { text: cfg.title || '' },
    },
    data: { node_type: 'atom' },
  }
}

// ── Start event — 绿色圆（画布隐藏 label） ──

const circleMarkup = [
  { tagName: 'circle', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

registerCircleOnce('ops-start-event', {
  width: 56,
  height: 56,
  markup: circleMarkup,
  attrs: {
    body: { fill: '#E1F3D8', stroke: '#67C23A', strokeWidth: 2.5, cx: 28, cy: 28, r: 26 },
    icon: { text: '▶', fill: '#67C23A', fontSize: 48, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 30, refY: 30 },
    label: { fill: '#333', fontSize: 11, fontFamily: 'Microsoft YaHei', refX: 28, refY: 72, textAnchor: 'middle', visibility: 'hidden' as const },
  },
  ports: {
    groups: { out: { position: { name: 'right' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, style: { visibility: 'hidden' }, stroke: COLOR_PORT_GRAY, strokeWidth: 1 } } } },
    items: [{ id: 'out', group: 'out' }],
  },
})

registerCircleOnce('ops-end-event', {
  width: 56,
  height: 56,
  markup: circleMarkup,
  attrs: {
    body: { fill: '#FDE2E2', stroke: '#F56C6C', strokeWidth: 2.5, cx: 28, cy: 28, r: 26 },
    icon: { text: '■', fill: '#F56C6C', fontSize: 64, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 28, refY: 24 },
    label: { fill: '#333', fontSize: 11, fontFamily: 'Microsoft YaHei', refX: 28, refY: 72, textAnchor: 'middle', visibility: 'hidden' as const },
  },
  ports: {
    groups: { in: { position: { name: 'left' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, style: { visibility: 'hidden' }, stroke: COLOR_PORT_GRAY, strokeWidth: 1 } } } },
    items: [{ id: 'in', group: 'in' }],
  },
})

// ── Gateway 菱形基础 markup ──

const diamondMarkup = [
  { tagName: 'path', selector: 'shadow' },
  { tagName: 'path', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

function diamondAttrs(color: string, iconText: string, iconSize = 24) {
  return {
    shadow: { d: 'M 37 7 L 67 37 L 37 67 L 7 37 Z', fill: `${color}15`, stroke: 'none' },
    body: { d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z', fill: '#FFF', stroke: color, strokeWidth: 2 },
    icon: { text: iconText, fill: color, fontSize: iconSize, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 35, refY: 33 },
    label: { fill: '#333', fontSize: 11, fontFamily: 'Microsoft YaHei', textAnchor: 'middle', textVerticalAnchor: 'top', refX: 35, refY: 74, visibility: 'hidden' as const },
  }
}

function diamondPorts() {
  return {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, stroke: COLOR_PORT_GRAY, strokeWidth: 1, style: { visibility: 'hidden' } } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, stroke: COLOR_PORT_GRAY, strokeWidth: 1, style: { visibility: 'hidden' } } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, stroke: COLOR_PORT_GRAY, strokeWidth: 1, style: { visibility: 'hidden' } } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, stroke: COLOR_PORT_GRAY, strokeWidth: 1, style: { visibility: 'hidden' } } } },
    },
    items: PORT_ITEMS,
  }
}

// Gateways — 看图知意图标（70×70，保持独立尺寸）
registerNodeOnce('ops-exclusive-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#E6A23C', '⊗', 28), ports: diamondPorts() })
registerNodeOnce('ops-parallel-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#409EFF', '⊞', 28), ports: diamondPorts() })
registerNodeOnce('ops-conditional-parallel-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#5CADFF', '◐', 26), ports: diamondPorts() })
registerNodeOnce('ops-converge-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#909399', '⨁', 28), ports: diamondPorts() })
registerNodeOnce('ops-approval', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#9B59B6', '✓', 28), ports: diamondPorts() })

// ── ops-subprocess: 卡片式虚线框（与 ops-atom 一致布局，208×64） ──

const subMarkup = [
  { tagName: 'rect', selector: 'shadow' },
  { tagName: 'rect', selector: 'body' },
  { tagName: 'rect', selector: 'icon-bg' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
  { tagName: 'text', selector: 'desc' },
  { tagName: 'circle', selector: 'del-btn-bg' },
  { tagName: 'text', selector: 'del-btn-icon' },
]

registerOnce('ops-subprocess', {
  width: CARD_WIDTH,
  height: CARD_HEIGHT,
  markup: subMarkup,
  attrs: {
    shadow: { fill: 'rgba(41,128,185,0.08)', x: 2, y: 2, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8 },
    body: { fill: '#F0F8FF', stroke: '#2980B9', strokeWidth: 1.5, x: 0, y: 0, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8, strokeDasharray: '6 3' },
    'icon-bg': { fill: '#D6EAF8', stroke: '#85C1E9', strokeWidth: 1, x: 10, y: 3, width: 28, height: 28, rx: 6 },
    icon: { text: 'S', fill: '#2980B9', fontSize: 13, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 24, refY: 17 },
    label: { text: 'Subprocess', fill: '#1A5276', fontSize: 14, fontWeight: 600, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'top', refX: 48, refY: 4 },
    desc: { text: '', fill: 'rgba(0,0,0,0.65)', fontSize: 12, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'bottom', refX: 10, refY: 54 },
    'del-btn-bg': { fill: '#FF4D4F', cx: 196, cy: 12, r: 10, cursor: 'pointer', visibility: 'hidden' as const },
    'del-btn-icon': { text: '✕', fill: '#FFF', fontSize: 12, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 196, refY: 13, cursor: 'pointer', visibility: 'hidden' as const },
  },
  ports: { groups: PORT_GROUPS, items: PORT_ITEMS },
})

// ── 共享类型从 types/ 集中导入 ──
export type { OutputField, VariableOption, ConditionRule, ConditionStruct } from '../types'

// ── 边条件验证集中（从前端 3 个分散文件移至此处） ──

/** ${...} 变量引用正则 */
export const EXPR_PATTERN = /\$\{([^}]*)\}/g
/** var.field 匹配正则 */
export const VAR_REF_PATTERN = /([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)/g

/** 默认边样式（6 处副本集中至此） */
export const DEFAULT_EDGE_ATTRS = {
  line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' },
}

/** 检查边条件表达式的括号和引号匹配 */
export function checkConditionSyntax(expr: string): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  let braceCount = 0
  let inQuote: string | null = null
  for (const ch of expr) {
    if (ch === '"' || ch === "'") {
      inQuote = inQuote === ch ? null : (inQuote ?? ch)
      continue
    }
    if (!inQuote) {
      if (ch === '{') braceCount++
      if (ch === '}') braceCount--
    }
  }
  if (braceCount !== 0) errors.push('Braces mismatch')
  if (inQuote) errors.push('Unclosed quote')
  return { valid: errors.length === 0, errors }
}

/** 检查条件中的节点引用是否存在于当前画布 */
export function checkConditionRefs(
  expr: string,
  nodeIds: Set<string>,
): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  const match = EXPR_PATTERN.exec(expr)
  if (match) {
    const refMatch = VAR_REF_PATTERN.exec(match[1])
    if (refMatch && !nodeIds.has(refMatch[1]) && refMatch[1] !== '_result') {
      errors.push(`Unknown node reference: ${refMatch[1]}`)
    }
  }
  return { valid: errors.length === 0, errors }
}

/** X6 节点缩放辅助 */
export const CARD_WIDTH = 208
export const CARD_HEIGHT = 56

export function resizeCard(node: any): void {
  if (node.resize) {
    node.resize(CARD_WIDTH, CARD_HEIGHT)
  }
}

/** 节点类型的默认输出字段 */
export const DEFAULT_OUTPUT_FIELDS: Record<string, OutputField[]> = {
  start_event: [],
  end_event: [],
  exclusive_gateway: [],
  parallel_gateway: [],
  conditional_parallel_gateway: [],
  converge_gateway: [],
  approval: [
    { key: '_result', label: '_result', type: 'boolean', description: '审批结果' },
    { key: 'approved_by', label: 'approved_by', type: 'string', description: '审批人' },
  ],
  subprocess: [
    { key: '_result', label: '_result', type: 'boolean', description: '子流程执行结果' },
  ],
}

/** 系统变量列表 */
export const SYSTEM_VARIABLES: OutputField[] = [
  { key: 'timestamp', label: '_system.timestamp', type: 'string', description: '当前时间戳' },
  { key: 'current_user', label: '_system.current_user', type: 'string', description: '当前用户' },
]

// ── Node type map ──

export function resolveNodeShape(node: any): string {
  const typeMap: Record<string, string> = {
    start_event: 'ops-start-event',
    end_event: 'ops-end-event',
    exclusive_gateway: 'ops-exclusive-gateway',
    parallel_gateway: 'ops-parallel-gateway',
    conditional_parallel_gateway: 'ops-conditional-parallel-gateway',
    converge_gateway: 'ops-converge-gateway',
    approval: 'ops-approval',
    subprocess: 'ops-subprocess',
  }
  return typeMap[node.node_type] || 'ops-atom'
}
