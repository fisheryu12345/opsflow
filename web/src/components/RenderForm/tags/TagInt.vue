<template>
  <el-input-number v-model="val" :min="min" :max="max" :step="step" :disabled="disabled"
    size="small" controls-position="right" style="width:100%" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  min?: number
  max?: number
  step?: number
  disabled?: boolean
}>(), { modelValue: 0, min: 0, max: 99999, step: 1 })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue ?? 0,
  set: (v) => emit('update:modelValue', v),
})
</script>
