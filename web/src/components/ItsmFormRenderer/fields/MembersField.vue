<template>
  <el-select
    v-model="val"
    :placeholder="placeholder || '请选择人员'"
    :disabled="disabled"
    filterable
    size="small"
    style="width:100%"
  >
    <el-option
      v-for="user in userOptions"
      :key="user.value"
      :label="user.label"
      :value="user.value"
    />
  </el-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  userOptions?: { label: string; value: any }[]
}>(), {
  modelValue: '',
  userOptions: () => [],
})

const emit = defineEmits<{ 'update:modelValue': [value: any] }>()

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
