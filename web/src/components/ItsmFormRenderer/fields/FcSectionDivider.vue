<template>
  <div class="fc-section">
    <div class="fc-section-line" />
    <span class="fc-section-label">{{ formCreateInject?.props?.label || '分组' }}</span>
    <div class="fc-section-line" />
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()

// Inject formCreate context for accessing design-time props
const formCreateInject: any = inject('formCreateInject', null)
</script>

<style scoped>
.fc-section {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0;
  width: 100%;
}
.fc-section-line {
  flex: 1;
  height: 1px;
  background: #e4e7ed;
}
.fc-section-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  white-space: nowrap;
}
</style>
