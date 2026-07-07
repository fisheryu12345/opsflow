<template>
  <div class="exec-list-page">
    <!-- Search (teleported to outer hero dark area) -->
    <Teleport v-if="active && searchEl" :to="searchEl">
      <el-input v-model="searchQuery" :placeholder="$t('message.execution.searchPlaceholder')" clearable size="default"
        class="exec-search-input" @keyup.enter="onSearch" @clear="onSearch">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </Teleport>

    <!-- Filter bar (teleported to outer hero filter area) -->
    <Teleport v-if="active && filterEl" :to="filterEl">
      <div class="exec-filter-bar">
        <div class="exec-filter-tabs">
          <div class="exec-tab" :class="{ active: filterStatus.length === 0 }" @click="filterStatus = []; onFilter()">
            <span class="exec-tab-dot" style="background:#409EFF" />{{ $t('message.execution.filterAll') }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('running') }" @click="filterStatus = ['running']; onFilter()">
            <span class="exec-tab-dot" style="background:#E6A23C" />{{ $t('message.execution.statRunning') }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('completed') }" @click="filterStatus = ['completed']; onFilter()">
            <span class="exec-tab-dot" style="background:#67C23A" />{{ $t('message.execution.statCompleted') }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('failed') }" @click="filterStatus = ['failed']; onFilter()">
            <span class="exec-tab-dot" style="background:#F56C6C" />{{ $t('message.execution.statFailed') }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('paused') }" @click="filterStatus = ['paused']; onFilter()">
            <span class="exec-tab-dot" style="background:#909399" />{{ $t("message.execution.statePaused") }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('pending_approval') }" @click="filterStatus = ['pending_approval']; onFilter()">
            <span class="exec-tab-dot" style="background:#9B59B6" />{{ $t("message.execution.statusPendingApproval") }}
          </div>
          <div class="exec-tab" :class="{ active: filterStatus.includes('pending') }" @click="filterStatus = ['pending']; onFilter()">
            <span class="exec-tab-dot" style="background:#909399" />{{ $t("message.execution.statePending") }}
          </div>
        </div>
        <div class="exec-filter-actions">
          <el-button :icon="Refresh" @click="fetchExecutions" :loading="loading" text size="small">{{ $t("message.common.refresh") }}</el-button>
        </div>
      </div>
    </Teleport>

    <!-- Body -->
    <div class="exec-body">

      <!-- Table card -->
      <div class="exec-table-card">
        <el-table :data="displayList" v-loading="loading" stripe highlight-current-row
          @row-click="onRowClick" style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column prop="id" :label="$t('message.execution.colId')" width="60" />
          <el-table-column :label="$t('message.execution.status')" width="140">
            <template #default="{ row }">
              <span class="exec-status-badge" :class="'st-' + row.status">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="template_name" :label="$t('message.execution.colTemplate')" min-width="180" show-overflow-tooltip />
          <el-table-column :label="$t('message.execution.colStarted')" width="160">
            <template #default="{ row }">{{ row.started_at || '-' }}</template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colDuration')" width="100">
            <template #default="{ row }">
              <span class="exec-duration">{{ row.started_at && row.ended_at ? formatDuration(row.started_at, row.ended_at) : (row.started_at ? t('message.execution.durationRunning') : '-') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colCrNumber')" width="140">
            <template #default="{ row }">
              <span class="exec-cr-number">{{ row.context?.cr_number || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colCrTitle')" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.context?.cr_title || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colCrStatus')" width="110">
            <template #default="{ row }">
              <span v-if="row.context?.cr_status === 'approved'" class="exec-cr-status st-approved">{{ $t("message.execution.stateApproved") }}</span>
              <span v-else-if="row.context?.cr_status === 'pending'" class="exec-cr-status st-pending-cr">{{ $t("message.execution.statePending") }}</span>
              <span v-else class="exec-cr-status st-none">-</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colSchedule')" width="160">
            <template #default="{ row }">
              <span>{{ row.schedule_plan_scheduled_at ? formatTime(row.schedule_plan_scheduled_at) : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.execution.colActions')" width="220" fixed="right">
            <template #default="{ row }">
              <div class="exec-actions">
                <el-tooltip :content="$t('message.execution.viewDetail')" placement="top">
                  <el-button size="small" circle text :icon="View" @click.stop="emit('viewDetail', row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'pending'" :content="$t('message.execution.start')" placement="top">
                  <el-button size="small" circle text type="success" v-can.edit :icon="VideoPlay" :loading="startingId === row.id" @click.stop="onStart(row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'pending_approval' || row.status === 'pending'" :content="$t('message.execution.cancel')" placement="top">
                  <el-button size="small" circle text type="danger" v-can.admin :icon="Close" :loading="cancellingId === row.id" @click.stop="onCancel(row)" />
                </el-tooltip>
                <el-tooltip v-if="row.status === 'running'" :content="$t('message.execution.pause')" placement="top">
                  <el-button size="small" circle text type="warning" v-can.admin :icon="VideoPause" :loading="pausingId === row.id" @click.stop="onPause(row)" />
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="exec-pagination" v-if="total > 0">
          <el-pagination v-model:currentPage="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @update:currentPage="onPageChange" size="small" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { useI18n } from 'vue-i18n'
import { Refresh, Search, View, VideoPlay, VideoPause, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetExecutions, StartExecution as StartExec, PauseExecution, CancelExecution } from '../../opsflow/api/executions'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const emit = defineEmits<{ viewDetail: [execution: any] }>()

const { reportStats: updateHeroStats, filterEl, searchEl } = useHeroConsumer()

const store = useOpsflowStore()
const { t } = useI18n()

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
const emptyText = computed(() => loading.value ? t('message.common.loading') : t('message.execution.noExecutions'))

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
  const m: Record<string, string> = { pending: t('message.execution.statePending'), pending_approval: t('message.execution.statusPendingApproval'), running: t('message.execution.statRunning'), paused: t('message.execution.statePaused'), completed: t('message.execution.statCompleted'), failed: t('message.execution.statFailed'), cancelled: t('message.execution.stateCancelled') }
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
    // Report stats to outer hero (only when this tab is active)
    if (props.active) reportStats()
  } catch { /* ignore */ }
  loading.value = false
}

function reportStats() {
  const execList = executions.value
  updateHeroStats([
    { value: total.value || execList.length, label: t('message.execution.statTotal') },
    { value: execList.filter((e: any) => e.status === 'running').length, label: t('message.execution.statRunning') },
    { value: execList.filter((e: any) => e.status === 'failed').length, label: t('message.execution.statFailed') },
    { value: execList.filter((e: any) => e.status === 'completed').length, label: t('message.execution.statCompleted') },
  ])
}

function onFilter() { page.value = 1; fetchExecutions() }
function onSearch() { page.value = 1; fetchExecutions() }
function onPageChange() { fetchExecutions() }

function onRowClick(row: any) { emit('viewDetail', row) }
async function onStart(row: any) { startingId.value = row.id; try { await StartExec(row.id); await fetchExecutions() } catch { /* ignore */ }; startingId.value = null }
async function onPause(row: any) { pausingId.value = row.id; try { await PauseExecution(row.id); await fetchExecutions() } catch { /* ignore */ }; pausingId.value = null }
async function onCancel(row: any) { cancellingId.value = row.id; try { await CancelExecution(row.id); ElMessage.success(t('message.execution.cancelSuccess')); await fetchExecutions() } catch { /* ignore */ }; cancellingId.value = null }

// Re-report stats when this tab becomes active
watch(() => props.active, (isActive) => {
  if (isActive && executions.value.length > 0) reportStats()
})

onMounted(async () => {
  if (!store.myProjects.length) await store.fetchMyProjects()
  fetchExecutions()
})
</script>

<style scoped>
.exec-list-page { height: 100%; display: flex; flex-direction: column; }

/* ===== Body ===== */
.exec-body { flex: 1; overflow-y: auto; padding: 16px 16px 24px; }

/* ===== Filter bar (teleported to outer hero) ===== */
.exec-filter-bar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.exec-filter-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; flex: 1; min-width: 0; }
.exec-filter-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
.exec-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.exec-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.exec-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.exec-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.exec-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.exec-search-input { width: 220px; }
.exec-search-input :deep(.el-input__wrapper) { border-radius: 10px; }
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
