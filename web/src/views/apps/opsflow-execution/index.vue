<template>
  <div class="opsflow-exec-page">
    <!-- List view -->
    <div v-if="!selectedExecution" class="exec-page-body">
      <ExecutionList @view-detail="onViewDetail" ref="listRef" :active="props.active" />
    </div>

    <!-- Detail view -->
    <div v-else class="exec-page-body">
      <ExecutionDetail :execution="selectedExecution"
                       @back="selectedExecution = null"
                       @execution-update="onExecutionUpdate" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ExecutionList from './components/ExecutionList.vue'
import ExecutionDetail from './components/ExecutionDetail.vue'
import { GetExecutionDetail } from '../opsflow/api/executions'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'

const props = withDefaults(defineProps<{ embedded?: boolean; active?: boolean }>(), { embedded: false, active: false })

const store = useOpsflowStore()
const route = useRoute()
const listRef = ref<InstanceType<typeof ExecutionList> | null>(null)
const selectedExecution = ref<any>(null)

function onViewDetail(execution: any) {
  selectedExecution.value = execution
}

function onExecutionUpdate(exec: any) {
  selectedExecution.value = exec
}

onMounted(async () => {
  const { t } = useI18n()
  if (!store.myProjects.length) await store.fetchMyProjects()

  // Check for execution ID from query param (e.g. from approval page "View" button)
  const execId = route.query.id
  if (execId) {
    try {
      const res = await GetExecutionDetail(Number(execId))
      const ex = res.data?.data || res.data || res
      if (ex && ex.id) {
        selectedExecution.value = ex
      }
    } catch {
      // fall through to list view
    }
  }

  const key = 'opsflow_tour_execution'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: t('message.execution.tourMsg'), duration: 1500 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style scoped>
.opsflow-exec-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: #f5f6fa;
  overflow: hidden;
}

.exec-page-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
