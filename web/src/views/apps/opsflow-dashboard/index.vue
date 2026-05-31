<template>
  <div class="opsflow-dashboard">
    <!-- Background decorative elements -->
    <div class="db-bg-grid" />
    <div class="db-bg-orb db-bg-orb-1" />
    <div class="db-bg-orb db-bg-orb-2" />

    <div class="db-body">
      <!-- Page header -->
      <div class="db-header">
        <div class="db-header-left">
          <div class="db-title-row">
            <div class="db-title-icon">
              <el-icon :size="20" color="#fff"><Histogram /></el-icon>
            </div>
            <div>
              <h2 class="db-title">OpsFlow Dashboard</h2>
              <span class="db-subtitle">Pipeline execution overview &amp; system health monitoring</span>
            </div>
          </div>
        </div>
        <div class="db-header-right">
          <div class="db-period-group">
            <el-radio-group v-model="period" size="small" @change="refreshAll">
              <el-radio-button value="7d">7D</el-radio-button>
              <el-radio-button value="14d">14D</el-radio-button>
              <el-radio-button value="30d">30D</el-radio-button>
            </el-radio-group>
          </div>
          <el-button :icon="Refresh" @click="refreshAll" :loading="loading" round>
            {{ loading ? 'Loading...' : 'Refresh' }}
          </el-button>
        </div>
      </div>

      <!-- Stats cards -->
      <div class="db-stats-row">
        <div class="db-stat-card" v-for="s in statsCards" :key="s.key" :style="{ '--accent': s.color }">
          <div class="db-stat-icon" :style="{ background: s.bgIcon || s.bg }">
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
          <div class="db-stat-shine" />
        </div>
      </div>

      <!-- Chart row 1: Execution Trend + Status Distribution -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Execution Trend</span>
              <span class="db-chart-subtitle">Daily execution volume over time</span>
            </div>
            <el-tag v-if="trendUp" size="small" :type="trendUp >= 0 ? 'success' : 'danger'" effect="light" round>
              <el-icon size="12" style="margin-right:2px"><Top v-if="trendUp >= 0" /><Bottom v-else /></el-icon>
              {{ Math.abs(trendUp) }}% vs last period
            </el-tag>
          </div>
          <div ref="trendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Status Distribution</span>
              <span class="db-chart-subtitle">{{ stats.total_executions }} total executions</span>
            </div>
          </div>
          <div ref="statusChartRef" class="db-chart-area" />
        </div>
      </div>

      <!-- Chart row 2: Top Templates + Duration -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Top Templates</span>
              <span class="db-chart-subtitle">Most executed workflow templates</span>
            </div>
            <el-tag size="small" effect="plain" round>Top 8</el-tag>
          </div>
          <div ref="templatesChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Node Type Distribution</span>
              <span class="db-chart-subtitle">{{ stats.total_nodes_executed || 0 }} total nodes</span>
            </div>
          </div>
          <div ref="nodeTypeChartRef" class="db-chart-area" />
          <div v-if="nodeTypeDist.length === 0" class="db-chart-empty">
            <el-icon :size="32" color="#d0d5dd"><Collection /></el-icon>
            <span>No node type data yet</span>
            <span class="empty-hint">Auto-generated after execution</span>
          </div>
        </div>
      </div>

      <!-- Section: Scheduler Statistics -->
      <div class="db-section-header">
        <div class="db-section-header-left">
          <div class="db-section-title-icon">
            <el-icon :size="16" color="#2f54eb"><Timer /></el-icon>
          </div>
          <h3 class="db-section-title">Scheduler Overview</h3>
        </div>
        <el-tag size="small" type="info" effect="light" round>
          {{ (scheduleStats.type_distribution || {}).cron || 0 }} cron · {{ (scheduleStats.type_distribution || {}).one_time || 0 }} one-time
        </el-tag>
      </div>

      <!-- Schedule stats cards -->
      <div class="db-stats-row">
        <div class="db-stat-card" v-for="s in schedCards" :key="s.key" :style="{ '--accent': s.color }">
          <div class="db-stat-icon" :style="{ background: s.bg }">
            <el-icon :size="20" :color="s.color"><component :is="s.icon" /></el-icon>
          </div>
          <div class="db-stat-body">
            <span class="db-stat-value" :style="{ color: s.color }">{{ s.value }}</span>
            <span class="db-stat-label">{{ s.label }}</span>
          </div>
          <div class="db-stat-shine" />
        </div>
      </div>

      <!-- Chart row 3: Schedule Trend + Top Schedules -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Schedule Execution Trend</span>
              <span class="db-chart-subtitle">Daily scheduled execution volume</span>
            </div>
            <el-tag v-if="scheduleTrendUp" size="small" type="success" effect="light" round>
              <el-icon size="12" style="margin-right:2px"><Top /></el-icon>
              +{{ scheduleTrendUp }}%
            </el-tag>
          </div>
          <div ref="schedTrendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">Top Schedules</span>
              <span class="db-chart-subtitle">Most active scheduled plans</span>
            </div>
          </div>
          <div class="sched-list">
            <div v-for="(s, si) in (scheduleStats.top_schedules || []).slice(0, 5)" :key="s.id"
                 class="sched-list-item" :style="{ '--idx': si }">
              <div class="sched-list-rank">{{ si + 1 }}</div>
              <div class="sched-list-left">
                <span class="sched-list-name">{{ s.name }}</span>
                <span class="sched-list-meta">{{ s.total_run_count }} runs · {{ s.schedule_type === 'cron' ? 'Cron' : 'One-time' }}</span>
              </div>
              <div class="sched-list-right">
                <span class="sched-status-dot" :class="s.is_active ? 'active' : 'inactive'" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom: User activity table + summary -->
      <div class="db-chart-row">
        <div class="db-chart-card db-table-card">
          <div class="db-chart-header">
            <div class="db-chart-header-left">
              <span class="db-chart-title">User Activity</span>
              <span class="db-chart-subtitle">{{ stats.active_users_7d }} active users in 7 days</span>
            </div>
          </div>
          <el-table :data="userActivity" stripe style="width: 100%" size="small" class="db-table">
            <el-table-column prop="username" label="User" min-width="110">
              <template #default="{ row }">
                <div class="user-cell">
                  <el-avatar :size="26" class="user-avatar">{{ row.username.charAt(0).toUpperCase() }}</el-avatar>
                  <span class="user-name">{{ row.username }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="execution_count" label="Executions" width="90" align="center">
              <template #default="{ row }">
                <span class="exec-count" :class="row.execution_count > 50 ? 'high' : row.execution_count > 20 ? 'mid' : 'low'">
                  {{ row.execution_count }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="template_count" label="Templates" width="90" align="center">
              <template #default="{ row }">
                <span class="tpl-count">{{ row.template_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="last_active" label="Last Active" width="110" />
            <el-table-column label="Activity" min-width="140">
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
            <div class="db-chart-header-left">
              <span class="db-chart-title">System Summary</span>
              <span class="db-chart-subtitle">Overall platform health</span>
            </div>
          </div>
          <div class="summary-list">
            <div class="summary-item">
              <span class="summary-label">Success Rate</span>
              <div class="summary-progress-wrap">
                <el-progress :percentage="stats.success_rate || 0" :stroke-width="10"
                             :status="(stats.success_rate || 0) >= 90 ? 'success' : (stats.success_rate || 0) >= 75 ? 'warning' : 'exception'"
                             :format="() => (stats.success_rate || 0) + '%'" />
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Average Duration</span>
              <span class="summary-value">{{ formatDuration(stats.avg_duration_sec) }}</span>
              <div class="summary-bar-mini">
                <div class="summary-bar-mini-fill duration-bar" style="width:60%" />
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Total Nodes Executed</span>
              <span class="summary-value">{{ (stats.total_nodes_executed || 0).toLocaleString() }}</span>
              <div class="summary-bar-mini">
                <div class="summary-bar-mini-fill" style="width:85%" />
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Templates</span>
              <div class="summary-stacked-bar">
                <div class="stacked-bar-track">
                  <div class="stacked-bar-seg" style="background:#67C23A; flex:66" :title="`Published: ${stats.published_templates || 0}`" />
                  <div class="stacked-bar-seg" style="background:#909399; flex:34" :title="`Draft: ${stats.draft_templates || 0}`" />
                </div>
                <div class="stacked-bar-labels">
                  <span><span class="label-dot" style="background:#67C23A" /> Published {{ stats.published_templates || 0 }}</span>
                  <span><span class="label-dot" style="background:#909399" /> Draft {{ stats.draft_templates || 0 }}</span>
                </div>
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Users</span>
              <div class="summary-stacked-bar">
                <div class="stacked-bar-track">
                  <div class="stacked-bar-seg" style="background:#409EFF; flex:1" />
                </div>
                <div class="stacked-bar-labels">
                  <span><span class="label-dot" style="background:#409EFF" /> {{ stats.total_users || 0 }} Registered</span>
                  <span><span class="label-dot" style="background:#67C23A" /> {{ stats.active_users_7d || 0 }} Active (7d)</span>
                </div>
              </div>
            </div>
            <div class="summary-item">
              <span class="summary-label">Execution Health</span>
              <div class="summary-health-chart">
                <div class="health-bar completed" :style="{ flex: stats.completed_executions || 1 }">
                  <span>{{ stats.completed_executions || 0 }}</span>
                </div>
                <div class="health-bar failed" :style="{ flex: stats.failed_executions || 0.01 }">
                  <span>{{ stats.failed_executions || 0 }}</span>
                </div>
                <div class="health-bar running" :style="{ flex: stats.running_executions || 0.01 }">
                  <span>{{ stats.running_executions || 0 }}</span>
                </div>
                <div class="health-bar other" :style="{ flex: (stats.cancelled_executions || 0) + (stats.paused_executions || 0) || 0.01 }">
                  <span>{{ (stats.cancelled_executions || 0) + (stats.paused_executions || 0) }}</span>
                </div>
              </div>
              <div class="health-legend">
                <span><span class="health-dot completed" /> Completed</span>
                <span><span class="health-dot failed" /> Failed</span>
                <span><span class="health-dot running" /> Running</span>
                <span><span class="health-dot other" /> Other</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <span v-if="false" class="mock-badge">Mock Data</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Refresh, Top, Bottom, Timer, VideoPlay, VideoPause, RefreshRight, Histogram, Collection } from '@element-plus/icons-vue'
import {
  GetDashboardStats, GetDashboardTrend, GetDashboardScheduleStats,
  GetDashboardTopTemplates, GetDashboardUserActivity,
  GetDashboardStatusDistribution, GetDashboardNodeTypeDistribution,
} from '/@/api/opsflow/dashboard'

/* ---------- State ---------- */
const loading = ref(false)
const period = ref<'7d' | '14d' | '30d'>('30d')

const stats = ref<any>({})
const trend = ref<any[]>([])
const topTemplates = ref<any[]>([])
const userActivity = ref<any[]>([])
const statusDist = ref<any[]>([])
const nodeTypeDist = ref<any[]>([])
const scheduleStats = ref<any>({})

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
  { key: 'total_exec', label: 'Total Executions', value: stats.value.total_executions, icon: 'Histogram', bg: '#e6f7ff', bgIcon: '#e6f7ff', color: '#1890ff', trend: 12 },
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

/* ---------- Shared chart options ---------- */
const tooltipTheme = {
  backgroundColor: 'rgba(255,255,255,0.95)',
  borderColor: '#e8e8e8',
  borderWidth: 1,
  borderRadius: 8,
  padding: [10, 14],
  textStyle: { fontSize: 12, color: '#303133' },
  extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08);',
}

/* ---------- Trend chart ---------- */
function renderTrendChart() {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const data = filteredTrend.value
  trendChart.setOption({
    tooltip: {
      ...tooltipTheme,
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
        params.forEach((p: any) => { html += `${p.marker} ${p.seriesName}: <strong>${p.value}</strong><br/>` })
        return html
      },
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#909399' } },
    grid: { left: 44, right: 16, top: 12, bottom: 40 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
    series: [
      {
        name: 'Total',
        type: 'line',
        data: data.map(d => d.total),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#409EFF', width: 2.5 },
        itemStyle: { color: '#409EFF' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.20)' }, { offset: 1, color: 'rgba(64,158,255,0.02)' }]) },
      },
      {
        name: 'Completed',
        type: 'line',
        data: data.map(d => d.completed),
        smooth: true,
        symbol: 'diamond',
        symbolSize: 5,
        lineStyle: { color: '#67C23A', width: 2, type: 'dashed' },
        itemStyle: { color: '#67C23A' },
      },
      {
        name: 'Failed',
        type: 'line',
        data: data.map(d => d.failed),
        smooth: true,
        symbol: 'triangle',
        symbolSize: 5,
        lineStyle: { color: '#F56C6C', width: 2, type: 'dashed' },
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
  const total = statusDist.value.reduce((s, d) => s + d.count, 0) || 1
  statusChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'item', formatter: '{b}: <strong>{c}</strong> ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['50%', '72%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 3 },
      label: { show: true, position: 'outside', fontSize: 11, color: '#606266', formatter: (p: any) => p.percent < 3 ? '' : `{b|${p.name}}\n{d|${p.percent}%}`, rich: { b: { fontSize: 11, color: '#606266' }, d: { fontSize: 12, fontWeight: 700, color: '#303133' } } },
      labelLine: { length: 10, length2: 12, smooth: true, lineStyle: { color: '#ddd' } },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.1)' } },
      animationType: 'scale',
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
      ...tooltipTheme,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0]
        const row = sorted[p.dataIndex]
        return `<div style="font-weight:600;margin-bottom:4px">${row.name}</div>
                Executions: <strong>${row.count}</strong><br/>
                Avg Duration: ${formatDuration(row.avg_duration)}<br/>
                Success Rate: <strong>${row.success_rate}%</strong>`
      },
    },
    grid: { left: 8, right: 44, top: 6, bottom: 8 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11, color: '#b0b0b0' }, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } } },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.name.length > 14 ? d.name.slice(0, 14) + '…' : d.name),
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
            { offset: 0, color: `rgba(64,158,255,${0.35 + i / sorted.length * 0.45})` },
            { offset: 1, color: `rgba(64,158,255,${0.55 + i / sorted.length * 0.35})` },
          ]),
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barWidth: 18,
      label: { show: true, position: 'right', fontSize: 11, color: '#909399', fontWeight: 500 },
      animationDuration: 600,
      animationEasing: 'cubicOut',
    }],
  })
}

