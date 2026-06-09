<template>
  <div class="execution-detail">
    <!-- Header -->
    <div class="detail-header">
      <el-button text :icon="ArrowLeft" @click="$emit('back')">{{ $t("message.common.back") }}</el-button>
      <div class="detail-header-info">
        <span class="detail-title">Execution #{{ execution.id }}</span>
        <el-tag :type="statusTagType" size="small" effect="dark">{{ statusLabel }}</el-tag>
        <el-tag v-if="execution.template_name" size="small" type="info" effect="plain">
          {{ execution.template_name }}
        </el-tag>
      </div>
      <div class="detail-header-actions">
        <el-button type="success" :disabled="execDetail.status !== 'pending'" :loading="starting"
                   @click="onStart">{{ $t("message.execution.start") }}</el-button>
        <el-button type="warning" :disabled="execDetail.status !== 'running'" :loading="pausing"
                   @click="onPause">{{ $t("message.execution.pause") }}</el-button>
        <el-button type="primary" :disabled="execDetail.status !== 'paused'" :loading="resuming"
                   @click="onResume">{{ $t("message.execution.resume") }}</el-button>
        <el-button type="danger" :disabled="selectedNodeId === null" @click="onRetry">{{ $t("message.execution.retry") }}</el-button>
        <el-button type="info" :disabled="selectedNodeId === null" @click="onSkip">{{ $t("message.execution.skip") }}</el-button>
        <el-button type="danger" :disabled="!isCancelable"
                   :loading="cancelling" @click="onCancel">{{ $t("message.execution.cancel") }}</el-button>
        <el-button type="info" @click="refresh">{{ $t("message.common.refresh") }}</el-button>
      </div>
    </div>

    <!-- Approval banner -->
    <div v-if="isPendingApproval" class="approval-banner">
      <div class="approval-banner-left">
        <el-icon :size="18" color="#9B59B6"><Clock /></el-icon>
        <span class="approval-banner-text">{{ $t("message.execution.approvalRequired") }}</span>
        <el-tag size="small" type="warning" effect="light" round>{{ execDetail.current_node || 'approval node' }}</el-tag>
      </div>
      <div class="approval-banner-actions">
        <el-button size="small" type="success" :loading="approving" @click="onApprove">
          <el-icon><CircleCheck /></el-icon> Approve
        </el-button>
        <el-button size="small" type="danger" :loading="rejecting" @click="onReject">
          <el-icon><Close /></el-icon> Reject
        </el-button>
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
          <el-tabs v-model="sideTab" class="trace-tabs">
            <!-- Logs Tab (existing) -->
            <el-tab-pane label="Logs" name="logs">
              <div class="side-section log-section">
                <div class="side-section-title">
                  <span><el-icon size="14"><Document /></el-icon> Execution Logs</span>
                  <el-tag size="small" type="info" effect="plain" round>{{ logs.length }}</el-tag>
                </div>
                <div class="log-list" ref="logScrollRef">
                  <div v-if="logsLoading" class="log-empty">Loading logs...</div>
                  <div v-else-if="logs.length === 0" class="log-empty">{{ $t("message.execution.noLogs") }}</div>
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
            </el-tab-pane>

            <!-- Traces Tab (new) -->
            <el-tab-pane label="Traces" name="traces">
              <div class="side-section trace-section">
                <div class="side-section-title">
                  <span><el-icon size="14"><Monitor /></el-icon> Node Traces</span>
                  <el-tag size="small" type="info" effect="plain" round>{{ traces.length }}</el-tag>
                </div>
                <!-- Trace Table -->
                <div class="trace-table-wrap">
                  <table class="trace-table" v-if="traces.length > 0">
                    <thead>
                      <tr>
                        <th>{{ $t("message.properties.nodeName") }}</th>
                        <th>{{ $t("message.execution.status") }}</th>
                        <th>{{ $t("message.execution.duration") }}</th>
                        <th>{{ $t("message.execution.retry") }}</th>
                        <th>{{ $t("message.execution.operate") }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="t in traces" :key="t.node_id + '-' + t.retry_count"
                          :class="['trace-row', traceRowClass(t.status), { 'trace-row-selected': selectedNodeId === t.node_id }]"
                          @click="selectTraceNode(t.node_id)">
                        <td class="trace-node-id" :title="t.node_label || t.node_id">
                          {{ t.node_label || t.node_id }}
                          <span v-if="t.retry_count > 0" class="trace-retry-badge">#{{ t.retry_count }}</span>
                        </td>
                        <td>
                          <el-tag :type="traceTagType(t.status)" size="small" effect="dark" round>{{ t.status }}</el-tag>
                        </td>
                        <td class="trace-duration">{{ formatDuration(t.duration_ms) }}</td>
                        <td class="trace-retry-count">{{ t.retry_count }}</td>
                        <td>
                          <el-button size="small" text type="primary" @click.stop="viewTraceLog(t.node_id)"
                                     :loading="logLoadingNode === t.node_id">{{ $t("message.execution.logView") }}</el-button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-else class="log-empty">{{ $t("message.execution.noTraces") }}</div>
                </div>
                <!-- Trace Log Viewer -->
                <div v-if="traceLogContent !== null" class="trace-log-viewer">
                  <div class="trace-log-header">
                    <span class="trace-log-title">Log: {{ traceLogNodeId }}</span>
                    <el-button size="small" text @click="traceLogContent = null">
                      <el-icon><Close /></el-icon>
                    </el-button>
                  </div>
                  <pre class="trace-log-body"><code>{{ traceLogContent }}</code></pre>
                </div>
              </div>
            </el-tab-pane>

            <!-- Data Tab (new — node inputs/outputs preview) -->
            <el-tab-pane label="Data" name="data">
              <div class="side-section data-section">
                <div class="side-section-title">
                  <span><el-icon size="14"><Monitor /></el-icon> Node Data</span>
                  <el-tag v-if="selectedNodeId" size="small" type="info" effect="plain" round>{{ selectedNodeId }}</el-tag>
                </div>
                <div v-if="!selectedNodeId" class="log-empty">{{ $t("message.execution.clickNodeHint") }}</div>
                <div v-else-if="dataLoading" class="log-empty">Loading...</div>
                <template v-else>
                  <!-- Inputs -->
                  <div class="data-group">
                    <div class="data-group-title">
                      <el-icon size="13"><Upload /></el-icon> Inputs
                    </div>
                    <div v-if="nodeInputs && Object.keys(nodeInputs).length" class="data-table">
                      <div v-for="(val, key) in nodeInputs" :key="key" class="data-row">
                        <span class="data-key">{{ key }}</span>
                        <span class="data-val">{{ formatDataValue(val) }}</span>
                      </div>
                    </div>
                    <div v-else class="data-empty">{{ $t("message.common.noData") }}</div>
                  </div>
                  <!-- Outputs -->
                  <div class="data-group">
                    <div class="data-group-title">
                      <el-icon size="13"><Download /></el-icon> Outputs
                    </div>
                    <div v-if="nodeOutputs && Object.keys(nodeOutputs).length" class="data-table">
                      <div v-for="(val, key) in nodeOutputs" :key="key" class="data-row" :class="{ 'data-row-error': key === '_error' && val }">
                        <span class="data-key">{{ key }}</span>
                        <span class="data-val">{{ formatDataValue(val) }}</span>
                      </div>
                    </div>
                    <div v-else class="data-empty">{{ $t("message.common.noData") }}</div>
                  </div>
                  <!-- Stdout (prominent) -->
                  <div v-if="nodeStdout" class="data-group">
                    <div class="data-group-title">
                      <el-icon size="13"><Document /></el-icon> stdout
                    </div>
                    <pre class="data-stdout"><code>{{ nodeStdout }}</code></pre>
                  </div>
                  <!-- Stderr -->
                  <div v-if="nodeStderr" class="data-group">
                    <div class="data-group-title data-group-title-error">
                      <el-icon size="13"><WarningFilled /></el-icon> stderr
                    </div>
                    <pre class="data-stderr"><code>{{ nodeStderr }}</code></pre>
                  </div>
                </template>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted, onActivated, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Refresh, Monitor, Document, Close, DArrowLeft, DArrowRight, CircleCheck, Clock, WarningFilled, Upload, Download } from '@element-plus/icons-vue'
