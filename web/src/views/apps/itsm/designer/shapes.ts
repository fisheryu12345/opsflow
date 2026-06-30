import { Graph, Shape, Node } from '@antv/x6'

// ── HMR 防重复注册 ──

function registerOnce(name: string, config: any) {
  try { Shape.Rect.define({ shape: name, ...config }) } catch { /* HMR */ }
}

function registerNodeOnce(name: string, config: any) {
  try { Node.define({ shape: name, ...config }) } catch { /* HMR */ }
}

function registerCircleOnce(name: string, config: any) {
  try { Shape.Circle.define({ shape: name, ...config }) } catch { /* HMR */ }
}

function registerGraphOnce(name: string, config: any) {
  try { Graph.registerNode(name, config, true) } catch { /* HMR */ }
}

// ── 常量 ──

export const CARD_WIDTH = 208
export const CARD_HEIGHT = 56
export const PORT_DOT_RADIUS = 4
const COLOR_PORT_GRAY = '#C2C8D5'
const COLOR_PORT_BLUE = '#5F95FF'

// ── ITSM 节点类型 → 颜色/图标映射 ──

export const ITSM_NODE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  NORMAL:    { icon: '📝', color: '#409EFF', label: '填单' },
  APPROVAL:  { icon: '✓',  color: '#E6A23C', label: '审批' },
  SIGN:      { icon: '✍',  color: '#9B59B6', label: '会签' },
  TASK:      { icon: '⚙',  color: '#67C23A', label: '自动任务' },
  ROUTER_P:  { icon: '⊞',  color: '#409EFF', label: '并行网关' },
  COVERAGE:  { icon: '⨁', color: '#909399', label: '汇聚网关' },
  EXCLUSIVE:  { icon: '⊗', color: '#E6A23C', label: '排他网关' },
  CONDITIONAL: { icon: '◐', color: '#5CADFF', label: '条件网关' },
  START:     { icon: '▶',  color: '#67C23A', label: '开始' },
  END:       { icon: '■',  color: '#F56C6C', label: '结束' },
}

export function getNodeConfig(type: string) {
  return ITSM_NODE_CONFIG[type] || { icon: '◇', color: '#909399', label: type }
}

// ── 节点默认表单字段（拖入画布时自动注入）──

export const DEFAULT_NODE_FIELDS: Record<string, any[]> = {
  /** 填单节点自带字段 */
  NORMAL: [
    { key: 'title', name: '工单标题', type: 'STRING', required: true, layout: 'COL_12', placeholder: '如 服务器磁盘空间不足' },
    { key: 'description', name: '详细描述', type: 'TEXT', required: true, layout: 'COL_12', placeholder: '请描述问题或需求详情' },
    {
      key: 'category', name: '服务分类', type: 'SELECT', required: true, layout: 'COL_6',
      choice: [
        { label: '网络故障', value: 'network' },
        { label: '数据库', value: 'database' },
        { label: '应用系统', value: 'application' },
        { label: '安全事件', value: 'security' },
        { label: '桌面支持', value: 'desktop' },
        { label: '其他', value: 'other' },
      ],
    },
    {
      key: 'priority', name: '优先级', type: 'SELECT', required: true, layout: 'COL_6',
      choice: [
        { label: 'P1 危急', value: 'P1' },
        { label: 'P2 高', value: 'P2' },
        { label: 'P3 中', value: 'P3' },
        { label: 'P4 低', value: 'P4' },
      ],
    },
    { key: 'attachment', name: '附件', type: 'FILE', required: false, layout: 'COL_12' },
  ],
  /** 审批节点自带字段 */
  APPROVAL: [
    { key: 'approval_opinion', name: '审批意见', type: 'TEXT', required: false, layout: 'COL_12' },
    {
      key: 'approval_result', name: '审批结果', type: 'SELECT', required: true, layout: 'COL_12',
      choice: [
        { label: '通过', value: 'approved' },
        { label: '驳回', value: 'rejected' },
      ],
    },
  ],
  /** 会签节点自带字段 */
  SIGN: [
    { key: 'sign_opinion', name: '会签意见', type: 'TEXT', required: false, layout: 'COL_12' },
    {
      key: 'sign_result', name: '会签结果', type: 'SELECT', required: true, layout: 'COL_12',
      choice: [
        { label: '同意', value: 'agree' },
        { label: '不同意', value: 'disagree' },
      ],
    },
  ],
}

