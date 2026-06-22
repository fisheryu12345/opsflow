<template>
  <div>
    <el-switch
      :model-value="!!localVal"
      :active-text="activeText"
      :inactive-text="inactiveText"
      :disabled="disabled"
      @update:model-value="onChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  disabled?: boolean
  active_text?: string
  inactive_text?: string
}>(), {
  modelValue: false,
  disabled: false,
  active_text: '',
  inactive_text: '',
})

const emit = defineEmits(['update:modelValue'])
const localVal = ref(props.modelValue)
const activeText = computed(() => props.active_text)
const inactiveText = computed(() => props.inactive_text)

watch(() => props.modelValue, (v) => { localVal.value = v })
function onChange(val: any) {
  localVal.value = val
  emit('update:modelValue', val)
}
</script>
