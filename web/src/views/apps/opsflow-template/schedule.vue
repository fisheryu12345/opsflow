<template>
  <div class="schedule-page">
    <!-- Header with stats -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-title-row">
          <h2 class="page-title">Schedule Management</h2>
          <el-tag size="small" type="primary" effect="light">{{ list.length }} total</el-tag>
        </div>
        <p class="page-subtitle">Manage recurring and one-time pipeline executions</p>
      </div>
      <div class="header-right">
        <el-button :icon="Refresh" @click="fetchList" :loading="loading" size="small">
          Refresh
        </el-button>
        <el-button type="primary" :icon="Plus" size="small" @click="openCreate">
          New Schedule
        </el-button>
      </div>
    </div>

    <!-- Stats cards -->
    <div class="stats-row">
      <div class="stat-card" v-for="s in stats" :key="s.key">
        <div class="stat-icon" :style="{ background: s.bg }">
          <el-icon :size="18" :color="s.color"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <span class="stat-value" :style="{ color: s.color }">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="table-container">
      <ScheduleTable
        :list="list"
        :loading="loading"
        show-template
        @edit="openEdit"
        @pause="handlePause"
        @resume="handleResume"
        @trigger="handleTrigger"
        @delete="handleDelete"
      />
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Timer, VideoPlay, VideoPause, CircleCheck, RefreshRight } from '@element-plus/icons-vue'
import {
  GetSchedulePlans,
  PauseSchedulePlan,
  ResumeSchedulePlan,
  TriggerSchedulePlan,
  DeleteSchedulePlan,
} from '/@/api/opsflow/schedule-plans'
import ScheduleTable from './components/ScheduleTable.vue'
import ScheduleForm from './components/ScheduleForm.vue'

const list = ref<any[]>([])
const loading = ref(false)
const formVisible = ref(false)
const editingPlan = ref<any>(null)

const stats = computed(() => [
  { key: 'total', label: 'Total', value: list.value.length, icon: Timer, bg: '#e6f7ff', color: '#1890ff' },
  { key: 'active', label: 'Active', value: list.value.filter(s => s.status === 'active').length, icon: VideoPlay, bg: '#f6ffed', color: '#52c41a' },
  { key: 'paused', label: 'Paused', value: list.value.filter(s => s.status === 'paused').length, icon: VideoPause, bg: '#fff7e6', color: '#fa8c16' },
  { key: 'completed', label: 'Completed', value: list.value.filter(s => s.status === 'completed').length, icon: CircleCheck, bg: '#f0f5ff', color: '#2f54eb' },
  { key: 'total_runs', label: 'Total Runs', value: list.value.reduce((s, r) => s + (r.total_run_count || 0), 0), icon: RefreshRight, bg: '#fff0f6', color: '#eb2f96' },
])

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

function openCreate() {
  editingPlan.value = null
  formVisible.value = true
}

function openEdit(row: any) {
  editingPlan.value = { ...row }
  formVisible.value = true
}

async function handlePause(row: any) {
  try {
    await PauseSchedulePlan(row.id)
    ElMessage.success('Schedule paused')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Operation failed')
  }
}

async function handleResume(row: any) {
  try {
    await ResumeSchedulePlan(row.id)
    ElMessage.success('Schedule resumed')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Operation failed')
  }
}

async function handleTrigger(row: any) {
  try {
    await TriggerSchedulePlan(row.id)
    ElMessage.success('Manual trigger submitted')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Operation failed')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`Delete schedule "${row.name}"?`, 'Confirm', { type: 'warning' })
    await DeleteSchedulePlan(row.id)
    ElMessage.success('Schedule deleted')
    fetchList()
  } catch {
    // cancelled
  }
}

onMounted(() => fetchList())
</script>

<style scoped>
.schedule-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------- Header ---------- */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.header-title-row { display: flex; align-items: center; gap: 10px; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #303133; }
.page-subtitle { margin: 0; font-size: 13px; color: #909399; }
.header-right { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ---------- Stats cards ---------- */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.stat-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-body { display: flex; flex-direction: column; gap: 2px; }
.stat-value { font-size: 20px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 12px; color: #909399; white-space: nowrap; }

/* ---------- Table container ---------- */
.table-container {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  overflow: hidden;
}
.table-container :deep(.el-table th.el-table__cell) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
  font-size: 12px;
}
.table-container :deep(.el-table__body tr:hover td) {
  background: #f5f7fa;
}
</style>
