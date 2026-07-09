<template>
  <el-date-picker
    v-model="val"
    type="date"
    :placeholder="placeholder || '选择日期'"
    :disabled="disabled"
    :clearable="true"
    size="small"
    style="width:100%"
    value-format="YYYY-MM-DD"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
}>(), { modelValue: '', placeholder: '选择日期' })

const emit = defineEmits<{ 'update:modelValue': [value: any] }>()
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