import { GetExecutionDetail, StartExecution, PauseExecution, ResumeExecution, RetryNode, SkipNode, CancelExecution, GetExecutionTraces, GetNodeTraceLog, ApproveNode, RejectNode, GetEngineStates } from '../../opsflow/api/executions'
import { GetTemplateDetail } from '../../opsflow/api/templates'
import { GetLogs } from '../../opsflow/api/logs'
import mittBus from '/@/utils/mitt'
import MonitorCanvas from '/@/views/apps/opsflow/components/canvas/MonitorCanvas.vue'

const props = defineProps<{ execution: any }>()
const emit = defineEmits<{ back: []; executionUpdate: [exec: any] }>()
const { t } = useI18n()

const monitorRef = ref<InstanceType<typeof MonitorCanvas> | null>(null)
const logScrollRef = ref<HTMLElement | null>(null)
const logs = ref<any[]>([])
const logsLoading = ref(false)
const starting = ref(false)
const pausing = ref(false)
const resuming = ref(false)
const cancelling = ref(false)
const selectedNodeId = ref<string | null>(null)
const execDetail = ref<any>(props.execution)
const logCollapsed = ref(true)
function toggleLogPanel() { logCollapsed.value = !logCollapsed.value }

// -- Traces state --
const sideTab = ref('logs')
const traces = ref<any[]>([])
const tracesLoading = ref(false)
const traceLogContent = ref<string | null>(null)
const traceLogNodeId = ref<string>('')
const logLoadingNode = ref<string | null>(null)

