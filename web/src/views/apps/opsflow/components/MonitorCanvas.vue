<template>
  <div class="monitor-canvas-wrapper">
    <div class="monitor-header">
      <div class="monitor-header-left">
        <el-icon size="16" :color="statusColor"><Monitor /></el-icon>
        <!-- Stats inline in header -->
        <div class="header-stats">
          <div class="hstat-item">
            <span class="hstat-value mc-completed">{{ statusStats.completed }}</span>
            <span class="hstat-label">Completed</span>
          </div>
          <div class="hstat-item">
            <span class="hstat-value mc-running">{{ statusStats.running }}</span>
            <span class="hstat-label">Running</span>
          </div>
          <div class="hstat-item">
            <span class="hstat-value mc-failed">{{ statusStats.failed }}</span>
            <span class="hstat-label">Failed</span>
          </div>
          <div class="hstat-item">
            <span class="hstat-value">{{ statusTotal }}</span>
            <span class="hstat-label">Total</span>
          </div>
          <div class="hstat-item" v-if="durationText">
            <span class="hstat-value hstat-duration">{{ durationText }}</span>
          </div>
        </div>
        <div class="header-progress">
          <el-progress :percentage="progressPct" :stroke-width="10" :status="progressStatus"
                       :format="() => `${statusStats.completed}/${statusTotal}`" />
        </div>
      </div>
      <div class="monitor-header-right">
        <div class="zoom-controls">
          <el-button size="small" text :icon="ZoomIn" @click="zoomIn" />
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button size="small" text :icon="ZoomOut" @click="zoomOut" />
          <el-button size="small" text :icon="FullScreen" @click="fitCanvas" />
        </div>
        <span v-if="wsConnected" class="ws-status ws-connected">
          <span class="ws-dot" /> Connected
        </span>
        <span v-else class="ws-status ws-disconnected">
          <span class="ws-dot" /> Disconnected
        </span>
      </div>
    </div>
    <div ref="canvasRef" class="x6-canvas" />
    <div class="monitor-legend">
      <span class="legend-item"><span class="legend-dot" style="background:#409EFF" /> Task</span>
      <span class="legend-item"><span class="legend-dot" style="background:#67C23A" /> Start</span>
      <span class="legend-item"><span class="legend-dot" style="background:#F56C6C" /> End</span>
      <span class="legend-item"><span class="legend-dot" style="background:#E6A23C" /> Gateway</span>
      <span class="legend-divider" />
      <span class="legend-item"><span class="legend-dot" style="background:#67C23A" /> Completed</span>
      <span class="legend-item"><span class="legend-dot" style="background:#E6A23C" /> Running</span>
      <span class="legend-item"><span class="legend-dot" style="background:#F56C6C" /> Failed</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onActivated, onBeforeUnmount } from 'vue'
