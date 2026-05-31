<template>
  <div class="opsflow-dashboard">
    <div class="db-body">
      <!-- Page header -->
      <div class="db-header">
        <div class="db-header-left">
          <h2 class="db-title">OpsFlow Dashboard</h2>
          <span class="db-subtitle">Real-time overview of pipeline executions & system health</span>
        </div>
        <div class="db-header-right">
          <el-radio-group v-model="period" size="small" @change="refreshAll">
            <el-radio-button value="7d">7D</el-radio-button>
            <el-radio-button value="14d">14D</el-radio-button>
            <el-radio-button value="30d">30D</el-radio-button>
          </el-radio-group>
          <el-button :icon="Refresh" @click="refreshAll" :loading="loading">
            Refresh
          </el-button>
        </div>
      </div>

      <!-- Stats cards -->
      <div class="db-stats-row">
        <div class="db-stat-card" v-for="s in statsCards" :key="s.key">
          <div class="db-stat-icon" :style="{ background: s.bg }">
            <el-icon :size="20" :color="s.color"><component :is="s.icon" /></el-icon>
          </div>
          <div class="db-stat-body">
            <span class="db-stat-value" :style="{ color: s.color }">{{ s.value }}</span>
            <span class="db-stat-label">{{ s.label }}</span>
          </div>
          <div v-if="s.trend !== undefined" class="db-stat-trend" :class="s.trend >= 0 ? 'up' : 'down'">
            <el-icon size="10"><Top v-if="s.trend >= 0" /><Bottom v-else /></el-icon>
            {{ Math.abs(s.trend) }}%
          </div>
        </div>
      </div>

      <!-- Chart row 1: Execution Trend + Status Distribution -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Execution Trend</span>
            <el-tag size="small" type="success" effect="plain">{{ trendUp ? '↑ +' + trendUp + '% vs last period' : '' }}</el-tag>
          </div>
          <div ref="trendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <span class="db-chart-title">Status Distribution</span>
            <span class="db-chart-total">{{ stats.total_executions }} total</span>
          </div>
          <div ref="statusChartRef" class="db-chart-area" />
        </div>
      </div>

      <!-- Chart row 2: Top Templates + Duration -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Top Templates by Executions</span>
            <span class="db-chart-total">Top 8</span>
          </div>
          <div ref="templatesChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <span class="db-chart-title">Node Type Distribution</span>
            <span class="db-chart-total">{{ stats.total_nodes_executed }} total</span>
          </div>
          <div ref="nodeTypeChartRef" class="db-chart-area" />
        </div>
      </div>

      <!-- Section: Scheduler Statistics -->
      <div class="db-section-header">
        <h3 class="db-section-title">Scheduler Overview</h3>
        <el-tag size="small" type="info" effect="plain">{{ scheduleStats.type_distribution.cron || 0 }} cron · {{ scheduleStats.type_distribution.one_time || 0 }} one-time</el-tag>
      </div>

      <!-- Schedule stats cards -->
      <div class="db-stats-row">
        <div class="db-stat-card" v-for="s in schedCards" :key="s.key">
          <div class="db-stat-icon" :style="{ background: s.bg }">
            <el-icon :size="20" :color="s.color"><component :is="s.icon" /></el-icon>
          </div>
          <div class="db-stat-body">
            <span class="db-stat-value" :style="{ color: s.color }">{{ s.value }}</span>
            <span class="db-stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>

      <!-- Chart row 3: Schedule Trend + Top Schedules -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Schedule Execution Trend</span>
            <el-tag size="small" type="success" effect="plain" v-if="scheduleTrendUp">↑ +{{ scheduleTrendUp }}%</el-tag>
          </div>
          <div ref="schedTrendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <span class="db-chart-title">Top Schedules</span>
            <span class="db-chart-total">Top 5</span>
          </div>
          <div class="sched-list">
            <div v-for="s in scheduleStats.top_schedules.slice(0, 5)" :key="s.id" class="sched-list-item">
              <div class="sched-list-left">
                <span class="sched-list-name">{{ s.name }}</span>
                <span class="sched-list-meta">{{ s.total_run_count }} runs · {{ s.schedule_type === 'cron' ? '周期' : '一次' }}</span>
              </div>
              <div class="sched-list-right">
                <el-tag :type="s.is_active ? 'success' : 'info'" size="small" effect="plain">
                  {{ s.is_active ? 'Active' : 'Inactive' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom: User activity table + summary -->
      <div class="db-bottom-row">
        <div class="db-chart-card db-table-card">
          <div class="db-chart-header">
            <span class="db-chart-title">User Activity</span>
            <span class="db-chart-total">{{ stats.active_users_7d }} active in 7d</span>
          </div>
          <el-table :data="userActivity" stripe style="width: 100%" size="small">
            <el-table-column prop="username" label="User" width="120">
              <template #default="{ row }">
                <div class="user-cell">
                  <el-avatar :size="24" style="background: #409EFF; font-size: 12px;">
                    {{ row.username.charAt(0).toUpperCase() }}
                  </el-avatar>
                  <span>{{ row.username }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="execution_count" label="Executions" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.execution_count > 50 ? 'success' : row.execution_count > 20 ? 'warning' : 'info'" size="small">
                  {{ row.execution_count }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="template_count" label="Templates" width="110" align="center" />
            <el-table-column prop="last_active" label="Last Active" width="140" />
            <el-table-column label="Activity Bar" min-width="160">
              <template #default="{ row }">
                <div class="activity-bar-track">
                  <div class="activity-bar-fill" :style="{ width: (row.execution_count / maxUserExec) * 100 + '%' }" />
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="db-chart-card db-summary-card">
          <div class="db-chart-header">
            <span class="db-chart-title">System Summary</span>
          </div>
          <div class="summary-list">
            <div class="summary-item">
              <span class="summary-label">Success Rate</span>
              <el-progress :percentage="stats.success_rate" :stroke-width="12"
                           :status="stats.success_rate >= 90 ? 'success' : stats.success_rate >= 75 ? 'warning' : 'exception'"
                           :format="() => stats.success_rate + '%'" />
            </div>
            <div class="summary-item">
              <span class="summary-label">Avg Duration</span>
              <span class="summary-value">{{ formatDuration(stats.avg_duration_sec) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Total Nodes Executed</span>
              <span class="summary-value">{{ stats.total_nodes_executed.toLocaleString() }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Templates</span>
              <div class="summary-bar-group">
                <span class="summary-bar-label">{{ stats.published_templates }} Published</span>
                <div class="summary-bar-track">
                  <div class="summary-bar-fill" style="background:#67C23A; width:66%" />
                </div>
                <span class="summary-bar-label">{{ stats.draft_templates }} Draft</span>
                <div class="summary-bar-track">
                  <div class="summary-bar-fill" style="background:#909399; width:34%" />
                </div>
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Users</span>
              <div class="summary-bar-group">
                <span class="summary-bar-label">{{ stats.total_users }} Registered</span>
                <div class="summary-bar-track">
                  <div class="summary-bar-fill" style="background:#409EFF; width:100%" />
                </div>
                <span class="summary-bar-label">{{ stats.active_users_7d }} Active (7d)</span>
                <div class="summary-bar-track">
                  <div class="summary-bar-fill" :style="{ background: '#67C23A', width: (stats.active_users_7d / stats.total_users * 100) + '%' }" />
                </div>
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Execution Health</span>
              <div class="summary-health-dots">
                <div class="health-row">
                  <span class="health-dot" style="background:#67C23A" />
                  <span>Completed: {{ stats.completed_executions }}</span>
                </div>
                <div class="health-row">
                  <span class="health-dot" style="background:#F56C6C" />
                  <span>Failed: {{ stats.failed_executions }}</span>
                </div>
                <div class="health-row">
                  <span class="health-dot" style="background:#E6A23C" />
                  <span>Running: {{ stats.running_executions }}</span>
                </div>
                <div class="health-row">
                  <span class="health-dot" style="background:#909399" />
                  <span>Other: {{ stats.cancelled_executions + stats.paused_executions }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <span v-if="useMock" class="mock-badge">Mock Data</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Refresh, Top, Bottom, Timer, VideoPlay, VideoPause, RefreshRight } from '@element-plus/icons-vue'
import {
  getMockStats, getMockTrend, getMockTopTemplates,
  getMockUserActivity, getMockStatusDistribution, getMockNodeTypeDistribution,
  getMockScheduleStats,
} from '/@/api/opsflow/dashboard'

/* ---------- State ---------- */
const loading = ref(false)
const useMock = ref(true) // always use mock for now
const period = ref<'7d' | '14d' | '30d'>('30d')

const stats = ref(getMockStats())
const trend = ref(getMockTrend())
const topTemplates = ref(getMockTopTemplates())
const userActivity = ref(getMockUserActivity())
const statusDist = ref(getMockStatusDistribution())
const nodeTypeDist = ref(getMockNodeTypeDistribution())
const scheduleStats = ref(getMockScheduleStats())

/* ---------- ECharts refs ---------- */
const trendChartRef = shallowRef<HTMLElement | null>(null)
const statusChartRef = shallowRef<HTMLElement | null>(null)
const templatesChartRef = shallowRef<HTMLElement | null>(null)
const nodeTypeChartRef = shallowRef<HTMLElement | null>(null)
const schedTrendChartRef = shallowRef<HTMLElement | null>(null)

let trendChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null
let templatesChart: echarts.ECharts | null = null
let nodeTypeChart: echarts.ECharts | null = null
let schedTrendChart: echarts.ECharts | null = null

/* ---------- Period filter ---------- */
const filteredTrend = computed(() => {
  const days = period.value === '7d' ? 7 : period.value === '14d' ? 14 : 30
  return trend.value.slice(-days)
})

const trendUp = computed(() => {
  if (filteredTrend.value.length < 4) return null
  const half = Math.floor(filteredTrend.value.length / 2)
  const first = filteredTrend.value.slice(0, half).reduce((s, d) => s + d.total, 0)
  const last = filteredTrend.value.slice(half).reduce((s, d) => s + d.total, 0)
  if (first === 0) return null
  return Math.round((last - first) / first * 100)
})

const maxUserExec = computed(() => Math.max(...userActivity.value.map(u => u.execution_count), 1))

/* ---------- Stats cards ---------- */
const statsCards = computed(() => [
  { key: 'total_exec', label: 'Total Executions', value: stats.value.total_executions, icon: 'Histogram', bg: '#e6f7ff', color: '#1890ff', trend: 12 },
  { key: 'running', label: 'Running Now', value: stats.value.running_executions, icon: 'Loading', bg: '#fff7e6', color: '#fa8c16', trend: undefined },
  { key: 'completed', label: 'Completed', value: stats.value.completed_executions, icon: 'CircleCheck', bg: '#f6ffed', color: '#52c41a', trend: 8 },
  { key: 'failed', label: 'Failed', value: stats.value.failed_executions, icon: 'CircleClose', bg: '#fff2f0', color: '#ff4d4f', trend: -5 },
  { key: 'templates', label: 'Templates', value: stats.value.total_templates, icon: 'Collection', bg: '#f0f5ff', color: '#2f54eb', trend: 4 },
  { key: 'published', label: 'Published', value: stats.value.published_templates, icon: 'Upload', bg: '#f6ffed', color: '#52c41a', trend: undefined },
  { key: 'users', label: 'Active Users (7d)', value: stats.value.active_users_7d, icon: 'User', bg: '#fff0f6', color: '#eb2f96', trend: undefined },
])

/* ---------- Scheduler cards ---------- */
const schedCards = computed(() => [
  { key: 'total_schedules', label: 'Sched Plans', value: stats.value.total_schedule_plans, icon: 'Timer', bg: '#f0f5ff', color: '#2f54eb' },
  { key: 'active_schedules', label: 'Active Plans', value: stats.value.active_schedule_plans, icon: 'VideoPlay', bg: '#f6ffed', color: '#52c41a' },
  { key: 'paused_schedules', label: 'Paused Plans', value: stats.value.paused_schedule_plans, icon: 'VideoPause', bg: '#fff7e6', color: '#fa8c16' },
  { key: 'total_runs', label: 'Total Runs', value: stats.value.total_scheduled_runs, icon: 'RefreshRight', bg: '#e6f7ff', color: '#1890ff' },
  { key: 'sched_success', label: 'Sched Success', value: stats.value.schedule_success_rate + '%', icon: 'CircleCheck', bg: '#f6ffed', color: '#52c41a' },
  { key: 'sched_running', label: 'Sched Running', value: stats.value.scheduled_executions_running, icon: 'Loading', bg: '#fff7e6', color: '#fa8c16' },
])

const scheduleTrendUp = computed(() => {
  const data = scheduleStats.value.trend
  if (!data || data.length < 4) return null
  const half = Math.floor(data.length / 2)
  const first = data.slice(0, half).reduce((s, d) => s + d.total, 0)
  const last = data.slice(half).reduce((s, d) => s + d.total, 0)
  if (first === 0) return null
  return Math.round((last - first) / first * 100)
})

/* ---------- Trend chart ---------- */
function renderTrendChart() {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const data = filteredTrend.value
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        let html = `<strong>${date}</strong><br/>`
        params.forEach((p: any) => { html += `${p.marker} ${p.seriesName}: ${p.value}<br/>` })
        return html
      },
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    grid: { left: 40, right: 16, top: 8, bottom: 36 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 11, color: '#909399' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLabel: { fontSize: 11, color: '#909399' } },
    series: [
      {
        name: 'Total',
        type: 'line',
        data: data.map(d => d.total),
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: '#409EFF', width: 2 },
        itemStyle: { color: '#409EFF' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.25)' }, { offset: 1, color: 'rgba(64,158,255,0.02)' }]) },
      },
      {
        name: 'Completed',
        type: 'line',
        data: data.map(d => d.completed),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#67C23A', width: 2 },
        itemStyle: { color: '#67C23A' },
      },
      {
        name: 'Failed',
        type: 'line',
        data: data.map(d => d.failed),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#F56C6C', width: 2 },
        itemStyle: { color: '#F56C6C' },
      },
    ],
  })
}

/* ---------- Status doughnut chart ---------- */
function renderStatusChart() {
  if (!statusChartRef.value) return
  if (!statusChart) statusChart = echarts.init(statusChartRef.value)
  const colorMap: Record<string, string> = { completed: '#67C23A', failed: '#F56C6C', running: '#E6A23C', paused: '#909399', cancelled: '#C0C4CC' }
  statusChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['48%', '70%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, position: 'outside', fontSize: 11, color: '#606266', formatter: '{b}\n{d}%' },
      labelLine: { length: 8, length2: 10, smooth: true },
      data: statusDist.value.map(d => ({ value: d.count, name: d.label, itemStyle: { color: colorMap[d.status] } })),
    }],
  })
}