const statusLabel = computed(() => {
  const map: Record<string, string> = { pending: t('message.execution.statePending'), pending_approval: t('message.execution.statusPendingApproval'), running: t('message.execution.statRunning'), paused: t('message.execution.statePaused'), completed: t('message.execution.statCompleted'), failed: t('message.execution.statFailed'), cancelled: t('message.execution.stateCancelled') }
  return map[execDetail.value.status] || execDetail.value.status
})
const statusTagType = computed(() => {
  const map: Record<string, string> = { pending: 'info', pending_approval: 'info', running: 'warning', paused: 'info', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[execDetail.value.status] || 'info'
})
const isRunning = computed(() => ['pending', 'pending_approval', 'running', 'paused'].includes(execDetail.value.status))
const isCancelable = computed(() => ['running', 'paused', 'pending', 'pending_approval'].includes(execDetail.value.status))
const isPendingApproval = computed(() => execDetail.value.status === 'paused' && execDetail.value.current_node !== '')
const approving = ref(false)
const rejecting = ref(false)



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

// -- Trace helpers --
function traceTagType(status: string) {
  const map: Record<string, string> = { completed: 'success', running: 'warning', failed: 'danger', pending: 'info', retrying: 'warning', cancelled: 'info', skipped: 'info' }
  return map[status] || 'info'
}
function traceRowClass(status: string) {
  return 'trace-status-' + status
}
function formatDuration(ms: number | null) {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
function selectTraceNode(nodeId: string) {
  selectedNodeId.value = selectedNodeId.value === nodeId ? null : nodeId
  if (selectedNodeId.value) {
    fetchNodeData(selectedNodeId.value)
    sideTab.value = 'data'
  }
}
async function fetchNodeData(nodeId: string) {
  dataLoading.value = true
  try {
    const res = await GetExecutionTraces(props.execution.id, nodeId)
    const data = res.data?.data || res.data
    const traces = data?.traces || []
    if (traces.length > 0) {
      const t = traces[0]
      nodeInputs.value = t.inputs || null
      nodeOutputs.value = t.outputs || null
      nodeStdout.value = t.outputs?.stdout || t.stdout || ''
      nodeStderr.value = t.outputs?.stderr || t.stderr || ''
    } else {
      nodeInputs.value = null; nodeOutputs.value = null
      nodeStdout.value = ''; nodeStderr.value = ''
    }
  } catch {
    nodeInputs.value = null; nodeOutputs.value = null
    nodeStdout.value = ''; nodeStderr.value = ''
  }
  dataLoading.value = false
}

// -- Node data preview state --
const dataLoading = ref(false)
const nodeInputs = ref<Record<string, any> | null>(null)
const nodeOutputs = ref<Record<string, any> | null>(null)
const nodeStdout = ref<string>('')
const nodeStderr = ref<string>('')

function formatDataValue(val: any): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return String(val)
}

async function viewTraceLog(nodeId: string) {
  logLoadingNode.value = nodeId
  try {
    const res = await GetNodeTraceLog(props.execution.id, nodeId)
    traceLogContent.value = res.data?.data || res.data || ''
    traceLogNodeId.value = nodeId
  } catch { traceLogContent.value = '(failed to load log)' }
  logLoadingNode.value = null
}
async function fetchTraces() {
  tracesLoading.value = true
  try {
    const res = await GetExecutionTraces(props.execution.id)
    const data = res.data?.data || res.data
    traces.value = data?.traces || []
    // If trace tab is active and no log viewer open, auto-show first failed node's log
    if (sideTab.value === 'traces' && traceLogContent.value === null) {
      const failed = traces.value.find((t: any) => t.status === 'failed')
      if (failed) viewTraceLog(failed.node_id)
    }
  } catch { /* ignore */ }
  tracesLoading.value = false
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

let graphInitialized = false

async function loadPipeline(full = true) {
  await nextTick()
  if (!monitorRef.value) return
  try {
    const detail = await GetExecutionDetail(props.execution.id)
    const ex = detail.data?.data || detail.data || detail
    execDetail.value = ex
    monitorRef.value.setExecutionStatus?.(ex.status)

    // 首次加载：先画图，后着色 — 确保 graph 有节点后再 coloring
    if (full && !graphInitialized) {
      const tree = ex.pipeline_tree || ex.context?.pipeline_tree || ex.template_snapshot?.pipeline_tree
      if (tree) {
        monitorRef.value.loadGraphData(toGraphData(tree))
      } else if (ex.template) {
        const tplRes = await GetTemplateDetail(ex.template)
        const tpl = tplRes.data?.data || tplRes.data || tplRes
        if (tpl?.pipeline_tree) monitorRef.value.loadGraphData(toGraphData(tpl.pipeline_tree))
      }
      graphInitialized = true
    }

    // 画布有节点后再着色（首次加载时刚画完，轮询时已有节点）
    if (ex.node_status) {
      monitorRef.value.loadNodeStatuses?.(ex.node_status)
    }
  } catch (e) {
    console.error('[ExecutionDetail] loadPipeline error:', e)
  }
}

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res = await GetLogs({ execution: props.execution.id, limit: 200 })
    logs.value = res.data?.results || res.data || res.results || []
    scrollLogBottom()
  } catch { /* ignore */ }
  logsLoading.value = false
}

