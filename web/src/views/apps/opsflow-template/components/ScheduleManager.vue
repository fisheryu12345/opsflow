<template>
  <el-dialog
    :title="`${templateName} - 调度计划`"
    v-model="visible"
    width="1000px"
    top="5vh"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center">
      <span style="font-size: 13px; color: #909399">
        共 {{ list.length }} 个调度计划
      </span>
      <el-button type="primary" size="small" @click="openCreate">新建调度</el-button>
    </div>

    <ScheduleTable
      :list="list"
      :loading="loading"
      @edit="openEdit"
      @pause="handlePause"
      @resume="handleResume"
      @trigger="handleTrigger"
      @delete="handleDelete"
    />

    <ScheduleForm
      v-model="formVisible"
      :plan="editingPlan"
      :template-id="templateId"
      @saved="fetchList"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  GetSchedulePlans,
  PauseSchedulePlan,
  ResumeSchedulePlan,
  TriggerSchedulePlan,
  DeleteSchedulePlan,
} from '/@/api/opsflow/schedule-plans'
import ScheduleTable from './ScheduleTable.vue'
import ScheduleForm from './ScheduleForm.vue'

const props = defineProps<{
  modelValue: boolean
  templateId: number
  templateName: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = ref(false)
const list = ref<any[]>([])
const loading = ref(false)
const formVisible = ref(false)
const editingPlan = ref<any>(null)

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val && props.templateId) {
      fetchList()
    }
  }
)

async function fetchList() {
  loading.value = true
  try {
    const res: any = await GetSchedulePlans({ template: props.templateId, limit: 100 })
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
    await ElMessageBox.confirm(`确定删除调度「${row.name}」？`, '确认', {
      type: 'warning',
    })
    await DeleteSchedulePlan(row.id)
    ElMessage.success('调度已删除')
    fetchList()
  } catch {
    // cancelled
  }
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>
