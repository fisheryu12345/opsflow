<template>
  <div class="execution-detail">
    <!-- Header -->
    <div class="detail-header">
      <el-button text :icon="ArrowLeft" @click="$emit('back')">Back</el-button>
      <div class="detail-header-info">
        <span class="detail-title">Execution #{{ execution.id }}</span>
        <el-tag :type="statusTagType" size="small" effect="dark">{{ statusLabel }}</el-tag>
        <el-tag v-if="execution.template_name" size="small" type="info" effect="plain">
          {{ execution.template_name }}
        </el-tag>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" :disabled="execution.status !== 'pending'" :loading="starting"
                   @click="onStart">Start</el-button>
        <el-button type="warning" :disabled="execution.status !== 'running'" :loading="pausing"
                   @click="onPause">Pause</el-button>
        <el-button type="primary" :disabled="execution.status !== 'paused'" :loading="resuming"
                   @click="onResume">Resume</el-button>
        <el-button type="danger" :disabled="selectedNodeId === null" @click="onRetry">Retry</el-button>
        <el-button type="info" :disabled="selectedNodeId === null" @click="onSkip">Skip</el-button>
        <el-button type="info" @click="refresh">Refresh</el-button>
      </div>
    </div>


    <!-- Body: MonitorCanvas | Logs -->
    <div class="detail-body">
      <div class="canvas-panel">
        <MonitorCanvas ref="monitorRef" :execution-id="execution.id"
                        :started-at="execDetail.started_at" :ended-at="execDetail.ended_at" />
      </div>
      <button class="side-toggle" :class="{ collapsed: logCollapsed }" @click="toggleLogPanel">
        <el-icon><component :is="logCollapsed ? DArrowLeft : DArrowRight" /></el-icon>
      </button>
      <div class="side-panel-wrapper" :class="{ collapsed: logCollapsed }">
        <div class="side-panel">
          <div class="side-section log-section">
            <div class="side-section-title">
              <span><el-icon size="14"><Document /></el-icon> Execution Logs</span>
              <el-tag size="small" type="info" effect="plain" round>{{ logs.length }}</el-tag>
            </div>
            <div class="log-list" ref="logScrollRef">
              <div v-if="logsLoading" class="log-empty">Loading logs...</div>
              <div v-else-if="logs.length === 0" class="log-empty">No logs yet</div>
              <div v-for="log in logs" :key="log.id" class="log-entry">
                <span class="log-time">{{ formatTime(log.created_at) }}</span>
                <el-tag :type="logTagType(log.status)" size="small" effect="dark" round>{{ log.status }}</el-tag>
                <div class="log-body">
                  <span class="log-step">{{ log.step }}</span>
                  <span class="log-msg">{{ log.message }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onBeforeUnmount, nextTick, watch } from 'vue'
import { ArrowLeft, Refresh, Monitor, Document, DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { GetExecutionDetail, StartExecution, PauseExecution, ResumeExecution, RetryNode, SkipNode } from '/@/api/opsflow/executions'
import { GetTemplateDetail } from '/@/api/opsflow/templates'
import { GetLogs } from '/@/api/opsflow/logs'
import MonitorCanvas from '/@/views/apps/opsflow/components/MonitorCanvas.vue'

const props = defineProps<{ execution: any }>()
const emit = defineEmits<{ back: []; executionUpdate: [exec: any] }>()

const monitorRef = ref<InstanceType<typeof MonitorCanvas> | null>(null)
const logScrollRef = ref<HTMLElement | null>(null)
const logs = ref<any[]>([])
const logsLoading = ref(false)
const starting = ref(false)
const pausing = ref(false)
const resuming = ref(false)
const selectedNodeId = ref<string | null>(null)
const execDetail = ref<any>(props.execution)
const logCollapsed = ref(true)
function toggleLogPanel() { logCollapsed.value = !logCollapsed.value }

const statusLabel = computed(() => {
  const map: Record<string, string> = { pending: 'Pending', running: 'Running', paused: 'Paused', completed: 'Completed', failed: 'Failed' }
  return map[execDetail.value.status] || execDetail.value.status
})
const statusTagType = computed(() => {
  const map: Record<string, string> = { pending: 'info', running: 'warning', paused: 'info', completed: 'success', failed: 'danger' }
  return map[execDetail.value.status] || 'info'
})
const isRunning = computed(() => ['pending', 'running', 'paused'].includes(execDetail.value.status))


function logTagType(status: string) {
  const map: Record<string, string> = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', skipped: 'info' }
  return map[status] || 'info'
}
function formatTime(t: string) {
  if (!t) return ''
  return t.slice(11, 19)
}
function scrollLogBottom() {
  nextTick(() => { if (logScrollRef.value) logScrollRef.value.scrollTop = logScrollRef.value.scrollHeight })
}

function toGraphData(pipelineTree: any): { nodes: any[]; edges: any[] } {
  if (!pipelineTree) return { nodes: [], edges: [] }
  if (pipelineTree.nodes && pipelineTree.edges) return { nodes: pipelineTree.nodes, edges: pipelineTree.edges }
  const cells = pipelineTree.cells || []
  const nodes: any[] = []; const edges: any[] = []
  for (const cell of cells) {
    if (cell.shape === 'edge' || cell.source) {
      const source = cell.source?.cell || cell.source
      const target = cell.target?.cell || cell.target
      const label = cell.labels?.[0]?.attrs?.text?.text || ''
      edges.push({ from: source, to: target, label })
    } else {
      nodes.push({ id: cell.id, label: cell.attrs?.label?.text || cell.label || cell.id })
    }
  }
  return { nodes, edges }
}

async function loadPipeline() {
  await nextTick()
  if (!monitorRef.value) return
  try {
    const detail = await GetExecutionDetail(props.execution.id)
    const ex = detail.data?.data || detail.data || detail
    execDetail.value = ex
    monitorRef.value.setExecutionStatus?.(ex.status)
    if (ex.node_status) {
      monitorRef.value.loadNodeStatuses?.(ex.node_status)
    }
    const tree = ex.pipeline_tree || ex.context?.pipeline_tree
    if (tree) {
      monitorRef.value.loadGraphData(toGraphData(tree))
    } else if (ex.template) {
      const tplRes = await GetTemplateDetail(ex.template)
      const tpl = tplRes.data?.data || tplRes.data || tplRes
      if (tpl?.pipeline_tree) monitorRef.value.loadGraphData(toGraphData(tpl.pipeline_tree))
    }
  } catch (e) {
    console.error('[ExecutionDetail] loadPipeline error:', e)
  }
}

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res = await GetLogs({ execution: props.execution.id })
    logs.value = res.data?.results || res.data || res.results || []
    scrollLogBottom()
  } catch { /* ignore */ }
  logsLoading.value = false
}

