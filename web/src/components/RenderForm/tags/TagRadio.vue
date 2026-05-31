<template>
  <el-radio-group v-model="val" :disabled="disabled">
    <el-radio v-for="opt in options" :key="opt.value" :value="opt.value">
      {{ opt.label }}
    </el-radio>
  </el-radio-group>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  options?: { label: string; value: any }[]
  disabled?: boolean
}>(), { modelValue: '', options: () => [] })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
