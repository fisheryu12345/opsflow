<template>
  <div class="monitor-page">
    <div class="of-card" style="margin-bottom:16px;">
      <el-tabs v-model="activeTab" class="of-tabs" style="padding:0 24px;">
        <el-tab-pane label="告警事件" name="alerts" />
        <el-tab-pane label="告警规则" name="rules" />
        <el-tab-pane label="监控目标" name="targets" />
      </el-tabs>
    </div>

    <!-- Alert Events -->
    <div v-show="activeTab === 'alerts'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">告警事件中心</h3>
        <div>
          <el-select v-model="severityFilter" placeholder="严重级别" clearable style="width:120px;margin-right:8px;">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
          <el-select v-model="statusFilter" placeholder="状态" clearable style="width:120px;">
            <el-option label="触发中" value="firing" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已恢复" value="resolved" />
          </el-select>
        </div>
      </div>
      <div class="of-card-body">
        <el-table :data="alertEvents" v-loading="loading" stripe>
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="severity" label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="metric_value" label="指标值" width="100" />
          <el-table-column prop="fired_at" label="触发时间" width="170" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status==='firing'" size="small" type="warning" @click="ackAlert(row)">确认</el-button>
              <el-button v-if="!row.incident" size="small" type="primary" @click="createIncident(row)">建工单</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Alert Rules -->
    <div v-show="activeTab === 'rules'" class="of-card">
      <div class="of-card-body">
        <el-table :data="alertRules" v-loading="loading" stripe>
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="severity" label="级别" width="80" />
          <el-table-column prop="condition_expr" label="条件" min-width="200" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-switch :model-value="row.status==='enabled'" @click="toggleRule(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="source" label="数据源" width="100" />
        </el-table>
      </div>
    </div>

    <!-- Monitor Targets -->
    <div v-show="activeTab === 'targets'" class="of-card">
      <div class="of-card-body">
        <el-table :data="targets" v-loading="loading" stripe>
          <el-table-column prop="name" label="目标名称" min-width="160" />
          <el-table-column prop="endpoint" label="端点" min-width="240" />
          <el-table-column prop="source" label="数据源" width="100" />
          <el-table-column prop="is_active" label="启用" width="80">
            <template #default="{ row }"><el-switch :model-value="row.is_active" @click="toggleTarget(row)" /></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { alertEventApi, alertRuleApi, targetApi, ToggleAlertRule, AcknowledgeAlert, CreateIncidentFromAlert, ToggleTarget } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'

const activeTab = ref('alerts')
const loading = ref(false)
const alertEvents = ref<any[]>([])
const alertRules = ref<any[]>([])
const targets = ref<any[]>([])
const severityFilter = ref('')
const statusFilter = ref('')

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
onMounted(loadAlerts)
</script>

<style scoped>
.monitor-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
