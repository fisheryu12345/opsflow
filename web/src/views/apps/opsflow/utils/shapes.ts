import { Shape, Node } from '@antv/x6'

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

const DEFAULT_GROUP_COLOR = '#409EFF'
const DEFAULT_GROUP_ICON = '◇'

// ── Port 常量 ──
const PORT_RADIUS = 5
const COLOR_PORT_GRAY = '#C2C8D5'
const COLOR_PORT_BLUE = '#5F95FF'

/** 根据分组名解析 icon 和 color */
function resolveGroupConfig(group: string): { icon: string; color: string } {
  const cfg = GROUP_CONFIG[group]
  return cfg || { icon: DEFAULT_GROUP_ICON, color: DEFAULT_GROUP_COLOR }
}

// ── Port 通用群组定义（所有形状共享相同的默认端口样式） ──

const BASE_PORT_ATTRS = {
  r: PORT_RADIUS,
  magnet: true,
  stroke: COLOR_PORT_GRAY,
  strokeWidth: 1.5,
  fill: COLOR_PORT_GRAY,
  opacity: 0,
}

const PORT_GROUPS = {
  top: { position: { name: 'top' }, attrs: { circle: { ...BASE_PORT_ATTRS } } },
  bottom: { position: { name: 'bottom' }, attrs: { circle: { ...BASE_PORT_ATTRS } } },
  left: { position: { name: 'left' }, attrs: { circle: { ...BASE_PORT_ATTRS } } },
  right: { position: { name: 'right' }, attrs: { circle: { ...BASE_PORT_ATTRS } } },
}

const PORT_ITEMS = [
  { id: 'top', group: 'top' },
  { id: 'bottom', group: 'bottom' },
  { id: 'left', group: 'left' },
  { id: 'right', group: 'right' },
]

// ── Port 连接状态工具函数 ──

/** 判断节点的某个 port 是否有已连接的边 */
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

/** 设置单个 port 的连接状态样式：已连接=蓝色常亮，未连接=灰色隐藏 */
export function setPortState(node: Node, portId: string, connected: boolean) {
  const fill = connected ? COLOR_PORT_BLUE : COLOR_PORT_GRAY
  const stroke = connected ? COLOR_PORT_BLUE : COLOR_PORT_GRAY
  const opacity = connected ? 1 : 0
  node.setPortProp(portId, 'attrs/circle/fill', fill)
  node.setPortProp(portId, 'attrs/circle/stroke', stroke)
  node.setPortProp(portId, 'attrs/circle/opacity', opacity)
}

/** 刷新节点所有 port 的连接状态样式 */
export function refreshPortStates(node: Node) {
  const ports = node.getPorts()
  for (let i = 0; i < ports.length; i += 1) {
    const id = ports[i].id as string
    const connected = isPortConnected(node, id)
    setPortState(node, id, connected)
  }
}

/** 生成 ops-atom 卡片节点的所有 attrs（设计态） */
export function makeAtomAttrs(
  color: string,
  icon: string,
  label: string,
  subtitle: string,
  configured?: boolean,
) {
  const c = color || DEFAULT_GROUP_COLOR
  return {
    shadow: { fill: 'rgba(0,0,0,0.08)', x: 2, y: 2, width: 236, height: 68, rx: 10 },
    'accent-bar': { fill: c, x: 0, y: 0, width: 4, height: 72, rx: 2 },
    body: { fill: '#FFF', stroke: '#E4E7ED', strokeWidth: 1, x: 4, y: 0, width: 232, height: 72, rx: 10 },
    'icon-bg': { fill: `${c}15`, stroke: `${c}30`, strokeWidth: 1, cx: 34, cy: 36, r: 16 },
    icon: { text: icon || DEFAULT_GROUP_ICON, fill: c, fontSize: 16, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 34, refY: 36 },
    label: { text: label, fill: '#303133', fontSize: 13, fontWeight: 600, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'top', refX: 60, refY: 18 },
    subtitle: { text: subtitle || '', fill: '#909399', fontSize: 11, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'top', refX: 60, refY: 38 },
    // Status dot: bottom-right, green=已配置插件, orange=待配置, transparent=默认
    'status-dot': {
      fill: configured === true ? '#67C23A' : configured === false ? '#E6A23C' : 'transparent',
      cx: 226,
      cy: 62,
      r: 4,
      stroke: 'none',
    },
    // Delete button（默认隐藏，hover 时通过 tools 显示）
    'del-btn-bg': { fill: '#FF4D4F', cx: 226, cy: 14, r: 10, cursor: 'pointer', opacity: 0 },
    'del-btn-icon': { text: '×', fill: '#fff', fontSize: 14, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 226, refY: 14.5, cursor: 'pointer', opacity: 0 },
  }
}

