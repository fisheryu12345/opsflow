<template>
  <div class="project-switcher" v-if="myProjects.length > 0">
    <el-select
      :model-value="currentProjectId"
      @change="onSwitch"
      placeholder="Project"
      size="default"
      popper-class="ps-popper"
    >
      <el-option v-for="p in myProjects" :key="p.id" :label="p.name" :value="p.id">
        <div class="ps-option">
          <span>{{ p.name }}</span>
          <el-tag :type="roleTag(p.role)" size="small" effect="plain">{{ p.role }}</el-tag>
        </div>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOpsflowStore } from '../stores/opsflowStore'

const store = useOpsflowStore()
const myProjects = computed(() => store.myProjects)
const currentProjectId = computed(() => store.currentProjectId)

function roleTag(role: string) {
  return role === 'admin' ? 'danger' : role === 'editor' ? 'primary' : 'info'
}

function onSwitch(id: number) {
  store.setCurrentProjectId(id)
  window.dispatchEvent(new CustomEvent('project-changed', { detail: { projectId: id } }))
}
</script>

<style scoped>
.project-switcher {
  flex: 0 0 auto;
}
.project-switcher :deep(.el-select__wrapper) {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none;
  border-radius: 10px;
  padding: 2px 12px;
  min-height: 33px;
}
.project-switcher :deep(.el-select__placeholder) {
  color: rgba(255,255,255,0.4);
  font-size: 14px;
}
.project-switcher :deep(.el-select__selected-item) {
  color: #fff;
  font-size: 14px;
}
.project-switcher :deep(.el-select__caret) {
  color: rgba(255,255,255,0.4);
  font-size: 14px;
}
.project-switcher :deep(.el-select__wrapper:hover) {
  border-color: rgba(255,255,255,0.25);
  background: rgba(255,255,255,0.15);
}
.ps-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.ps-option span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<!-- Global style for dropdown popper (can't be scoped) -->
<style>
.ps-popper {
  border-radius: 10px !important;
  margin-top: 4px !important;
}
.ps-popper .el-select-dropdown__item {
  font-size: 13px;
  padding: 6px 14px;
}
</style>