/* ---------- Top templates bar chart ---------- */
function renderTemplatesChart() {
  if (!templatesChartRef.value) return
  if (!templatesChart) templatesChart = echarts.init(templatesChartRef.value)
  const sorted = [...topTemplates.value].sort((a, b) => a.count - b.count)
  templatesChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0]
        const row = sorted[p.dataIndex]
        return `<strong>${row.name}</strong><br/>Executions: ${row.count}<br/>Avg Duration: ${formatDuration(row.avg_duration)}<br/>Success Rate: ${row.success_rate}%`
      },
    },
    grid: { left: 8, right: 40, top: 4, bottom: 8 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11, color: '#909399' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.name.length > 12 ? d.name.slice(0, 12) + '…' : d.name),
      axisLabel: { fontSize: 11, color: '#303133', fontWeight: 500 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar',
      data: sorted.map((d, i) => ({
        value: d.count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: `rgba(64,158,255,${0.4 + i / sorted.length * 0.5})` },
            { offset: 1, color: `rgba(64,158,255,${0.6 + i / sorted.length * 0.4})` },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barWidth: 16,
      label: { show: true, position: 'right', fontSize: 11, color: '#909399' },
    }],
  })
}

/* ---------- Node type doughnut chart ---------- */
function renderNodeTypeChart() {
  if (!nodeTypeChartRef.value) return
  if (!nodeTypeChart) nodeTypeChart = echarts.init(nodeTypeChartRef.value)
  const colors: Record<string, string> = { ansible: '#67C23A', http: '#E6A23C', servicenow: '#909399', esxi: '#20B2AA', other: '#C0C4CC' }
  nodeTypeChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, position: 'outside', fontSize: 11, color: '#606266', formatter: '{b}\n{d}%' },
      labelLine: { length: 8, length2: 8 },
      data: nodeTypeDist.value.map(d => ({ value: d.count, name: d.label, itemStyle: { color: colors[d.type] } })),
    }],
  })
}

