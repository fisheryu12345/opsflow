<template>
  <div class="itsm-page">
    <div class="of-card" style="margin-bottom:16px;">
      <el-tabs v-model="activeTab" class="of-tabs" style="padding:0 24px;">
        <el-tab-pane label="事件工单" name="incidents" />
        <el-tab-pane label="变更申请" name="changes" />
        <el-tab-pane label="服务请求" name="requests" />
        <el-tab-pane label="问题管理" name="problems" />
        <el-tab-pane label="SLA 策略" name="sla" />
      </el-tabs>
    </div>

    <!-- Incidents -->
    <div v-show="activeTab === 'incidents'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">事件工单</h3>
        <el-button type="primary" @click="showCreateIncident = true">+ 新建工单</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="incidents" v-loading="loadingIncidents" stripe>
          <el-table-column prop="incident_id" label="编号" width="130" />
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="priority" label="优先级" width="90">
            <template #default="{ row }">
              <el-tag :type="row.priority === 'P1' ? 'danger' : row.priority === 'P2' ? 'warning' : 'info'" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sla_status" label="SLA" width="80">
            <template #default="{ row }">
              <el-tag :type="row.sla_status === 'breached' ? 'danger' : row.sla_status === 'warning' ? 'warning' : 'success'" size="mini">{{ row.sla_status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="assignee_name" label="处理人" width="120" />
          <el-table-column prop="create_datetime" label="创建时间" width="170" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="assignIncident(row)">分派</el-button>
              <el-button size="small" link @click="resolveIncident(row)">解决</el-button>
              <el-button size="small" type="success" link @click="closeIncident(row)">关闭</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Changes -->
    <div v-show="activeTab === 'changes'" class="of-card">
      <div class="of-card-body">
        <el-table :data="changes" v-loading="loadingChanges" stripe>
          <el-table-column prop="change_id" label="编号" width="130" />
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="change_type" label="类型" width="110" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="risk_level" label="风险" width="80" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button v-if="row.status==='pending_approval'" size="small" type="success" @click="approveChange(row)">批准</el-button>
              <el-button v-if="row.status==='pending_approval'" size="small" type="danger" @click="rejectChange(row)">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- SLA Policies -->
    <div v-show="activeTab === 'sla'" class="of-card">
      <div class="of-card-body">
        <el-table :data="slaPolicies" v-loading="loadingSla" stripe>
          <el-table-column prop="name" label="策略名称" />
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column prop="response_minutes" label="响应时限(min)" width="140" />
          <el-table-column prop="resolve_minutes" label="解决时限(min)" width="140" />
          <el-table-column prop="is_active" label="启用" width="80">
            <template #default="{ row }"><el-switch v-model="row.is_active" /></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { incidentApi, changeApi, slaPolicyApi, AssignIncident, ResolveIncident, CloseIncident, ApproveChange, RejectChange } from '/@/api/itsm/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('incidents')
const loadingIncidents = ref(false)
const loadingChanges = ref(false)
const loadingSla = ref(false)
const incidents = ref<any[]>([])
const changes = ref<any[]>([])
const slaPolicies = ref<any[]>([])
const showCreateIncident = ref(false)

function statusTag(s: string) {
  const m: Record<string, string> = { new: 'info', assigned: 'warning', in_progress: 'primary', resolved: 'success', closed: '', escalated: 'danger' }
  return m[s] || 'info'
}

async function loadIncidents() {
  loadingIncidents.value = true
  try { const res = await incidentApi.list(); incidents.value = res.data || [] } finally { loadingIncidents.value = false }
}
async function loadChanges() {
  loadingChanges.value = true
  try { const res = await changeApi.list(); changes.value = res.data || [] } finally { loadingChanges.value = false }
}
async function loadSla() {
  loadingSla.value = true
  try { const res = await slaPolicyApi.list(); slaPolicies.value = res.data || [] } finally { loadingSla.value = false }
}

async function assignIncident(row: any) {
  const { value } = await ElMessageBox.prompt('输入处理人 ID', '分派工单')
  await AssignIncident(row.id, Number(value))
  ElMessage.success('已分派'); await loadIncidents()
}
async function resolveIncident(row: any) {
  const { value } = await ElMessageBox.prompt('输入解决方案', '解决工单')
  await ResolveIncident(row.id, value)
  ElMessage.success('已解决'); await loadIncidents()
}
async function closeIncident(row: any) {
  await CloseIncident(row.id)
  ElMessage.success('已关闭'); await loadIncidents()
}
async function approveChange(row: any) {
  await ApproveChange(row.id)
  ElMessage.success('已批准'); await loadChanges()
}
async function rejectChange(row: any) {
  await RejectChange(row.id)
  ElMessage.success('已驳回'); await loadChanges()
}

onMounted(() => { loadIncidents(); loadChanges(); loadSla() })
</script>

<style scoped>
.itsm-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
