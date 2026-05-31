import { Shape, Node } from '@antv/x6'

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
    label: { fontSize: 0 },
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
    label: { fontSize: 0 },
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

/** 根据节点类型映射到 X6 shape 名称 */
export function resolveNodeShape(node: any): string {
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
