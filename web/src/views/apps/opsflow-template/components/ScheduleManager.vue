<template>
  <el-dialog
    :title="displayName"
    v-model="visible"
    width="1000px"
    top="5vh"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div style="margin-bottom: 16px;">
      <span style="font-size: 13px; color: #909399">
        {{ list.length }} schedule(s)
      </span>
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
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  GetSchedulePlans,
  PauseSchedulePlan,
  ResumeSchedulePlan,
  TriggerSchedulePlan,
  DeleteSchedulePlan,
} from '../../opsflow/api/schedule-plans'
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
const displayName = computed(() => {
  const name = props.templateName || ''
  return (name.length > 20 ? name.slice(0, 20) + '…' : name) + ' - Schedule'
})

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
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Operation failed')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`Delete schedule "${row.name}"?`, 'Confirm', {
      type: 'warning',
    })
    await DeleteSchedulePlan(row.id)
    ElMessage.success('Schedule deleted')
    fetchList()
  } catch {
    // cancelled
  }
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>
