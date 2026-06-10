<template>
  <div class="monitor-page">
    <!-- Header -->
    <div class="monitor-header">
      <div class="monitor-header-left">
        <h1 class="monitor-title">监控告警中心</h1>
        <span class="monitor-subtitle">Monitoring & Alerting Platform</span>
      </div>
      <div class="monitor-header-center">
        <el-select v-model="filterBiz" placeholder="业务" clearable size="default" style="width:130px;margin-right:8px;">
          <el-option label="全部业务" value="" />
        </el-select>
        <el-select v-model="activeTab" size="default" style="width:160px;">
          <el-option label="🔥 告警事件" value="alerts" />
          <el-option label="📋 告警规则" value="strategies" />
          <el-option label="👥 通知组" value="notify-groups" />
          <el-option label="📊 看板" value="dashboard" />
          <el-option label="📅 值班日历" value="duty" />
          <el-option label="📋 分派规则" value="assign" />
          <el-option label="🔇 屏蔽计划" value="shields" />
          <el-option label="🔌 动作插件" value="actions" />
          <el-option label="📡 采集器" value="collectors" />
          <el-option label="🗄️ 数据源" value="datasources" />
        </el-select>
      </div>
      <div class="monitor-header-stats">
        <div class="stat-item"><span class="stat-val firing">{{ firingCount }}</span><span class="stat-lbl">Firing</span></div>
        <el-divider direction="vertical" />
        <div class="stat-item"><span class="stat-val">{{ strategyCount }}</span><span class="stat-lbl">Rules</span></div>
      </div>
    </div>

    <!-- ════════════ tab: alerts ════════════ -->
    <div v-show="activeTab==='alerts'" class="monitor-body">
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">告警事件中心</span>
          <div class="section-actions">
            <el-select v-model="alertFilter.severity" placeholder="级别" clearable size="small" style="width:100px;margin-right:8px;">
              <el-option label="致命" :value="1" /><el-option label="预警" :value="2" /><el-option label="提醒" :value="3" />
            </el-select>
            <el-select v-model="alertFilter.status" placeholder="状态" clearable size="small" style="width:120px;margin-right:8px;">
              <el-option label="触发中" value="firing" />
              <el-option label="已确认" value="acknowledged" />
              <el-option label="已恢复" value="resolved" />
              <el-option label="已静默" value="silenced" />
              <el-option label="已关闭" value="closed" />
            </el-select>
            <el-button :icon="Refresh" size="small" @click="loadAlerts" :loading="loading">刷新</el-button>
            <el-button v-if="selectedAlerts.length" size="small" type="warning" @click="batchAck">批量确认</el-button>
            <el-button v-if="selectedAlerts.length" size="small" type="danger" @click="batchClose">批量关闭</el-button>
          </div>
        </div>
        <el-table :data="alerts" v-loading="loading" stripe style="width:100%" size="small"
          @selection-change="(rows:any)=>selectedAlerts=rows.map((r:any)=>r.id)"
          empty-text="暂无告警事件">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column label="级别" width="80">
            <template #default="{row}">
              <el-tag :type="sevType(row.severity)" size="small">{{ {1:'致命',2:'预警',3:'提醒'}[row.severity] }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{row}">
              <span :class="'status-'+row.status">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="current_value" label="值" width="90" />
          <el-table-column prop="event_count" label="次数" width="60" />
          <el-table-column prop="fired_at" label="触发时间" width="160" />
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{row}">
              <el-button v-if="row.status==='firing'" size="small" text type="warning" @click="ackAlert(row)">确认</el-button>
              <el-button v-if="row.status==='firing'||row.status==='acknowledged'" size="small" text type="success" @click="resolveAlert(row)">恢复</el-button>
              <el-button v-if="row.status!=='closed'" size="small" text type="info" @click="closeAlert(row)">关闭</el-button>
              <el-button v-if="!row.incident_id" size="small" text type="primary" @click="createIncident(row)">建单</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:pageSize="alertPageSize" v-model:currentPage="alertPage"
            :total="alertTotal" size="small" layout="total,prev,pager,next" />
        </div>
      </div>
    </div>

    <!-- ════════════ tab: strategies ════════════ -->
    <div v-show="activeTab==='strategies'" class="monitor-body">
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">告警规则</span>
          <div class="section-actions">
            <el-input v-model="strategySearch" placeholder="搜索规则" clearable size="small" style="width:200px;margin-right:8px;" />
            <el-button type="primary" size="small" @click="showStrategyWizard = true">+ 创建策略</el-button>
            <el-button :icon="Refresh" size="small" @click="loadStrategies" :loading="loading">刷新</el-button>
          </div>
        </div>
        <el-table :data="strategies" v-loading="loading" stripe style="width:100%" size="small" empty-text="暂无告警规则">
          <el-table-column prop="name" label="规则名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="scenario" label="场景" width="100" />
          <el-table-column label="级别" width="80">
            <template #default="{row}">
              <el-tag :type="sevType(row.severity)" size="small">{{ {1:'致命',2:'预警',3:'提醒'}[row.severity] || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80" align="center">
            <template #default="{row}">
              <el-switch :model-value="row.is_enabled" size="small" @click="toggleStrategy(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="item_count" label="监控项数" width="90" />
          <el-table-column prop="create_time" label="创建时间" width="160" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{row}">
              <el-button size="small" text @click="cloneStrategy(row)">克隆</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- ════════════ tab: notify-groups ════════════ -->
    <div v-show="activeTab==='notify-groups'" class="monitor-body">
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">通知组</span>
          <div class="section-actions">
            <el-button :icon="Refresh" size="small" @click="loadNotifyGroups" :loading="loading">刷新</el-button>
          </div>
        </div>
        <el-table :data="notifyGroups" v-loading="loading" stripe style="width:100%" size="small" empty-text="暂无通知组">
          <el-table-column prop="name" label="组名称" min-width="160" />
          <el-table-column prop="member_count" label="成员数" width="80" />
          <el-table-column label="启用" width="80" align="center">
            <template #default="{row}">
              <el-switch :model-value="row.is_enabled" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </div>

    <!-- ════════════ tab: dashboard ════════════ -->
    <div v-show="activeTab==='dashboard'" class="monitor-body">
      <div class="dashboard-grid">
        <div class="dash-card" v-for="s in summaryStats" :key="s.label">
          <div class="dash-val" :style="{color:s.color}">{{ s.value }}</div>
          <div class="dash-lbl">{{ s.label }}</div>
        </div>
      </div>
      <div class="section-card" style="margin-top:16px;">
        <div class="section-header"><span class="section-title">30天告警趋势</span></div>
        <div style="height:280px;padding:16px 0;" ref="trendChartRef"></div>
      </div>
    </div>

    <!-- ════════════ tab: duty calendar ════════════ -->
    <div v-show="activeTab==='duty'" class="monitor-body">
      <DutyCalendar />
    </div>

    <!-- ════════════ tab: assign rules ════════════ -->
    <div v-show="activeTab==='assign'" class="monitor-body">
      <AssignRules />
    </div>

    <!-- ════════════ tab: shield plans ════════════ -->
    <div v-show="activeTab==='shields'" class="monitor-body">
      <ShieldPlans />
    </div>

    <!-- ════════════ tab: action plugins ════════════ -->
    <div v-show="activeTab==='actions'" class="monitor-body">
      <ActionPlugins />
    </div>

    <!-- ════════════ tab: collectors ════════════ -->
    <div v-show="activeTab==='collectors'" class="monitor-body">
      <CollectConfigs />
    </div>

    <!-- ════════════ tab: datasources ════════════ -->
    <div v-show="activeTab==='datasources'" class="monitor-body">
      <DataSources />
    </div>

    <!-- Strategy Wizard Dialog -->
    <StrategyWizard :visible="showStrategyWizard" @close="showStrategyWizard = false" @created="onStrategyCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import {
  alertApi, strategyApi, notifyGroupApi, dashboardApi,
} from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import DutyCalendar from './DutyCalendar.vue'
import AssignRules from './AssignRules.vue'
import ShieldPlans from './ShieldPlans.vue'
import ActionPlugins from './ActionPlugins.vue'
import CollectConfigs from './CollectConfigs.vue'
import DataSources from './DataSources.vue'
import StrategyWizard from './StrategyWizard.vue'

// ── state ──
const activeTab = ref('alerts')
const loading = ref(false)
const filterBiz = ref('')
const strategySearch = ref('')
const selectedAlerts = ref<number[]>([])
const showStrategyWizard = ref(false)

// alerts
const alerts = ref<any[]>([])
const alertPage = ref(1)
const alertPageSize = ref(20)
const alertTotal = ref(0)
const alertFilter = reactive({ severity: undefined as number|undefined, status: '' })

// strategies
const strategies = ref<any[]>([])
const strategyCount = ref(0)

// notify groups
const notifyGroups = ref<any[]>([])

// dashboard
const summaryStats = ref<{label:string;value:number;color:string}[]>([])
const trendChartRef = ref<HTMLElement|null>(null)
let trendChart: echarts.ECharts|null = null

// ── computed ──
const firingCount = computed(() => alerts.value.filter((e:any) => e.status === 'firing').length)

// ── helpers ──
function sevType(s: number) { return { 1:'danger', 2:'warning', 3:'info' }[s] || 'info' }
function statusLabel(s: string) { return { firing:'触发中', acknowledged:'已确认', resolved:'已恢复', silenced:'已静默', closed:'已关闭' }[s] || s }

// ── loaders ──
async function loadAlerts() {
  loading.value = true
  try {
    const params: any = { page: alertPage.value, limit: alertPageSize.value }
    if (alertFilter.severity) params.severity = alertFilter.severity
    if (alertFilter.status) params.status = alertFilter.status
    const r = await alertApi.list(params)
    alerts.value = r.data || []
    alertTotal.value = r.total || 0
  } finally { loading.value = false }
}

async function loadStrategies() {
  loading.value = true
  try {
    const params: any = {}
    if (strategySearch.value) params.search = strategySearch.value
    const r = await strategyApi.list(params)
    strategies.value = r.data || []
    strategyCount.value = strategies.value.length
  } finally { loading.value = false }
}

async function loadNotifyGroups() {
  loading.value = true
  try {
    const r = await notifyGroupApi.list()
    notifyGroups.value = r.data || []
  } finally { loading.value = false }
}

async function loadDashboard() {
  try {
    const [s, trend] = await Promise.all([
      dashboardApi.summary(),
      dashboardApi.trend(30),
    ])
    summaryStats.value = [
      { label: '触发中', value: s.data?.firing || 0, color: '#F56C6C' },
      { label: '已确认', value: s.data?.acknowledged || 0, color: '#E6A23C' },
      { label: '已恢复', value: s.data?.resolved || 0, color: '#67C23A' },
      { label: '总告警', value: s.data?.total_alerts || 0, color: '#409EFF' },
      { label: '策略数', value: s.data?.total_strategies || 0, color: '#909399' },
    ]
    renderTrendChart(trend.data || [])
  } catch { /* ignore */ }
}

function renderTrendChart(data: any[]) {
  nextTick(() => {
    if (!trendChartRef.value) return
    if (!trendChart) trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, bottom: 30, top: 10 },
      xAxis: { type: 'category', data: data.map((d:any) => d.date), axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{ type: 'line', data: data.map((d:any) => d.count), smooth: true, lineStyle: { color: '#409EFF' }, areaStyle: { color: 'rgba(64,158,255,0.1)' } }],
    })
  })
}

