<template>
  <el-upload
    v-model:file-list="fileList"
    :disabled="disabled"
    :limit="limit"
    action="#"
    :auto-upload="false"
    :class="{ 'ifr-file-disabled': disabled }"
  >
    <template v-if="!disabled">
      <el-button size="small" type="primary">
        <el-icon><Upload /></el-icon>
        {{ placeholder || '上传附件' }}
      </el-button>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Upload } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  limit?: number
}>(), {
  modelValue: undefined,
  limit: 5,
})

const emit = defineEmits<{ 'update:modelValue': [value: any] }>()

const fileList = computed<any[]>({
  get: () => (Array.isArray(props.modelValue) ? props.modelValue : []),
  set: (v) => emit('update:modelValue', v),
})
</script>

<style scoped>
.ifr-file-disabled :deep(.el-upload) {
  pointer-events: none;
  opacity: 0.6;
}
</style>