/** 运行时根据节点 data 更新 ops-atom 的视觉属性 */
export function updateAtomNode(node: Node) {
  const data = node.getData() || {}
  const group = data.group || ''
  const groupCfg = resolveGroupConfig(group)
  const color = groupCfg.color
  const icon = groupCfg.icon
  const label = data.label || '未命名节点'
  const risk = data.risk_level || ''
  const subtitle = group ? `${group}${risk ? ' · ' + risk : ''}` : ''
  // configured = 已有 atom_type（已分配插件）
  const configured = !!data.atom_type
  node.setAttrs(makeAtomAttrs(color, icon, label, subtitle, configured))
}

// ── ops-atom: 卡片式原子节点（240x72） ────────────────────────────

const ATOM_WIDTH = 240
const ATOM_HEIGHT = 72

const atomMarkup = [
  { tagName: 'rect', selector: 'shadow' },
  { tagName: 'rect', selector: 'accent-bar' },
  { tagName: 'rect', selector: 'body' },
  { tagName: 'circle', selector: 'icon-bg' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
  { tagName: 'text', selector: 'subtitle' },
  { tagName: 'circle', selector: 'status-dot' },
  // Delete button（hover 时显示）
  { tagName: 'circle', selector: 'del-btn-bg' },
  { tagName: 'text', selector: 'del-btn-icon' },
]

Shape.Rect.define({
  shape: 'ops-atom',
  width: ATOM_WIDTH,
  height: ATOM_HEIGHT,
  markup: atomMarkup,
  attrs: makeAtomAttrs(DEFAULT_GROUP_COLOR, DEFAULT_GROUP_ICON, '选择插件', '', false),
  ports: {
    groups: PORT_GROUPS,
    items: PORT_ITEMS,
  },
})

// ── Start event — 绿色圆 ────────────────────────────────────────

const circleShadowMarkup = [
  { tagName: 'circle', selector: 'shadow' },
  { tagName: 'circle', selector: 'body' },
  { tagName: 'text', selector: 'label' },
]

Shape.Circle.define({
  shape: 'ops-start-event',
  width: 56,
  height: 56,
  markup: circleShadowMarkup,
  attrs: {
    shadow: { fill: 'rgba(103,194,58,0.15)', cx: 30, cy: 30, r: 30 },
    body: { fill: '#E1F3D8', stroke: '#67C23A', strokeWidth: 2.5, cx: 28, cy: 28, r: 28 },
    label: { fill: '#333', fontSize: 11, fontFamily: 'Microsoft YaHei', refY: 62 },
  },
  ports: {
    groups: {
      out: { position: { name: 'right' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
    },
    items: [
      { id: 'out', group: 'out' },
    ],
  },
})

// ── End event — 红色圆 ──────────────────────────────────────────

Shape.Circle.define({
  shape: 'ops-end-event',
  width: 56,
  height: 56,
  markup: circleShadowMarkup,
  attrs: {
    shadow: { fill: 'rgba(245,108,108,0.15)', cx: 30, cy: 30, r: 30 },
    body: { fill: '#FDE2E2', stroke: '#F56C6C', strokeWidth: 2.5, cx: 28, cy: 28, r: 28 },
    label: { fill: '#333', fontSize: 11, fontFamily: 'Microsoft YaHei', refY: 62 },
  },
  ports: {
    groups: {
      in: { position: { name: 'left' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
    },
    items: [
      { id: 'in', group: 'in' },
    ],
  },
})

// ── Gateway 菱形基础 markup ─────────────────────────────────────

const diamondMarkup = [
  { tagName: 'path', selector: 'shadow' },
  { tagName: 'path', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

/** 生成网格菱形节点的通用 attrs */
function diamondAttrs(color: string, iconText: string, iconSize = 24) {
  return {
    shadow: {
      d: 'M 37 7 L 67 37 L 37 67 L 7 37 Z',
      fill: `${color}15`,
      stroke: 'none',
    },
    body: {
      d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z',
      fill: '#FFF',
      stroke: color,
      strokeWidth: 2,
    },
    icon: {
      text: iconText,
      fill: color,
      fontSize: iconSize,
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
      textVerticalAnchor: 'top',
      refX: 35,
      refY: 74,
    },
  }
}

function diamondPorts() {
  return {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  }
}

// ── Exclusive gateway — 菱形（橙色 X） ──────────────────────────

Node.define({
  shape: 'ops-exclusive-gateway',
  width: 70,
  height: 70,
  markup: diamondMarkup,
  attrs: diamondAttrs('#E6A23C', '×', 24),
  ports: diamondPorts(),
})

// ── Parallel gateway — 菱形（蓝色 +） ───────────────────────────

Node.define({
  shape: 'ops-parallel-gateway',
  width: 70,
  height: 70,
  markup: diamondMarkup,
  attrs: diamondAttrs('#409EFF', '+', 28),
  ports: diamondPorts(),
})

// ── Conditional parallel gateway — 菱形（青色 ✓） ──────────────

Node.define({
  shape: 'ops-conditional-parallel-gateway',
  width: 70,
  height: 70,
  markup: diamondMarkup,
  attrs: diamondAttrs('#5CADFF', '✓', 24),
  ports: diamondPorts(),
})

// ── Converge gateway — 菱形（灰色 ⨁） ──────────────────────────

Node.define({
  shape: 'ops-converge-gateway',
  width: 70,
  height: 70,
  markup: diamondMarkup,
  attrs: diamondAttrs('#909399', '⨁', 22),
  ports: diamondPorts(),
})

// ── Approval node — 菱形（紫色 🔐） ─────────────────────────────

Node.define({
  shape: 'ops-approval',
  width: 70,
  height: 70,
  markup: diamondMarkup,
  attrs: diamondAttrs('#9B59B6', '🔐', 22),
  ports: diamondPorts(),
})

// ── Subprocess node — 卡片式虚线框 ─────────────────────────────

const subMarkup = [
  { tagName: 'rect', selector: 'shadow' },
  { tagName: 'rect', selector: 'accent-bar' },
  { tagName: 'rect', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

Shape.Rect.define({
  shape: 'ops-subprocess',
  width: 200,
  height: 56,
  markup: subMarkup,
  attrs: {
    shadow: { fill: 'rgba(41,128,185,0.1)', x: 2, y: 2, width: 196, height: 56, rx: 8 },
    'accent-bar': { fill: '#2980B9', x: 0, y: 0, width: 4, height: 56, rx: 2 },
    body: { fill: '#EBF5FB', stroke: '#2980B9', strokeWidth: 2, x: 4, y: 0, width: 192, height: 56, rx: 8, strokeDasharray: '6 3' },
    icon: { text: '↻', fill: '#2980B9', fontSize: 16, refX: 28, refY: 32, textAnchor: 'middle', textVerticalAnchor: 'middle' },
    label: { fill: '#2C3E50', fontSize: 13, fontFamily: 'Microsoft YaHei', refX: 52, refY: 32, textVerticalAnchor: 'middle' },
  },
  ports: {
    groups: {
      top: { position: { name: 'top' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      bottom: { position: { name: 'bottom' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      left: { position: { name: 'left' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
      right: { position: { name: 'right' }, attrs: { circle: { r: PORT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, opacity: 0, stroke: COLOR_PORT_GRAY, strokeWidth: 1.5 } } },
    },
    items: [
      { id: 'top', group: 'top' },
      { id: 'bottom', group: 'bottom' },
      { id: 'left', group: 'left' },
      { id: 'right', group: 'right' },
    ],
  },
})

// ── Node type map ───────────────────────────────────────────────

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
