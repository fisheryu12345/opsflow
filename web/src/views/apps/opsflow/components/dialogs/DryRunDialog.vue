<template>
  <el-dialog
    v-model="visible"
    title="🧪 Dry Run"
    width="960px"
    top="5vh"
    :close-on-click-modal="false"
    class="opsflow-dialog"
    @close="handleClose"
    @opened="mounted = true"
    destroy-on-close
  >
    <div class="dryrun-body">
      <ExecutionDetail
        v-if="mounted && executionId"
        :execution="{ id: executionId }"
        @back="visible = false"
      />
    </div>

    <template #footer>
      <div class="dryrun-footer">
        <el-tag v-if="statusLabel" :type="statusTag" effect="dark" >
          {{ statusLabel }}
        </el-tag>
        <el-button type="primary" @click="visible = false">Close</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import ExecutionDetail from '/@/views/apps/opsflow-execution/components/ExecutionDetail.vue'
import { GetExecutionDetail } from '../../api/executions'

const props = defineProps<{
  modelValue: boolean
  executionId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const mounted = ref(false)
const execDetail = ref<any>(null)
const statusLabel = ref('')
const statusTag = ref('info')

let pollTimer: ReturnType<typeof setInterval> | null = null

watch(() => props.executionId, (id) => {
  if (id) startPolling()
  else stopPolling()
}, { immediate: true })

watch(visible, (v) => {
  if (!v) { mounted.value = false; stopPolling() }
  else if (props.executionId) startPolling()
})

function startPolling() {
  stopPolling()
  pollTimer = setInterval(fetchStatus, 10000)
  setTimeout(() => fetchStatus(), 500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function fetchStatus() {
  if (!props.executionId) return
  try {
    const res = await GetExecutionDetail(props.executionId)
    const ex = res.data?.data || res.data
    execDetail.value = ex
    const map: Record<string, string> = {
      pending: 'Pending', running: 'Running', completed: 'Completed',
      failed: 'Failed', cancelled: 'Cancelled',
    }
    statusLabel.value = map[ex?.status || ''] || ''
    const tagMap: Record<string, string> = {
      pending: 'info', running: 'warning', completed: 'success', failed: 'danger',
    }
    statusTag.value = tagMap[ex?.status || ''] || 'info'
    if (ex?.status && ['completed', 'failed', 'cancelled'].includes(ex.status)) {
      setTimeout(() => stopPolling(), 3000)
    }
  } catch {}
}

function handleClose() {
  mounted.value = false
  stopPolling()
  emit('update:modelValue', false)
}

onBeforeUnmount(() => stopPolling())
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { padding: 0 !important; min-height: 0; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }

.dryrun-body {
  height: 560px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.dryrun-body :deep(.execution-detail) { flex: 1; min-height: 0; }
.dryrun-body :deep(.detail-header) { display: none; }
.dryrun-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
