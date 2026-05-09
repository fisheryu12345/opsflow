<template>
  <span :class="colorClass">{{ formattedValue }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number | string | null | undefined
  type?: 'currency' | 'percent' | 'number' | 'plain'
  precision?: number
  colorBySign?: boolean
}>(), {
  type: 'plain',
  precision: 2,
  colorBySign: true,
})

const numericValue = computed(() => {
  if (props.value === null || props.value === undefined) return null
  const num = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  return isNaN(num) ? null : num
})

const colorClass = computed(() => {
  if (!props.colorBySign || numericValue.value === null) return ''
  return numericValue.value >= 0 ? 'cell-positive' : 'cell-negative'
})

const formattedValue = computed(() => {
  if (numericValue.value === null) return '--'
  const num = numericValue.value
  switch (props.type) {
    case 'currency':
      return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: props.precision, maximumFractionDigits: props.precision })}`
    case 'percent':
      return `${num.toFixed(props.precision)}%`
    case 'number':
      return num.toLocaleString('zh-CN', { minimumFractionDigits: props.precision, maximumFractionDigits: props.precision })
    default:
      return String(props.value ?? '')
  }
})
</script>

<style scoped>
.cell-positive {
  color: #f5222d;
  font-weight: 500;
}
.cell-negative {
  color: #52c41a;
  font-weight: 500;
}
</style>
