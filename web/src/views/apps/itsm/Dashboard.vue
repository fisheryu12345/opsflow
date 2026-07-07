<template>
  <div class="itsm-dashboard">
    <!-- Stats Cards -->
    <div class="itsm-dash-stats">
      <div class="itsm-dash-stat-card">
        <div class="itsm-dash-stat-icon" style="background: #ecf5ff; color: #409EFF;">
          <el-icon size="24"><List /></el-icon>
        </div>
        <div class="itsm-dash-stat-body">
          <span class="itsm-dash-stat-value">{{ summary.pending_tickets }}</span>
          <span class="itsm-dash-stat-label">{{ $t('message.dashboard.myPending') }}</span>
        </div>
      </div>
      <div class="itsm-dash-stat-card">
        <div class="itsm-dash-stat-icon" style="background: #fef0f0; color: #F56C6C;">
          <el-icon size="24"><WarningFilled /></el-icon>
        </div>
        <div class="itsm-dash-stat-body">
          <span class="itsm-dash-stat-value">{{ summary.overdue_count }}</span>
          <span class="itsm-dash-stat-label">{{ $t('message.dashboard.overdue') }}</span>
        </div>
      </div>
      <div class="itsm-dash-stat-card">
        <div class="itsm-dash-stat-icon" style="background: #f0f9eb; color: #67C23A;">
          <el-icon size="24"><Finished /></el-icon>
        </div>
        <div class="itsm-dash-stat-body">
          <span class="itsm-dash-stat-value">{{ summary.today_resolved }}</span>
          <span class="itsm-dash-stat-label">{{ $t('message.dashboard.todayResolved') }}</span>
        </div>
      </div>
      <div class="itsm-dash-stat-card">
        <div class="itsm-dash-stat-icon" style="background: #fdf6ec; color: #E6A23C;">
          <el-icon size="24"><Clock /></el-icon>
        </div>
        <div class="itsm-dash-stat-body">
          <span class="itsm-dash-stat-value">{{ summary.avg_resolution_hours }}</span>
          <span class="itsm-dash-stat-label">{{ $t('message.dashboard.avgResolution') }}</span>
        </div>
      </div>
    </div>

    <!-- Chart + Overdue side by side -->
    <div class="itsm-dash-row">
      <!-- 30-day Trend Chart -->
      <div class="itsm-dash-card itsm-dash-card-chart">
        <div class="itsm-dash-card-header">
          <span class="itsm-dash-card-title">{{ $t('message.dashboard.trend30d') }}</span>
        </div>
        <div ref="chartRef" style="height: 280px; width: 100%;" />
      </div>

      <!-- Overdue Tickets -->
      <div class="itsm-dash-card itsm-dash-card-list">
        <div class="itsm-dash-card-header">
          <span class="itsm-dash-card-title">{{ $t('message.dashboard.overdueList', { n: overdue.length }) }}</span>
        </div>
        <div class="itsm-dash-list" v-if="overdue.length">
          <div v-for="item in overdue" :key="item.id" class="itsm-dash-list-item">
            <div class="itsm-dash-list-left">
              <span class="itsm-prio-badge" :class="'it-prio-' + (item.priority || 'p3').toLowerCase()">{{ item.priority }}</span>
              <span class="itsm-dash-list-title" @click="$emit('view-ticket', item)">{{ item.sn }} {{ item.title }}</span>
            </div>
            <span class="itsm-dash-list-meta">{{ formatOverdue(item.overdue_seconds) }}</span>
          </div>
        </div>
        <el-empty v-else :description="$t('message.dashboard.noOverdue')" :image-size="40" />
      </div>
    </div>

    <!-- My Tasks -->
    <div class="itsm-dash-card">
      <div class="itsm-dash-card-header">
        <span class="itsm-dash-card-title">{{ $t('message.dashboard.myTasks', { n: myTasks.length }) }}</span>
        <el-button size="small" text @click="$emit('switch-tab', 'tickets')">
          {{ $t('message.dashboard.viewAll') }}
        </el-button>
      </div>
      <el-table :data="myTasks" stripe style="width:100%" size="small"
        :empty-text="$t('message.dashboard.noTasks')"
        @row-click="(row: any) => $emit('view-ticket', row)">
        <el-table-column prop="sn" :label="$t('message.itsmPage.colSn')" width="150" />
        <el-table-column prop="title" :label="$t('message.itsmPage.colTitle')" min-width="180" show-overflow-tooltip />
        <el-table-column prop="node_name" :label="$t('message.dashboard.currentNode')" width="140" />
        <el-table-column prop="node_type" :label="$t('message.dashboard.nodeType')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.node_type === 'APPROVAL' ? 'warning' : 'primary'" size="small">
              {{ row.node_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80">
          <template #default="{ row }">
            <span class="itsm-prio-badge" :class="'it-prio-' + (row.priority || 'p3').toLowerCase()">{{ row.priority }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="create_datetime" :label="$t('message.itsmPage.colCreateTime')" width="160" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { List, WarningFilled, Finished, Clock } from '@element-plus/icons-vue'
import { dashboardApi } from '/@/api/itsm/index'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'

const { t } = useI18n()

const props = defineProps<{
  tickets?: any[]
  active?: boolean
}>()

defineEmits<{
  'view-ticket': [row: any]
  'switch-tab': [tab: string]
}>()

const { reportStats: updateHeroStats } = useHeroConsumer()

// ===== Data =====
const summary = reactive({
  pending_tickets: 0,
  overdue_count: 0,
  today_resolved: 0,
  avg_resolution_hours: 0,
})
const myTasks = ref<any[]>([])
const trendData = ref<any[]>([])
const overdue = ref<any[]>([])
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null

async function loadDashboard() {
  try {
    const [summaryRes, tasksRes, trendRes, overdueRes] = await Promise.all([
      dashboardApi.summary(),
      dashboardApi.myTasks(),
      dashboardApi.trend(),
      dashboardApi.overdue(),
    ])
    Object.assign(summary, summaryRes?.data || summaryRes || {})
    myTasks.value = tasksRes?.data || []
    trendData.value = trendRes?.data || []
    overdue.value = overdueRes?.data || []
  } catch (e) {
    console.warn('[Dashboard] Failed to load:', e)
  }
}

// ===== ECharts =====
async function renderChart() {
  if (!chartRef.value || !trendData.value.length) return
  chartInstance?.dispose()
  const echarts = await import('echarts')
  chartInstance = echarts.init(chartRef.value)
  const dates = trendData.value.map((d: any) => d.date?.slice(5) || '')
  const counts = trendData.value.map((d: any) => d.count || 0)
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, bottom: 24, top: 16 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 10, color: '#909399' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { fontSize: 10, color: '#909399' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [{
      type: 'line',
      data: counts,
      smooth: true,
      lineStyle: { color: '#409EFF', width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' },
          ],
        },
      },
      itemStyle: { color: '#409EFF' },
    }],
  })
}

