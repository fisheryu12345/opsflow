<template>
  <div class="dtp-wrap">
    <div class="dtp-bar">
      <el-button-group>
        <el-button :icon="ZoomIn" size="small" @click="zoomIn" />
        <el-button :icon="ZoomOut" size="small" @click="zoomOut" />
        <el-button :icon="FullScreen" size="small" @click="fitView" />
        <el-button :icon="Refresh" size="small" @click="reLayout" />
      </el-button-group>
      <span class="dtp-sep" />
      <el-tag size="small" type="info">{{ $t('message.drCanvas.statTemplate', { nodes: count, edges: edgeCount }) }}</el-tag>
      <span class="dtp-sep" />
      <el-switch v-model="showLabels" size="small" :active-text="$t('message.cmdb.labels')" inactive-text="" style="margin-right:8px" />
      <el-button size="small" type="primary" :loading="aiLayouting" @click="doAiLayout">
        {{ $t('message.drCanvas.aiLayout') }}
      </el-button>
    </div>

    <div ref="containerRef" class="dtp-cvs" />
    <div class="dtp-legend">
      <div class="dtp-legend-item"><span class="dtp-dot primary" />{{ $t('message.cmdb.legendPrimary') }}</div>
      <div class="dtp-legend-item"><span class="dtp-dot standby" />{{ $t('message.cmdb.legendStandby') }}</div>
      <div class="dtp-legend-item"><span class="dtp-dot host" />{{ $t('message.cmdb.legendHost') }}</div>
      <div class="dtp-legend-item"><span class="dtp-dot process" />{{ $t('message.cmdb.legendProcess') }}</div>
      <div class="dtp-legend-item"><span class="dtp-dot drgroup" />{{ $t('message.cmdb.legendDrgroup') }}</div>
    </div>
    <div v-if="ctxNode" class="dtp-ctx" :style="{ left: ctxPos.x + 'px', top: ctxPos.y + 'px' }" @click.stop>
      <div class="dtp-ctx-hd">
        <strong>{{ ctxNode.label }}</strong>
        <el-tag size="small" :type="nodeTagType(ctxNode)" effect="dark">{{ nodeTypeLabel(ctxNode) }}</el-tag>
      </div>
      <div class="dtp-ctx-bd">
        <div v-for="(v, k) in ctxAttrs" :key="k" class="dtp-ctx-r">
          <span class="dtp-ctx-k">{{ k }}</span>
          <span class="dtp-ctx-v">{{ v }}</span>
        </div>
      </div>
      <el-button size="small" text @click="ctxNode = null" style="width:100%;margin-top:6px;">{{ $t('message.cmdb.close') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import G6 from '@antv/g6'
import { ZoomIn, ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'

const { t } = useI18n()
const props = defineProps<{ nodes: any[]; edges: any[] }>()

const containerRef = ref<HTMLDivElement | null>(null)
const graph = ref<any>(null)
const count = ref(0)
const edgeCount = ref(0)
const ctxNode = ref<any>(null)
const ctxPos = ref({ x: 0, y: 0 })
const showLabels = ref(true)
const aiLayouting = ref(false)

const NAMES = () => ({
  DrSite: t('message.cmdb.typeDrSite'),
  DrGroup: t('message.cmdb.typeDrGroup'),
  Host: t('message.cmdb.typeHost'),
  Process: t('message.cmdb.typeProcess'),
})

function mc(n: any): string {
  const c = n.model_code || n.__model_code || n.attrs?.__model_code || n.attrs?.model_code || ''
  if (c) return c
  const id = (n.id || '').toLowerCase()
  const a = n.attrs || {}
  if (id.startsWith('host-') || id.startsWith('dr-')) return 'Host'
  if (a.pid !== undefined || a.command || a.cpu_percent !== undefined || a.memory_mb !== undefined) return 'Process'
  if (a.site_type || a.priority !== undefined) return 'DrSite'
  // broader matching
  if (a.status === 'active' || a.status === 'failed_over') return 'DrGroup'
  return ''
}
function nlabel(n: any): string { return n.label || n.name || n.hostname || n.attrs?.name || n.attrs?.hostname || n.id }
function ncolor(n: any): string {
  const m = mc(n); const s = n.status || n.attrs?.status || ''
  if (m === 'DrSite') return n.site_type === 'standby' ? '#f5222d' : '#1890ff'
  if (m === 'DrGroup') return '#722ed1'
  if (m === 'Host') return '#8c8c8c'
  if (m === 'Process') return s === 'running' ? '#52c41a' : s === 'stopped' ? '#8c8c8c' : '#faad14'
  return '#b37feb'
}
function nodeTagType(n: any): string {
  const m = mc(n)
  if (m === 'DrSite') return n.site_type === 'standby' ? 'danger' : 'primary'
  if (m === 'DrGroup') return 'warning'; if (m === 'Host') return 'info'; return 'success'
}
function nodeTypeLabel(n: any): string { return NAMES()[mc(n)] || t('message.cmdb.typeUnknown') }
function estyle(t: string): any {
  if (t === 'FAILOVER_TO') return { stroke: '#f5222d', lineWidth: 3, endArrow: { path: 'M0,0 L8,6 L8,-6 Z', fill: '#f5222d' } }
  if (t === 'CALLS') return { stroke: '#52c41a', lineWidth: 2, endArrow: { path: 'M0,0 L6,4 L6,-4 Z', fill: '#52c41a' } }
  if (t === 'SITE_CONTAINS' || t === 'CONTAINS') return { stroke: '#1890ff', lineWidth: 1.5, lineDash: [5, 3] }
  if (t === 'RUNS_ON' || t === 'RUNS') return { stroke: '#8c8c8c', lineWidth: 1 }
  if (t === 'BELONGS_TO') return { stroke: '#722ed1', lineWidth: 1, lineDash: [3, 3] }
  return { stroke: '#ccc', lineWidth: 1 }
}

// ─── Manual two‑column hierarchical layout ───
function buildGraphData() {
  // Normalize
  for (const n of props.nodes) {
    if (!mc(n)) continue
    if (!n.site_type) n.site_type = n.attrs?.site_type || ''
  }

  // edge index
  const bySrc: Record<string, { to: string; type: string }[]> = {}
  const byDst: Record<string, { from: string; type: string }[]> = {}
  for (const e of props.edges) {
    const s = e.from || e.source; const d = e.to || e.target; const t = e.type || ''
    ;(bySrc[s] = bySrc[s] || []).push({ to: d, type: t })
    ;(byDst[d] = byDst[d] || []).push({ from: s, type: t })
  }

  // Find children
  function childrenOf(id: string, edgeType: string): string[] {
    return (bySrc[id] || []).filter(x => x.type === edgeType).map(x => x.to)
  }

  const gNodes: any[] = []
  const done = new Set<string>()

  const GX = 100, GAPX = 320, GAPY = 50, H_GAP = 35

  function placeSite(n: any, cx: number, topY: number): number {
    const sid = n.id
    done.add(sid)
    let y = topY
    // site rect
    gNodes.push({ id: sid, type: 'circle', label: showLabels.value ? nlabel(n).slice(0,24) : '', size: 50,
      x: cx, y, style: { fill: ncolor(n), stroke: '#fff', lineWidth: 3, cursor: 'pointer' },
      labelCfg: { style: { fill: '#333', fontSize: 11, fontWeight: 600 }, position: 'bottom', offset: 6 }, attrs: n })
    y += 70
    const hosts = childrenOf(sid, 'SITE_CONTAINS')
    for (const hid of hosts) {
      const h = props.nodes.find(x => x.id === hid)
      if (!h) continue
      done.add(hid)
      gNodes.push({ id: hid, type: 'circle', label: showLabels.value ? nlabel(h).slice(0,20) : '', size: 40,
        x: cx, y, style: { fill: ncolor(h), stroke: '#d9d9d9', lineWidth: 2, cursor: 'pointer' },
        labelCfg: { style: { fill: '#333', fontSize: 10, fontWeight: 600 }, position: 'bottom', offset: 5 }, attrs: h })
      y += 34
      const procs = childrenOf(hid, 'RUNS_ON').length ? childrenOf(hid, 'RUNS_ON') : childrenOf(hid, 'RUNS')
      for (const pid of procs) {
        const p = props.nodes.find(x => x.id === pid)
        if (!p) continue
        done.add(pid)
        gNodes.push({ id: pid, type: 'circle', label: showLabels.value ? nlabel(p).slice(0,18) : '', size: 30,
          x: cx + 10, y, style: { fill: ncolor(p), stroke: '#fff', lineWidth: 2, cursor: 'pointer' },
          labelCfg: { style: { fill: '#333', fontSize: 9, fontWeight: 500 }, position: 'bottom', offset: 4 }, attrs: p })
        y += 28
      }
      y += H_GAP
    }
    // DrGroups under this site
    for (const [gid] of Object.entries(byDst)) {
      if (done.has(gid)) continue
      if (childrenOf(gid, 'BELONGS_TO').length === 0) continue
      const grp = props.nodes.find(x => x.id === gid)
      if (!grp || mc(grp) !== 'DrGroup') continue
      done.add(gid)
      gNodes.push({ id: gid, type: 'circle', label: showLabels.value ? nlabel(grp).slice(0,20) : '', size: 40,
        x: cx + 20, y, style: { fill: ncolor(grp), stroke: '#fff', lineWidth: 2, cursor: 'pointer' },
        labelCfg: { style: { fill: '#333', fontSize: 10, fontWeight: 600 }, position: 'bottom', offset: 5 }, attrs: grp })
      y += 34
    }
    return y + 40
  }

  let y0 = 60
  const primary = props.nodes.filter(n => mc(n) === 'DrSite' && n.site_type !== 'standby')
  for (const s of primary) y0 = placeSite(s, GX, y0)

  let y1 = 60
  const standby = props.nodes.filter(n => mc(n) === 'DrSite' && n.site_type === 'standby')
  for (const s of standby) y1 = placeSite(s, GX + GAPX + 100, y1)

  // Unassigned orphans
  let ox = GX + GAPX * 2 + 200, oy = 60
  for (const n of props.nodes) {
    if (done.has(n.id)) continue
    done.add(n.id)
    gNodes.push({ id: n.id, type: 'circle', label: showLabels.value ? nlabel(n).slice(0,20) : '', size: 40,
      x: ox, y: oy, style: { fill: ncolor(n), stroke: '#fff', lineWidth: 2, cursor: 'pointer' },
      labelCfg: { style: { fill: '#333', fontSize: 10, fontWeight: 600 }, position: 'bottom', offset: 5 }, attrs: n })
    oy += 34
  }

  const gEdges = props.edges.map(e => ({
    source: e.from || e.source, target: e.to || e.target, type: e.type || '',
    style: estyle(e.type || ''), label: e.type || '',
    labelCfg: { style: { fill: '#909399', fontSize: 8 }, offset: 6 },
  }))

  return { nodes: gNodes, edges: gEdges }
}

function init() {
  if (!containerRef.value) return
  if (graph.value) { graph.value.destroy(); graph.value = null }
  const data = buildGraphData()
  if (!data.nodes.length) return
  const rect = containerRef.value.getBoundingClientRect()
  const w = rect.width || 800, h = rect.height || 500
  const g = new G6.Graph({
    container: containerRef.value, width: w, height: h, fitView: true, fitViewPadding: [40,40,40,40],
    animate: { duration: 300, easing: 'easeCubicOut' },
    modes: { default: ['zoom-canvas', 'drag-canvas', 'drag-node'] },
    defaultEdge: { type: 'quadratic', style: { stroke: '#ccc', lineWidth: 1.5, endArrow: { path: 'M0,0 L5,4 L5,-4 Z', fill: '#ccc' } } },
  })
  g.on('node:contextmenu', (evt: any) => {
    evt.preventDefault?.()
    const model = evt.item.getModel()
    ctxNode.value = model
    const cp = g.getCanvasByClient(evt.clientX, evt.clientY)
    ctxPos.value = { x: Math.min(cp.x+10, w-260), y: Math.min(cp.y-10, h-200) }
  })
  g.on('canvas:click', () => { ctxNode.value = null })
  g.data(data); g.render()
  if (h > 100) { setTimeout(() => g.fitView([40,40,40,40]), 200) }
  count.value = g.getNodes().length; edgeCount.value = g.getEdges().length
  graph.value = g; watchSize()
}

function zoomIn() { graph.value?.zoom(1.25) }
function zoomOut() { graph.value?.zoom(0.8) }
function fitView() { graph.value?.fitView([40,40,40,40]) }
function reLayout() { if (graph.value) { graph.value.destroy(); graph.value = null } init() }

async function doAiLayout() {
  if (!graph.value) return
  aiLayouting.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({
      url: '/api/cmdb/topology/dr_layout/',
      method: 'post',
      data: {
        nodes: props.nodes.map(n => ({ id: n.id, type: mc(n), label: nlabel(n) })),
        edges: props.edges.map(e => ({ from: e.from || e.source, to: e.to || e.target, type: e.type })),
      },
    })
    const positions = res?.data?.data?.positions || res?.data?.positions || []
    if (!positions.length) return
    for (const pos of positions) {
      const item = graph.value.findById(pos.id)
      if (!item) continue
      graph.value.updateItem(item, { x: pos.x, y: pos.y })
    }
    graph.value.fitView([40, 40, 40, 40])
  } catch {
    // ignore
  } finally {
    aiLayouting.value = false
  }
}

let ro: ResizeObserver | null = null
function watchSize() {
  if (!containerRef.value) return
  ro = new ResizeObserver(() => {
    if (graph.value && containerRef.value) {
      const r = containerRef.value.getBoundingClientRect()
      if (r.width > 0 && r.height > 0) graph.value.changeSize(r.width, r.height)
    }
  })
  ro.observe(containerRef.value)
}

const ATTR_MAP = () => ({
  name: t('message.cmdb.ctxName'), site_type: t('message.cmdb.ctxSiteType'), region: t('message.cmdb.ctxRegion'),
  status: t('message.cmdb.ctxStatus'), priority: t('message.cmdb.ctxPriority'), description: t('message.cmdb.ctxDescription'),
  pid: t('message.cmdb.ctxPid'), user: t('message.cmdb.ctxUser'), command: t('message.cmdb.ctxCommand'),
  port: t('message.cmdb.ctxPort'), ip: t('message.cmdb.ctxIp'), hostname: t('message.cmdb.ctxHostname'),
})
const ctxAttrs = computed(() => {
  if (!ctxNode.value) return {}
  const a = ctxNode.value.attrs || {}
  const L = ATTR_MAP()
  const r: Record<string, any> = {}
  for (const [k,v] of Object.entries(a)) r[L[k]||k] = v
  return r
})

watch(showLabels, () => {
  if (!graph.value) return
  const data = buildGraphData()
  data.nodes.forEach((n: any) => { const item = graph.value.findById(n.id); if (item) item.update(n) })
})
watch(() => [props.nodes.length, props.edges.length], () => {
  if (graph.value) { graph.value.destroy(); graph.value = null }
  requestAnimationFrame(() => init())
})
onMounted(() => requestAnimationFrame(() => init()))
onBeforeUnmount(() => { ro?.disconnect(); graph.value?.destroy() })
</script>

<style scoped>
.dtp-wrap { width:100%; height:100%; display:flex; flex-direction:column; background:#fafafa; overflow:hidden; position:relative; }
.dtp-bar { display:flex; align-items:center; gap:6px; padding:6px 16px; background:#fff; border-bottom:1px solid #ebeef5; flex-shrink:0; z-index:10; }
.dtp-sep { width:1px; height:18px; background:#dcdfe6; margin:0 4px; }
.dtp-cvs { flex:1; min-height:400px; width:100%; }

/* Legend */
.dtp-legend {
  position:absolute; bottom:16px; left:16px; z-index:10;
  background:rgba(255,255,255,.92); border:1px solid #e4e7ed; border-radius:8px;
  padding:8px 12px; display:flex; flex-wrap:wrap; gap:8px; backdrop-filter:blur(4px);
}
.dtp-legend-item { display:flex; align-items:center; gap:5px; font-size:11px; color:#606266; }
.dtp-dot { width:10px; height:10px; border-radius:50%; border:1px solid rgba(0,0,0,.08); }
.dtp-dot.primary { background:#1890ff; }
.dtp-dot.standby { background:#f5222d; }
.dtp-dot.host { background:#8c8c8c; }
.dtp-dot.process { background:#52c41a; }
.dtp-dot.drgroup { background:#722ed1; }

.dtp-ctx { position:absolute; z-index:100; background:#fff; border:1px solid #e4e7ed; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,.1); padding:10px 14px; min-width:200px; max-width:280px; pointer-events:auto; }
.dtp-ctx-hd { display:flex; align-items:center; margin-bottom:8px; gap:6px; }
.dtp-ctx-hd strong { font-size:13px; }
.dtp-ctx-r { display:flex; justify-content:space-between; padding:3px 0; font-size:12px; }
.dtp-ctx-k { color:#909399; }
.dtp-ctx-v { color:#303133; font-weight:500; }
</style>
