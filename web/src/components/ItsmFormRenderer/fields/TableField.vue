<template>
  <div class="ifr-table-placeholder" :class="{ 'ifr-table-disabled': disabled }">
    <el-icon><Grid /></el-icon>
    <span>{{ placeholder || '子表格（待配置列定义）' }}</span>
  </div>
</template>

<script setup lang="ts">
import { Grid } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  placeholder?: string
  disabled?: boolean
}>(), {})
</script>

<style scoped>
.ifr-table-placeholder {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px dashed #d9ecff;
  border-radius: 4px;
  font-size: 12px;
  color: #909399;
  background: #fafafa;
}
.ifr-table-disabled {
  opacity: 0.6;
}
</style>
