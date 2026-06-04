<template>
  <div class="itsm-page">
    <!-- ===== Hero Section ===== -->
    <div class="itsm-hero">
      <div class="itsm-hero-bg" />
      <div class="itsm-hero-inner">
        <div class="itsm-hero-left">
          <h1 class="itsm-hero-title">ITSM</h1>
          <p class="itsm-hero-subtitle">IT service management — 工单与变更管理</p>
        </div>
        <div class="itsm-hero-stats">
          <div class="itsm-stat-item"><span class="itsm-stat-value">{{ incidents.length }}</span><span class="itsm-stat-label">Incidents</span></div>
          <div class="itsm-stat-divider" />
          <div class="itsm-stat-item"><span class="itsm-stat-value">{{ changes.length }}</span><span class="itsm-stat-label">Changes</span></div>
          <div class="itsm-stat-divider" />
          <div class="itsm-stat-item"><span class="itsm-stat-value">{{ slaPolicies.length }}</span><span class="itsm-stat-label">SLA</span></div>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="itsm-hero-tabs">
        <div class="itsm-hero-tab" :class="{ active: activeTab === 'incidents' }" @click="activeTab = 'incidents'">
          <el-icon><WarningFilled /></el-icon> 事件工单
        </div>
        <div class="itsm-hero-tab" :class="{ active: activeTab === 'changes' }" @click="activeTab = 'changes'">
          <el-icon><Edit /></el-icon> 变更申请
        </div>
        <div class="itsm-hero-tab" :class="{ active: activeTab === 'requests' }" @click="activeTab = 'requests'">
          <el-icon><Message /></el-icon> 服务请求
        </div>
        <div class="itsm-hero-tab" :class="{ active: activeTab === 'problems' }" @click="activeTab = 'problems'">
          <el-icon><QuestionFilled /></el-icon> 问题管理
        </div>
        <div class="itsm-hero-tab" :class="{ active: activeTab === 'sla' }" @click="activeTab = 'sla'">
          <el-icon><Clock /></el-icon> SLA 策略
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="itsm-body">

      <!-- ── Incidents ── -->
      <div v-show="activeTab === 'incidents'" class="itsm-section of-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">事件工单</span>
            <el-button type="primary" size="small" @click="showCreateIncident = true">
              <el-icon><Plus /></el-icon> 新建工单
            </el-button>
          </div>
          <el-table :data="incidents" v-loading="loadingIncidents" stripe style="width:100%" size="small"
            :empty-text="loadingIncidents ? '加载中...' : '暂无事件工单'">
            <el-table-column prop="incident_id" label="编号" width="130" />
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="90">
              <template #default="{ row }">
                <span class="itsm-prio-badge" :class="'itsm-prio-' + (row.priority || '').toLowerCase()">{{ row.priority }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="itsm-status-badge" :class="'itsm-status-' + row.status">
                  <span class="itsm-status-dot" />{{ row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="sla_status" label="SLA" width="80">
              <template #default="{ row }">
                <span class="itsm-status-badge" :class="'itsm-status-' + (row.sla_status === 'breached' ? 'failed' : row.sla_status === 'warning' ? 'warning' : 'success')">
                  <span class="itsm-status-dot" />{{ row.sla_status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="assignee_name" label="处理人" width="120" />
            <el-table-column prop="create_datetime" label="创建时间" width="170" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="assignIncident(row)">
                  <el-icon><User /></el-icon> 分派
                </el-button>
                <el-button size="small" text type="success" @click="resolveIncident(row)">
                  <el-icon><Finished /></el-icon> 解决
                </el-button>
                <el-button size="small" text type="info" @click="closeIncident(row)">
                  <el-icon><CircleClose /></el-icon> 关闭
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Changes ── -->
      <div v-show="activeTab === 'changes'" class="itsm-section of-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">变更申请</span>
          </div>
          <el-table :data="changes" v-loading="loadingChanges" stripe style="width:100%" size="small"
            :empty-text="loadingChanges ? '加载中...' : '暂无变更申请'">
            <el-table-column prop="change_id" label="编号" width="130" />
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="change_type" label="类型" width="110" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <span class="itsm-status-badge" :class="'itsm-status-' + row.status">
                  <span class="itsm-status-dot" />{{ row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险" width="80">
              <template #default="{ row }">
                <span class="itsm-prio-badge" :class="'itsm-prio-' + (row.risk_level || '').toLowerCase()">{{ row.risk_level }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status==='pending_approval'" size="small" text type="success" @click="approveChange(row)">
                  <el-icon><Select /></el-icon> 批准
                </el-button>
                <el-button v-if="row.status==='pending_approval'" size="small" text type="danger" @click="rejectChange(row)">
                  <el-icon><Close /></el-icon> 驳回
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Service Requests ── -->
      <div v-show="activeTab === 'requests'" class="itsm-section of-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">服务请求</span>
          </div>
          <el-empty description="服务请求模块开发中" :image-size="60" />
        </div>
      </div>

      <!-- ── Problems ── -->
      <div v-show="activeTab === 'problems'" class="itsm-section of-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">问题管理</span>
          </div>
          <el-empty description="问题管理模块开发中" :image-size="60" />
        </div>
      </div>

      <!-- ── SLA ── -->
      <div v-show="activeTab === 'sla'" class="itsm-section of-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">SLA 策略</span>
          </div>
          <el-table :data="slaPolicies" v-loading="loadingSla" stripe style="width:100%" size="small"
            :empty-text="loadingSla ? '加载中...' : '暂无 SLA 策略'">
            <el-table-column prop="name" label="策略名称" min-width="200" />
            <el-table-column prop="priority" label="优先级" width="80" />
            <el-table-column prop="response_minutes" label="响应时限(min)" width="140" />
            <el-table-column prop="resolve_minutes" label="解决时限(min)" width="140" />
            <el-table-column prop="is_active" label="启用" width="80" align="center">
              <template #default="{ row }"><el-switch v-model="row.is_active" size="small" /></template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { incidentApi, changeApi, slaPolicyApi, AssignIncident, ResolveIncident, CloseIncident, ApproveChange, RejectChange } from '/@/api/itsm/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, User, Finished, CircleClose, Select, Close, WarningFilled, Edit, Message, QuestionFilled, Clock } from '@element-plus/icons-vue'

const activeTab = ref('incidents')
const loadingIncidents = ref(false)
const loadingChanges = ref(false)
const loadingSla = ref(false)
const incidents = ref<any[]>([])
const changes = ref<any[]>([])
const slaPolicies = ref<any[]>([])
const showCreateIncident = ref(false)

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

onMounted(async () => {
  await Promise.all([loadIncidents(), loadChanges(), loadSla()])

  const key = 'opsflow_tour_itsm'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🎫 ITSM — IT 服务管理，事件工单与变更审批全生命周期管理', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../opsflow/styles/opsflow-global' as *;

.itsm-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.itsm-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.itsm-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.itsm-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.itsm-hero-left { flex: 1 1 auto; }
.itsm-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; }
.itsm-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); }
.itsm-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.itsm-stat-item { text-align: center; padding: 0 14px; }
.itsm-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.itsm-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.itsm-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.itsm-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.itsm-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.itsm-hero-tab:hover { color: rgba(255,255,255,0.9); }
.itsm-hero-tab.active { color: #fff; border-bottom-color: #409EFF; }

/* ===== Body ===== */
.itsm-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.itsm-section { padding-top: 16px; }

/* ===== Table Card ===== */
.itsm-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.itsm-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.itsm-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.itsm-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.itsm-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }

/* ===== Status Badge ===== */
.itsm-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.itsm-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }

.itsm-status-new .itsm-status-dot,
.itsm-status-open .itsm-status-dot { background: #409EFF; }
.itsm-status-new { background: #ecf5ff; color: #409EFF; }
.itsm-status-open { background: #ecf5ff; color: #409EFF; }

.itsm-status-assigned .itsm-status-dot,
.itsm-status-in_progress .itsm-status-dot,
.itsm-status-pending_approval .itsm-status-dot { background: #E6A23C; }
.itsm-status-assigned { background: #fdf6ec; color: #E6A23C; }
.itsm-status-in_progress { background: #fdf6ec; color: #E6A23C; }
.itsm-status-pending_approval { background: #fdf6ec; color: #E6A23C; }

.itsm-status-resolved .itsm-status-dot,
.itsm-status-success .itsm-status-dot,
.itsm-status-approved .itsm-status-dot { background: #67C23A; }
.itsm-status-resolved { background: #f0f9eb; color: #67C23A; }
.itsm-status-success { background: #f0f9eb; color: #67C23A; }
.itsm-status-approved { background: #f0f9eb; color: #67C23A; }

.itsm-status-closed .itsm-status-dot { background: #c0c4cc; }
.itsm-status-closed { background: #f5f7fa; color: #909399; }

.itsm-status-escalated .itsm-status-dot,
.itsm-status-failed .itsm-status-dot,
.itsm-status-rejected .itsm-status-dot,
.itsm-status-danger .itsm-status-dot { background: #F56C6C; }
.itsm-status-escalated { background: #fef0f0; color: #F56C6C; }
.itsm-status-failed { background: #fef0f0; color: #F56C6C; }
.itsm-status-rejected { background: #fef0f0; color: #F56C6C; }

.itsm-status-warning .itsm-status-dot { background: #E6A23C; }
.itsm-status-warning { background: #fdf6ec; color: #E6A23C; }

/* ===== Priority Badge ===== */
.itsm-prio-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px;
}
.itsm-prio-p1 { background: #fef0f0; color: #F56C6C; }
.itsm-prio-p2 { background: #fdf6ec; color: #E6A23C; }
.itsm-prio-p3,
.itsm-prio-p4 { background: #f0f9eb; color: #67C23A; }
.itsm-prio-low { background: #f0f9eb; color: #67C23A; }
.itsm-prio-medium { background: #fdf6ec; color: #E6A23C; }
.itsm-prio-high { background: #fef0f0; color: #F56C6C; }
.itsm-prio-critical { background: #fbe9e7; color: #D32F2F; }
</style>
