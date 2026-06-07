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
        <ProjectSwitcher :dark="true" />
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
          <div class="exec-tab" :class="{ active: filterStatus.includes('pending_approval') }" @click="filterStatus = ['pending_approval']; onFilter()">
            <span class="exec-tab-dot" style="background:#9B59B6" />Pending Approval
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('pending') }" @click="filterStatus = ['pending']; onFilter()">
            <span class="exec-tab-dot" style="background:#909399" />Pending
          </div>
        </div>
        <div class="exec-filter-actions">
          <el-button :icon="Refresh" @click="fetchExecutions" :loading="loading" text size="small">Refresh</el-button>
        </div>
      </div>

      <!-- Table card -->
      <div class="exec-table-card">
        <el-table :data="displayList" v-loading="loading" stripe highlight-current-row
          @row-click="onRowClick" style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column label="Status" width="140">
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
          <el-table-column label="CR Number" width="140">
            <template #default="{ row }">
              <span class="exec-cr-number">{{ row.context?.cr_number || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="CR Title" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.context?.cr_title || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="CR Status" width="110">
            <template #default="{ row }">
              <span v-if="row.context?.cr_status === 'approved'" class="exec-cr-status st-approved">Approved</span>
              <span v-else-if="row.context?.cr_status === 'pending'" class="exec-cr-status st-pending-cr">Pending</span>
              <span v-else class="exec-cr-status st-none">-</span>
            </template>
          </el-table-column>
          <el-table-column label="Schedule" width="160">
            <template #default="{ row }">
              <span>{{ row.schedule_plan_scheduled_at ? formatTime(row.schedule_plan_scheduled_at) : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="220" fixed="right">
            <template #default="{ row }">
              <div class="exec-actions">
                <el-tooltip content="View Detail" placement="top">
                  <el-button size="small" circle text type="primary" :icon="View" @click.stop="emit('viewDetail', row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'pending'" content="Start" placement="top">
                  <el-button size="small" circle text type="success" :icon="VideoPlay" :loading="startingId === row.id" @click.stop="onStart(row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'pending_approval' || row.status === 'pending'" content="Cancel" placement="top">
                  <el-button size="small" circle text type="danger" :icon="Close" :loading="cancellingId === row.id" @click.stop="onCancel(row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'running'" content="Pause" placement="top">
                  <el-button size="small" circle text type="warning" :icon="VideoPause" :loading="pausingId === row.id" @click.stop="onPause(row)" />
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="exec-pagination" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @current-change="onPageChange" small />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, Search, View, VideoPlay, VideoPause, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetExecutions, StartExecution as StartExec, PauseExecution, CancelExecution } from '../../opsflow/api/executions'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'
import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'
const emit = defineEmits<{ viewDetail: [execution: any] }>()

const store = useOpsflowStore()

const executions = ref<any[]>([])
const loading = ref(false)
const filterStatus = ref<string[]>([])
const searchQuery = ref('')
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const startingId = ref<number | null>(null)
const pausingId = ref<number | null>(null)
const cancellingId = ref<number | null>(null)

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

function statusLabel(s: string) {
  const m: Record<string, string> = { pending: 'Pending', pending_approval: 'Pending Approval', running: 'Running', paused: 'Paused', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled' }
  return m[s] || s
}
function formatDuration(start: string, end: string) {
  const diff = new Date(end).getTime() - new Date(start).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
}

function formatTime(dt: string) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

async function fetchExecutions() {
  loading.value = true
  try {
    const params: any = { limit: pageSize.value, page: page.value }
    const r = await GetExecutions(params)
    // r 已经是 {code:2000, data:[...], total:112} (拦截器已处理)
    const list = Array.isArray(r) ? r : (Array.isArray(r.data) ? r.data : (r.results || []))
    executions.value = list
    total.value = r.total || r.count || 0
  } catch { /* ignore */ }
  loading.value = false
}

function onFilter() { page.value = 1; fetchExecutions() }
function onSearch() { page.value = 1; fetchExecutions() }
function onPageChange() { fetchExecutions() }

function onRowClick(row: any) { emit('viewDetail', row) }
async function onStart(row: any) { startingId.value = row.id; try { await StartExec(row.id); await fetchExecutions() } catch { /* ignore */ }; startingId.value = null }
async function onPause(row: any) { pausingId.value = row.id; try { await PauseExecution(row.id); await fetchExecutions() } catch { /* ignore */ }; pausingId.value = null }
async function onCancel(row: any) { cancellingId.value = row.id; try { await CancelExecution(row.id); ElMessage.success('Execution cancelled'); await fetchExecutions() } catch { /* ignore */ }; cancellingId.value = null }

onMounted(async () => {
  if (!store.myProjects.length) await store.fetchMyProjects()
  fetchExecutions()
})
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
.exec-actions { display: flex; gap: 2px; align-items: center; }

/* ===== Table card ===== */
.exec-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.exec-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.exec-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.exec-status-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; }
.st-pending { background: #f5f5f5; color: #909399; }
.st-pending_approval { background: #f3e8ff; color: #9B59B6; }
.st-running { background: #fdf6ec; color: #E6A23C; }
.st-paused { background: #f0f5ff; color: #2f54eb; }
.st-completed { background: #f0f9eb; color: #67C23A; }
.st-failed { background: #fef0f0; color: #F56C6C; }
.st-cancelled { background: #f5f5f5; color: #909399; }
.exec-duration { font-size: 12px; color: #909399; }
.exec-cr-number { font-family: monospace; font-size: 12px; color: #409EFF; font-weight: 600; }
.exec-cr-status { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 8px; }
.exec-cr-status.st-approved { background: #f0f9eb; color: #67C23A; }
.exec-cr-status.st-pending-cr { background: #fdf6ec; color: #E6A23C; }
.exec-cr-status.st-none { background: #f5f5f5; color: #C0C4CC; }
.exec-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }
</style>