import { Graph } from '@antv/x6'
import { Monitor, ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
import { useMonitor } from '../composables/useMonitor'
import { resolveNodeShape } from '../utils/shapes'

const props = defineProps<{ executionId: number; startedAt?: string; endedAt?: string }>()

const canvasRef = ref<HTMLElement | null>(null)
let graph: Graph | null = null
const zoomLevel = ref(1)
const graphNodeCount = ref(0)

const { connected: wsConnected, nodeStatuses, executionStatus, connect, disconnect, getNodeColor } = useMonitor()

// Live node stats from graph node count + WebSocket status data
const statusStats = computed(() => {
  const vals = Object.values(nodeStatuses.value) as string[]
  let completed = 0, running = 0, failed = 0
  for (const s of vals) {
    if (s === 'completed') completed++
    else if (s === 'running') running++
    else if (s === 'failed') failed++
  }
  return { completed, running, failed }
})
const statusTotal = computed(() => Math.max(graphNodeCount.value, Object.keys(nodeStatuses.value).length))
const progressPct = computed(() => {
  const total = statusTotal.value
  return total > 0 ? Math.round((statusStats.value.completed / total) * 100) : 0
})
const progressStatus = computed(() => {
  if (statusStats.value.failed > 0) return 'exception'
  if (progressPct.value === 100 && statusTotal.value > 0) return 'success'
  return ''
})

const statusColor = computed(() => ({
  completed: '#67c23a', running: '#e6a23c', failed: '#f56c6c', paused: '#909399', cancelled: '#909399',
})[executionStatus.value] || '#909399')
const durationText = computed(() => {
  const s = props.startedAt
  const e = props.endedAt
  if (!s) return ''
  const end = e ? new Date(e).getTime() : Date.now()
  const diff = end - new Date(s).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
})

function initGraph() {
  if (!canvasRef.value) return
  graph = new Graph({
    container: canvasRef.value,
    grid: true,
    interacting: false,
    connecting: {
        router: { name: 'manhattan', args: { padding: { top: 30, bottom: 30, left: 30, right: 30 }, step: 20, maxLoopCount: 10000 } },
        connector: 'rounded',
    },
  })
}

function computeFallbackLayout(nodes: any[], edges: any[]): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>()
  if (nodes.length === 0) return pos
  const ids = new Set(nodes.map(n => n.id))
  const inDeg = new Map<string, number>()
  const adj = new Map<string, string[]>()
  for (const nid of ids) { inDeg.set(nid, 0); adj.set(nid, []) }
  for (const e of edges) {
    const f = e.from || e.source; const t = e.to || e.target
    if (adj.has(f) && inDeg.has(t)) { adj.get(f)!.push(t); inDeg.set(t, inDeg.get(t)! + 1) }
  }
  const layer = new Map<string, number>()
  let q: string[] = []
  for (const [nid, d] of inDeg) { if (d === 0) { layer.set(nid, 0); q.push(nid) } }
  if (q.length === 0 && nodes.length > 0) { layer.set(nodes[0].id, 0); q.push(nodes[0].id) }
  const seen = new Set(q)
  while (q.length) {
    const nxt: string[] = []
    for (const nid of q) {
      const cur = layer.get(nid) || 0
      for (const nb of adj.get(nid) || []) {
        if (!seen.has(nb)) { seen.add(nb); layer.set(nb, cur + 1); nxt.push(nb) }
        else { layer.set(nb, Math.max(layer.get(nb) || 0, cur + 1)) }
      }
    }
    q = nxt
  }
  for (const nid of ids) { if (!layer.has(nid)) layer.set(nid, 0) }
  const groups = new Map<number, string[]>()
  for (const [nid, l] of layer) { if (!groups.has(l)) groups.set(l, []); groups.get(l)!.push(nid) }
  const hGap = 220, vGap = 60
  const sorted = [...groups.keys()].sort((a, b) => a - b)
  for (const l of sorted) {
    const g = groups.get(l)!
    const totalH = (g.length - 1) * vGap
    let y = -totalH / 2
    g.forEach((id, i) => { pos.set(id, { x: l * hGap + 60, y }); y += vGap })
  }
  return pos
}

function loadGraphData(data: { nodes: any[]; edges: any[] }) {
  if (!graph) { console.warn('[MonitorCanvas] graph not ready'); return }
  try {
    const cells: any[] = []

    // 检测是否缺少坐标（兼容老数据），需要时计算后备布局
    const needLayout = (data.nodes || []).some(n => n.x == null)
    const fallbackPos = needLayout ? computeFallbackLayout(data.nodes || [], data.edges || []) : null

    for (const node of data.nodes || []) {
      const shapeName = resolveNodeShape(node)
      let x = node.x, y = node.y
      if (x == null && fallbackPos) {
        const p = fallbackPos.get(node.id)
        if (p) { x = p.x; y = p.y }
      }
      cells.push(graph.createNode({
        id: node.id,
        shape: shapeName,
        x: x ?? 0,
        y: y ?? 0,
        label: node.label || '',
        data: node,
      }))
    }

    for (const edge of data.edges || []) {
      cells.push(graph.createEdge({
        source: { cell: edge.from, port: edge.sourcePort || 'right' },
        target: { cell: edge.to, port: edge.targetPort || 'left' },
        labels: edge.label ? [{ attrs: { text: { text: edge.label } } }] : undefined,
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
      }))
    }

    if (cells.length === 0) return

    graphNodeCount.value = (data.nodes || []).length
    graph.resetCells(cells)
    graph.centerContent()
    zoomLevel.value = graph.zoom()
    graph.on('scale', () => { zoomLevel.value = graph?.zoom() || 1 })
  } catch (e) {
    console.error('[MonitorCanvas] loadGraphData error:', e)
  }
}

function applyNodeColor(nodeId: string, status: string) {
  if (!graph) return
  const cell = graph.getCellById(nodeId)
  if (!cell || !cell.isNode()) return
  const color = getNodeColor(status)
  cell.setAttrByPath('body/stroke', color)
  if (status === 'running') cell.setAttrByPath('body/fill', '#fdf6ec')
  else if (status === 'completed') cell.setAttrByPath('body/fill', '#f0f9eb')
  else if (status === 'failed') cell.setAttrByPath('body/fill', '#fef0f0')
  else if (status === 'skipped') cell.setAttrByPath('body/fill', '#f5f7fa')
  // else keep original type fill (set during loadGraphData)
}

