<template>
  <div class="opsflow-stats">
    <div class="stats-bg-grid" />
    <div class="stats-body">
      <!-- Header -->
      <div class="stats-header">
        <div class="stats-header-left">
          <div class="stats-title-row">
            <div class="stats-title-icon">
              <el-icon :size="18" color="#fff"><DataAnalysis /></el-icon>
            </div>
            <div>
              <h2 class="stats-title">Statistics &amp; Analysis</h2>
              <span class="stats-subtitle">Execution performance, duration distribution &amp; trends</span>
            </div>
          </div>
        </div>
        <div class="stats-header-right">
          <el-radio-group v-model="period" size="small" @change="refreshAll">
            <el-radio-button value="7d">7D</el-radio-button>
            <el-radio-button value="14d">14D</el-radio-button>
            <el-radio-button value="30d">30D</el-radio-button>
          </el-radio-group>
          <el-button :icon="Refresh" @click="refreshAll" :loading="loading" round>Refresh</el-button>
        </div>
      </div>

      <!-- Chart row 1: Duration Distribution + Node Duration Top -->
      <div class="stats-chart-row">
        <div class="stats-chart-card stats-chart-wide">
          <div class="stats-chart-header">
            <div class="stats-chart-header-left">
              <span class="stats-chart-title">Execution Duration Distribution</span>
              <span class="stats-chart-subtitle">How long executions take to complete</span>
            </div>
          </div>
          <div ref="durationChartRef" class="stats-chart-area" />
        </div>
        <div class="stats-chart-card stats-chart-narrow">
          <div class="stats-chart-header">
            <div class="stats-chart-header-left">
              <span class="stats-chart-title">Slowest Node Types</span>
              <span class="stats-chart-subtitle">Top 10 by avg duration</span>
            </div>
          </div>
          <div ref="nodeDurationChartRef" class="stats-chart-area" />
        </div>
      </div>

      <!-- Chart row 2: Success Rate Trend -->
      <div class="stats-chart-row">
        <div class="stats-chart-card stats-chart-wide">
          <div class="stats-chart-header">
            <div class="stats-chart-header-left">
              <span class="stats-chart-title">Success Rate Trend</span>
              <span class="stats-chart-subtitle">Daily execution count &amp; success rate over time</span>
            </div>
            <el-tag v-if="avgSuccessRate" size="small" :type="avgSuccessRate >= 90 ? 'success' : avgSuccessRate >= 75 ? 'warning' : 'danger'" effect="light" round>
              Avg {{ avgSuccessRate }}%
            </el-tag>
          </div>
          <div ref="successRateChartRef" class="stats-chart-area" />
        </div>
      </div>

      <!-- Template Stats Table -->
      <div class="stats-chart-card stats-table-card">
        <div class="stats-chart-header">
          <div class="stats-chart-header-left">
            <span class="stats-chart-title">Template Execution Summary</span>
            <span class="stats-chart-subtitle">Per-template aggregate performance</span>
          </div>
        </div>
        <el-table :data="templateStats" stripe style="width:100%" size="small" empty-text="No template data yet">
          <el-table-column prop="name" label="Template" min-width="180" show-overflow-tooltip />
          <el-table-column prop="total" label="Executions" width="100" align="center" sortable />
          <el-table-column prop="avg_duration" label="Avg Duration" width="120" align="center" sortable>
            <template #default="{ row }">
              <span class="dur-cell">{{ formatDuration(row.avg_duration) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="success_rate" label="Success Rate" width="120" align="center" sortable>
            <template #default="{ row }">
              <el-tag :type="row.success_rate >= 90 ? 'success' : row.success_rate >= 75 ? 'warning' : 'danger'" size="small" effect="dark" round>
                {{ row.success_rate }}%
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Refresh, DataAnalysis } from '@element-plus/icons-vue'
import {
  GetDashboardDurationDistribution, GetDashboardNodeDurationTop,
  GetDashboardSuccessRateTrend, GetDashboardTemplateStats,
  getMockDurationDistribution, getMockNodeDurationTop,
  getMockSuccessRateTrend, getMockTemplateStats,
} from '/@/api/opsflow/dashboard'

/* ---------- State ---------- */
const loading = ref(false)
const period = ref<'7d' | '14d' | '30d'>('30d')
const durationDist = ref<any[]>([])
const nodeDurationTop = ref<any[]>([])
const successRateTrend = ref<any[]>([])
const templateStats = ref<any[]>([])

const days = computed(() => period.value === '7d' ? 7 : period.value === '14d' ? 14 : 30)
const filteredRateTrend = computed(() => successRateTrend.value.slice(-days.value))
const avgSuccessRate = computed(() => {
  const data = filteredRateTrend.value
  if (!data.length) return null
  const valid = data.filter(d => d.total > 0)
  if (!valid.length) return null
  return +(valid.reduce((s, d) => s + d.rate, 0) / valid.length).toFixed(1)
})

/* ---------- Chart refs ---------- */
const durationChartRef = shallowRef<HTMLElement | null>(null)
const nodeDurationChartRef = shallowRef<HTMLElement | null>(null)
const successRateChartRef = shallowRef<HTMLElement | null>(null)
let durationChart: echarts.ECharts | null = null
let nodeDurationChart: echarts.ECharts | null = null
let successRateChart: echarts.ECharts | null = null

/* ---------- Tooltip theme ---------- */
const tooltipTheme = {
  backgroundColor: 'rgba(255,255,255,0.95)',
  borderColor: '#e8e8e8', borderWidth: 1, borderRadius: 8,
  padding: [10, 14], textStyle: { fontSize: 12, color: '#303133' },
  extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08);',
}

