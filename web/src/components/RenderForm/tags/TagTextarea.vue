<template>
  <el-input v-model="val" type="textarea" :placeholder="placeholder" :disabled="disabled"
    :rows="rows" size="small" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  rows?: number
}>(), { modelValue: '', rows: 3 })
const emit = defineEmits(['update:modelValue'])
const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