// ── 端口定义（与 OpsFlow 一致） ──

const PORT_ATTRS = {
  r: PORT_DOT_RADIUS, magnet: true,
  stroke: COLOR_PORT_GRAY, strokeWidth: 1, fill: COLOR_PORT_GRAY,
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

// ── ITSM 节点卡片 attrs ──

function makeItsmNodeAttrs(color: string, icon: string, label: string, desc: string, configured?: boolean) {
  const c = color || '#409EFF'
  const iconBg = `${c}18`
  const iconStroke = `${c}30`
  return {
    shadow: { fill: 'rgba(0,0,0,0.06)', x: 2, y: 2, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8 },
    body: { fill: '#FFF', stroke: c, strokeWidth: 1, x: 0, y: 0, width: CARD_WIDTH, height: CARD_HEIGHT, rx: 8 },
    'icon-bg': { fill: iconBg, stroke: iconStroke, strokeWidth: 1, x: 10, y: 3, width: 28, height: 28, rx: 6 },
    icon: { text: icon, fill: c, fontSize: 13, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 24, refY: 17 },
    label: { text: label, fill: '#303133', fontSize: 14, fontWeight: 600, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'middle', refX: 48, refY: 17 },
    desc: { text: desc || '', fill: 'rgba(0,0,0,0.65)', fontSize: 12, fontFamily: 'Microsoft YaHei', textAnchor: 'start', textVerticalAnchor: 'bottom', refX: 10, refY: 56 },
    'del-btn-bg': { fill: '#FF4D4F', cx: 196, cy: 12, r: 10, cursor: 'pointer', visibility: 'hidden' as const },
    'del-btn-icon': { text: '✕', fill: '#FFF', fontSize: 12, fontWeight: 600, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 196, refY: 13, cursor: 'pointer', visibility: 'hidden' as const },
    'status-dot': {
      fill: configured === true ? '#67C23A' : configured === false ? '#E6A23C' : 'transparent',
      cx: 200, cy: 50, r: 4, stroke: 'none',
    },
  }
}

/** 运行时更新 ITSM 节点视觉（全量刷新 — 从 node:change:data 触发） */
export function updateItsmNode(node: Node) {
  const data = node.getData() || {}
  const cfg = getNodeConfig(data.type || 'NORMAL')
  const label = data.name || cfg.label
  const processorText = data.processors_type ? `→ ${data.processorsRaw || data.processors_type}` : ''
  const fieldText = data.fields?.length ? `📋${data.fields.length}` : ''
  const desc = [processorText, fieldText].filter(Boolean).join(' ')
  const configured = !!data.name
  node.setAttrs(makeItsmNodeAttrs(cfg.color, cfg.icon, label, desc, configured))
}

// ── ITSM 节点卡片（208×56） ──

const itsmNodeMarkup = [
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

registerOnce('itsm-node', {
  width: CARD_WIDTH,
  height: CARD_HEIGHT,
  markup: itsmNodeMarkup,
  attrs: makeItsmNodeAttrs('#409EFF', '📝', '节点', ''),
  ports: { groups: PORT_GROUPS, items: PORT_ITEMS },
})

// ── ITSM 开始/结束事件（圆形，与 OpsFlow 同风格） ──

const circleMarkup = [
  { tagName: 'circle', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

registerCircleOnce('itsm-start-event', {
  width: 56, height: 56, markup: circleMarkup,
  attrs: {
    body: { fill: '#E1F3D8', stroke: '#67C23A', strokeWidth: 2.5, cx: 28, cy: 28, r: 26 },
    icon: { text: '▶', fill: '#67C23A', fontSize: 48, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 30, refY: 30 },
    label: { visibility: 'hidden' as const },
  },
  ports: {
    groups: { out: { position: { name: 'right' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, style: { visibility: 'hidden' }, stroke: COLOR_PORT_GRAY, strokeWidth: 1 } } } },
    items: [{ id: 'out', group: 'out' }],
  },
})

registerCircleOnce('itsm-end-event', {
  width: 56, height: 56, markup: circleMarkup,
  attrs: {
    body: { fill: '#FDE2E2', stroke: '#F56C6C', strokeWidth: 2.5, cx: 28, cy: 28, r: 26 },
    icon: { text: '■', fill: '#F56C6C', fontSize: 64, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 28, refY: 24 },
    label: { visibility: 'hidden' as const },
  },
  ports: {
    groups: { in: { position: { name: 'left' }, attrs: { circle: { r: PORT_DOT_RADIUS, magnet: true, fill: COLOR_PORT_GRAY, style: { visibility: 'hidden' }, stroke: COLOR_PORT_GRAY, strokeWidth: 1 } } } },
    items: [{ id: 'in', group: 'in' }],
  },
})

// ── ITSM 并行/汇聚网关（菱形，与 OpsFlow 同风格） ──

const diamondMarkup = [
  { tagName: 'path', selector: 'shadow' },
  { tagName: 'path', selector: 'body' },
  { tagName: 'text', selector: 'icon' },
  { tagName: 'text', selector: 'label' },
]

function diamondAttrs(color: string, text: string, iconSize = 28) {
  return {
    shadow: { d: 'M 37 7 L 67 37 L 37 67 L 7 37 Z', fill: `${color}15`, stroke: 'none' },
    body: { d: 'M 35 5 L 65 35 L 35 65 L 5 35 Z', fill: '#FFF', stroke: color, strokeWidth: 2 },
    icon: { text, fill: color, fontSize: iconSize, fontWeight: 900, textAnchor: 'middle', textVerticalAnchor: 'middle', refX: 35, refY: 33 },
    label: { visibility: 'hidden' as const },
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

registerNodeOnce('itsm-parallel-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#409EFF', '⊞', 28), ports: diamondPorts() })
registerNodeOnce('itsm-converge-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#909399', '⨁', 28), ports: diamondPorts() })
registerNodeOnce('itsm-exclusive-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#E6A23C', '⊗', 28), ports: diamondPorts() })
registerNodeOnce('itsm-conditional-parallel-gateway', { width: 70, height: 70, markup: diamondMarkup, attrs: diamondAttrs('#5CADFF', '◐', 26), ports: diamondPorts() })