/* ---------- Node type doughnut chart ---------- */
function renderNodeTypeChart() {
  if (!nodeTypeChartRef.value) return
  if (!nodeTypeChart) nodeTypeChart = echarts.init(nodeTypeChartRef.value)
  const colors: Record<string, string> = { ansible: '#67C23A', http: '#E6A23C', servicenow: '#909399', esxi: '#20B2AA', other: '#C0C4CC' }
  nodeTypeChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'item', formatter: '{b}: <strong>{c}</strong> ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 3 },
      label: { show: true, position: 'outside', fontSize: 11, color: '#606266', formatter: (p: any) => p.percent < 3 ? '' : `{b|${p.name}}\n{d|${p.percent}%}`, rich: { b: { fontSize: 11, color: '#606266' }, d: { fontSize: 12, fontWeight: 700, color: '#303133' } } },
      labelLine: { length: 10, length2: 10, lineStyle: { color: '#ddd' } },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.1)' } },
      animationType: 'scale',
      data: nodeTypeDist.value.map(d => ({ value: d.count, name: d.label, itemStyle: { color: colors[d.type] || '#C0C4CC' } })),
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
      ...tooltipTheme,
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
        params.forEach((p: any) => { html += `${p.marker} ${p.seriesName}: <strong>${p.value}</strong><br/>` })
        return html
      },
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#909399' } },
    grid: { left: 44, right: 16, top: 12, bottom: 40 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
    series: [
      {
        name: 'Total',
        type: 'line',
        data: data.map(d => d.total),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#2f54eb', width: 2.5 },
        itemStyle: { color: '#2f54eb' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(47,84,235,0.20)' }, { offset: 1, color: 'rgba(47,84,235,0.02)' }]) },
      },
      {
        name: 'Completed',
        type: 'line',
        data: data.map(d => d.completed),
        smooth: true,
        symbol: 'diamond',
        symbolSize: 5,
        lineStyle: { color: '#67C23A', width: 2, type: 'dashed' },
        itemStyle: { color: '#67C23A' },
      },
      {
        name: 'Failed',
        type: 'line',
        data: data.map(d => d.failed),
        smooth: true,
        symbol: 'triangle',
        symbolSize: 5,
        lineStyle: { color: '#F56C6C', width: 2, type: 'dashed' },
        itemStyle: { color: '#F56C6C' },
      },
    ],
  })
}

