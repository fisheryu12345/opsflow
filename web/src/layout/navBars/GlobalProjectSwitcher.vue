<template>
  <div class="global-project-switcher">
    <el-select
      :model-value="currentProjectId"
      @change="onSwitch"
      placeholder="Select project"
      size="small"
      :loading="loading"
      :disabled="myProjects.length === 0"
      popper-class="gps-popper"
    >
      <template #prefix>
        <el-icon><Collection /></el-icon>
      </template>
      <el-option v-for="p in myProjects" :key="p.id" :label="p.name" :value="p.id">
        <div class="gps-option">
          <span>{{ p.name }}</span>
          <el-tag :type="roleTag(p.role)" size="small" effect="plain">{{ p.role }}</el-tag>
        </div>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Collection } from '@element-plus/icons-vue'
import { useProjectStore } from '/@/stores/project'

const store = useProjectStore()
const loading = ref(false)
const myProjects = computed(() => store.myProjects)
const currentProjectId = computed(() => store.currentProjectId)

function roleTag(role: string) {
  return role === 'admin' ? 'danger' : role === 'editor' ? 'primary' : 'info'
}

function onSwitch(id: number) {
  store.setCurrentProjectId(id)
}

onMounted(async () => {
  if (!store.myProjects.length) {
    loading.value = true
    try {
      await store.fetchMyProjects()
    } finally {
      loading.value = false
    }
  }
})
</script>

<style lang="scss" scoped>
.global-project-switcher {
  flex-shrink: 0;
  margin-right: 8px;
}
.global-project-switcher :deep(.el-select__wrapper) {
  background: transparent;
  border: 1px solid var(--next-border-color-light);
  box-shadow: none;
  border-radius: 8px;
  padding: 1px 10px;
  min-height: 30px;
}
.global-project-switcher :deep(.el-select__wrapper:hover) {
  border-color: #409EFF;
}
.global-project-switcher :deep(.el-select__placeholder) {
  color: var(--next-bg-topBarColor);
  opacity: 0.5;
  font-size: 13px;
}
.global-project-switcher :deep(.el-select__selected-item) {
  color: var(--next-bg-topBarColor);
  font-size: 13px;
}
.gps-option {
  display: flex;
  align-items: center;
  gap: 6px;
}
.gps-option span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<style>
.gps-popper {
  border-radius: 8px !important;
  margin-top: 4px !important;
}
.gps-popper .el-select-dropdown__item {
  font-size: 13px;
}
</style>