async function refresh() { await loadPipeline(false); await fetchLogs(); await fetchTraces() }

async function onStart() {
  starting.value = true
  try {
    const res = await StartExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch (e: any) { ElMessage.error(e?.msg || '启动失败') }
  starting.value = false
}
async function onPause() {
  pausing.value = true
  try {
    const res = await PauseExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch (e: any) { ElMessage.error(e?.msg || '暂停失败') }
  pausing.value = false
}
async function onResume() {
  resuming.value = true
  try {
    const res = await ResumeExecution(props.execution.id)
    const ex = res.data || res
    if (ex.id) execDetail.value = ex
    emit('executionUpdate', { ...execDetail.value })
  } catch (e: any) { ElMessage.error(e?.msg || '恢复失败') }
  resuming.value = false
}
async function onRetry() {
  if (!selectedNodeId.value) return
  try { await RetryNode(props.execution.id, selectedNodeId.value); await fetchLogs(); ElMessage.success('重试已提交') }
  catch (e: any) { ElMessage.error(e?.msg || '重试失败') }
}
async function onSkip() {
  if (!selectedNodeId.value) return
  try { await SkipNode(props.execution.id, selectedNodeId.value); await fetchLogs(); ElMessage.success('节点已跳过') }
  catch (e: any) { ElMessage.error(e?.msg || '跳过失败') }
}
async function onApprove() {
  approving.value = true
  try {
    await ApproveNode(props.execution.id, execDetail.value.current_node)
    ElMessage.success('Approved')
    await refresh()
  } catch (e: any) { ElMessage.error(e?.msg || 'Approve failed') }
  approving.value = false
}
async function onReject() {
  rejecting.value = true
  try {
    await RejectNode(props.execution.id, execDetail.value.current_node, 'Rejected')
    ElMessage.success('Rejected')
    await refresh()
  } catch (e: any) { ElMessage.error(e?.msg || 'Reject failed') }
  rejecting.value = false
}
async function onCancel() {
  cancelling.value = true
  try {
    await CancelExecution(props.execution.id)
    execDetail.value.status = 'cancelled'
    monitorRef.value?.setExecutionStatus?.('cancelled')
    emit('executionUpdate', { ...execDetail.value })
  } catch (e: any) { ElMessage.error(e?.msg || '取消失败') }
  cancelling.value = false
}

// Auto-refresh while execution is active (pending/running/paused)
let autoTimer: ReturnType<typeof setInterval> | null = null
function startAutoRefresh() { if (!autoTimer) autoTimer = setInterval(() => refresh(), 10000) }
function stopAutoRefresh() { if (autoTimer) { clearInterval(autoTimer); autoTimer = null } }

watch(isRunning, (v) => { if (v) startAutoRefresh(); else stopAutoRefresh() }, { immediate: true })
watch(() => props.execution.id, (newId) => { if (newId) { graphInitialized = false; loadPipeline(true); fetchLogs(); fetchTraces() } })

// WebSocket real-time node status update handler
function handleNodeStatusChange(payload: any) {
  if (payload.execution_id === props.execution.id) {
    monitorRef.value?.updateNodeStatus?.(payload.node_id, payload.status)
  }
}

onMounted(() => {
  loadPipeline()
  fetchLogs()
  fetchTraces()
  mittBus.on('nodeStatusChange', handleNodeStatusChange)
})
onActivated(() => { nextTick(() => { monitorRef.value?.refreshCanvas() }) })
onBeforeUnmount(() => {
  stopAutoRefresh()
  mittBus.off('nodeStatusChange', handleNodeStatusChange)
})
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

/* Traces tab */
.trace-section { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.trace-table-wrap { flex: 1; overflow-y: auto; }
.trace-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.trace-table th { text-align: left; padding: 4px 6px; background: #f5f7fa; color: #909399; font-weight: 500; position: sticky; top: 0; z-index: 1; }
.trace-table td { padding: 4px 6px; border-bottom: 1px solid #f2f2f2; }
.trace-table tbody tr { cursor: pointer; transition: background 0.15s; }
.trace-table tbody tr:hover { background: #f5f7fa; }
.trace-row-selected { background: #ecf5ff !important; }
.trace-status-completed td:first-child { border-left: 3px solid #67C23A; }
.trace-status-failed td:first-child { border-left: 3px solid #F56C6C; }
.trace-status-running td:first-child, .trace-status-retrying td:first-child { border-left: 3px solid #E6A23C; }
.trace-status-cancelled td:first-child { border-left: 3px solid #909399; }
.trace-node-id { font-family: monospace; font-size: 11px; color: #606266; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-retry-badge { display: inline-block; background: #e6a23c; color: #fff; border-radius: 8px; padding: 0 5px; font-size: 10px; line-height: 1.5; margin-left: 3px; vertical-align: middle; }
.trace-duration { font-family: monospace; font-size: 11px; color: #909399; }
.trace-retry-count { text-align: center; color: #909399; font-size: 11px; }

/* Trace log viewer */
.trace-log-viewer { border-top: 1px solid #e4e7ed; flex-shrink: 0; max-height: 200px; display: flex; flex-direction: column; }
.trace-log-header { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: #f5f7fa; font-size: 12px; font-weight: 500; color: #606266; }
.trace-log-title { font-family: monospace; }
.trace-log-body { margin: 0; padding: 8px; overflow-y: auto; font-size: 11px; line-height: 1.5; background: #f8f9fa; color: #303133; border: 1px solid #ebeef5; border-radius: 4px; flex: 1; white-space: pre-wrap; word-break: break-all; }

/* Tabs styling */
.trace-tabs { height: 100%; display: flex; flex-direction: column; }
.trace-tabs :deep(.el-tabs__header) { margin: 0; padding: 0 10px; }
.trace-tabs :deep(.el-tabs__content) { flex: 1; overflow: hidden; }

/* Approval banner */
.approval-banner {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 20px; background: #fdf0ff;
  border-bottom: 1px solid #ebd0f5; flex-shrink: 0;
}
.approval-banner-left { display: flex; align-items: center; gap: 10px; }
.approval-banner-text { font-size: 14px; font-weight: 600; color: #8E44AD; }
.approval-banner-actions { display: flex; gap: 8px; }
.trace-tabs :deep(.el-tab-pane) { height: 100%; overflow: hidden; }
.trace-tabs :deep(.el-tabs__nav-scroll) { padding: 0; }
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

/* ---------- Data Tab ---------- */
.data-section { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }
.data-group { margin-bottom: 14px; }
.data-group-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: #606266; padding: 6px 0; margin-bottom: 4px;
  border-bottom: 1px solid #e8e8e8;
}
.data-group-title-error { color: #F56C6C; }
.data-table { font-size: 12px; }
.data-row {
  display: flex; padding: 3px 0; gap: 8px;
  border-bottom: 1px solid #f5f5f5;
}
.data-row-error { background: #fff2f0; border-radius: 4px; padding: 3px 4px; }
.data-key {
  font-family: monospace; font-size: 11px; color: #409EFF; font-weight: 600;
  min-width: 80px; flex-shrink: 0; word-break: break-all;
}
.data-val {
  font-family: monospace; font-size: 11px; color: #303133;
  word-break: break-all; white-space: pre-wrap; flex: 1;
}
.data-empty { font-size: 12px; color: #C0C4CC; padding: 4px 0; }
.data-stdout {
  margin: 0; padding: 8px; background: #f8f9fa; color: #303133;
  border: 1px solid #ebeef5; border-radius: 6px; font-size: 11px; line-height: 1.5; max-height: 200px;
  overflow-y: auto; white-space: pre-wrap; word-break: break-all;
}
.data-stderr {
  margin: 0; padding: 8px; background: #2d1b1b; color: #ff6b6b;
  border-radius: 6px; font-size: 11px; line-height: 1.5; max-height: 200px;
  overflow-y: auto; white-space: pre-wrap; word-break: break-all;
}
</style>