/* ---------- Helpers ---------- */
function formatDuration(sec: number): string {
  if (!sec) return '0s'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}

/* ---------- Refresh ---------- */
async function refreshAll() {
  loading.value = true
  const days = period.value === '7d' ? 7 : period.value === '14d' ? 14 : 30
  try {
    const [sRes, tRes, ttRes, uaRes, sdRes, ntRes, ssRes] = await Promise.allSettled([
      GetDashboardStats({ days }),
      GetDashboardTrend({ days }),
      GetDashboardTopTemplates({ limit: 8 }),
      GetDashboardUserActivity({ limit: 10 }),
      GetDashboardStatusDistribution(),
      GetDashboardNodeTypeDistribution(),
      GetDashboardScheduleStats({ days }),
    ])
    if (sRes.status === 'fulfilled') stats.value = sRes.value.data?.data || sRes.value.data || {}
    if (tRes.status === 'fulfilled') trend.value = tRes.value.data?.data || tRes.value.data || []
    if (ttRes.status === 'fulfilled') topTemplates.value = ttRes.value.data?.data || ttRes.value.data || []
    if (uaRes.status === 'fulfilled') userActivity.value = uaRes.value.data?.data || uaRes.value.data || []
    if (sdRes.status === 'fulfilled') statusDist.value = sdRes.value.data?.data || sdRes.value.data || []
    if (ntRes.status === 'fulfilled') nodeTypeDist.value = ntRes.value.data?.data || ntRes.value.data || []
    if (ssRes.status === 'fulfilled') scheduleStats.value = ssRes.value.data?.data || ssRes.value.data || {}
  } catch {
    // fallback handled per-Promise via allSettled
  }
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
  refreshAll()
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
/* =============================================
   OpsFlow Dashboard — Modern UI
   ============================================= */

/* ---- Base ---- */
.opsflow-dashboard {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #eef1f5 100%);
  overflow: hidden; position: relative;
}

/* ---- Background decorative ---- */
.db-bg-grid {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(64,158,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64,158,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none; z-index: 0;
}
.db-bg-orb {
  position: absolute; border-radius: 50%; filter: blur(80px);
  pointer-events: none; z-index: 0;
}
.db-bg-orb-1 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(64,158,255,0.06) 0%, transparent 70%);
  top: -120px; right: -80px;
}
.db-bg-orb-2 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(103,194,58,0.05) 0%, transparent 70%);
  bottom: -80px; left: -60px;
}

