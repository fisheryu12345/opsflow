<template>
  <div class="flowchart-wrapper">
    <div class="fc-toolbar">
      <div class="fc-toolbar-left">
        <span class="fc-zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
      </div>
      <div class="fc-toolbar-right">
        <el-button size="small" text :icon="ZoomIn" @click="zoomIn" />
        <el-button size="small" text :icon="ZoomOut" @click="zoomOut" />
        <el-button size="small" text :icon="FullScreen" @click="fitCanvas" />
      </div>
    </div>
    <div class="flowchart-container" ref="containerRef" v-loading="loading" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Graph } from '@antv/x6'
import { ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
import { resolveItsmShape, updateItsmNode, CARD_WIDTH, CARD_HEIGHT } from './designer/shapes'
import { layoutNodes } from './designer/layoutUtils'
import './designer/shapes'

const props = defineProps<{
  pipelineTree?: { nodes: any[]; edges: any[] } | null
  nodeStatus?: Array<{ state_id: number; status: string; [key: string]: any }>
}>()

const containerRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const zoomLevel = ref(1)
let graph: Graph | null = null
const { t } = useI18n()

// ── Align with Opsflow MonitorCanvas status colors ──
const STATUS_STROKE: Record<string, string> = {
  FINISHED: '#67C23A',
  RUNNING: '#E6A23C',
  WAIT: '#C0C4CC',
  FAILED: '#F56C6C',
}
const STATUS_FILL: Record<string, string> = {
  FINISHED: '#E1F3D8',
  RUNNING: '#FDF6EC',
  WAIT: '#F5F7FA',
  FAILED: '#FEF0F0',
}

function zoomIn() {
  if (!graph) return
  graph.zoom(0.2)
  zoomLevel.value = graph.zoom()
}

function zoomOut() {
  if (!graph) return
  graph.zoom(-0.2)
  zoomLevel.value = graph.zoom()
}

function fitCanvas() {
  if (!graph) return
  graph.zoomToFit({ padding: 30, maxScale: 1.5 })
  zoomLevel.value = graph.zoom()
}

function getStatusForKey(nodeId: string, nodeData: any): string {
  if (!props.nodeStatus?.length) return 'WAIT'
  // Match by state_id (DB id) first, then fall back to node_id string
  const stateId = nodeData.state_id
  const ns = props.nodeStatus.find(
    n => (stateId != null && Number(n.state_id) === Number(stateId)) ||
         String(n.state_id) === nodeId ||
         String(n.state_id) === nodeId.replace('__', '')
  )
  if (!ns) {
    if (nodeId === '__start__' || nodeId.startsWith('__start')) return 'FINISHED'
    if (nodeId === '__end__' || nodeId.startsWith('__end')) return 'FINISHED'
    return 'WAIT'
  }
  return ns.status || 'WAIT'
}

function buildGraph() {
  if (!containerRef.value) return
  loading.value = true

  if (graph) { graph.dispose(); graph = null }

  graph = new Graph({
    container: containerRef.value,
    width: containerRef.value.clientWidth || 600,
    height: 400,
    grid: false,
    panning: { enabled: true },
    mousewheel: false,
    interacting: {
      nodeMovable: false,
      edgeMovable: false,
      edgeLabelMovable: false,
    },
  })

  const nodes = props.pipelineTree?.nodes || []
  const edges = props.pipelineTree?.edges || []
  if (!nodes.length) { loading.value = false; return }

  // Render nodes
  for (const node of nodes) {
    const nk = node.id || node.node_key || ''
    const nodeType = node.node_type || node.type || 'NORMAL'
    // Map node_type to ITSM shape
    let shap: string
    if (nodeType === 'start_event') shap = 'itsm-start-event'
    else if (nodeType === 'end_event') shap = 'itsm-end-event'
    else if (nodeType.includes('gateway')) shap = `itsm-${nodeType.replace('_gateway', '')}-gateway`
    else shap = resolveItsmShape(nodeType)

    const isGateway = shap.includes('gateway')
    const isEvent = shap.includes('event')
    const w = isEvent ? 56 : isGateway ? 70 : CARD_WIDTH
    const h = isEvent ? 56 : isGateway ? 70 : CARD_HEIGHT
    const stKey = getStatusForKey(nk, node)
    const stroke = STATUS_STROKE[stKey] || STATUS_STROKE.WAIT
    const fill = STATUS_FILL[stKey] || STATUS_FILL.WAIT
    const isRunning = stKey === 'RUNNING'

    // Map state_type back to ITSM type for correct icon/name display
    const itsmType = node.state_type || node.type || nodeType
    const labelName = node.label || node.name || ''
    const cell = graph!.addNode({
      shape: shap, id: nk, x: 0, y: 0, width: w, height: h,
      data: { ...node, type: itsmType, name: labelName, _nodeType: nodeType },
    })

    if (shap === 'itsm-node' && cell) {
      updateItsmNode(cell)  // Apply correct icon/color based on data.type
      cell.setAttrByPath('body/stroke', stroke)
      cell.setAttrByPath('body/strokeWidth', isRunning ? 2.5 : 1.5)
      cell.setAttrByPath('body/fill', fill)
    } else if (cell) {
      cell.setAttrByPath('body/stroke', stroke)
      cell.setAttrByPath('body/strokeWidth', isRunning ? 3 : 2)
      cell.setAttrByPath('body/fill', fill)
    }
  }

  // Render edges
  for (const edge of edges) {
    const fromKey = edge.from || edge.from_node_key || ''
    const toKey = edge.to || edge.to_node_key || ''
    if (!fromKey || !toKey) continue
    const isReject = (edge.direction || '').toLowerCase() === 'reject'

    graph!.addEdge({
      source: { cell: fromKey, anchor: { name: 'center' } },
      target: { cell: toKey, anchor: { name: 'center' } },
      attrs: {
        line: {
          stroke: isReject ? '#F56C6C' : (edge.condition || edge.label) ? '#E6A23C' : '#DCDFE6',
          strokeWidth: 1.5,
          targetMarker: 'classic',
          strokeDasharray: isReject ? '8,4' : undefined,
        },
      },
      labels: (isReject || edge.label) ? [{
        attrs: { text: { text: edge.label || (isReject ? t('message.flowChart.rejectLabel') : ''), fill: isReject ? '#F56C6C' : '#909399', fontSize: 10 } },
      }] : [],
    })
  }

  // Auto layout — use Opsflow's layoutNodes (LAYER_GAP=480, NODE_GAP=120)
  try {
    const nodeList = nodes.map(n => ({ id: n.id || n.node_key || '', node_type: n.node_type || n.type || 'NORMAL' }))
    const edgeList = edges.map(e => ({ from: e.from || e.from_node_key || '', to: e.to || e.to_node_key || '' }))
    const positions = layoutNodes(nodeList, edgeList)
    for (const [id, pos] of Object.entries(positions)) {
      const cell = graph!.getCellById(id)
      if (cell?.isNode()) cell.position(pos.x, pos.y)
    }
    // Position nodes that layoutNodes didn't cover (orphaned nodes)
    const positioned = new Set(Object.keys(positions))
    let orphanY = 40
    for (const n of nodes) {
      const nk = n.id || n.node_key || ''
      if (!positioned.has(nk)) {
        const cell = graph!.getCellById(nk)
        if (cell?.isNode()) {
          cell.position(600, orphanY)
          orphanY += 100
        }
      }
    }
  } catch {
    nodes.forEach((n, i) => {
      const nk = n.id || n.node_key || ''
      const cell = graph!.getCellById(nk)
      if (cell?.isNode()) cell.position(80 + (i % 10) * 280, 40 + Math.floor(i / 10) * 100)
    })
  }

  graph.centerContent()
  loading.value = false

  nextTick(() => {
    if (graph) {
      graph.zoomToFit({ padding: 20, maxScale: 1.2 })
      zoomLevel.value = graph.zoom()
    }
  })
}

watch(() => [props.pipelineTree, props.nodeStatus], () => { nextTick(buildGraph) }, { deep: true })

onMounted(() => nextTick(buildGraph))
onBeforeUnmount(() => { if (graph) { graph.dispose(); graph = null } })

defineExpose({ buildGraph })
</script>

<style scoped>
.flowchart-wrapper {
  position: relative;
}
.fc-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0 8px;
}
.fc-toolbar-left { display: flex; align-items: center; gap: 8px; }
.fc-toolbar-right {
  display: flex; align-items: center; gap: 2px;
  background: #f5f7fa; border-radius: 6px; padding: 2px;
}
.fc-zoom-level {
  font-size: 12px; color: #909399;
  font-family: monospace; min-width: 36px;
}
.flowchart-container {
  width: 100%; min-height: 400px;
  background: #fafbfc; border-radius: 8px;
  overflow: hidden; position: relative;
}
</style>
