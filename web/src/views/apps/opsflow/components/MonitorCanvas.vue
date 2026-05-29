<template>
  <div class="monitor-canvas-wrapper">
    <div class="monitor-header">
      <div class="monitor-header-left">
        <el-icon size="16" :color="statusColor"><Monitor /></el-icon>
        <span class="execution-status">
          Status:
          <el-tag :type="statusTagType" size="small" effect="dark">{{ statusText }}</el-tag>
        </span>
      </div>
      <div class="monitor-header-right">
        <span v-if="wsConnected" class="ws-status ws-connected">
          <span class="ws-dot" /> Connected
        </span>
        <span v-else class="ws-status ws-disconnected">
          <span class="ws-dot" /> Disconnected
        </span>
      </div>
    </div>
    <div id="monitor-canvas-container" ref="canvasRef" class="x6-canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Graph, Shape } from '@antv/x6'
import { Monitor } from '@element-plus/icons-vue'
import { useMonitor } from '../composables/useMonitor'

const props = defineProps<{
  executionId: number
}>()

const canvasRef = ref<HTMLElement | null>(null)
let graph: Graph | null = null

const {
  connected: wsConnected,
  nodeStatuses, executionStatus,
  connect, disconnect, getNodeColor,
} = useMonitor()

const statusColor = computed(() => {
  switch (executionStatus.value) {
    case 'completed': return '#67c23a'
    case 'running': return '#e6a23c'
    case 'failed': return '#f56c6c'
    case 'paused': return '#909399'
    default: return '#909399'
  }
})

const statusTagType = computed(() => {
  switch (executionStatus.value) {
    case 'completed': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    case 'paused': return 'info'
    default: return 'info'
  }
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    '': 'Pending', pending: 'Pending', running: 'Running',
    paused: 'Paused', completed: 'Completed', failed: 'Failed',
  }
  return map[executionStatus.value] || executionStatus.value
})

function initGraph() {
  if (!canvasRef.value) return
  graph = new Graph({
    container: canvasRef.value,
    width: canvasRef.value.clientWidth || 800,
    height: 600,
    grid: true,
    interacting: false,
  })
}

function loadGraphData(data: { nodes: any[]; edges: any[] }) {
  if (!graph) return
  const cells: any[] = []

  for (const node of data.nodes || []) {
    cells.push(graph.createNode({
      id: node.id,
      x: 0, y: 0,
      width: 180, height: 48,
      label: node.label,
      attrs: {
        body: { fill: '#FFF', stroke: '#909399', strokeWidth: 1.5, rx: 6, ry: 6 },
        label: { fill: '#333', fontSize: 13 },
      },
    }))
  }

  for (const edge of data.edges || []) {
    cells.push(graph.createEdge({
      source: edge.from,
      target: edge.to,
      labels: edge.label ? [{ attrs: { text: { text: edge.label } } }] : undefined,
      attrs: { line: { stroke: '#DCDFE6', strokeWidth: 1.5, targetMarker: 'classic' } },
    }))
  }

  graph.resetCells(cells)
  graph.centerContent()
}

watch(nodeStatuses, (statuses) => {
  if (!graph) return
  for (const [nodeId, status] of Object.entries(statuses)) {
    const cell = graph.getCellById(nodeId)
    if (cell && cell.isNode()) {
      const color = getNodeColor(status)
      cell.setAttrByPath('body/stroke', color)
      if (status === 'running') {
        cell.setAttrByPath('body/fill', '#fdf6ec')
      } else if (status === 'completed') {
        cell.setAttrByPath('body/fill', '#f0f9eb')
      } else if (status === 'failed') {
        cell.setAttrByPath('body/fill', '#fef0f0')
      } else {
        cell.setAttrByPath('body/fill', '#FFF')
      }
    }
  }
}, { deep: true })

onMounted(() => {
  initGraph()
  connect(props.executionId)
})

onBeforeUnmount(() => {
  if (graph) {
    graph.dispose()
    graph = null
  }
  disconnect()
})

defineExpose({ loadGraphData })
</script>

<style scoped>
.monitor-canvas-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.monitor-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.monitor-header-right {
  display: flex;
  align-items: center;
}
.execution-status {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ws-status {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ws-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.ws-connected {
  background: #f0f9eb;
  color: #67c23a;
}
.ws-connected .ws-dot {
  background: #67c23a;
  animation: pulse 2s infinite;
}
.ws-disconnected {
  background: #fef0f0;
  color: #f56c6c;
}
.ws-disconnected .ws-dot {
  background: #f56c6c;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.x6-canvas {
  flex: 1;
  min-height: 500px;
}
</style>
