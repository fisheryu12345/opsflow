<template>
  <div class="ifr-section">
    <div class="ifr-section-title">
      <el-icon><FolderOpened /></el-icon>
      {{ label || '分组' }}
    </div>
    <div class="ifr-section-line" />
  </div>
</template>

<script setup lang="ts">
import { FolderOpened } from '@element-plus/icons-vue'

defineProps<{
  label?: string
}>()
</script>

<style scoped>
.ifr-section {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 0 4px;
}
.ifr-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ifr-section-line {
  flex: 1;
  height: 1px;
  background: #e4e7ed;
}
</style>
