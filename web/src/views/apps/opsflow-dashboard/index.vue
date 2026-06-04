<template>
  <div class="db-page">
    <!-- Hero Section -->
    <div class="db-hero">
      <div class="db-hero-bg" />
      <div class="db-hero-inner">
        <div class="db-hero-left">
          <h1 class="db-hero-title">Dashboard</h1>
          <p class="db-hero-subtitle">Pipeline execution overview &amp; system health</p>
        </div>
        <div class="db-hero-center">
          <el-radio-group v-model="period" size="small" @change="refreshAll" class="db-period-group">
            <el-radio-button value="7d">7D</el-radio-button>
            <el-radio-button value="14d">14D</el-radio-button>
            <el-radio-button value="30d">30D</el-radio-button>
          </el-radio-group>
        </div>
        <div class="db-hero-stats">
          <div class="db-stat-item"><span class="db-stat-value">{{ stats.total_executions ?? 0 }}</span><span class="db-stat-label">Exec</span></div>
          <div class="db-stat-divider" />
          <div class="db-stat-item"><span class="db-stat-value">{{ stats.running_executions ?? 0 }}</span><span class="db-stat-label">Run</span></div>
          <div class="db-stat-divider" />
          <div class="db-stat-item"><span class="db-stat-value">{{ (stats.success_rate ?? 0) + '%' }}</span><span class="db-stat-label">Ok</span></div>
          <div class="db-stat-divider" />
          <div class="db-stat-item"><span class="db-stat-value">{{ stats.failed_executions ?? 0 }}</span><span class="db-stat-label">Fail</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="db-body">
      <!-- Stats cards row -->
      <div class="db-stats-row">
        <div v-for="s in statsCards" :key="s.key" class="db-stat-card">
          <div class="db-stat-top">
            <div class="db-stat-icon"><el-icon :size="18" :color="s.color"><component :is="s.icon" /></el-icon></div>
            <div class="db-stat-body">
              <span class="db-stat-value db-stat-num">{{ s.value }}</span>
              <span class="db-stat-label">{{ s.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Chart row 1: Execution Trend + Status Distribution -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Execution Trend</span>
            <el-tag v-if="trendUp !== null" :type="trendUp >= 0 ? 'success' : 'danger'" size="small" effect="plain">
              {{ trendUp >= 0 ? '+' : '' }}{{ trendUp }}%
            </el-tag>
          </div>
          <div ref="trendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <span class="db-chart-title">Status</span>
          </div>
          <div ref="statusChartRef" class="db-chart-area" />
        </div>
      </div>

      <!-- Chart row 2: Top Templates + Node Type -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Top Templates</span>
            <el-tag size="small" type="info" effect="plain">Top 8</el-tag>
          </div>
          <div ref="templatesChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header">
            <span class="db-chart-title">Node Type</span>
          </div>
          <div ref="nodeTypeChartRef" class="db-chart-area" />
          <div v-if="nodeTypeDist.length === 0" class="db-chart-empty">No data yet</div>
        </div>
      </div>

      <!-- Scheduler Section -->
      <div class="db-section-header">
        <div class="db-section-header-left">
          <el-icon :size="16" color="#409EFF"><Timer /></el-icon>
          <span class="db-section-title">Scheduler</span>
        </div>
        <el-tag size="small" type="info" effect="plain">
          {{ (scheduleStats.type_distribution || {}).cron || 0 }} cron · {{ (scheduleStats.type_distribution || {}).one_time || 0 }} once
        </el-tag>
      </div>

      <!-- Scheduler stat cards -->
      <div class="db-stats-row">
        <div v-for="s in schedCards" :key="s.key" class="db-stat-card">
          <div class="db-stat-top">
            <div class="db-stat-icon"><el-icon :size="18" :color="s.color"><component :is="s.icon" /></el-icon></div>
            <div class="db-stat-body">
              <span class="db-stat-value db-stat-num">{{ s.value }}</span>
              <span class="db-stat-label">{{ s.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Chart row 3: Schedule Trend + Top Schedules -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header">
            <span class="db-chart-title">Schedule Execution Trend</span>
            <el-tag v-if="scheduleTrendUp !== null" size="small" type="success" effect="plain">+{{ scheduleTrendUp }}%</el-tag>
          </div>
          <div ref="schedTrendChartRef" class="db-chart-area" />
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header"><span class="db-chart-title">Top Schedules</span></div>
          <div class="db-sched-list">
            <div v-for="(s, si) in (scheduleStats.top_schedules || []).slice(0, 5)" :key="s.id" class="db-sched-item" :style="{ '--idx': si }">
              <span class="db-sched-rank">{{ si + 1 }}</span>
              <div class="db-sched-info">
                <span class="db-sched-name">{{ s.name }}</span>
                <span class="db-sched-meta">{{ s.total_run_count }} runs</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom row: User Activity + System Summary -->
      <div class="db-chart-row">
        <div class="db-chart-card db-chart-wide">
          <div class="db-chart-header"><span class="db-chart-title">User Activity</span></div>
          <el-table :data="userActivity" stripe size="small" style="width:100%" empty-text="No data" class="db-table">
            <el-table-column label="User" min-width="120">
              <template #default="{ row }">
                <div class="db-user-cell"><el-avatar :size="24" class="db-user-avatar">{{ (row.username || '?').charAt(0).toUpperCase() }}</el-avatar><span>{{ row.username }}</span></div>
              </template>
            </el-table-column>
            <el-table-column prop="execution_count" label="Exec" width="70" align="center" />
            <el-table-column prop="template_count" label="Tpl" width="60" align="center" />
            <el-table-column label="Activity" min-width="120">
              <template #default="{ row }">
                <div class="db-act-bar"><div class="db-act-fill" :style="{ width: (row.execution_count / Math.max(...userActivity.map(u => u.execution_count), 1)) * 100 + '%' }" /></div>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="db-chart-card db-chart-narrow">
          <div class="db-chart-header"><span class="db-chart-title">System Summary</span></div>
          <div class="db-summary">
            <div class="db-summary-item">
              <span class="db-summary-label">Success Rate</span>
              <el-progress :percentage="stats.success_rate || 0" :stroke-width="8" :status="(stats.success_rate || 0) >= 90 ? 'success' : (stats.success_rate || 0) >= 75 ? 'warning' : 'exception'" :format="() => (stats.success_rate || 0) + '%'" />
            </div>
            <div class="db-summary-item">
              <span class="db-summary-label">Avg Duration</span>
              <span class="db-summary-value">{{ formatDuration(stats.avg_duration_sec) }}</span>
            </div>
            <div class="db-summary-item">
              <span class="db-summary-label">Nodes Executed</span>
              <span class="db-summary-value">{{ (stats.total_nodes_executed || 0).toLocaleString() }}</span>
            </div>
            <div class="db-summary-item">
              <span class="db-summary-label">Templates</span>
              <div class="db-stacked-bar">
                <div class="db-stack-track"><div class="db-stack-seg" style="background:#67C23A;flex:66" /><div class="db-stack-seg" style="background:#C0C4CC;flex:34" /></div>
                <div class="db-stack-labels"><span><span class="dot" style="background:#67C23A" /> {{ stats.published_templates || 0 }}</span><span><span class="dot" style="background:#C0C4CC" /> {{ stats.draft_templates || 0 }}</span></div>
              </div>
            </div>
            <div class="db-summary-item">
              <span class="db-summary-label">Health</span>
              <div class="db-health"><div class="db-health-bar h-completed" :style="{ flex: stats.completed_executions || 1 }">{{ stats.completed_executions || 0 }}</div><div class="db-health-bar h-failed" :style="{ flex: stats.failed_executions || 0.01 }">{{ stats.failed_executions || 0 }}</div><div class="db-health-bar h-running" :style="{ flex: stats.running_executions || 0.01 }">{{ stats.running_executions || 0 }}</div></div>
              <div class="db-health-legend"><span><span class="dot" style="background:#67C23A" /> OK</span><span><span class="dot" style="background:#F56C6C" /> Fail</span><span><span class="dot" style="background:#E6A23C" /> Run</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { Refresh, Top, Bottom, Timer, VideoPlay, VideoPause, RefreshRight, Histogram, Collection, CircleCheck, CircleClose, User, Loading, Upload } from '@element-plus/icons-vue'
import {
  GetDashboardStats, GetDashboardTrend, GetDashboardScheduleStats,
  GetDashboardTopTemplates, GetDashboardUserActivity,
  GetDashboardStatusDistribution, GetDashboardNodeTypeDistribution,
} from '../opsflow/api/dashboard'

const loading = ref(false)
const period = ref<'7d' | '14d' | '30d'>('30d')
const stats = ref<any>({})
const trend = ref<any[]>([])
const topTemplates = ref<any[]>([])
const userActivity = ref<any[]>([])
const statusDist = ref<any[]>([])
const nodeTypeDist = ref<any[]>([])
const scheduleStats = ref<any>({})

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

const filteredTrend = computed(() => {
  const days = period.value === '7d' ? 7 : period.value === '14d' ? 14 : 30
  return trend.value.slice(-days)
})

const trendUp = computed(() => {
  if (filteredTrend.value.length < 4) return null
  const half = Math.floor(filteredTrend.value.length / 2)
  const first = filteredTrend.value.slice(0, half).reduce((s: number, d: any) => s + d.total, 0)
  const last = filteredTrend.value.slice(half).reduce((s: number, d: any) => s + d.total, 0)
  if (first === 0) return null
  return Math.round((last - first) / first * 100)
})

const statsCards = computed(() => [
  { key: 'total_exec', label: 'Total Executions', value: stats.value.total_executions ?? 0, icon: Histogram, color: '#409EFF' },
  { key: 'running', label: 'Running Now', value: stats.value.running_executions ?? 0, icon: Loading, color: '#E6A23C' },
  { key: 'completed', label: 'Completed', value: stats.value.completed_executions ?? 0, icon: CircleCheck, color: '#67C23A' },
  { key: 'failed', label: 'Failed', value: stats.value.failed_executions ?? 0, icon: CircleClose, color: '#F56C6C' },
  { key: 'templates', label: 'Templates', value: stats.value.total_templates ?? 0, icon: Collection, color: '#2f54eb' },
  { key: 'published', label: 'Published', value: stats.value.published_templates ?? 0, icon: Upload, color: '#52c41a' },
  { key: 'users', label: 'Active Users', value: stats.value.active_users_7d ?? 0, icon: User, color: '#eb2f96' },
])

const schedCards = computed(() => [
  { key: 'total_schedules', label: 'Sched Plans', value: stats.value.total_schedule_plans ?? 0, icon: Timer, color: '#2f54eb' },
  { key: 'active_schedules', label: 'Active', value: stats.value.active_schedule_plans ?? 0, icon: VideoPlay, color: '#67C23A' },
  { key: 'paused_schedules', label: 'Paused', value: stats.value.paused_schedule_plans ?? 0, icon: VideoPause, color: '#E6A23C' },
  { key: 'total_runs', label: 'Total Runs', value: stats.value.total_scheduled_runs ?? 0, icon: RefreshRight, color: '#409EFF' },
  { key: 'sched_success', label: 'Sched Success', value: (stats.value.schedule_success_rate ?? 0) + '%', icon: CircleCheck, color: '#52c41a' },
])

const scheduleTrendUp = computed(() => {
  const data = scheduleStats.value.trend || []
  if (data.length < 4) return null
  const half = Math.floor(data.length / 2)
  const first = data.slice(0, half).reduce((s: number, d: any) => s + d.total, 0)
  const last = data.slice(half).reduce((s: number, d: any) => s + d.total, 0)
  if (first === 0) return null
  return Math.round((last - first) / first * 100)
})

const tooltipTheme = { backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e8e8e8', borderWidth: 1, borderRadius: 8, padding: [10, 14], textStyle: { fontSize: 12, color: '#303133' }, extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08)' }

function renderTrendChart() {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const data = filteredTrend.value
  trendChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'axis' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#909399' } },
    grid: { left: 44, right: 16, top: 12, bottom: 40 },
    xAxis: { type: 'category', data: data.map((d: any) => (d.date || '').slice(5)), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
    series: [
      { name: 'Total', type: 'line', data: data.map((d: any) => d.total), smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#409EFF', width: 2.5 }, itemStyle: { color: '#409EFF' }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.20)' }, { offset: 1, color: 'rgba(64,158,255,0.02)' }]) } },
      { name: 'Completed', type: 'line', data: data.map((d: any) => d.completed), smooth: true, symbol: 'diamond', symbolSize: 5, lineStyle: { color: '#67C23A', width: 2, type: 'dashed' }, itemStyle: { color: '#67C23A' } },
      { name: 'Failed', type: 'line', data: data.map((d: any) => d.failed), smooth: true, symbol: 'triangle', symbolSize: 5, lineStyle: { color: '#F56C6C', width: 2, type: 'dashed' }, itemStyle: { color: '#F56C6C' } },
    ],
  })
}

function renderStatusChart() {
  if (!statusChartRef.value) return
  if (!statusChart) statusChart = echarts.init(statusChartRef.value)
  const colorMap: Record<string, string> = { completed: '#67C23A', failed: '#F56C6C', running: '#E6A23C', paused: '#909399', cancelled: '#C0C4CC' }
  statusChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'item', formatter: '{b}: <strong>{c}</strong> ({d}%)' },
    series: [{ type: 'pie', radius: ['48%', '70%'], padAngle: 2, itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 3 }, label: { show: true, position: 'outside', fontSize: 11, color: '#606266' }, labelLine: { length: 10, length2: 10, lineStyle: { color: '#ddd' } }, data: statusDist.value.map((d: any) => ({ value: d.count, name: d.label, itemStyle: { color: colorMap[d.status] } })) }],
  })
}

function renderTemplatesChart() {
  if (!templatesChartRef.value) return
  if (!templatesChart) templatesChart = echarts.init(templatesChartRef.value)
  const sorted = [...topTemplates.value].sort((a: any, b: any) => a.count - b.count)
  templatesChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 44, top: 6, bottom: 8 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11, color: '#b0b0b0' }, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } } },
    yAxis: { type: 'category', data: sorted.map((d: any) => (d.name || '').length > 14 ? (d.name || '').slice(0, 14) + '…' : d.name), axisLabel: { fontSize: 11, color: '#303133', fontWeight: 500 }, axisLine: { show: false }, axisTick: { show: false } },
    series: [{ type: 'bar', data: sorted.map((d: any, i: number) => ({ value: d.count, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `rgba(64,158,255,${0.35 + i / sorted.length * 0.45})` }, { offset: 1, color: `rgba(64,158,255,${0.55 + i / sorted.length * 0.35})` }]), borderRadius: [0, 6, 6, 0] } })), barWidth: 18, label: { show: true, position: 'right', fontSize: 11, color: '#909399' } }],
  })
}