// ── actions ──
async function ackAlert(row: any) { await alertApi.acknowledge(row.id); ElMessage.success('已确认'); loadAlerts() }
async function resolveAlert(row: any) { await alertApi.resolve(row.id); ElMessage.success('已恢复'); loadAlerts() }
async function closeAlert(row: any) { await alertApi.close(row.id); ElMessage.success('已关闭'); loadAlerts() }
async function createIncident(row: any) {
  const r = await alertApi.createIncident(row.id)
  ElMessage.success(`工单: ${r.data?.incident_id}`)
  loadAlerts()
}
async function batchAck() { await alertApi.batchAck(selectedAlerts.value); ElMessage.success('批量确认成功'); loadAlerts() }
async function batchClose() { await alertApi.batchClose(selectedAlerts.value); ElMessage.success('批量关闭成功'); loadAlerts() }
async function toggleStrategy(row: any) { await strategyApi.toggle(row.id); ElMessage.success('操作成功'); loadStrategies() }
async function cloneStrategy(row: any) { await strategyApi.clone(row.id); ElMessage.success('克隆成功'); loadStrategies() }
function onStrategyCreated() { showStrategyWizard.value = false; loadStrategies() }

// ── watch ──
watch(() => alertFilter, () => { alertPage.value = 1; loadAlerts() }, { deep: true })
watch(alertPage, () => loadAlerts())
watch(strategySearch, () => loadStrategies())
watch(activeTab, (tab) => {
  if (tab === 'alerts') loadAlerts()
  else if (tab === 'strategies') loadStrategies()
  else if (tab === 'notify-groups') loadNotifyGroups()
  else if (tab === 'dashboard') loadDashboard()
})