/* ---------- Schedule trend chart ---------- */
function renderSchedTrendChart() {
  if (!schedTrendChartRef.value) return
  if (!schedTrendChart) schedTrendChart = echarts.init(schedTrendChartRef.value)
  const data = scheduleStats.value.trend || []
  schedTrendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        let html = `<strong>${date}</strong><br/>`
        params.forEach((p: any) => { html += `${p.marker} ${p.seriesName}: ${p.value}<br/>` })
        return html
      },
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    grid: { left: 40, right: 16, top: 8, bottom: 36 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 11, color: '#909399' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLabel: { fontSize: 11, color: '#909399' } },
    series: [
      {
        name: 'Total',
        type: 'line',
        data: data.map(d => d.total),
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: '#2f54eb', width: 2 },
        itemStyle: { color: '#2f54eb' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(47,84,235,0.25)' }, { offset: 1, color: 'rgba(47,84,235,0.02)' }]) },
      },
      {
        name: 'Completed',
        type: 'line',
        data: data.map(d => d.completed),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#67C23A', width: 2 },
        itemStyle: { color: '#67C23A' },
      },
      {
        name: 'Failed',
        type: 'line',
        data: data.map(d => d.failed),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#F56C6C', width: 2 },
        itemStyle: { color: '#F56C6C' },
      },
    ],
  })
}

