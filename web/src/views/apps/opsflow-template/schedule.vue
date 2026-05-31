<template>
  <div class="schedule-page">
    <div class="page-header">
      <span class="page-title">调度管理</span>
      <el-button type="primary" size="small" @click="openCreate">新建调度</el-button>
    </div>
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
    <ScheduleForm
      v-model="formVisible"
      :plan="editingPlan"
      :template-id="editingPlan?.template || undefined"
      @saved="fetchList"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
    ElMessage.success('调度已暂停')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  }
}

async function handleResume(row: any) {
  try {
    await ResumeSchedulePlan(row.id)
    ElMessage.success('调度已恢复')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  }
}

async function handleTrigger(row: any) {
  try {
    await TriggerSchedulePlan(row.id)
    ElMessage.success('手动触发已提交')
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除调度「${row.name}」？`, '确认', { type: 'warning' })
    await DeleteSchedulePlan(row.id)
    ElMessage.success('调度已删除')
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
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
</style>
