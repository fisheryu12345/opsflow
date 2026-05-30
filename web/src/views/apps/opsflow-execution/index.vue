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
import { ref } from 'vue'
import ExecutionList from './components/ExecutionList.vue'
import ExecutionDetail from './components/ExecutionDetail.vue'

const listRef = ref<InstanceType<typeof ExecutionList> | null>(null)
const selectedExecution = ref<any>(null)

function onViewDetail(execution: any) {
  selectedExecution.value = execution
}

function onExecutionUpdate(exec: any) {
  selectedExecution.value = exec
}
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
  background: #f0f2f5;
  overflow: hidden;
}

.exec-page-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin: 8px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
</style>
