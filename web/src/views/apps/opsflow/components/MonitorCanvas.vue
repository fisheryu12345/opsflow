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
import { resolveNodeShape, updateAtomNode } from '../utils/shapes'

const props = defineProps<{ executionId: number; startedAt?: string; endedAt?: string }>()

const canvasRef = ref<HTMLElement | null>(null)
const graphNodeCount = ref(0)

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

// ── 运行态节点颜色映射（ops-atom 卡片风格） ──

interface MonitorAttrs {
  'accent-bar'?: Record<string, any>
  body?: Record<string, any>
  label?: Record<string, any>
  subtitle?: Record<string, any>
  'icon-bg'?: Record<string, any>
  icon?: Record<string, any>
  'status-dot'?: Record<string, any>
}

/** 根据状态生成 ops-atom 的全部 attrs 覆盖 */
function atomMonitorAttrs(status: string, _label: string): MonitorAttrs {
  const override: MonitorAttrs = {}
  switch (status) {
    case 'running':
      override['accent-bar'] = { fill: '#E6A23C' }
      override.body = { fill: '#FFFBF0', stroke: '#E6A23C', class: 'op-node-running' }
      override.label = { fill: '#E6A23C' }
      override.subtitle = { fill: '#E6A23C', text: '执行中' }
      override['icon-bg'] = { stroke: '#E6A23C', strokeDasharray: '60 28' }
      override['status-dot'] = { fill: '#E6A23C', class: 'op-dot-pulse' }
      break
    case 'completed':
      override['accent-bar'] = { fill: '#67C23A' }
      override.body = { fill: '#F0F9EB', stroke: '#67C23A', class: '' }
      override.label = { fill: '#67C23A' }
      override.subtitle = { fill: '#67C23A', text: '已完成' }
      override['icon-bg'] = { fill: '#E1F3D8', stroke: '#67C23A', strokeDasharray: '' }
      override.icon = { text: '✓', fill: '#67C23A', fontSize: 14 }
      override['status-dot'] = { fill: '#67C23A', class: '' }
      break
    case 'failed':
      override['accent-bar'] = { fill: '#F56C6C' }
      override.body = { fill: '#FEF0F0', stroke: '#F56C6C', class: '' }
      override.label = { fill: '#F56C6C' }
      override.subtitle = { fill: '#F56C6C', text: '失败' }
      override['icon-bg'] = { fill: '#FDE2E2', stroke: '#F56C6C', strokeDasharray: '' }
      override.icon = { text: '✕', fill: '#F56C6C', fontSize: 14 }
      override['status-dot'] = { fill: '#F56C6C', class: '' }
      break
    case 'skipped':
      override['accent-bar'] = { fill: '#C0C4CC' }
      override.body = { fill: '#F5F7FA', stroke: '#C0C4CC', class: '' }
      override.label = { fill: '#C0C4CC' }
      override.subtitle = { fill: '#C0C4CC', text: '已跳过' }
      override['icon-bg'] = { fill: '#EBEEF5', stroke: '#C0C4CC', strokeDasharray: '' }
      override['status-dot'] = { fill: '#C0C4CC', class: '' }
      break
    case 'pending_approval':
      override['accent-bar'] = { fill: '#9B59B6' }
      override.body = { fill: '#F3E8FF', stroke: '#9B59B6', class: '' }
      override.label = { fill: '#9B59B6' }
      override.subtitle = { fill: '#9B59B6', text: '等待审批' }
      override['icon-bg'] = { fill: '#EDDDFF', stroke: '#9B59B6', strokeDasharray: '' }
      override.icon = { text: '🔐', fontSize: 14 }
      override['status-dot'] = { fill: '#9B59B6', class: '' }
      break
    default: // pending / undefined
      override['accent-bar'] = { fill: '#909399' }
      override.body = { fill: '#FFF', stroke: '#DCDFE6', class: '' }
      override.label = { fill: '#C0C4CC' }
      override.subtitle = { fill: '#C0C4CC', text: '等待执行' }
      override['icon-bg'] = { fill: '#F5F7FA', stroke: '#DCDFE6', strokeDasharray: '' }
      override['status-dot'] = { fill: 'transparent', class: '' }
  }
  return override
}

// ── 画布加载 ──

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
      const x6Node = graph.value.createNode({
        id: node.id,
        shape: shapeName,
        x: x ?? 0, y: y ?? 0,
        label: node.label || '',
        data: node,
      })
      // 对 ops-atom 应用卡片样式（设计态默认）
      if (x6Node.shape === 'ops-atom') {
        updateAtomNode(x6Node)
      }
      cells.push(x6Node)
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

    // 重新应用已知状态
    if (Object.keys(nodeStatuses.value).length) {
      for (const [nid, s] of Object.entries(nodeStatuses.value)) applyNodeColor(nid, s)
    }
  } catch (e) {
    console.error('[MonitorCanvas] loadGraphData error:', e)
  }
}

// ── 节点着色（适配 ops-atom 卡片 markup + 传统节点） ──

const runningNodeIds = new Set<string>()

function applyNodeColor(nodeId: string, status: string) {
  if (!graph.value) return
  const cell = graph.value.getCellById(nodeId)
  if (!cell || !cell.isNode()) return

  const wasRunning = runningNodeIds.has(nodeId)
  const isRunning = status === 'running'

  if (cell.shape === 'ops-atom') {
    const label = cell.getData()?.label || ''
    const attrs = atomMonitorAttrs(status, label)
    cell.setAttrs(attrs)
  } else {
    // 传统节点（start/end/gateway/approval/subprocess）
    const color = getNodeColor(status)
    cell.setAttrByPath('body/stroke', color)
    if (isRunning) {
      cell.setAttrByPath('body/fill', '#fdf6ec')
      cell.setAttrByPath('body/class', 'op-node-running')
    } else {
      if (wasRunning) cell.setAttrByPath('body/class', '')
      if (status === 'completed') cell.setAttrByPath('body/fill', '#f0f9eb')
      else if (status === 'failed') cell.setAttrByPath('body/fill', '#fef0f0')
      else if (status === 'skipped') cell.setAttrByPath('body/fill', '#f5f7fa')
    }
  }

  if (isRunning) runningNodeIds.add(nodeId)
  else runningNodeIds.delete(nodeId)
}

watch(nodeStatuses, (statuses) => {
  for (const [nid, s] of Object.entries(statuses)) applyNodeColor(nid, s)
}, { deep: true })

function loadNodeStatuses(statusMap: Record<string, string>) {
  nodeStatuses.value = { ...statusMap }
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

/* 运行态节点闪烁动画 */
:deep(.op-node-running) {
  animation: op-pulse 1.5s ease-in-out infinite !important;
}
@keyframes op-pulse {
  0%, 100% { stroke-opacity: 1; stroke-width: 2.5; fill-opacity: 1; }
  50% { stroke-opacity: 0.3; fill-opacity: 0.5; }
}

/* 状态圆点脉动动画 */
:deep(.op-dot-pulse) {
  animation: op-dot-breathe 1.5s ease-in-out infinite;
}
@keyframes op-dot-breathe {
  0%, 100% { opacity: 1; r: 4; }
  50% { opacity: 0.3; r: 6; }
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
