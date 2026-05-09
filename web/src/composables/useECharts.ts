import { ref, onUnmounted, type Ref } from 'vue'
import * as echarts from 'echarts'

export function useECharts() {
  const chartRef: Ref<HTMLElement | null> = ref(null)
  let chartInstance: echarts.ECharts | null = null

  function initChart(theme?: string) {
    if (!chartRef.value) return
    if (chartInstance) {
      chartInstance.dispose()
    }
    chartInstance = echarts.init(chartRef.value, theme)
    return chartInstance
  }

  function setOption(option: echarts.EChartsOption, notMerge?: boolean) {
    if (!chartInstance) return
    chartInstance.setOption(option, notMerge ?? true)
  }

  function resize() {
    chartInstance?.resize()
  }

  function dispose() {
    chartInstance?.dispose()
    chartInstance = null
  }

  function getResponsiveFontConfig() {
    const width = window.innerWidth
    if (width < 480) {
      return { title: 13, subtitle: 9, axisName: 9, legend: 10, tooltip: 11, label: 10 }
    } else if (width < 768) {
      return { title: 15, subtitle: 11, axisName: 11, legend: 11, tooltip: 12, label: 11 }
    }
    return { title: 16, subtitle: 12, axisName: 12, legend: 12, tooltip: 12, label: 12 }
  }

  onUnmounted(dispose)

  return { chartRef, initChart, setOption, resize, dispose, getResponsiveFontConfig }
}