/* ---------- Duration distribution bar chart ---------- */
function renderDurationChart() {
  if (!durationChartRef.value) return
  if (!durationChart) durationChart = echarts.init(durationChartRef.value)
  const data = durationDist.value
  durationChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 56, right: 16, top: 8, bottom: 28 },
    xAxis: { type: 'category', data: data.map(d => d.range), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
    series: [{
      type: 'bar',
      data: data.map((d, i) => ({
        value: d.count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `rgba(64,158,255,${0.4 + i / data.length * 0.5})` },
            { offset: 1, color: `rgba(64,158,255,${0.5 + i / data.length * 0.4})` },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      })),
      barWidth: '60%',
      label: { show: true, position: 'top', fontSize: 11, color: '#909399' },
      animationDuration: 500,
      animationEasing: 'cubicOut',
    }],
  })
}

/* ---------- Node duration top bar chart ---------- */
function renderNodeDurationChart() {
  if (!nodeDurationChartRef.value) return
  if (!nodeDurationChart) nodeDurationChart = echarts.init(nodeDurationChartRef.value)
  const sorted = [...nodeDurationTop.value].sort((a, b) => a.avg_duration - b.avg_duration)
  const colors = ['#95de64', '#73d13d', '#52c41a', '#36cfc9', '#40a9ff', '#409EFF', '#597ef7', '#2f54eb', '#722ed1', '#9B59B6']
  nodeDurationChart.setOption({
    tooltip: {
      ...tooltipTheme, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0]
        const row = sorted[p.dataIndex]
        return `<strong>${row.atom_type}</strong><br/>Avg: ${formatMs(row.avg_duration)}<br/>Max: ${formatMs(row.max_duration)}<br/>Count: ${row.count}`
      },
    },
    grid: { left: 8, right: 52, top: 6, bottom: 8 },
    xAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#b0b0b0', formatter: (v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}s` : `${v}ms` }, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } } },
    yAxis: { type: 'category', data: sorted.map(d => d.atom_type.length > 12 ? d.atom_type.slice(0, 12) + '…' : d.atom_type), axisLabel: { fontSize: 11, color: '#303133', fontWeight: 500 }, axisLine: { show: false }, axisTick: { show: false } },
    series: [{
      type: 'bar',
      data: sorted.map((d, i) => ({ value: d.avg_duration, itemStyle: { color: colors[i % colors.length], borderRadius: [0, 4, 4, 0] } })),
      barWidth: 14,
      label: { show: true, position: 'right', fontSize: 10, color: '#909399', formatter: (p: any) => formatMs(p.value) },
      animationDuration: 600,
      animationEasing: 'cubicOut',
    }],
  })
}

