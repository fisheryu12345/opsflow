<template>
  <div class="echarts-wrapper" :style="{ height }">
    <div ref="chartRef" class="echarts-instance" :style="{ height: '100%' }"></div>
    <el-empty v-if="noData" description="暂无数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  option?: echarts.EChartsOption
  height?: string
  theme?: string
  loading?: boolean
  noData?: boolean
}>(), {
  height: '350px',
  loading: false,
  noData: false,
})

const emit = defineEmits<{
  ready: [instance: echarts.ECharts]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value, props.theme)
  emit('ready', chartInstance)
  if (props.option) {
    chartInstance.setOption(props.option)
  }
}

function handleResize() {
  chartInstance?.resize()
}

watch(() => props.option, (opt) => {
  if (chartInstance && opt) {
    chartInstance.setOption(opt, true)
  }
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.echarts-wrapper {
  position: relative;
  width: 100%;
}
.echarts-instance {
  width: 100%;
}
</style>
