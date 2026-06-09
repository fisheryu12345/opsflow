<template>
  <div class="project-switcher" v-if="myProjects.length > 0" :class="{ dark }">
    <el-select
      :model-value="currentProjectId"
      @change="onSwitch"
      placeholder="Project"
      size="default"
      popper-class="ps-popper"
    >
      <template #prefix>
        <el-icon class="ps-icon"><Collection /></el-icon>
      </template>
      <el-option v-for="p in myProjects" :key="p.id" :label="p.name" :value="p.id">
        <div class="ps-option">
          <el-icon class="ps-option-icon" :size="14"><FolderOpened /></el-icon>
          <span>{{ p.name }}</span>
          <el-tag :type="roleTag(p.role)" size="small" effect="plain">{{ p.role }}</el-tag>
        </div>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { computed, withDefaults } from 'vue'
import { Collection, FolderOpened } from '@element-plus/icons-vue'
import { useOpsflowStore } from '../../stores/opsflowStore'

interface Props {
  dark?: boolean
}
const props = withDefaults(defineProps<Props>(), { dark: false })

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

<style lang="scss" scoped>
@use '../../../../../styles/opsflow-global' as *;

.project-switcher {
  flex: 0 0 auto;
}
/* ===== Light mode (default, used in toolbar) ===== */
.project-switcher :deep(.el-select__wrapper) {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  box-shadow: none;
  border-radius: 10px;
  padding: 2px 12px;
  min-height: 33px;
}
.project-switcher :deep(.el-select__wrapper:hover) {
  border-color: #409EFF;
  background: #ecf5ff;
}
.project-switcher :deep(.el-select__placeholder) {
  color: #a8abb2;
  font-size: 14px;
}
.project-switcher :deep(.el-select__selected-item) {
  color: #303133;
  font-size: 14px;
}
.project-switcher :deep(.el-select__caret) {
  color: #a8abb2;
  font-size: 14px;
}
.ps-icon {
  color: #a8abb2;
  margin-right: 2px;
}

/* ===== Dark mode (for hero sections) ===== */
.project-switcher.dark :deep(.el-select__wrapper) {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.12);
}
.project-switcher.dark :deep(.el-select__wrapper:hover) {
  border-color: rgba(255,255,255,0.3);
  background: rgba(255,255,255,0.18);
}
.project-switcher.dark :deep(.el-select__placeholder) {
  color: rgba(255,255,255,0.4);
}
.project-switcher.dark :deep(.el-select__selected-item) {
  color: #fff;
}
.project-switcher.dark :deep(.el-select__caret) {
  color: rgba(255,255,255,0.4);
}
.project-switcher.dark .ps-icon {
  color: rgba(255,255,255,0.4);
}

/* ===== Option slot ===== */
.ps-option {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ps-option-icon {
  color: #c0c4cc;
  flex-shrink: 0;
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