/* ---------- Success rate trend chart ---------- */
function renderSuccessRateChart() {
  if (!successRateChartRef.value) return
  if (!successRateChart) successRateChart = echarts.init(successRateChartRef.value)
  const data = filteredRateTrend.value
  successRateChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'axis', axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        const date = params[0].axisValue
        let html = `<strong>${date}</strong><br/>`
        params.forEach((p: any) => { html += `${p.marker} ${p.seriesName}: <strong>${p.value}</strong>${p.seriesName === 'Success Rate' ? '%' : ''}<br/>` })
        return html
      },
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#909399' } },
    grid: { left: 44, right: 44, top: 12, bottom: 36 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: [
      { type: 'value', name: 'Count', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
      { type: 'value', name: '%', min: 0, max: 100, splitLine: { show: false }, axisLabel: { fontSize: 11, color: '#52c41a', formatter: '{value}%' } },
    ],
    series: [
      {
        name: 'Completed', type: 'bar', stack: 'total', barWidth: '50%',
        data: data.map(d => d.completed),
        itemStyle: { color: '#67C23A', borderRadius: [0, 0, 0, 0] },
      },
      {
        name: 'Failed', type: 'bar', stack: 'total',
        data: data.map(d => d.failed),
        itemStyle: { color: '#F56C6C', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: 'Success Rate', type: 'line', yAxisIndex: 1, smooth: true,
        data: data.map(d => d.rate),
        symbol: 'circle', symbolSize: 5,
        lineStyle: { color: '#2f54eb', width: 2.5 },
        itemStyle: { color: '#2f54eb' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(47,84,235,0.20)' }, { offset: 1, color: 'rgba(47,84,235,0.02)' }]) },
      },
    ],
  })
}

/* ---------- Helpers ---------- */
function formatDuration(sec: number): string {
  if (!sec) return '-'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}
function formatMs(ms: number): string {
  if (!ms) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/* ---------- Refresh ---------- */
async function refreshAll() {
  loading.value = true
  try {
    const [dd, nd, sr, ts] = await Promise.allSettled([
      GetDashboardDurationDistribution({ days: days.value }),
      GetDashboardNodeDurationTop({ limit: 10 }),
      GetDashboardSuccessRateTrend({ days: days.value }),
      GetDashboardTemplateStats(),
    ])
    if (dd.status === 'fulfilled') durationDist.value = dd.value.data?.data || dd.value.data || getMockDurationDistribution()
    else durationDist.value = getMockDurationDistribution()
    if (nd.status === 'fulfilled') nodeDurationTop.value = nd.value.data?.data || nd.value.data || getMockNodeDurationTop()
    else nodeDurationTop.value = getMockNodeDurationTop()
    if (sr.status === 'fulfilled') successRateTrend.value = sr.value.data?.data || sr.value.data || getMockSuccessRateTrend()
    else successRateTrend.value = getMockSuccessRateTrend()
    if (ts.status === 'fulfilled') templateStats.value = ts.value.data?.data || ts.value.data || getMockTemplateStats()
    else templateStats.value = getMockTemplateStats()
  } catch {
    durationDist.value = getMockDurationDistribution()
    nodeDurationTop.value = getMockNodeDurationTop()
    successRateTrend.value = getMockSuccessRateTrend()
    templateStats.value = getMockTemplateStats()
  }
  nextTick(() => {
    renderDurationChart()
    renderNodeDurationChart()
    renderSuccessRateChart()
  })
  loading.value = false
}

/* ---------- Resize ---------- */
function onResize() {
  durationChart?.resize()
  nodeDurationChart?.resize()
  successRateChart?.resize()
}

/* ---------- Lifecycle ---------- */
onMounted(() => {
  refreshAll()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  durationChart?.dispose()
  nodeDurationChart?.dispose()
  successRateChart?.dispose()
})
</script>

<style scoped>
.opsflow-stats {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #eef1f5 100%);
  overflow: hidden; position: relative;
}
.stats-bg-grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(64,158,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64,158,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none; z-index: 0;
}
.stats-body {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 16px;
  position: relative; z-index: 1;
}
.stats-header {
  display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-shrink: 0;
}
.stats-title-row { display: flex; align-items: center; gap: 14px; }
.stats-title-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #2f54eb, #597ef7);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(47,84,235,0.30); flex-shrink: 0;
}
.stats-title { margin: 0; font-size: 22px; font-weight: 700; color: #1a1a2e; }
.stats-subtitle { font-size: 13px; color: #909399; }
.stats-header-right { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }
.stats-chart-row {
  display: grid; grid-template-columns: 1fr 380px; gap: 16px;
}
.stats-chart-card {
  background: rgba(255,255,255,0.90); backdrop-filter: blur(8px);
  border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  padding: 18px; display: flex; flex-direction: column;
  border: 1px solid rgba(255,255,255,0.6);
}
.stats-chart-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 12px; flex-shrink: 0; gap: 12px;
}
.stats-chart-header-left { display: flex; flex-direction: column; gap: 2px; }
.stats-chart-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.stats-chart-subtitle { font-size: 11px; color: #b0b0b0; }
.stats-chart-area { flex: 1; min-height: 260px; }
.stats-table-card { padding: 0 0 6px; }
.stats-table-card .stats-chart-header { padding: 14px 18px 10px; }
.dur-cell { font-family: monospace; font-size: 12px; color: #606266; }
</style>
