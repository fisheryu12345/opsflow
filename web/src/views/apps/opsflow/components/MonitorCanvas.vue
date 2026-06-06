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
/**
 * MonitorCanvas — 执行监控画布
 *
 * 完全基于 API 轮询驱动，父组件（ExecutionDetail）周期性调用 GetExecutionDetail
 * 并将 node_status 传递给本组件。
 */
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { Monitor, ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
import { useGraphCanvas, layoutNodes } from '../composables/useGraphCanvas'
import { resolveNodeShape, updateAtomNode, CARD_WIDTH, CARD_HEIGHT } from '../utils/shapes'

const props = defineProps<{ executionId: number; startedAt?: string; endedAt?: string }>()

const canvasRef = ref<HTMLElement | null>(null)
const graphNodeCount = ref(0)

const {
  graph, zoomLevel,
  initGraph, zoomIn, zoomOut, fitCanvas,
  enableResize, enableVisibilityRefresh,
} = useGraphCanvas('monitor-canvas-container', { mode: 'monitor' })

// 本地状态 — 由父组件通过 loadNodeStatuses / setExecutionStatus 驱动
const nodeStatuses = ref<Record<string, string>>({})
const executionStatus = ref<string>('')

// Live node stats
const statusStats = computed(() => {
  const vals = Object.values(nodeStatuses.value)
  let completed = 0, running = 0, failed = 0
  for (const s of vals) {
    if (s === 'completed') completed++
    else if (s === 'running') running++
    else if (s === 'failed') failed++
  }
  return { completed, running, failed }
})
const statusTotal = computed(() => graphNodeCount.value || 1)
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

// ── 节点颜色映射 ──

interface MonitorAttrs {
  body?: Record<string, any>
  label?: Record<string, any>
  desc?: Record<string, any>
  'icon-bg'?: Record<string, any>
  icon?: Record<string, any>
  'status-dot'?: Record<string, any>
}

function atomMonitorAttrs(status: string, _label: string): MonitorAttrs {
  const override: MonitorAttrs = {}
  switch (status) {
    case 'running':
      override.body = { fill: '#FFFBF0', stroke: '#E6A23C' }
      override.label = { fill: '#E6A23C' }
      override.desc = { fill: '#E6A23C', text: '执行中' }
      override['icon-bg'] = { stroke: '#E6A23C', strokeDasharray: '60 28' }
      override['status-dot'] = { fill: '#E6A23C' }
      break
    case 'completed':
      override.body = { fill: '#F0F9EB', stroke: '#67C23A' }
      override.label = { fill: '#67C23A' }
      override.desc = { fill: '#67C23A', text: '已完成' }
      override['icon-bg'] = { fill: '#E1F3D8', stroke: '#67C23A', strokeDasharray: '' }
      override.icon = { text: '✓', fill: '#67C23A', fontSize: 14 }
      override['status-dot'] = { fill: '#67C23A' }
      break
    case 'failed':
      override.body = { fill: '#FEF0F0', stroke: '#F56C6C' }
      override.label = { fill: '#F56C6C' }
      override.desc = { fill: '#F56C6C', text: '失败' }
      override['icon-bg'] = { fill: '#FDE2E2', stroke: '#F56C6C', strokeDasharray: '' }
      override.icon = { text: '✕', fill: '#F56C6C', fontSize: 14 }
      override['status-dot'] = { fill: '#F56C6C' }
      break
    case 'skipped':
      override.body = { fill: '#F5F7FA', stroke: '#C0C4CC' }
      override.label = { fill: '#C0C4CC' }
      override.desc = { fill: '#C0C4CC', text: '已跳过' }
      override['icon-bg'] = { fill: '#EBEEF5', stroke: '#C0C4CC', strokeDasharray: '' }
      override['status-dot'] = { fill: '#C0C4CC' }
      break
    case 'pending_approval':
      override.body = { fill: '#F3E8FF', stroke: '#9B59B6' }
      override.label = { fill: '#9B59B6' }
      override.desc = { fill: '#9B59B6', text: '等待审批' }
      override['icon-bg'] = { fill: '#EDDDFF', stroke: '#9B59B6', strokeDasharray: '' }
      override.icon = { text: '🔐', fontSize: 14 }
      override['status-dot'] = { fill: '#9B59B6' }
      break
    default:
      override.body = { fill: '#FFF', stroke: '#DCDFE6' }
      override.label = { fill: '#C0C4CC' }
      override.desc = { fill: '#C0C4CC', text: '等待执行' }
      override['icon-bg'] = { fill: '#F5F7FA', stroke: '#DCDFE6', strokeDasharray: '' }
      override['status-dot'] = { fill: 'transparent' }
  }
  return override
}

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
    const color = getColor(status)
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

function getColor(status: string): string {
  switch (status) {
    case 'completed': return '#67C23A'
    case 'running': return '#E6A23C'
    case 'failed': return '#F56C6C'
    default: return '#909399'
  }
}

// ── 画布加载 ──

function loadGraphData(data: { nodes: any[]; edges: any[] }) {
  if (!graph.value) { console.warn('[MonitorCanvas] graph not ready'); return }
  try {
    const cells: any[] = []
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
        id: node.id, shape: shapeName, x: x ?? 0, y: y ?? 0, data: node,
      })
      if (x6Node.shape === 'ops-atom') {
        updateAtomNode(x6Node)
        x6Node.resize(CARD_WIDTH, CARD_HEIGHT)
        x6Node.setPosition(x6Node.getPosition().x, x6Node.getPosition().y - 4)
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
    graph.value.zoomToFit({ padding: 24, maxZoom: 1 })

    // 应用节点颜色
    const statuses = nodeStatuses.value
    graph.value.getNodes().forEach((cell: any) => {
      const nid = cell.id
      if (nid && statuses[nid]) applyNodeColor(nid, statuses[nid])
    })
  } catch (e) {
    console.error('[MonitorCanvas] loadGraphData error:', e)
  }
}

