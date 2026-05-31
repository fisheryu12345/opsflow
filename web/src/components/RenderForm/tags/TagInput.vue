<template>
  <el-input v-model="val" :placeholder="placeholder" :disabled="disabled" :clearable="clearable" size="small" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
}>(), { modelValue: '' })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
