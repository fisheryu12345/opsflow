<template>
  <div class="exec-list-page">
    <!-- Hero Section -->
    <div class="exec-hero">
      <div class="exec-hero-bg" />
      <div class="exec-hero-inner">
        <div class="exec-hero-left">
          <h1 class="exec-hero-title">Executions</h1>
          <p class="exec-hero-subtitle">Pipeline execution history and monitoring</p>
        </div>
        <div class="exec-hero-center">
          <el-input v-model="searchQuery" placeholder="Search by template name..." clearable size="default"
            class="exec-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="exec-hero-stats">
          <div class="exec-stat-item"><span class="exec-stat-value">{{ total }}</span><span class="exec-stat-label">Total</span></div>
          <div class="exec-stat-divider" />
          <div class="exec-stat-item"><span class="exec-stat-value">{{ runningCount }}</span><span class="exec-stat-label">Running</span></div>
          <div class="exec-stat-divider" />
          <div class="exec-stat-item"><span class="exec-stat-value">{{ failedCount }}</span><span class="exec-stat-label">Failed</span></div>
          <div class="exec-stat-divider" />
          <div class="exec-stat-item"><span class="exec-stat-value">{{ completedCount }}</span><span class="exec-stat-label">Completed</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="exec-body">
      <!-- Filter bar -->
      <div class="exec-filter-bar">
        <div class="exec-filter-tabs">
          <div class="exec-tab" :class="{ active: filterStatus.length === 0 }" @click="filterStatus = []; onFilter()">
            <span class="exec-tab-dot" style="background:#409EFF" />All
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('running') }" @click="filterStatus = ['running']; onFilter()">
            <span class="exec-tab-dot" style="background:#E6A23C" />Running
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('completed') }" @click="filterStatus = ['completed']; onFilter()">
            <span class="exec-tab-dot" style="background:#67C23A" />Completed
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('failed') }" @click="filterStatus = ['failed']; onFilter()">
            <span class="exec-tab-dot" style="background:#F56C6C" />Failed
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('paused') }" @click="filterStatus = ['paused']; onFilter()">
            <span class="exec-tab-dot" style="background:#909399" />Paused
          </div>
        </div>
        <div class="exec-filter-actions">
          <el-select v-model="filterTemplate" placeholder="Template" clearable filterable size="small" style="width:160px" @change="onFilter">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
          <el-button :icon="Refresh" @click="fetchExecutions" :loading="loading" text size="small">Refresh</el-button>
          <el-button type="primary" :icon="Plus" @click="showCreateDialog" :disabled="templates.length === 0" size="small">New Execution</el-button>
        </div>
      </div>

      <!-- Table card -->
      <div class="exec-table-card">
        <el-table :data="displayList" v-loading="loading" stripe highlight-current-row
          @row-click="onRowClick" style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column label="Status" width="100">
            <template #default="{ row }">
              <span class="exec-status-badge" :class="'st-' + row.status">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="template_name" label="Template" min-width="180" show-overflow-tooltip />
          <el-table-column label="Started" width="160">
            <template #default="{ row }">{{ row.started_at || '-' }}</template>
          </el-table-column>
          <el-table-column label="Duration" width="100">
            <template #default="{ row }">
              <span class="exec-duration">{{ row.started_at && row.ended_at ? formatDuration(row.started_at, row.ended_at) : (row.started_at ? 'Running...' : '-') }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click.stop="emit('viewDetail', row)">Detail</el-button>
              <el-button v-if="row.status === 'pending'" size="small" text type="success"
                :loading="startingId === row.id" @click.stop="onStart(row)">Start</el-button>
              <el-button v-if="row.status === 'running'" size="small" text type="warning"
                :loading="pausingId === row.id" @click.stop="onPause(row)">Pause</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="exec-pagination" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @current-change="onPageChange" small />
        </div>
      </div>
    </div>

    <!-- Create dialog -->
    <el-dialog v-model="createVisible" title="New Execution" width="480px" top="8vh" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="Template">
          <el-select v-model="createTemplateId" placeholder="Select template" filterable style="width:100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id">
              <div class="exec-tpl-option"><span>{{ t.name }}</span><el-tag v-if="t.is_draft" size="small" type="info" effect="plain">draft</el-tag></div>
            </el-option>
          </el-select>
        </el-form-item>
        <div v-if="selectedTemplate" class="exec-tpl-info">
          <div class="exec-tpl-row"><span class="exec-tpl-label">Created:</span><span>{{ selectedTemplate.created_at }}</span></div>
          <div class="exec-tpl-row" v-if="selectedTemplate.pipeline_tree"><span class="exec-tpl-label">Nodes:</span><span>{{ selectedTemplate.pipeline_tree.nodes?.length || 0 }}</span></div>
        </div>
        <div v-if="optionalNodes.length > 0" class="exec-optional-section">
          <div class="exec-optional-label">Optional Nodes (deselect to skip)</div>
          <el-checkbox-group v-model="selectedNodeIds" class="exec-checkbox-group">
            <el-checkbox v-for="node in optionalNodes" :key="node.id" :label="node.id">{{ node.label || node.id }}</el-checkbox>
          </el-checkbox-group>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false" size="small">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="onCreate" size="small">Create</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetTemplates } from '/@/api/opsflow/templates'
import { GetExecutions, CreateExecution, StartExecution as StartExec, PauseExecution } from '/@/api/opsflow/executions'

const emit = defineEmits<{ viewDetail: [execution: any] }>()

const templates = ref<any[]>([])
const executions = ref<any[]>([])
const loading = ref(false)
const filterTemplate = ref<number | null>(null)
const filterStatus = ref<string[]>([])
const searchQuery = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const startingId = ref<number | null>(null)
const pausingId = ref<number | null>(null)
const createVisible = ref(false)
const createTemplateId = ref<number | null>(null)
const creating = ref(false)

const runningCount = computed(() => executions.value.filter(e => e.status === 'running').length)
const failedCount = computed(() => executions.value.filter(e => e.status === 'failed').length)
const completedCount = computed(() => executions.value.filter(e => e.status === 'completed').length)
const emptyText = computed(() => loading.value ? 'Loading...' : 'No executions yet')

const displayList = computed(() => {
  let items = executions.value
  if (filterStatus.value.length) items = items.filter(e => filterStatus.value.includes(e.status))
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(e => (e.template_name || '').toLowerCase().includes(q))
  }
  return items
})

