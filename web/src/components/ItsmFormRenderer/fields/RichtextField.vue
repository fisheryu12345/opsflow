<template>
  <div :class="{ 'ifr-richtext-disabled': disabled }">
    <div v-if="disabled" class="ifr-richtext-placeholder">
      {{ placeholder || '富文本内容区域' }}
    </div>
    <el-input
      v-else
      v-model="val"
      type="textarea"
      :rows="6"
      :placeholder="placeholder || '请输入富文本内容'"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
}>(), {
  modelValue: '',
})

const emit = defineEmits<{ 'update:modelValue': [value: any] }>()

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>

<style scoped>
.ifr-richtext-disabled {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px 12px;
  min-height: 120px;
  background: #f5f7fa;
}
.ifr-richtext-placeholder {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
