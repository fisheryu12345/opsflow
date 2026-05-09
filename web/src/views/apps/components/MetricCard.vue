<template>
  <div
    class="metric-card"
    :class="[borderColorClass, { 'fade-in-up': animate }]"
    :style="{ animationDelay: `${delay}ms` }"
  >
    <div class="card-label">
      {{ label }}
      <el-tooltip v-if="tooltip" :content="tooltip" placement="top" popper-style="max-width: 280px; font-size: 12px; line-height: 1.5;">
        <el-icon class="tooltip-icon" style="margin-left: 4px; cursor: help; color: #999; font-size: 13px; vertical-align: middle;">
          <InfoFilled />
        </el-icon>
      </el-tooltip>
    </div>
    <div class="card-value" :class="colorClass">
      <span v-if="html" v-html="displayValue"></span>
      <template v-else>{{ displayValue }}</template>
      <span v-if="suffix" class="card-suffix">{{ suffix }}</span>
    </div>
    <el-icon v-if="icon" class="card-icon">
      <component :is="icon" />
    </el-icon>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  colorType?: 'positive' | 'negative' | 'neutral' | 'sign'
  icon?: Component
  suffix?: string
  borderColor?: 'green' | 'red' | 'blue' | 'orange' | 'purple'
  animate?: boolean
  delay?: number
  formatCurrency?: boolean
  tooltip?: string
  html?: boolean
}>(), {
  colorType: 'neutral',
  borderColor: 'blue',
  animate: true,
  delay: 0,
  formatCurrency: false,
  html: false,
})

const colorClass = computed(() => {
  if (props.colorType === 'sign') {
    const num = Number(props.value)
    if (num > 0) return 'positive'
    if (num < 0) return 'negative'
    return 'neutral'
  }
  return props.colorType
})

const borderColorClass = computed(() => `border-${props.borderColor}`)

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '--'
  if (props.formatCurrency) {
    const num = Number(props.value)
    const sign = num >= 0 ? '+' : ''
    return sign + num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }
  return props.value
})
</script>
