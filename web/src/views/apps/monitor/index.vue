<template>
  <div class="monitor-page">
    <!-- ===== Hero Section ===== -->
    <div class="monitor-hero">
      <div class="monitor-hero-bg" />
      <div class="monitor-hero-inner">
        <div class="monitor-hero-left">
          <h1 class="monitor-hero-title">监控中心</h1>
          <p class="monitor-hero-subtitle">Monitoring & alerting — 全方位系统监控与告警管理</p>
        </div>
        <div class="monitor-hero-center">
          <el-select v-model="severityFilter" placeholder="严重级别" clearable size="default" style="width:130px;margin-right:8px;">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
          <el-select v-model="statusFilter" placeholder="状态" clearable size="default" style="width:130px;">
            <el-option label="触发中" value="firing" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已恢复" value="resolved" />
          </el-select>
        </div>
        <div class="monitor-hero-stats">
          <div class="monitor-stat-item"><span class="monitor-stat-value">{{ firingCount }}</span><span class="monitor-stat-label">Firing</span></div>
          <div class="monitor-stat-divider" />
          <div class="monitor-stat-item"><span class="monitor-stat-value">{{ alertRules.length }}</span><span class="monitor-stat-label">Rules</span></div>
          <div class="monitor-stat-divider" />
          <div class="monitor-stat-item"><span class="monitor-stat-value">{{ targets.length }}</span><span class="monitor-stat-label">Targets</span></div>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="monitor-hero-tabs">
        <div class="monitor-hero-tab" :class="{ active: activeTab === 'alerts' }" @click="activeTab = 'alerts'">
          <el-icon><WarningFilled /></el-icon> 告警事件
        </div>
        <div class="monitor-hero-tab" :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'">
          <el-icon><List /></el-icon> 告警规则
        </div>
        <div class="monitor-hero-tab" :class="{ active: activeTab === 'targets' }" @click="activeTab = 'targets'">
          <el-icon><Monitor /></el-icon> 监控目标
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="monitor-body">

      <!-- ── Alert Events ── -->
      <div v-show="activeTab === 'alerts'" class="monitor-section of-fade-in-up">
        <div class="monitor-table-card">
          <div class="monitor-table-header">
            <span class="monitor-table-title">告警事件中心</span>
            <el-button :icon="Refresh" text size="small" @click="loadAlerts" :loading="loading">刷新</el-button>
          </div>
          <el-table :data="alertEvents" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无告警事件'">
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="severity" label="级别" width="90">
              <template #default="{ row }">
                <span class="monitor-severity-badge" :class="'monitor-severity-' + row.severity">
                  <span class="monitor-severity-dot" />{{ row.severity }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="monitor-status-badge" :class="'monitor-status-' + row.status">
                  <span class="monitor-status-dot" />{{ row.status === 'firing' ? '触发中' : row.status === 'acknowledged' ? '已确认' : row.status === 'resolved' ? '已恢复' : row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="metric_value" label="指标值" width="100" />
            <el-table-column prop="fired_at" label="触发时间" width="170" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status==='firing'" size="small" text type="warning" @click="ackAlert(row)">
                  <el-icon><Select /></el-icon> 确认
                </el-button>
                <el-button v-if="!row.incident" size="small" text type="primary" @click="createIncident(row)">
                  <el-icon><Plus /></el-icon> 建工单
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Alert Rules ── -->
      <div v-show="activeTab === 'rules'" class="monitor-section of-fade-in-up">
        <div class="monitor-table-card">
          <div class="monitor-table-header">
            <span class="monitor-table-title">告警规则</span>
          </div>
          <el-table :data="alertRules" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无告警规则'">
            <el-table-column prop="name" label="规则名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="severity" label="级别" width="80">
              <template #default="{ row }">
                <span class="monitor-severity-badge" :class="'monitor-severity-' + row.severity">
                  <span class="monitor-severity-dot" />{{ row.severity }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="condition_expr" label="条件" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="启用" width="80" align="center">
              <template #default="{ row }">
                <el-switch :model-value="row.status==='enabled'" size="small" @click="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="source" label="数据源" width="100" />
          </el-table>
        </div>
      </div>

      <!-- ── Monitor Targets ── -->
      <div v-show="activeTab === 'targets'" class="monitor-section of-fade-in-up">
        <div class="monitor-table-card">
          <div class="monitor-table-header">
            <span class="monitor-table-title">监控目标</span>
          </div>
          <el-table :data="targets" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无监控目标'">
            <el-table-column prop="name" label="目标名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="endpoint" label="端点" min-width="240" show-overflow-tooltip />
            <el-table-column prop="source" label="数据源" width="100" />
            <el-table-column prop="is_active" label="启用" width="80" align="center">
              <template #default="{ row }"><el-switch :model-value="row.is_active" size="small" @click="toggleTarget(row)" /></template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { alertEventApi, alertRuleApi, targetApi, ToggleAlertRule, AcknowledgeAlert, CreateIncidentFromAlert, ToggleTarget } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'
import { WarningFilled, List, Monitor, Select, Plus, Refresh } from '@element-plus/icons-vue'

const activeTab = ref('alerts')
const loading = ref(false)
const alertEvents = ref<any[]>([])
const alertRules = ref<any[]>([])
const targets = ref<any[]>([])
const severityFilter = ref('')
const statusFilter = ref('')

const firingCount = computed(() => alertEvents.value.filter(e => e.status === 'firing').length)

async function loadAlerts() {
  loading.value = true
  try {
    const params: any = {}
    if (severityFilter.value) params.severity = severityFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const [ev, ru, ta] = await Promise.all([
      alertEventApi.list(params),
      alertRuleApi.list(),
      targetApi.list(),
    ])
    alertEvents.value = ev.data || []
    alertRules.value = ru.data || []
    targets.value = ta.data || []
  } finally { loading.value = false }
}

async function ackAlert(row: any) { await AcknowledgeAlert(row.id); ElMessage.success('已确认'); await loadAlerts() }
async function createIncident(row: any) { const r = await CreateIncidentFromAlert(row.id); ElMessage.success(`工单已创建: ${r.data.incident_id}`); await loadAlerts() }
async function toggleRule(row: any) { await ToggleAlertRule(row.id); ElMessage.success('操作成功'); await loadAlerts() }
async function toggleTarget(row: any) { await ToggleTarget(row.id); ElMessage.success('操作成功'); await loadAlerts() }

watch([severityFilter, statusFilter], () => loadAlerts())

onMounted(async () => {
  await loadAlerts()

  const key = 'opsflow_tour_monitor'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '📊 监控中心 — 集中管理告警事件、告警规则与监控目标，支持联动 ITSM 建单', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../opsflow/styles/opsflow-global' as *;

.monitor-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.monitor-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #2d1a1a 0%, #3e1616 50%, #4a1a1a 100%);
}
.monitor-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.monitor-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.monitor-hero-left { flex: 0 0 auto; }
.monitor-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.monitor-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.monitor-hero-center { flex: 1 1 auto; min-width: 0; display: flex; justify-content: center; }
.monitor-hero-center :deep(.el-select .el-input__wrapper) {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none; border-radius: 10px; padding: 2px 12px;
}
.monitor-hero-center :deep(.el-select .el-input__inner) { color: #fff; }
.monitor-hero-center :deep(.el-select .el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.monitor-hero-center :deep(.el-select .el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.monitor-hero-center :deep(.el-select .el-input__suffix-inner) { color: rgba(255,255,255,0.4); }
.monitor-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.monitor-stat-item { text-align: center; padding: 0 14px; }
.monitor-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.monitor-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.monitor-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.monitor-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.monitor-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.monitor-hero-tab:hover { color: rgba(255,255,255,0.9); }
.monitor-hero-tab.active { color: #fff; border-bottom-color: #F56C6C; }

/* ===== Body ===== */
.monitor-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.monitor-section { padding-top: 16px; }

/* ===== Table Card ===== */
.monitor-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.monitor-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.monitor-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.monitor-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.monitor-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }

/* ===== Severity Badge ===== */
.monitor-severity-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.monitor-severity-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.monitor-severity-critical .monitor-severity-dot { background: #F56C6C; }
.monitor-severity-critical { background: #fef0f0; color: #F56C6C; }
.monitor-severity-warning .monitor-severity-dot { background: #E6A23C; }
.monitor-severity-warning { background: #fdf6ec; color: #E6A23C; }
.monitor-severity-info .monitor-severity-dot { background: #909399; }
.monitor-severity-info { background: #f5f7fa; color: #909399; }

/* ===== Status Badge ===== */
.monitor-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.monitor-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.monitor-status-firing .monitor-status-dot { background: #F56C6C; }
.monitor-status-firing { background: #fef0f0; color: #F56C6C; }
.monitor-status-acknowledged .monitor-status-dot { background: #E6A23C; }
.monitor-status-acknowledged { background: #fdf6ec; color: #E6A23C; }
.monitor-status-resolved .monitor-status-dot { background: #67C23A; }
.monitor-status-resolved { background: #f0f9eb; color: #67C23A; }
</style>