function renderNodeTypeChart() {
  if (!nodeTypeChartRef.value) return
  if (!nodeTypeChart) nodeTypeChart = echarts.init(nodeTypeChartRef.value)
  const colors: Record<string, string> = { ansible: '#67C23A', http: '#E6A23C', servicenow: '#909399', esxi: '#20B2AA', other: '#C0C4CC' }
  nodeTypeChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'item', formatter: '{b}: <strong>{c}</strong> ({d}%)' },
    series: [{ type: 'pie', radius: ['40%', '66%'], padAngle: 2, itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 3 }, label: { show: true, position: 'outside', fontSize: 11 }, labelLine: { length: 10, length2: 10 }, data: nodeTypeDist.value.map((d: any) => ({ value: d.count, name: d.label, itemStyle: { color: colors[d.type] || '#C0C4CC' } })) }],
  })
}

function renderSchedTrendChart() {
  if (!schedTrendChartRef.value) return
  if (!schedTrendChart) schedTrendChart = echarts.init(schedTrendChartRef.value)
  const data = scheduleStats.value.trend || []
  schedTrendChart.setOption({
    tooltip: { ...tooltipTheme, trigger: 'axis' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#909399' } },
    grid: { left: 44, right: 16, top: 12, bottom: 40 },
    xAxis: { type: 'category', data: data.map((d: any) => (d.date || '').slice(5)), axisLabel: { fontSize: 11, color: '#b0b0b0' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#b0b0b0' } },
    series: [
      { name: 'Total', type: 'line', data: data.map((d: any) => d.total), smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#2f54eb', width: 2.5 }, itemStyle: { color: '#2f54eb' }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(47,84,235,0.20)' }, { offset: 1, color: 'rgba(47,84,235,0.02)' }]) } },
      { name: 'Completed', type: 'line', data: data.map((d: any) => d.completed), smooth: true, symbol: 'diamond', symbolSize: 5, lineStyle: { color: '#67C23A', width: 2, type: 'dashed' }, itemStyle: { color: '#67C23A' } },
      { name: 'Failed', type: 'line', data: data.map((d: any) => d.failed), smooth: true, symbol: 'triangle', symbolSize: 5, lineStyle: { color: '#F56C6C', width: 2, type: 'dashed' }, itemStyle: { color: '#F56C6C' } },
    ],
  })
}

function formatDuration(sec: number): string {
  if (!sec) return '0s'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`
}

async function refreshAll() {
  loading.value = true
  const days = period.value === '7d' ? 7 : period.value === '14d' ? 14 : 30
  try {
    const [sRes, tRes, ttRes, uaRes, sdRes, ntRes, ssRes] = await Promise.allSettled([
      GetDashboardStats({ days }), GetDashboardTrend({ days }), GetDashboardTopTemplates({ limit: 8 }),
      GetDashboardUserActivity({ limit: 10 }), GetDashboardStatusDistribution(),
      GetDashboardNodeTypeDistribution(), GetDashboardScheduleStats({ days }),
    ])
    if (sRes.status === 'fulfilled') stats.value = sRes.value.data?.data || sRes.value.data || {}
    if (tRes.status === 'fulfilled') trend.value = tRes.value.data?.data || tRes.value.data || []
    if (ttRes.status === 'fulfilled') topTemplates.value = ttRes.value.data?.data || ttRes.value.data || []
    if (uaRes.status === 'fulfilled') userActivity.value = uaRes.value.data?.data || uaRes.value.data || []
    if (sdRes.status === 'fulfilled') statusDist.value = sdRes.value.data?.data || sdRes.value.data || []
    if (ntRes.status === 'fulfilled') nodeTypeDist.value = ntRes.value.data?.data || ntRes.value.data || []
    if (ssRes.status === 'fulfilled') scheduleStats.value = ssRes.value.data?.data || ssRes.value.data || {}
  } catch { /* handled by allSettled */ }
  nextTick(() => { renderTrendChart(); renderStatusChart(); renderTemplatesChart(); renderNodeTypeChart(); renderSchedTrendChart() })
  loading.value = false
}

function onResize() { [trendChart, statusChart, templatesChart, nodeTypeChart, schedTrendChart].forEach(c => c?.resize()) }

onMounted(() => {
  refreshAll(); window.addEventListener('resize', onResize)
  const key = 'opsflow_tour_dashboard'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '📊 仪表盘 — OpsFlow 全局概览，展示执行趋势、节点分布、项目活跃度', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
onUnmounted(() => { window.removeEventListener('resize', onResize); [trendChart, statusChart, templatesChart, nodeTypeChart, schedTrendChart].forEach(c => c?.dispose()) })
</script>

<style scoped>
.db-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.db-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.db-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.db-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.db-hero-left { flex: 0 0 auto; }
.db-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.db-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.db-hero-center { flex: 0 0 auto; }
.db-period-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.25); color: #fff; box-shadow: none; }
.db-period-group :deep(.el-radio-button__inner) { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.12); color: rgba(255,255,255,0.7); border-radius: 8px !important; padding: 4px 14px; font-size: 12px; }
.db-period-group :deep(.el-radio-button:first-child .el-radio-button__inner) { border-radius: 8px 0 0 8px !important; }
.db-period-group :deep(.el-radio-button:last-child .el-radio-button__inner) { border-radius: 0 8px 8px 0 !important; }
.db-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.db-stat-item { text-align: center; padding: 0 14px; }
.db-stat-item .db-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.db-stat-item .db-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.db-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.db-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; display: flex; flex-direction: column; gap: 16px; }

/* ===== Stats cards row ===== */
.db-stats-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; flex-shrink: 0; margin-top: 16px; }
.db-stat-card { background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06); position: relative; overflow: hidden; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); border: 1px solid #f0f0f0; }
.db-stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-color: transparent; }
.db-stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; opacity: 0; transition: opacity 0.25s; }
.db-stat-card:hover::before { opacity: 1; }
.db-stat-card:nth-child(7n+1)::before { background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.db-stat-card:nth-child(7n+2)::before { background: linear-gradient(90deg, #E6A23C, #f5d76e); }
.db-stat-card:nth-child(7n+3)::before { background: linear-gradient(90deg, #67C23A, #95de64); }
.db-stat-card:nth-child(7n+4)::before { background: linear-gradient(90deg, #F56C6C, #ff7875); }
.db-stat-card:nth-child(7n+5)::before { background: linear-gradient(90deg, #2f54eb, #5b7ffa); }
.db-stat-card:nth-child(7n+6)::before { background: linear-gradient(90deg, #52c41a, #73d13d); }
.db-stat-card:nth-child(7n+7)::before { background: linear-gradient(90deg, #eb2f96, #ff85c0); }
.db-stat-top { display: flex; align-items: center; gap: 12px; }
.db-stat-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: #f5f7fa; }
.db-stat-body { min-width: 0; }
.db-stat-num { font-size: 20px; font-weight: 800; color: #1a1a2e; line-height: 1.2; display: block; }
.db-stat-label { font-size: 11px; color: #909399; }

/* ===== Chart cards ===== */
.db-chart-row { display: grid; grid-template-columns: 1fr 360px; gap: 16px; }
.db-chart-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); padding: 18px; display: flex; flex-direction: column; }
.db-chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.db-chart-title { font-size: 14px; font-weight: 600; color: #303133; }
.db-chart-area { flex: 1; min-height: 260px; }
.db-chart-empty { text-align: center; padding: 40px 0; font-size: 13px; color: #C0C4CC; }

/* ===== Section header ===== */
.db-section-header { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
.db-section-header-left { display: flex; align-items: center; gap: 8px; }
.db-section-title { font-size: 15px; font-weight: 600; color: #303133; }

/* ===== Schedule list ===== */
.db-sched-list { display: flex; flex-direction: column; gap: 6px; padding: 4px 0; }
.db-sched-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 10px; background: #f8f9fb; transition: background .15s; cursor: default; }
.db-sched-item:hover { background: #f0f5ff; }
.db-sched-rank { width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #909399; background: #e8eaed; flex-shrink: 0; }
.db-sched-item:nth-child(1) .db-sched-rank { background: #ffe58f; color: #d48806; }
.db-sched-item:nth-child(2) .db-sched-rank { background: #f0f0f0; color: #595959; }
.db-sched-item:nth-child(3) .db-sched-rank { background: #f5e6d0; color: #8c6d46; }
.db-sched-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
.db-sched-name { font-size: 13px; font-weight: 500; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.db-sched-meta { font-size: 11px; color: #b0b0b0; }

/* ===== Table ===== */
.db-table { width: 100%; }
.db-table :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.db-table :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.db-user-cell { display: flex; align-items: center; gap: 8px; }
.db-user-avatar { background: linear-gradient(135deg, #409EFF, #66b1ff) !important; font-size: 11px; font-weight: 600; flex-shrink: 0; }
.db-act-bar { height: 6px; background: #f0f2f5; border-radius: 3px; overflow: hidden; }
.db-act-fill { height: 100%; background: linear-gradient(90deg, #409EFF, #7ec1ff); border-radius: 3px; }

/* ===== Summary ===== */
.db-summary { display: flex; flex-direction: column; gap: 14px; }
.db-summary-item { display: flex; flex-direction: column; gap: 4px; }
.db-summary-label { font-size: 12px; color: #909399; font-weight: 500; }
.db-summary-value { font-size: 18px; font-weight: 800; color: #1a1a2e; }
.db-stacked-bar { display: flex; flex-direction: column; gap: 4px; }
.db-stack-track { display: flex; height: 6px; background: #f0f2f5; border-radius: 3px; overflow: hidden; gap: 2px; }
.db-stack-seg { border-radius: 3px; min-width: 6px; }
.db-stack-labels { display: flex; gap: 12px; font-size: 11px; color: #606266; }
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.db-health { display: flex; height: 24px; border-radius: 6px; overflow: hidden; gap: 2px; }
.db-health-bar { display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; min-width: 20px; border-radius: 4px; }
.h-completed { background: linear-gradient(135deg, #67C23A, #95de64); }
.h-failed { background: linear-gradient(135deg, #F56C6C, #ff7875); }
.h-running { background: linear-gradient(135deg, #E6A23C, #ffc53d); }
.db-health-legend { display: flex; gap: 10px; font-size: 11px; color: #606266; margin-top: 4px; }

/* ===== Scrollbar ===== */
.db-body::-webkit-scrollbar { width: 4px; }
.db-body::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 2px; }
.db-body::-webkit-scrollbar-track { background: transparent; }
</style>