function handleResize() {
  chartInstance?.resize()
}

watch(() => trendData.value, () => {
  nextTick(renderChart)
})

function formatOverdue(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return '-'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const day = t('message.itsmPage.slaDays')
  const hour = t('message.itsmPage.slaHours')
  const min = t('message.itsmPage.slaMinutes')
  if (d > 0) return `${d}${day}${h}${hour}`
  if (h > 0) return `${h}${hour}`
  return `${Math.floor(seconds / 60)}${min}`
}

function reportStats() {
  updateHeroStats([
    { value: summary.pending_tickets, label: '待处理' },
    { value: summary.overdue_count, label: '已逾期' },
    { value: summary.today_resolved, label: '今日解决' },
    { value: summary.avg_resolution_hours + 'h', label: '平均解决' },
  ])
}

onMounted(async () => {
  await loadDashboard()
  if (props.active) reportStats()
  nextTick(renderChart)
  window.addEventListener('resize', handleResize)
})

// Re-report stats when this tab becomes active
watch(() => props.active, (isActive) => {
  if (isActive && summary.pending_tickets !== undefined) reportStats()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.itsm-dashboard {
  padding: 16px 0;
}

/* ===== Stats Cards ===== */
.itsm-dash-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.itsm-dash-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: $g-shadow-card;
}

.itsm-dash-stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.itsm-dash-stat-body {
  display: flex;
  flex-direction: column;
}

.itsm-dash-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: $g-text-primary;
  line-height: 1.2;
}

.itsm-dash-stat-label {
  font-size: 12px;
  color: $g-text-muted;
  margin-top: 2px;
}

/* ===== Row Layout ===== */
.itsm-dash-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}

/* ===== Card ===== */
.itsm-dash-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: $g-shadow-card;
  padding: 16px 18px;
}

.itsm-dash-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.itsm-dash-card-title {
  font-size: 14px;
  font-weight: 600;
  color: $g-text-primary;
}

/* ===== Overdue List ===== */
.itsm-dash-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.itsm-dash-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fafafa;
  transition: background 0.15s;
  cursor: default;
  &:hover { background: #f0f5ff; }
}

.itsm-dash-list-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.itsm-dash-list-title {
  font-size: 13px;
  color: $g-text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  &:hover { color: #409EFF; }
}

.itsm-dash-list-meta {
  font-size: 11px;
  color: $g-text-muted;
  flex-shrink: 0;
}

/* ===== Table style ===== */
.itsm-dash-card :deep(.el-table th.el-table__cell) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
  font-size: 12px;
}

.itsm-dash-card :deep(.el-table__body tr:hover td) {
  background: #f0f5ff;
  cursor: pointer;
}
</style>
