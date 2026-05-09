<template>
  <el-tag :type="tagType" :class="customClass" size="small" effect="plain">
    {{ displayText }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  type: 'direction' | 'trade' | 'signal' | 'level' | 'active' | 'breakout' | 'executed'
  value: string | number | boolean | null | undefined
}>(), {
  value: '',
})

const displayText = computed(() => {
  if (props.value === null || props.value === undefined) return '--'

  switch (props.type) {
    case 'direction':
      if (props.value === 1 || props.value === 'LONG' || props.value === 'long' || props.value === '多') return '多'
      if (props.value === -1 || props.value === 'SHORT' || props.value === 'short' || props.value === '空') return '空'
      if (props.value === 0 || props.value === 'NONE' || props.value === 'none' || props.value === '无') return '无'
      return String(props.value)

    case 'active':
      return props.value ? '启用' : '停用'

    case 'breakout':
      return props.value ? '突破' : '未突破'

    case 'executed':
      if (props.value === 'PENDING' || props.value === 'pending') return '待执行'
      if (props.value === 'SUCCESS' || props.value === 'success') return '成功'
      if (props.value === 'FAILED' || props.value === 'failed') return '失败'
      if (props.value === 'SKIPPED' || props.value === 'skipped') return '跳过'
      return String(props.value)

    case 'level':
      return String(props.value).toUpperCase()

    default:
      return String(props.value)
  }
})

const tagType = computed(() => {
  switch (props.type) {
    case 'direction':
      return props.value === 1 || props.value === 'LONG' || props.value === 'long' || props.value === '多' ? 'danger' : 'success'
    case 'active':
      return props.value ? 'success' : 'info'
    case 'breakout':
      return props.value ? 'warning' : 'info'
    case 'executed':
      if (props.value === 'SUCCESS' || props.value === 'success') return 'success'
      if (props.value === 'FAILED' || props.value === 'failed') return 'danger'
      if (props.value === 'PENDING' || props.value === 'pending') return 'warning'
      return 'info'
    case 'level':
      if (props.value === 'ERROR' || props.value === 'CRITICAL') return 'danger'
      if (props.value === 'WARNING') return 'warning'
      if (props.value === 'SUCCESS') return 'success'
      return 'info'
    default:
      return 'info'
  }
})

const customClass = computed(() => {
  if (props.type === 'direction') {
    return props.value === 1 || props.value === 'LONG' || props.value === 'long' || props.value === '多' ? 'tag-long' : 'tag-short'
  }
  return ''
})
</script>