onMounted(() => loadAlerts())
</script>

<style lang="scss" scoped>
.monitor-page {
  position:absolute; top:0; left:0; right:0; bottom:0; display:flex; flex-direction:column;
  background:#f5f6fa; overflow:hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.monitor-header {
  flex-shrink:0; display:flex; align-items:center; padding:12px 24px;
  background:linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  gap:16px;
}
.monitor-header-left { flex:0 0 auto; }
.monitor-title { margin:0; font-size:20px; font-weight:700; color:#fff; }
.monitor-subtitle { font-size:11px; color:rgba(255,255,255,0.4); }
.monitor-header-center { flex:1; display:flex; justify-content:center; }
.monitor-header-center :deep(.el-select .el-input__wrapper) {
  background:rgba(255,255,255,0.1); border-color:rgba(255,255,255,0.12); box-shadow:none; border-radius:8px;
}
.monitor-header-center :deep(.el-select .el-input__inner) { color:#fff; }
.monitor-header-center :deep(.el-select .el-input__inner::placeholder) { color:rgba(255,255,255,0.4); }
.monitor-header-stats { flex:0 0 auto; display:flex; align-items:center; gap:12px; }
.stat-item { text-align:center; }
.stat-val { display:block; font-size:18px; font-weight:700; color:#fff; line-height:1.2; }
.stat-val.firing { color:#F56C6C; }
.stat-lbl { font-size:10px; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:0.5px; }

.monitor-body { flex:1; overflow-y:auto; padding:16px 20px; }
.section-card { background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,0.06); overflow:hidden; }
.section-header {
  display:flex; justify-content:space-between; align-items:center; padding:14px 20px;
  border-bottom:1px solid #f0f0f0;
}
.section-title { font-size:15px; font-weight:600; color:#303133; }
.section-actions { display:flex; align-items:center; }
.pagination-wrap { padding:12px 20px; display:flex; justify-content:flex-end; }

.status-firing { color:#F56C6C; font-weight:500; }
.status-acknowledged { color:#E6A23C; }
.status-resolved { color:#67C23A; }
.status-silenced { color:#909399; }
.status-closed { color:#C0C4CC; }

.dashboard-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }
.dash-card {
  background:#fff; border-radius:12px; padding:20px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.06);
}
.dash-val { font-size:32px; font-weight:700; }
.dash-lbl { font-size:13px; color:#909399; margin-top:4px; }
</style>
