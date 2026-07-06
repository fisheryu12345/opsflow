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
import { resolveItsmShape, CARD_WIDTH, CARD_HEIGHT } from './designer/shapes'
import './designer/shapes'

const props = defineProps<{
  states: Record<string, any>
  transitions: Record<string, any>
  nodeStatus: Array<{ state_id: number; status: string; [key: string]: any }>
}>()

const containerRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const zoomLevel = ref(1)
let graph: Graph | null = null
const { t } = useI18n()

const STATUS_COLORS: Record<string, string> = {
  FINISHED: '#67C23A',
  RUNNING: '#409EFF',
  WAIT: '#C0C4CC',
  FAILED: '#F56C6C',
}

function zoomIn() {
  if (!graph) return
  graph.zoom(0.2)  // relative: +0.2
  zoomLevel.value = graph.zoom()
}

function zoomOut() {
  if (!graph) return
  graph.zoom(-0.2)  // relative: -0.2
  zoomLevel.value = graph.zoom()
}

function fitCanvas() {
  if (!graph) return
  graph.zoomToFit({ padding: 30, maxScale: 1.5 })
  zoomLevel.value = graph.zoom()
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
    interacting: false,
  })

  const states = Object.values(props.states) as any[]
  const transList = Object.values(props.transitions) as any[]
  if (!states.length) { loading.value = false; return }

  const stateIdToNk: Record<string, string> = {}
  for (const st of states) {
    const nk = st.node_key || `node_${st.id}`
    stateIdToNk[String(st.id)] = nk
    if (st.node_key) stateIdToNk[st.node_key] = nk
  }

  for (const st of states) {
    const nk = st.node_key || `node_${st.id}`
    const shap = resolveItsmShape(st.type)
    const isGateway = shap.includes('gateway')
    const isEvent = shap.includes('event')
    const w = isEvent ? 56 : isGateway ? 70 : CARD_WIDTH
    const h = isEvent ? 56 : isGateway ? 70 : CARD_HEIGHT
    const runtimeStatus = props.nodeStatus.find(n => Number(n.state_id) === Number(st.id))?.status || 'WAIT'
    const borderColor = STATUS_COLORS[runtimeStatus] || STATUS_COLORS.WAIT
    const isRunning = runtimeStatus === 'RUNNING'

    const node = graph.addNode({
      shape: shap, id: nk, x: 0, y: 0, width: w, height: h, data: { ...st },
    })

    if (shap === 'itsm-node') {
      node.setAttrByPath('body/stroke', borderColor)
      node.setAttrByPath('body/strokeWidth', isRunning ? 2.5 : 1.5)
    } else {
      node.setAttrByPath('body/stroke', borderColor)
      node.setAttrByPath('body/strokeWidth', isRunning ? 3 : 2)
    }
  }

  for (const t of transList) {
    const fromKey = t.from_node_key || stateIdToNk[String(t.from_state_id)] || stateIdToNk[String(t.from_state)]
    const toKey = t.to_node_key || stateIdToNk[String(t.to_state_id)] || stateIdToNk[String(t.to_state)]
    if (!fromKey || !toKey) continue
    const isReject = (t.direction || '').toLowerCase() === 'reject' || t.name === 'reject'

    graph.addEdge({
      source: { cell: fromKey, anchor: { name: 'center' } },
      target: { cell: toKey, anchor: { name: 'center' } },
      attrs: {
        line: {
          stroke: isReject ? '#F56C6C' : t.condition ? '#E6A23C' : '#DCDFE6',
          strokeWidth: 1.5,
          targetMarker: 'classic',
          strokeDasharray: isReject ? '8,4' : undefined,
        },
      },
      labels: isReject ? [{ attrs: { text: { text: t('message.flowChart.rejectLabel'), fill: '#F56C6C', fontSize: 10 } } }] : [],
    })
  }

  try {
    graph.layout('dagre', { rankdir: 'LR', nodesep: 40, ranksep: 80, align: 'UL' })
  } catch {
    states.forEach((st, i) => {
      const nk = st.node_key || `node_${st.id}`
      const cell = graph.getCellById(nk)
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

watch(() => [props.states, props.transitions, props.nodeStatus], () => {
  nextTick(buildGraph)
}, { deep: true })

onMounted(() => nextTick(buildGraph))
onBeforeUnmount(() => { if (graph) { graph.dispose(); graph = null } })
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
  display: flex;
  align-items: center;
  gap: 2px;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 2px;
}
.fc-zoom-level {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
  min-width: 36px;
}
.flowchart-container {
  width: 100%;
  min-height: 300px;
  background: #fafbfc;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}
</style>