// ── 公开方法：父组件调用 ──

function loadNodeStatuses(statusMap: Record<string, string>) {
  nodeStatuses.value = { ...statusMap }
  if (!graph.value) return
  graph.value.getNodes().forEach((cell: any) => {
    const st = statusMap[cell.id]
    if (st) applyNodeColor(cell.id, st)
  })
}

function setExecutionStatus(status: string) {
  executionStatus.value = status
}

function refreshCanvas() {
  if (graph.value) graph.value.resize()
}

// ── 边动画 ──

let edgeAnimationActive = false

function setEdgeAnimation(active: boolean) {
  edgeAnimationActive = active
  if (!graph.value) return
  graph.value.batchUpdate('edge-animation', () => {
    graph.value.getEdges().forEach(edge => {
      edge.stopTransition('attrs/line/strokeDashoffset')
      if (active) {
        edge.setAttrByPath('line/strokeDasharray', '8 4')
        edge.setAttrByPath('line/stroke', '#E6A23C')
        edge.setAttrByPath('line/strokeWidth', 2)
        edge.setAttrByPath('line/strokeDashoffset', 0)
        const tick = () => {
          if (!edgeAnimationActive) return
          edge.transition('attrs/line/strokeDashoffset', -12, { timing: 'linear', duration: 350 })
          edge.once('transition:complete', () => {
            edge.setAttrByPath('line/strokeDashoffset', 0)
            tick()
          })
        }
        tick()
      } else {
        edge.setAttrByPath('line/strokeDashoffset', 0)
        edge.setAttrByPath('line/strokeDasharray', '')
        edge.setAttrByPath('line/stroke', '#DCDFE6')
        edge.setAttrByPath('line/strokeWidth', 1.5)
      }
    })
  })
}

watch(executionStatus, (status) => {
  if (status === 'running') {
    setEdgeAnimation(true)
  } else if (['completed', 'failed', 'cancelled', 'paused'].includes(status)) {
    setEdgeAnimation(false)
  }
})

// ── 生命周期 ──

onMounted(() => {
  initGraph()
  enableResize()
  enableVisibilityRefresh()
})

onActivated(() => {
  if (graph.value) graph.value.resize()
})

defineExpose({ loadGraphData, loadNodeStatuses, setExecutionStatus, refreshCanvas })
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
:deep(.op-node-running) { animation: op-pulse 1.5s ease-in-out infinite !important; }
@keyframes op-pulse {
  0%, 100% { stroke-opacity: 1; stroke-width: 2.5; fill-opacity: 1; }
  50% { stroke-opacity: 0.3; fill-opacity: 0.5; }
}
</style>
