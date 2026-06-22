<template>
  <div style="display:flex;align-items:center;gap:12px;">
    <el-slider
      v-model="sliderVal"
      :min="min"
      :max="max"
      :step="1"
      :disabled="disabled"
      show-stops
      style="flex:1"
    />
    <span style="font-size:12px;color:#666;min-width:70px;white-space:nowrap;">
      {{ label }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  disabled?: boolean
  min?: number
  max?: number
  'label-0'?: string
  'label-1'?: string
  'label-n'?: string
}>(), {
  modelValue: 0,
  disabled: false,
  min: 0,
  max: 20,
  'label-0': '无',
  'label-1': '',
  'label-n': '{value}',
})

const emit = defineEmits(['update:modelValue'])
const sliderVal = ref(typeof props.modelValue === 'number' ? props.modelValue : 0)

watch(() => props.modelValue, (v) => { sliderVal.value = typeof v === 'number' ? v : 0 })
watch(sliderVal, (v) => { emit('update:modelValue', v) })

const min = computed(() => props.min)
const max = computed(() => props.max)

const label = computed(() => {
  const v = sliderVal.value
  if (max.value === 1) {
    return v === 0 ? props['label-0'] : (props['label-1'] || String(v))
  }
  if (v === 0) return props['label-0']
  const tmpl = props['label-n'] || '{value}'
  return tmpl.replace('{value}', String(v))
})
</script>