/* ---------- Helpers ---------- */
function formatDuration(sec: number): string {
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}

/* ---------- Refresh ---------- */
function refreshAll() {
  loading.value = true
  stats.value = getMockStats()
  trend.value = getMockTrend()
  topTemplates.value = getMockTopTemplates()
  userActivity.value = getMockUserActivity()
  statusDist.value = getMockStatusDistribution()
  nodeTypeDist.value = getMockNodeTypeDistribution()
  scheduleStats.value = getMockScheduleStats()
  nextTick(() => {
    renderTrendChart()
    renderStatusChart()
    renderTemplatesChart()
    renderNodeTypeChart()
    renderSchedTrendChart()
  })
  loading.value = false
}

/* ---------- Resize handler ---------- */
function onResize() {
  trendChart?.resize()
  statusChart?.resize()
  templatesChart?.resize()
  nodeTypeChart?.resize()
  schedTrendChart?.resize()
}

/* ---------- Lifecycle ---------- */
onMounted(() => {
  nextTick(() => {
    renderTrendChart()
    renderStatusChart()
    renderTemplatesChart()
    renderNodeTypeChart()
    renderSchedTrendChart()
  })
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  statusChart?.dispose()
  templatesChart?.dispose()
  nodeTypeChart?.dispose()
  schedTrendChart?.dispose()
})
</script>