async function refresh() { await loadPipeline(); await fetchLogs() }

async function onStart() {
  starting.value = true
  try {
    const res = await StartExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch { /* ignore */ }
  starting.value = false
}
async function onPause() {
  pausing.value = true
  try {
    const res = await PauseExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch { /* ignore */ }
  pausing.value = false
}
async function onResume() {
  resuming.value = true
  try {
    const res = await ResumeExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch { /* ignore */ }
  resuming.value = false
}
async function onRetry() {
  if (!selectedNodeId.value) return
  try { await RetryNode(props.execution.id, selectedNodeId.value); await fetchLogs() } catch { /* ignore */ }
}
async function onSkip() {
  if (!selectedNodeId.value) return
  try { await SkipNode(props.execution.id, selectedNodeId.value); await fetchLogs() } catch { /* ignore */ }
}

// Auto-refresh while execution is active (pending/running/paused)
let autoTimer: ReturnType<typeof setInterval> | null = null
function startAutoRefresh() { if (!autoTimer) autoTimer = setInterval(() => refresh(), 3000) }
function stopAutoRefresh() { if (autoTimer) { clearInterval(autoTimer); autoTimer = null } }

watch(isRunning, (v) => { if (v) startAutoRefresh(); else stopAutoRefresh() }, { immediate: true })
watch(() => props.execution.id, (newId) => { if (newId) { loadPipeline(); fetchLogs() } })

onMounted(() => { loadPipeline(); fetchLogs() })
onActivated(() => { nextTick(() => { monitorRef.value?.refreshCanvas() }) })
onBeforeUnmount(() => stopAutoRefresh())
</script>

<style scoped>
.execution-detail { display: flex; flex-direction: column; height: 100%; }
.detail-header {
  display: flex; align-items: center; gap: 12px; padding: 8px 16px;
  background: #fff; border-bottom: 1px solid #e4e7ed; flex-shrink: 0;
}
.detail-header-info { display: flex; align-items: center; gap: 8px; flex: 1; }
.detail-title { font-size: 15px; font-weight: 600; color: #303133; }
.detail-header-actions { display: flex; gap: 8px; }

/* Stats bar */
.stats-bar {
  display: flex; align-items: center; gap: 20px; padding: 8px 20px;
  background: #fafafa; border-bottom: 1px solid #e4e7ed; flex-shrink: 0;
}
.stat-item { display: flex; flex-direction: column; align-items: center; min-width: 50px; }
.stat-value { font-size: 18px; font-weight: 700; color: #303133; line-height: 1.3; }
.stat-label { font-size: 11px; color: #909399; }
.stat-progress { flex: 1; min-width: 120px; }

.detail-body { flex: 1; display: flex; overflow: hidden; }
.canvas-panel { flex: 1; min-width: 0; overflow: hidden; }
.side-panel {
  width: 340px; display: flex; flex-direction: column;
  border-left: 1px solid #e4e7ed; background: #fafafa; height: 100%;
}
.side-panel-wrapper {
  flex-shrink: 0; width: 340px; overflow: hidden;
  transition: width 0.25s ease; display: flex;
}
.side-panel-wrapper.collapsed { width: 0; }
.side-toggle {
  flex-shrink: 0; width: 16px; cursor: pointer; border: none; outline: none;
  background: #f5f7fa; color: #909399; display: flex; align-items: center;
  justify-content: center; padding: 0; font-size: 12px; transition: color 0.2s, background 0.2s;
}
.side-toggle:hover { background: #e8eaed; color: #606266; }
.side-toggle.collapsed { width: 16px; }
.side-section { padding: 12px 14px; }
.side-section-title {
  font-size: 13px; font-weight: 600; color: #606266; margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}
.log-section { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.log-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.log-empty { color: #999; padding: 20px 0; text-align: center; }
.log-entry {
  display: flex; align-items: flex-start; gap: 6px; padding: 6px 0;
  line-height: 1.5; border-bottom: 1px solid #f2f2f2;
}
.log-entry:hover { background: #f5f7fa; }
.log-time { color: #999; white-space: nowrap; font-family: monospace; font-size: 11px; padding-top: 2px; flex-shrink: 0; }
.log-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.log-step { color: #606266; font-weight: 500; font-size: 12px; }
.log-msg { color: #909399; font-size: 11px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
