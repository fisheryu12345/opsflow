<template>
  <el-date-picker v-model="val" type="datetime" :placeholder="placeholder" :disabled="disabled"
    :clearable="clearable" size="small" style="width:100%"
    value-format="YYYY-MM-DD HH:mm:ss" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
}>(), { modelValue: '', placeholder: '选择日期时间' })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
