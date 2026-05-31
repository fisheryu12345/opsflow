<template>
  <el-select v-model="val" :placeholder="placeholder" :disabled="disabled" :multiple="multiple"
    :clearable="clearable" size="small" style="width:100%">
    <el-option v-for="opt in options" :key="opt.value" :label="opt.label" :value="opt.value" />
  </el-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  options?: { label: string; value: any }[]
  placeholder?: string
  disabled?: boolean
  multiple?: boolean
  clearable?: boolean
}>(), { modelValue: '', options: () => [] })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