// ── Stencil 预览节点 ──

const stencilMarkup = [
  { tagName: 'rect', selector: 'body' },
  { tagName: 'rect', selector: 'iconRect' },
  { tagName: 'text', selector: 'iconLabel' },
  { tagName: 'text', selector: 'title' },
]

registerGraphOnce('itsm-stencil', {
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

// ── 形状解析 ──

export function resolveItsmShape(type: string): string {
  const map: Record<string, string> = {
    START: 'itsm-start-event',
    END: 'itsm-end-event',
    ROUTER_P: 'itsm-parallel-gateway',
    COVERAGE: 'itsm-converge-gateway',
    EXCLUSIVE: 'itsm-exclusive-gateway',
    CONDITIONAL: 'itsm-conditional-parallel-gateway',
  }
  return map[type] || 'itsm-node'
}

// ── 端口工具函数 ──

export function isPortConnected(node: Node, portId: string): boolean {
  const model = node.model
  if (!model) return false
  return model.getConnectedEdges(node).some(
    e => (e.getSourceCellId() === node.id && e.getSourcePortId() === portId) ||
         (e.getTargetCellId() === node.id && e.getTargetPortId() === portId),
  )
}

function setPortVisible(node: Node, portId: string, visible: boolean) {
  node.setPortProp(portId, 'attrs/circle/style/visibility', visible ? 'visible' : 'hidden')
}

function setPortColor(node: Node, portId: string, color: string) {
  node.setPortProp(portId, 'attrs/circle/fill', color)
  node.setPortProp(portId, 'attrs/circle/stroke', color)
}

function setPortDot(node: Node, portId: string, visible: boolean, color?: string) {
  setPortVisible(node, portId, visible)
  if (color) setPortColor(node, portId, color)
}

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

export function refreshPortStates(node: Node) {
  const ps = node.getPorts()
  for (let i = 0; i < ps.length; i += 1) {
    const id = ps[i].id as string
    const connected = isPortConnected(node, id)
    setPortDot(node, id, connected, connected ? COLOR_PORT_BLUE : COLOR_PORT_GRAY)
  }
}

// ── 默认边样式（与 OpsFlow 一致） ──

export const DEFAULT_EDGE_ATTRS = {
  line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' },
}
