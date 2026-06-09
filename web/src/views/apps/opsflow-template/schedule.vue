<template>
  <div class="sc-page">
    <!-- Hero Section -->
    <div class="sc-hero">
      <div class="sc-hero-bg" />
      <div class="sc-hero-inner">
        <div class="sc-hero-left">
          <h1 class="sc-hero-title">{{ $t('message.schedule.title') }}</h1>
          <p class="sc-hero-subtitle">{{ $t('message.schedule.schSubtitle') }}</p>
        </div>
        <ProjectSwitcher :dark="true" />
        <div class="sc-hero-center">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('message.schedule.schSearchPlaceholder')"
            clearable
            size="default"
            class="sc-search-input"
            @keyup.enter="onSearch"
            @clear="onSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="sc-hero-stats">
          <div class="sc-stat-item"><span class="sc-stat-value">{{ total }}</span><span class="sc-stat-label">{{ $t('message.schedule.schStatTotal') }}</span></div>
          <div class="sc-stat-divider" />
          <div class="sc-stat-item"><span class="sc-stat-value">{{ activeCount }}</span><span class="sc-stat-label">{{ $t('message.schedule.schStatActive') }}</span></div>
          <div class="sc-stat-divider" />
          <div class="sc-stat-item"><span class="sc-stat-value">{{ totalRuns }}</span><span class="sc-stat-label">{{ $t('message.schedule.schStatRuns') }}</span></div>
          <div class="sc-stat-divider" />
          <div class="sc-stat-item"><span class="sc-stat-value">{{ pausedCount }}</span><span class="sc-stat-label">{{ $t('message.schedule.schStatPaused') }}</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="sc-body">
      <!-- Filter bar -->
      <div class="sc-filter-bar">
        <div class="sc-filter-tabs">
          <div class="sc-tab" :class="{ active: filterType === '' }" @click="filterType = ''; onSearch()">
            <span class="sc-tab-dot" style="background:#409EFF" />{{ $t('message.schedule.schFilterAll') }}
          </div>
          <div class="sc-tab" :class="{ active: filterType === 'active' }" @click="filterType = 'active'; onSearch()">
            <span class="sc-tab-dot" style="background:#67C23A" />{{ $t('message.schedule.enabled') }}
          </div>
          <div class="sc-tab" :class="{ active: filterType === 'paused' }" @click="filterType = 'paused'; onSearch()">
            <span class="sc-tab-dot" style="background:#E6A23C" />{{ $t('message.schedule.disabled') }}
          </div>
          <div class="sc-tab" :class="{ active: filterType === 'one_time' }" @click="filterType = 'one_time'; onSearch()">
            <span class="sc-tab-dot" style="background:#9B59B6" />{{ $t('message.schedule.onceTrigger') }}
          </div>
          <div class="sc-tab" :class="{ active: filterType === 'cron' }" @click="filterType = 'cron'; onSearch()">
            <span class="sc-tab-dot" style="background:#409EFF" />{{ $t('message.schedule.cronTrigger') }}
          </div>
        </div>
        <div class="sc-filter-actions">
          <el-button :icon="Refresh" @click="fetchList" :loading="loading" text size="small">{{ $t('message.common.refresh') }}</el-button>
        </div>
      </div>

      <!-- Table -->
      <div class="sc-table-card">
        <ScheduleTable
          :list="filteredList"
          :loading="loading"
          show-template
          @edit="openEdit"
          @pause="handlePause"
          @resume="handleResume"
          @trigger="handleTrigger"
          @delete="handleDelete"
        />
        <el-empty v-if="!loading && filteredList.length === 0" :description="emptyText" :image-size="80" style="padding: 60px 0" />
      </div>
    </div>

    <ScheduleForm
      v-model="formVisible"
      :plan="editingPlan"
      :template-id="editingPlan?.template || undefined"
      @saved="fetchList"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import {
  GetSchedulePlans,
  PauseSchedulePlan,
  ResumeSchedulePlan,
  TriggerSchedulePlan,
  DeleteSchedulePlan,
} from '../opsflow/api/schedule-plans'
import ScheduleTable from './components/ScheduleTable.vue'
import ScheduleForm from './components/ScheduleForm.vue'

import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'
const { t } = useI18n()
const list = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')
const filterType = ref('')
const formVisible = ref(false)
const editingPlan = ref<any>(null)

const total = computed(() => list.value.length)
const activeCount = computed(() => list.value.filter(s => s.status === 'active').length)
const pausedCount = computed(() => list.value.filter(s => s.status === 'paused').length)
const totalRuns = computed(() => list.value.reduce((s, r) => s + (r.total_run_count || 0), 0))

const filteredList = computed(() => {
  let items = list.value
  if (filterType.value === 'active') items = items.filter(s => s.status === 'active')
  else if (filterType.value === 'paused') items = items.filter(s => s.status === 'paused')
  else if (filterType.value === 'one_time') items = items.filter(s => s.schedule_type === 'one_time')
  else if (filterType.value === 'cron') items = items.filter(s => s.schedule_type === 'cron')
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(s => s.name?.toLowerCase().includes(q) || s.template_name?.toLowerCase().includes(q))
  }
  return items
})

const emptyText = computed(() => t('message.schedule.noSchedules'))

async function fetchList() {
  loading.value = true
  try {
    const res: any = await GetSchedulePlans({ limit: 200 })
    list.value = res?.data || []
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

function openEdit(row: any) {
  editingPlan.value = { ...row }
  formVisible.value = true
}

async function handlePause(row: any) {
  try { await PauseSchedulePlan(row.id); ElMessage.success(t('message.schedule.schPaused')); fetchList()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.schedule.schOperationFailed')) }
}

async function handleResume(row: any) {
  try { await ResumeSchedulePlan(row.id); ElMessage.success(t('message.schedule.schResumed')); fetchList()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.schedule.schOperationFailed')) }
}

async function handleTrigger(row: any) {
  try { await TriggerSchedulePlan(row.id); ElMessage.success(t('message.schedule.schTriggered')); fetchList()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.schedule.schOperationFailed')) }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(t('message.schedule.schDeleteConfirm', { name: row.name }), t('message.common.confirm'), { type: 'warning' })
    await DeleteSchedulePlan(row.id); ElMessage.success(t('message.schedule.deleteSuccess')); fetchList()
  } catch { /* cancelled */ }
}

function onSearch() { /* computed auto-filters */ }

// Re-fetch schedules when project switches via ProjectSwitcher
function onProjectChanged() {
  fetchList()
}

onMounted(async () => {
  const { useOpsflowStore } = await import('/@/views/apps/opsflow/stores/opsflowStore');
  const store = useOpsflowStore();
  if (!store.myProjects.length) await store.fetchMyProjects();
  fetchList()
  window.addEventListener('project-changed', onProjectChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
})
</script>

<style scoped>
/* ===== Layout ===== */
.sc-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.sc-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.sc-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.sc-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.sc-hero-left { flex: 0 0 auto; }
.sc-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.sc-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.sc-hero-center { flex: 1 1 auto; min-width: 0; }
.sc-search-input { width: 100%; max-width: 320px; }
.sc-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.sc-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.sc-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.sc-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.sc-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.sc-stat-item { text-align: center; padding: 0 14px; }
.sc-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.sc-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.sc-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.sc-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.sc-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.sc-filter-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
.sc-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.sc-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.sc-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.sc-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.sc-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table card ===== */
.sc-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); overflow: hidden; }
.sc-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.sc-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
</style>
