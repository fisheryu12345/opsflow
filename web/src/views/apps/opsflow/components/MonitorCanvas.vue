<template>
  <div class="monitor-canvas-wrapper">
    <div class="monitor-header">
      <div class="monitor-header-left">
        <el-icon size="16" :color="statusColor"><Monitor /></el-icon>
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
    <div id="monitor-canvas-container" ref="canvasRef" class="x6-canvas" />
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
import { Monitor, ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
import { useMonitor } from '../composables/useMonitor'
import { useGraphCanvas, layoutNodes } from '../composables/useGraphCanvas'
import { resolveNodeShape } from '../utils/shapes'

const props = defineProps<{ executionId: number; startedAt?: string; endedAt?: string }>()

const canvasRef = ref<HTMLElement | null>(null)
const graphNodeCount = ref(0)

// 使用通用 Graph composable（监控模式）
const {
  graph, zoomLevel,
  initGraph, zoomIn, zoomOut, fitCanvas,
  enableResize, enableVisibilityRefresh,
} = useGraphCanvas('monitor-canvas-container', { mode: 'monitor' })

const { connected: wsConnected, nodeStatuses, executionStatus, connect, disconnect, getNodeColor } = useMonitor()

// Live node stats
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
const statusTotal = computed(() => Object.keys(nodeStatuses.value).length)
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

// ── 画布加载（监控模式：按给定数据渲染，不自动创建 start/end） ──

function loadGraphData(data: { nodes: any[]; edges: any[] }) {
  if (!graph.value) { console.warn('[MonitorCanvas] graph not ready'); return }
  try {
    const cells: any[] = []

    // 缺少坐标时计算后备布局
    const needLayout = (data.nodes || []).some(n => n.x == null)
    const fallbackPos = needLayout
      ? layoutNodes(data.nodes || [], (data.edges || []).map(e => ({ from: e.from || e.source, to: e.to || e.target })))
      : null

    for (const node of data.nodes || []) {
      const shapeName = resolveNodeShape(node)
      let x = node.x, y = node.y
      if (x == null && fallbackPos) {
        const p = fallbackPos[node.id]
        if (p) { x = p.x; y = p.y }
      }
      cells.push(graph.value.createNode({
        id: node.id,
        shape: shapeName,
        x: x ?? 0, y: y ?? 0,
        label: node.label || '',
        data: node,
      }))
    }

    for (const edge of data.edges || []) {
      cells.push(graph.value.createEdge({
        source: { cell: edge.from, port: edge.sourcePort || 'right' },
        target: { cell: edge.to, port: edge.targetPort || 'left' },
        labels: edge.label ? [{ attrs: { text: { text: edge.label } } }] : undefined,
        attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
      }))
    }

    if (cells.length === 0) return

    graphNodeCount.value = (data.nodes || []).length
    graph.value.resetCells(cells)
    graph.value.centerContent()

    // 重新应用已知状态（loadNodeStatuses 可能在画布创建前被调用）
    if (Object.keys(nodeStatuses.value).length) {
      for (const [nid, s] of Object.entries(nodeStatuses.value)) applyNodeColor(nid, s)
    }
  } catch (e) {
    console.error('[MonitorCanvas] loadGraphData error:', e)
  }
}

// ── 节点着色 + 运行态闪烁动画 ──

const runningNodeIds = new Set<string>()

function applyNodeColor(nodeId: string, status: string) {
  if (!graph.value) return
  const cell = graph.value.getCellById(nodeId)
  if (!cell || !cell.isNode()) return
  const color = getNodeColor(status)
  cell.setAttrByPath('body/stroke', color)

  // 填充色 + 运行态闪烁 class
  const wasRunning = runningNodeIds.has(nodeId)
  if (status === 'running') {
    cell.setAttrByPath('body/fill', '#fdf6ec')
    cell.setAttrByPath('body/class', 'op-node-running')
    runningNodeIds.add(nodeId)
  } else {
    if (wasRunning) {
      runningNodeIds.delete(nodeId)
      cell.setAttrByPath('body/class', '')
    }
    if (status === 'completed') cell.setAttrByPath('body/fill', '#f0f9eb')
    else if (status === 'failed') cell.setAttrByPath('body/fill', '#fef0f0')
    else if (status === 'skipped') cell.setAttrByPath('body/fill', '#f5f7fa')
  }
}

watch(nodeStatuses, (statuses) => {
  for (const [nid, s] of Object.entries(statuses)) applyNodeColor(nid, s)
}, { deep: true })

function loadNodeStatuses(statusMap: Record<string, string>) {
  nodeStatuses.value = { ...statusMap }
  // 由下方 deep watch 统一处理 applyNodeColor，避免重复遍历
}

function refreshCanvas() {
  if (graph.value) graph.value.resize()
}

function setExecutionStatus(status: string) {
  executionStatus.value = status
}

// ── 生命周期 ──

onMounted(() => {
  initGraph()
  enableResize()
  enableVisibilityRefresh()
  connect(props.executionId)
})

onActivated(() => {
  // keep-alive 切回时刷新画布
  if (graph.value) graph.value.resize()
})

defineExpose({ loadGraphData, loadNodeStatuses, refreshCanvas, setExecutionStatus })
</script>

<style lang="scss" scoped>
@import '../styles/opsflow-global';

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

/* 运行态节点闪烁动画（边框 + 填充同步脉冲） */
:deep(.op-node-running) {
  animation: op-pulse 1.5s ease-in-out infinite !important;
}
@keyframes op-pulse {
  0%, 100% { stroke-opacity: 1; stroke-width: 2.5; fill-opacity: 1; }
  50% { stroke-opacity: 0.3; fill-opacity: 0.5; }
}

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
