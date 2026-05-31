<template>
  <el-checkbox-group v-model="val" :disabled="disabled">
    <el-checkbox v-for="opt in options" :key="opt.value" :label="opt.value" :value="opt.value">
      {{ opt.label }}
    </el-checkbox>
  </el-checkbox-group>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  options?: { label: string; value: any }[]
  disabled?: boolean
}>(), { modelValue: () => [], options: () => [] })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