const selectedTemplate = computed(() => templates.value.find(t => t.id === createTemplateId.value))
const selectedNodeIds = ref<string[]>([])
const optionalNodes = computed(() => {
  const tree = selectedTemplate.value?.pipeline_tree || {}
  return (tree.nodes || []).filter((n: any) => n.node_type === 'atom' && n.optional !== false)
})
watch(createTemplateId, () => { selectedNodeIds.value = optionalNodes.value.map((n: any) => n.id) })

function statusLabel(s: string) {
  const m: Record<string, string> = { pending: 'Pending', running: 'Running', paused: 'Paused', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled' }
  return m[s] || s
}
function formatDuration(start: string, end: string) {
  const diff = new Date(end).getTime() - new Date(start).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
}

async function fetchTemplates() {
  try { const r = await GetTemplates(); templates.value = r.data || r.results || [] } catch { /* ignore */ }
}
async function fetchExecutions() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterTemplate.value) params.template = filterTemplate.value
    const r = await GetExecutions(params)
    executions.value = r.data?.results || r.data || r.results || []
    total.value = r.data?.count || r.count || 0
  } catch { /* ignore */ }
  loading.value = false
}

function showCreateDialog() { createTemplateId.value = null; createVisible.value = true }
function onFilter() { page.value = 1; fetchExecutions() }
function onSearch() { page.value = 1; fetchExecutions() }
function onPageChange() { fetchExecutions() }

async function onCreate() {
  if (!createTemplateId.value) { ElMessage.warning('Please select a template'); return }
  creating.value = true
  try {
    const allOptional = optionalNodes.value.map((n: any) => n.id)
    const excluded = allOptional.filter((id: string) => !selectedNodeIds.value.includes(id))
    const data: any = { template: createTemplateId.value }
    if (excluded.length > 0) data.excluded_nodes = excluded
    const res = await CreateExecution(data)
    const exec = res.data?.data || res.data
    if (exec?.id) {
      createVisible.value = false; ElMessage.success('Execution created')
      await fetchExecutions(); emit('viewDetail', exec)
    }
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed') }
  creating.value = false
}
function onRowClick(row: any) { emit('viewDetail', row) }
async function onStart(row: any) { startingId.value = row.id; try { await StartExec(row.id); await fetchExecutions() } catch { /* ignore */ }; startingId.value = null }
async function onPause(row: any) { pausingId.value = row.id; try { await PauseExecution(row.id); await fetchExecutions() } catch { /* ignore */ }; pausingId.value = null }

onMounted(() => { fetchTemplates(); fetchExecutions() })
</script>

<style scoped>
.exec-list-page { height: 100%; display: flex; flex-direction: column; }

/* ===== Hero ===== */
.exec-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.exec-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.exec-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.exec-hero-left { flex: 0 0 auto; }
.exec-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.exec-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.exec-hero-center { flex: 1 1 auto; min-width: 0; }
.exec-search-input { width: 100%; max-width: 320px; }
.exec-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.exec-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.exec-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.exec-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.exec-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.exec-stat-item { text-align: center; padding: 0 14px; }
.exec-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.exec-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.exec-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.exec-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.exec-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.exec-filter-tabs { display: flex; gap: 4px; }
.exec-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.exec-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.exec-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.exec-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.exec-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table card ===== */
.exec-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.exec-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.exec-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.exec-status-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; }
.st-pending { background: #f5f5f5; color: #909399; }
.st-running { background: #fdf6ec; color: #E6A23C; }
.st-paused { background: #f0f5ff; color: #2f54eb; }
.st-completed { background: #f0f9eb; color: #67C23A; }
.st-failed { background: #fef0f0; color: #F56C6C; }
.st-cancelled { background: #f5f5f5; color: #909399; }
.exec-duration { font-size: 12px; color: #909399; }
.exec-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }
.exec-tpl-option { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.exec-tpl-info { margin-top: 8px; padding: 10px 12px; background: #f5f7fa; border-radius: 8px; font-size: 12px; }
.exec-tpl-row { display: flex; justify-content: space-between; padding: 2px 0; }
.exec-tpl-label { color: #909399; }
.exec-optional-section { margin-top: 12px; }
.exec-optional-label { font-size: 12px; color: #606266; font-weight: 500; margin-bottom: 8px; }
.exec-checkbox-group { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; padding: 8px 12px; background: #fafafa; border-radius: 8px; }
</style>
