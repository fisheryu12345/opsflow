<template>
  <el-cascader
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :options="cascaderOptions"
    :props="cascaderProps"
    :placeholder="formCreateInject?.props?.placeholder || '请选择'"
    :disabled="disabled"
    filterable
    clearable
    :show-all-levels="true"
    style="width: 100%"
  />
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()

const formCreateInject: any = inject('formCreateInject', null)

const cascaderOptions = computed(() => {
  // Support both static options and API-loaded options
  return formCreateInject?.props?.options || []
})

const cascaderProps = computed(() => {
  return {
    multiple: formCreateInject?.props?.multiple ?? false,
    checkStrictly: formCreateInject?.props?.checkStrictly ?? true,
    emitPath: formCreateInject?.props?.emitPath ?? true,
    value: formCreateInject?.props?.valueKey || 'value',
    label: formCreateInject?.props?.labelKey || 'label',
    children: formCreateInject?.props?.childrenKey || 'children',
  }
})
</script>