<style scoped>
.opsflow-dashboard {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; background: #f0f2f5; overflow: hidden;
}
.db-body {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 16px;
}

/* ---------- Header ---------- */
.db-header {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
  flex-shrink: 0;
}
.db-header-left { display: flex; flex-direction: column; gap: 2px; }
.db-title { margin: 0; font-size: 22px; font-weight: 700; color: #303133; }
.db-subtitle { font-size: 13px; color: #909399; }
.db-header-right { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }

/* ---------- Stats cards ---------- */
.db-stats-row {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px;
  flex-shrink: 0;
}
.db-stat-card {
  display: flex; align-items: center; gap: 12px; padding: 14px 16px;
  background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  position: relative;
}
.db-stat-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.db-stat-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.db-stat-value { font-size: 20px; font-weight: 700; line-height: 1.2; }
.db-stat-label { font-size: 12px; color: #909399; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.db-stat-trend {
  position: absolute; top: 8px; right: 10px; font-size: 11px; display: flex; align-items: center; gap: 2px;
}
.db-stat-trend.up { color: #52c41a; }
.db-stat-trend.down { color: #ff4d4f; }

/* ---------- Chart cards ---------- */
.db-chart-row {
  display: grid; grid-template-columns: 1fr 360px; gap: 16px;
}
.db-chart-card {
  background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  padding: 16px; display: flex; flex-direction: column;
}
.db-chart-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
  flex-shrink: 0;
}
.db-chart-title { font-size: 14px; font-weight: 600; color: #303133; }
.db-chart-total { font-size: 12px; color: #909399; }
.db-chart-area { flex: 1; min-height: 260px; }

/* ---------- Bottom row ---------- */
.db-bottom-row {
  display: grid; grid-template-columns: 1fr 360px; gap: 16px;
}
.db-table-card,
.db-summary-card { padding: 0 0 4px; }
.db-table-card .db-chart-header,
.db-summary-card .db-chart-header { padding: 12px 16px 8px; }
.db-table-card :deep(.el-table th) { background: #fafafa; }

/* ---------- User cell ---------- */
.user-cell { display: flex; align-items: center; gap: 8px; }
.activity-bar-track { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.activity-bar-fill { height: 100%; background: linear-gradient(90deg, #409EFF, #7ec1ff); border-radius: 4px; transition: width 0.3s; }

/* ---------- Summary ---------- */
.summary-list { padding: 0 16px 12px; display: flex; flex-direction: column; gap: 14px; }
.summary-item { display: flex; flex-direction: column; gap: 4px; }
.summary-label { font-size: 12px; color: #909399; }
.summary-value { font-size: 18px; font-weight: 700; color: #303133; }
.summary-bar-group { display: flex; flex-direction: column; gap: 4px; }
.summary-bar-label { font-size: 11px; color: #606266; }
.summary-bar-track { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.summary-bar-fill { height: 100%; border-radius: 4px; }

/* Health dots */
.summary-health-dots { display: flex; flex-direction: column; gap: 4px; }
.health-row { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #606266; }
.health-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

/* ---------- Section header ---------- */
.db-section-header {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  flex-shrink: 0; margin-top: 4px;
}
.db-section-title { margin: 0; font-size: 16px; font-weight: 600; color: #303133; }

/* ---------- Schedule list (sidebar) ---------- */
.sched-list {
  display: flex; flex-direction: column; gap: 8px; overflow-y: auto; flex: 1;
}
.sched-list-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; border-radius: 6px; background: #fafafa; transition: background 0.2s;
}
.sched-list-item:hover { background: #f0f5ff; }
.sched-list-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.sched-list-name { font-size: 13px; font-weight: 500; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sched-list-meta { font-size: 11px; color: #909399; }
.sched-list-right { flex-shrink: 0; }

/* ---------- Mock badge ---------- */
.mock-badge {
  position: fixed; bottom: 16px; right: 16px;
  font-size: 11px; color: #E6A23C; background: #fdf6ec;
  padding: 4px 12px; border-radius: 4px; z-index: 100;
}
</style>
