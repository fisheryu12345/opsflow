<template>
  <div class="tag-code-editor">
    <el-input v-model="val" type="textarea" :placeholder="placeholder" :disabled="disabled"
      :rows="rows" size="small" class="code-input" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  language?: string
  height?: string
  rows?: number
}>(), { modelValue: '', rows: 5, height: '150px' })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>

<style scoped>
.tag-code-editor { width: 100%; }
.code-input :deep(textarea) {
  font-family: 'SF Mono', 'Cascadia Code', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>
