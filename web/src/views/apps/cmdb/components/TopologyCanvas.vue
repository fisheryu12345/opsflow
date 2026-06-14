<template>
  <div class="tp-wrap">
    <div class="tp-bar">
      <el-button-group>
        <el-button :icon="ZoomIn" size="small" @click="zoomIn" />
        <el-button :icon="ZoomOut" size="small" @click="zoomOut" />
        <el-button :icon="FullScreen" size="small" @click="fitView" />
        <el-button :icon="Refresh" size="small" @click="resetExpand" />
      </el-button-group>
      <span class="tp-sep" />
      <span class="tp-hint">{{ count }} {{ $t('message.cmdb.statNodes') }}</span>
    </div>
    <div ref="containerRef" class="tp-cvs" />
    <div v-if="ctxNode" class="tp-ctx" :style="{ left: ctxPos.x + 'px', top: ctxPos.y + 'px' }" @click.stop>
      <div class="tp-ctx-hd">
        <strong>{{ ctxLabel }}</strong>
        <el-tag size="small" :type="ctxTagType" effect="dark">{{ ctxTypeLabel }}</el-tag>
      </div>
      <div class="tp-ctx-bd">
        <div v-for="(v, k) in ctxAttrs" :key="k" class="tp-ctx-r">
          <span class="tp-ctx-k">{{ k }}</span>
          <span class="tp-ctx-v">{{ v }}</span>
        </div>
      </div>
      <el-button size="small" text @click="ctxNode = null" style="width:100%;margin-top:6px;">{{ $t('message.cmdb.close') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { Graph, treeToGraphData, ExtensionCategory, Rect, Badge, register } from '@antv/g6'
import { ZoomIn, ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'

const { t } = useI18n()
const props = withDefaults(defineProps<{ nodes: any[]; edges: any[] }>(), {
  nodes: () => [],
  edges: () => [],
})
const emit = defineEmits<{ nodeClick: [n: any] }>()

const containerRef = ref<HTMLDivElement | null>(null)
const graph = ref<any>(null)
const count = ref(0)
const ctxNode = ref<any>(null)
const ctxPos = ref({ x: 0, y: 0 })

const NAMES: Record<string, string> = {
  Biz: t('message.topology.biz'), Set: t('message.topology.set'), Module: t('message.topology.module'),
  Host: t('message.cmdb.typeHost'), Process: t('message.cmdb.typeProcess'),
}
const TAG_TYPES: Record<string, string> = { Biz:'primary', Set:'success', Module:'warning', Host:'info', Process:'' }
const COLORS: Record<string, string> = {
  Biz:'#1783FF', Set:'#60C42D', Module:'#722ed1', Host:'#13c2c2', Process:'#8c8c8c',
}
const GREY = '#CED4D9'

function getType(n: any): string { return n.model_code || n.type || '' }
function getAttrs(n: any): any { return n.attrs || n }
function getStatus(n: any): string { return getAttrs(n).status || '' }

// ─── Build nested tree from flat edges ───
const _seen = new Set<string>()
function buildTree(): any {
  if (!props.nodes?.length) return null
  _seen.clear()
  const nodeMap: Record<string, any> = {}
  const children: Record<string, string[]> = {}
  const parent: Record<string, string> = {}
  for (const n of props.nodes) { nodeMap[n.id] = n; children[n.id] = [] }
  for (const e of (props.edges || [])) {
    if ((e.type || '').match(/^(RUNS|DEPENDS_ON|runs|depends_on)$/)) continue
    if (children[e.from]) children[e.from].push(e.to)
    parent[e.to] = e.from
  }
  const roots = props.nodes.filter(n => !parent[n.id]).map(n => n.id)
  if (!roots.length && props.nodes.length) roots.push(props.nodes[0].id)

  function walk(id: string): any {
    if (!id || _seen.has(id)) return null
    _seen.add(id)
    const n = nodeMap[id]
    if (!n) return null
    const tp = getType(n)
    const kids = (children[id] || []).map(walk).filter(Boolean)
    const a = getAttrs(n)
    const label = n.label || n.name || a.name || n.hostname || a.hostname || id
    const sub = tp === 'Host' ? (a.ip || a.hostname || '') : tp === 'Process' ? (a.name || '') : ''
    return {
      id, name: label, sub,
      type: tp, model_code: tp, status: getStatus(n),
      attrs: a, children: kids.length ? kids : undefined,
    }
  }
  if (roots.length === 1) return walk(roots[0])
  return { id:'_root', name:'CMDB', type:'root', children: roots.map(walk).filter(Boolean) }
}

// ─── Register custom tree node — badge visual only, click handled at graph level ───
class CmdbTreeNode extends Rect {
  get data() { return (this.context as any).model.getNodeLikeDatum(this.id) }
  get childrenData() { return (this.context as any).model.getChildrenData(this.id) }

  getLabelStyle(attrs: any): any {
    const [w] = this.getSize(attrs)
    return {
      x: -w / 2 + 10, y: -10,
      text: this.data.name || '', fontSize: 13, fontWeight: 600,
      fill: '#000', opacity: 0.88,
    }
  }

  getSubStyle(attrs: any): any {
    const [w, h] = this.getSize(attrs)
    if (!this.data.sub) return null
    return {
      x: -w / 2 + 10, y: h / 2 - 6,
      text: this.data.sub, fontSize: 10,
      fill: '#666', opacity: 0.7,
    }
  }

  getCollapseStyle(attrs: any): any {
    if (this.childrenData.length === 0) return false
    const { collapsed } = attrs
    const [w] = this.getSize(attrs)
    return {
      backgroundFill: '#fff', backgroundHeight: 18, backgroundLineWidth: 1,
      backgroundRadius: 9, backgroundStroke: GREY, backgroundWidth: 18,
      fill: '#333', fontSize: 14, fontWeight: 700,
      text: collapsed ? '+' : '−', textAlign: 'center' as any, textBaseline: 'middle' as any,
      x: w / 2, y: 0,
    }
  }

  getKeyStyle(attrs: any) {
    const keyStyle = super.getKeyStyle(attrs)
    const color = COLORS[this.data.model_code] || '#1890ff'
    return { ...keyStyle, fill: color, stroke: '#fff', lineWidth: 2, radius: 6 }
  }

  render(attrs = this.parsedAttributes, container: any) {
    super.render(attrs, container)

    // status dot
    const [w] = this.getSize(attrs)
    const st = this.data.status || ''
    const dotColor = st === 'normal' || st === 'running' ? '#52c41a' : st === 'alarm' ? '#f5222d' : st === 'offline' ? '#8c8c8c' : '#ddd'
    this.upsert('status-dot', 'circle', {
      cx: -w / 2 + 48, cy: -20, r: 4, fill: dotColor, stroke: '#fff', lineWidth: 1,
    }, container)

    // label
    this.upsert('label', 'text', this.getLabelStyle(attrs), container)

    // subtext
    const subStyle = this.getSubStyle(attrs)
    if (subStyle) this.upsert('sub', 'text', subStyle, container)

    // collapse badge — visual ONLY, no listener
    const colStyle = this.getCollapseStyle(attrs)
    if (colStyle) this.upsert('collapse', Badge, colStyle, container)
  }
}
if (!(window as any).__CMDB_TREE_NODE_REGISTERED) {
  register(ExtensionCategory.NODE, 'cmdb-tree-node', CmdbTreeNode)
  ;(window as any).__CMDB_TREE_NODE_REGISTERED = true
}

// ─── Context menu state ───
const ctxLabel = computed(() => ctxNode.value?.name || ctxNode.value?.label || '')
const ctxTypeLabel = computed(() => NAMES[ctxNode.value?.model_code] || ctxNode.value?.model_code || '')
const ctxTagType = computed(() => TAG_TYPES[ctxNode.value?.model_code] || 'info')
const ctxAttrs = computed(() => {
  if (!ctxNode.value?.attrs) return {}
  const a = ctxNode.value.attrs
  const L: Record<string, string> = {
    ip: 'IP', hostname: t('message.cmdb.ctxHostname'), status: t('message.cmdb.ctxStatus'), os_type: t('message.cmdb.ctxOsType'),
    cpu_cores: t('message.cmdb.ctxCpu'), memory_mb: t('message.cmdb.ctxMemory'), disk_gb: t('message.cmdb.ctxDisk'),
    region: t('message.cmdb.ctxRegion'), operator: t('message.cmdb.ctxOperator'), description: t('message.cmdb.ctxDescription'),
  }
  const r: Record<string, any> = {}
  for (const [k, v] of Object.entries(a)) r[L[k] || k] = v
  return r
})

// ─── Init ───
function init() {
  if (!containerRef.value) return
  if (graph.value) { graph.value.destroy(); graph.value = null }

  const tree = buildTree()
  if (!tree?.id) return

  const graphData = treeToGraphData(tree, {
    getNodeData: (datum: any, depth: number) => {
      if (!datum.style) datum.style = {}
      datum.style.collapsed = depth >= 2
      if (!datum.children) return datum
      const { children, ...rest } = datum
      return { ...rest, children: children.map((c: any) => c.id) }
    },
  })

  const g = new Graph({
    container: containerRef.value,
    data: graphData,
    autoFit: { type: 'view' } as any,
    node: {
      type: 'cmdb-tree-node',
      style: {
        size: [200, 48],
        ports: [{ placement: 'left' }, { placement: 'right' }],
        radius: 6,
      },
    },
    edge: {
      type: 'cubic-horizontal',
      style: { stroke: GREY, lineWidth: 1.5 },
    },
    layout: {
      type: 'indented',
      direction: 'LR',
      dropCap: false,
      indent: 240,
      getHeight: () => 48,
      preLayout: false,
    },
    behaviors: ['zoom-canvas', 'drag-canvas'],
  })

  // node:click — detect badge (shape 'collapse') and toggle expand/collapse
  g.on('node:click', (evt: any) => {
    const target = evt.target
    const isBadge = target?.id === 'collapse' || target?.parentNode?.id === 'collapse'
    if (!isBadge) return
    const id = evt.targetId || target?.__parentId
    if (!id) return
    const nodeData = g.getNodeData(id)
    if (!nodeData) return
    const collapsed = nodeData.style?.collapsed
    if (collapsed) g.expandElement(id)
    else g.collapseElement(id)
  })

  g.on('node:contextmenu', (evt: any) => {
    evt.preventDefault?.()
    const id = evt.targetId
    if (!id) return
    const data = g.getNodeData(id)
    if (!data?.data) return
    ctxNode.value = data.data
    const cp = g.getCanvasByClient({ x: evt.clientX, y: evt.clientY })
    if (cp) {
      const cx = Array.isArray(cp) ? cp[0] : cp.x
      const cy = Array.isArray(cp) ? cp[1] : cp.y
      ctxPos.value = { x: Math.min(cx + 10, window.innerWidth - 300), y: Math.min(cy - 10, window.innerHeight - 200) }
    }
    emit('nodeClick', data.data)
  })
  g.on('canvas:click', () => { ctxNode.value = null })

  g.render()
  count.value = graphData.nodes?.length || 0
  graph.value = g
  watchSize()
}

let ro: ResizeObserver | null = null
function watchSize() {
  if (!containerRef.value) return
  ro = new ResizeObserver(() => {
    if (graph.value && containerRef.value) {
      const r = containerRef.value.getBoundingClientRect()
      if (r.width > 0 && r.height > 0) graph.value.resize(r.width, r.height)
    }
  })
  ro.observe(containerRef.value)
}

function zoomIn() { graph.value?.zoomBy(1.25) }
function zoomOut() { graph.value?.zoomBy(0.8) }
function fitView() { try { graph.value?.fitView() } catch {} }
function resetExpand() {
  if (!graph.value) return
  const tree = buildTree()
  if (!tree) return
  const graphData = treeToGraphData(tree, {
    getNodeData: (datum: any, depth: number) => {
      if (!datum.style) datum.style = {}
      datum.style.collapsed = depth >= 2
      if (!datum.children) return datum
      const { children, ...rest } = datum
      return { ...rest, children: children.map((c: any) => c.id) }
    },
  })
  graph.value.setData(graphData); graph.value.render(); graph.value.fitView()
}

watch(() => [props.nodes?.length, props.edges?.length], () => {
  if (graph.value) { graph.value.destroy(); graph.value = null }
  requestAnimationFrame(() => init())
})
onMounted(() => requestAnimationFrame(() => init()))
onBeforeUnmount(() => { ro?.disconnect(); graph.value?.destroy() })
</script>

<style scoped>
.tp-wrap { width:100%; height:100%; display:flex; flex-direction:column; background:#fafafa; overflow:hidden; position:relative; }
.tp-bar { display:flex; align-items:center; gap:6px; padding:6px 16px; background:#fff; border-bottom:1px solid #ebeef5; flex-shrink:0; z-index:10; }
.tp-sep { width:1px; height:18px; background:#dcdfe6; margin:0 4px; }
.tp-hint { font-size:12px; color:#909399; }
.tp-cvs { flex:1; min-height:400px; width:100%; }
.tp-ctx { position:absolute; z-index:100; background:#fff; border:1px solid #e4e7ed; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,.1); padding:10px 14px; min-width:200px; max-width:280px; pointer-events:auto; }
.tp-ctx-hd { display:flex; align-items:center; margin-bottom:8px; gap:6px; }
.tp-ctx-hd strong { font-size:13px; }
.tp-ctx-r { display:flex; justify-content:space-between; padding:3px 0; font-size:12px; }
.tp-ctx-k { color:#909399; }
.tp-ctx-v { color:#303133; font-weight:500; }
</style>