watch(nodeStatuses, (statuses) => {
  for (const [nid, s] of Object.entries(statuses)) applyNodeColor(nid, s)
}, { deep: true })

function loadNodeStatuses(statusMap: Record<string, string>) {
  nodeStatuses.value = { ...statusMap }
  for (const [nid, s] of Object.entries(statusMap)) applyNodeColor(nid, s)
}

function zoomIn() { graph?.zoom(0.15); zoomLevel.value = graph?.zoom() || 1 }
function zoomOut() { graph?.zoom(-0.15); zoomLevel.value = graph?.zoom() || 1 }
function fitCanvas() { graph?.centerContent(); graph?.zoomToFit({ padding: 40 }); zoomLevel.value = graph?.zoom() || 1 }

let resizeObs: ResizeObserver | null = null

function onVisibilityChange() {
  if (document.visibilityState === 'visible' && graph && canvasRef.value) {
    const w = canvasRef.value.clientWidth
    const h = canvasRef.value.clientHeight
    if (w > 0 && h > 0) {
      graph.resize(w, h)
      graph.centerContent()
    }
  }
}

onMounted(() => {
  initGraph()
  connect(props.executionId)
  document.addEventListener('visibilitychange', onVisibilityChange)
  if (canvasRef.value) {
    resizeObs = new ResizeObserver(() => {
      if (graph && canvasRef.value) {
        const w = canvasRef.value.clientWidth
        const h = canvasRef.value.clientHeight
        if (w > 0 && h > 0) graph.resize(w, h)
      }
    })
    resizeObs.observe(canvasRef.value)
  }
})
onActivated(() => {
  // keep-alive 切回时刷新画布
  if (graph && canvasRef.value) {
    const w = canvasRef.value.clientWidth
    const h = canvasRef.value.clientHeight
    if (w > 0 && h > 0) {
      graph.resize(w, h)
      graph.centerContent()
    }
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  resizeObs?.disconnect()
  if (graph) { graph.dispose(); graph = null }
  disconnect()
})

function refreshCanvas() {
  if (graph && canvasRef.value) {
    const w = canvasRef.value.clientWidth
    const h = canvasRef.value.clientHeight
    if (w > 0 && h > 0) {
      graph.resize(w, h)
      graph.centerContent()
    }
  }
}

function setExecutionStatus(status: string) {
  executionStatus.value = status
}

defineExpose({ loadGraphData, loadNodeStatuses, refreshCanvas, setExecutionStatus })
</script>

<style scoped>
.monitor-canvas-wrapper { display: flex; flex-direction: column; height: 100%; }
.monitor-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 16px; background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
  border-bottom: 1px solid #e4e7ed; flex-shrink: 0; gap: 12px;
}
.monitor-header-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.monitor-header-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.zoom-controls { display: flex; align-items: center; gap: 2px; background: #f5f7fa; border-radius: 6px; padding: 2px; }
.zoom-level { font-size: 11px; color: #909399; min-width: 36px; text-align: center; font-family: monospace; }
.ws-status { font-size: 12px; padding: 3px 10px; border-radius: 12px; display: inline-flex; align-items: center; gap: 4px; }
.ws-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.ws-connected { background: #f0f9eb; color: #67c23a; }
.ws-connected .ws-dot { background: #67c23a; animation: pulse 2s infinite; }
.ws-disconnected { background: #fef0f0; color: #f56c6c; }
.ws-disconnected .ws-dot { background: #f56c6c; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Header inline stats */
.header-stats { display: flex; align-items: center; gap: 10px; }
.hstat-item { display: flex; align-items: center; gap: 3px; }
.hstat-value { font-size: 14px; font-weight: 700; color: #303133; line-height: 1; }
.hstat-value.mc-completed { color: #67C23A; }
.hstat-value.mc-running { color: #E6A23C; }
.hstat-value.mc-failed { color: #F56C6C; }
.hstat-value.hstat-duration { font-size: 13px; font-weight: 600; color: #606266; }
.hstat-label { font-size: 11px; color: #909399; margin-left: 1px; }
.header-progress { flex: 1; min-width: 120px; }

.x6-canvas { flex: 1; min-height: 400px; }
.monitor-legend {
  display: flex; align-items: center; gap: 12px; padding: 6px 16px;
  background: #fafafa; border-top: 1px solid #e4e7ed; flex-shrink: 0; font-size: 11px; color: #909399;
}
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.legend-divider { width: 1px; height: 14px; background: #e4e7ed; margin: 0 4px; }
</style>
