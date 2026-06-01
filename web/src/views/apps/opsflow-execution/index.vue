<template>
  <div class="opsflow-exec-page">
    <!-- List view -->
    <div v-if="!selectedExecution" class="exec-page-body">
      <ExecutionList @view-detail="onViewDetail" ref="listRef" />
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
import { ref, onMounted } from 'vue'
import ExecutionList from './components/ExecutionList.vue'
import ExecutionDetail from './components/ExecutionDetail.vue'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'

const store = useOpsflowStore()
const listRef = ref<InstanceType<typeof ExecutionList> | null>(null)
const selectedExecution = ref<any>(null)

function onViewDetail(execution: any) {
  selectedExecution.value = execution
}

function onExecutionUpdate(exec: any) {
  selectedExecution.value = exec
}

onMounted(async () => {
  if (!store.myProjects.length) await store.fetchMyProjects()
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