.db-body {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 18px;
  position: relative; z-index: 1;
}

/* ---- Header ---- */
.db-header {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  flex-shrink: 0;
}
.db-header-left { display: flex; flex-direction: column; }
.db-title-row { display: flex; align-items: center; gap: 14px; }
.db-title-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #409EFF, #2a7de1);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(64,158,255,0.30);
  flex-shrink: 0;
}
.db-title { margin: 0; font-size: 22px; font-weight: 700; color: #1a1a2e; letter-spacing: -0.3px; }
.db-subtitle { font-size: 13px; color: #909399; margin-top: 1px; }
.db-header-right { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }
.db-period-group {
  background: #fff; border-radius: 8px; padding: 2px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ---- Stats cards ---- */
.db-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 14px;
  flex-shrink: 0;
}
.db-stat-card {
  display: flex; align-items: center; gap: 14px; padding: 16px 18px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
  position: relative; overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(255,255,255,0.6);
  cursor: default;
}
.db-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.03);
  background: rgba(255,255,255,0.95);
}
.db-stat-shine {
  position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4) 0%, transparent 60%);
  pointer-events: none; opacity: 0; transition: opacity 0.4s;
}
.db-stat-card:hover .db-stat-shine { opacity: 1; }
.db-stat-icon {
  width: 42px; height: 42px; border-radius: 11px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  position: relative;
}
.db-stat-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.db-stat-value { font-size: 22px; font-weight: 800; line-height: 1.2; letter-spacing: -0.5px; }
.db-stat-label { font-size: 12px; color: #909399; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.db-stat-trend {
  position: absolute; top: 10px; right: 12px;
  font-size: 11px; display: flex; align-items: center; gap: 2px;
  padding: 2px 8px; border-radius: 10px; font-weight: 600;
}
.db-stat-trend.up { color: #52c41a; background: rgba(82,196,26,0.08); }
.db-stat-trend.down { color: #ff4d4f; background: rgba(255,77,79,0.08); }

/* ---- Chart cards ---- */
.db-chart-row {
  display: grid; grid-template-columns: 1fr 380px; gap: 16px;
}
.db-chart-card {
  background: rgba(255,255,255,0.90);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
  padding: 18px; display: flex; flex-direction: column;
  border: 1px solid rgba(255,255,255,0.6);
  transition: box-shadow 0.25s ease;
}
.db-chart-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.03);
}
.db-chart-header {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;
  flex-shrink: 0; gap: 12px;
}
.db-chart-header-left { display: flex; flex-direction: column; gap: 2px; }
.db-chart-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.db-chart-subtitle { font-size: 11px; color: #b0b0b0; }
.db-chart-total { font-size: 12px; color: #909399; }
.db-chart-area { flex: 1; min-height: 270px; }
.db-chart-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 4px; min-height: 270px; color: #bfc1c5;
}
.db-chart-empty span { font-size: 13px; }
.db-chart-empty .empty-hint { font-size: 11px; color: #d0d5dd; }

/* ---- Section header ---- */
.db-section-header {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  flex-shrink: 0; margin-top: 4px;
}
.db-section-header-left { display: flex; align-items: center; gap: 10px; }
.db-section-title-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: #f0f5ff;
  display: flex; align-items: center; justify-content: center;
}
.db-section-title { margin: 0; font-size: 16px; font-weight: 600; color: #1a1a2e; }

/* ---- Bottom row ---- */
.db-table-card,
.db-summary-card { padding: 0 0 6px; }
.db-table-card .db-chart-header,
.db-summary-card .db-chart-header { padding: 14px 18px 10px; }

/* ---- Table ---- */
.db-table { border-radius: 0 0 12px 12px; overflow: hidden; }
.db-table :deep(.el-table th.el-table__cell) {
  background: #fafbfc; color: #606266; font-weight: 600; font-size: 12px;
}
.db-table :deep(.el-table__body tr:hover > td) { background: #f5f9ff; }
.db-table :deep(.el-table__body tr) { transition: background 0.15s; }

/* ---- User cell ---- */
.user-cell { display: flex; align-items: center; gap: 8px; }
.user-avatar {
  background: linear-gradient(135deg, #409EFF, #66b1ff) !important;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}
.user-name { font-size: 13px; font-weight: 500; color: #303133; }
.exec-count, .tpl-count {
  display: inline-block; padding: 1px 10px; border-radius: 10px;
  font-size: 12px; font-weight: 600;
}
.exec-count.high { background: #f6ffed; color: #52c41a; }
.exec-count.mid { background: #fffbe6; color: #faad14; }
.exec-count.low { background: #f5f5f5; color: #909399; }
.tpl-count { color: #606266; font-weight: 500; }

/* ---- Activity bar ---- */
.activity-bar-track {
  height: 6px; background: #f0f2f5; border-radius: 3px; overflow: hidden;
}
.activity-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #409EFF, #7ec1ff);
  border-radius: 3px; transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ---- Summary ---- */
.summary-list { padding: 0 18px 14px; display: flex; flex-direction: column; gap: 16px; }
.summary-item { display: flex; flex-direction: column; gap: 4px; }
.summary-label { font-size: 12px; color: #909399; font-weight: 500; }
.summary-value { font-size: 20px; font-weight: 800; color: #1a1a2e; letter-spacing: -0.5px; }
.summary-progress-wrap { margin-top: 2px; }

/* Mini bar */
.summary-bar-mini { height: 4px; background: #f0f2f5; border-radius: 2px; overflow: hidden; margin-top: 2px; }
.summary-bar-mini-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #409EFF, #7ec1ff); transition: width 0.6s ease; }
.summary-bar-mini-fill.duration-bar { background: linear-gradient(90deg, #2f54eb, #5b7ffa); }

/* Stacked bar */
.summary-stacked-bar { display: flex; flex-direction: column; gap: 6px; }
.stacked-bar-track { display: flex; height: 8px; background: #f0f2f5; border-radius: 4px; overflow: hidden; gap: 2px; }
.stacked-bar-seg { border-radius: 4px; transition: flex 0.5s ease; min-width: 8px; }
.stacked-bar-labels { display: flex; gap: 16px; font-size: 11px; color: #606266; }
.label-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

/* Health chart */
.summary-health-chart {
  display: flex; height: 28px; border-radius: 6px; overflow: hidden; gap: 2px; margin-top: 4px;
}
.health-bar {
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: #fff;
  min-width: 20px; border-radius: 4px;
  transition: flex 0.5s ease;
}
.health-bar.completed { background: linear-gradient(135deg, #67C23A, #95de64); }
.health-bar.failed { background: linear-gradient(135deg, #F56C6C, #ff7875); }
.health-bar.running { background: linear-gradient(135deg, #E6A23C, #ffc53d); }
.health-bar.other { background: linear-gradient(135deg, #909399, #bfc1c5); }
.health-legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 11px; color: #606266; margin-top: 6px; }
.health-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.health-dot.completed { background: #67C23A; }
.health-dot.failed { background: #F56C6C; }
.health-dot.running { background: #E6A23C; }
.health-dot.other { background: #909399; }

/* ---- Schedule list ---- */
.sched-list {
  display: flex; flex-direction: column; gap: 8px; overflow-y: auto; flex: 1;
  padding: 0 2px;
}
.sched-list-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 10px;
  background: #f8f9fb; border: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  cursor: default;
}
.sched-list-item:hover {
  background: #f0f5ff; border-color: #d6e4ff; transform: translateX(2px);
}
.sched-list-rank {
  width: 22px; height: 22px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #909399;
  background: #e8eaed; flex-shrink: 0;
}
.sched-list-item:nth-child(1) .sched-list-rank { background: #ffe58f; color: #d48806; }
.sched-list-item:nth-child(2) .sched-list-rank { background: #f0f0f0; color: #595959; }
.sched-list-item:nth-child(3) .sched-list-rank { background: #f5e6d0; color: #8c6d46; }
.sched-list-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.sched-list-name { font-size: 13px; font-weight: 500; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sched-list-meta { font-size: 11px; color: #b0b0b0; }
.sched-list-right { flex-shrink: 0; }
.sched-status-dot {
  display: block; width: 8px; height: 8px; border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(0,0,0,0.04);
}
.sched-status-dot.active { background: #52c41a; box-shadow: 0 0 0 3px rgba(82,196,26,0.12); }
.sched-status-dot.inactive { background: #d9d9d9; }

/* ---- Mock badge ---- */
.mock-badge {
  position: fixed; bottom: 16px; right: 16px;
  font-size: 11px; color: #E6A23C; background: #fdf6ec;
  padding: 4px 12px; border-radius: 4px; z-index: 100;
}

/* ---- Scrollbar ---- */
.db-body::-webkit-scrollbar { width: 4px; }
.db-body::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 2px; }
.db-body::-webkit-scrollbar-track { background: transparent; }
</style>