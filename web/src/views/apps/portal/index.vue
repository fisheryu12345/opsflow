<template>
  <div class="portal-page">
    <!-- ===== Hero Section ===== -->
    <div class="portal-hero">
      <div class="portal-hero-bg" />
      <div class="portal-hero-inner">
        <div class="portal-hero-content">
          <div class="portal-hero-welcome">
            <h1 class="portal-hero-title">
              运维工作台
              <span class="portal-hero-user" v-if="userInfo?.name">
                — {{ userInfo.name }}
              </span>
            </h1>
            <p class="portal-hero-subtitle">Welcome back — 这里聚合了你的待办、系统概览和快捷操作</p>
          </div>
          <div class="portal-hero-stats">
            <div class="portal-stat-item">
              <span class="portal-stat-value" :class="{ 'text-danger': stats.alerts?.firing > 0 }">{{ stats.alerts?.firing ?? '--' }}</span>
              <span class="portal-stat-label">告警中</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value">{{ stats.itsm_ticket_stats?.running ?? stats.incidents?.open ?? '--' }}</span>
              <span class="portal-stat-label">进行中工单</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value">{{ stats.execution_stats?.running ?? '--' }}</span>
              <span class="portal-stat-label">执行中作业</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value" :class="{ 'text-danger': stats.incident_stats?.overdue > 0 }">{{ stats.incident_stats?.overdue ?? '--' }}</span>
              <span class="portal-stat-label">SLA 违例</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="portal-body">

      <!-- Quick Stats Cards -->
      <div class="portal-quick-stats of-fade-in-up">
        <div class="portal-qstat-card" style="--qstat-color: #F56C6C; --qstat-bg: #fef0f0;">
          <div class="portal-qstat-icon"><el-icon :size="22"><WarningFilled /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.alerts?.firing ?? '--' }}</div>
            <div class="portal-qstat-label">进行中告警</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #E6A23C; --qstat-bg: #fdf6ec;">
          <div class="portal-qstat-icon"><el-icon :size="22"><List /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.itsm_ticket_stats?.running ?? stats.incidents?.open ?? '--' }}</div>
            <div class="portal-qstat-label">开放工单</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #67C23A; --qstat-bg: #f0f9eb;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Monitor /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.execution_stats?.running ?? '--' }}</div>
            <div class="portal-qstat-label">执行中作业</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #409EFF; --qstat-bg: #ecf5ff;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Clock /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value" :class="{ 'text-danger': stats.incident_stats?.overdue > 0 }">{{ stats.incident_stats?.overdue ?? '--' }}</div>
            <div class="portal-qstat-label">SLA 违例</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #909399; --qstat-bg: #f5f7fa;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Folder /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.opsflow_template_stats?.published ?? '--' }}</div>
            <div class="portal-qstat-label">已发布模板</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #F56C6C; --qstat-bg: #fef0f0;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Warning /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.execution_stats?.failed_today ?? '--' }}</div>
            <div class="portal-qstat-label">今日失败</div>
          </div>
        </div>
      </div>

      <!-- Two-column layout -->
      <div class="portal-grid-2col">

        <!-- Left: My Tasks -->
        <div class="portal-table-card of-fade-in-up">
          <div class="portal-table-header">
            <span class="portal-table-title">我的待办</span>
            <el-button link type="primary" size="small" @click="$router.push('/apps/itsm')">查看全部</el-button>
          </div>
          <el-table :data="tasks" v-loading="loadingTasks" stripe style="width:100%" size="small"
            :empty-text="loadingTasks ? '加载中...' : '暂无待办事项'"
            @row-click="(row: any) => handleTaskClick(row)">
            <el-table-column label="类型" width="90">
              <template #default="{ row }">
                <span class="portal-type-badge" :class="'portal-type-' + (row.type || 'incident')">
                  {{ row.type === 'incident' ? '工单' : row.type === 'approval' ? '审批' : row.type === 'execution_approval' ? '流程' : '变更' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="id" label="编号" width="110" />
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }">
                <span class="portal-prio-badge" :class="'portal-prio-' + (row.priority || '').toLowerCase()" v-if="row.priority">{{ row.priority }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="portal-status-badge" :class="'portal-status-' + row.status">
                  <span class="portal-status-dot" />{{ row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160" />
          </el-table>
        </div>

        <!-- Right: Recent Activity -->
        <div class="portal-table-card of-fade-in-up">
          <div class="portal-table-header">
            <span class="portal-table-title">近期活动</span>
            <el-button link type="primary" size="small" @click="loadRecentActivity">刷新</el-button>
          </div>
          <div class="portal-activity-list" v-loading="loadingActivity">
            <div v-if="activities.length === 0 && !loadingActivity" class="portal-empty">暂无活动记录</div>
            <div v-for="act in activities" :key="act.type + '-' + act.id"
              class="portal-activity-item"
              @click="handleActivityClick(act)">
              <span class="portal-activity-icon" :class="'act-icon-' + act.type">
                <el-icon :size="16">
                  <WarningFilled v-if="act.type === 'alert'" />
                  <List v-if="act.type === 'ticket'" />
                  <CaretRight v-if="act.type === 'execution'" />
                  <Monitor v-if="act.type === 'cmdb'" />
                </el-icon>
              </span>
              <div class="portal-activity-body">
                <div class="portal-activity-title">{{ act.title }}</div>
                <div class="portal-activity-meta">
                  <span class="portal-activity-status" :class="'act-status-' + act.status">{{ act.status }}</span>
                  <span v-if="act.user" class="portal-activity-user">{{ act.user }}</span>
                  <span class="portal-activity-time">{{ formatTime(act.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Favorites -->
      <div class="portal-table-card of-fade-in-up" v-if="favorites.templates?.length > 0 || favorites.recent_actions?.length > 0">
        <div class="portal-table-header">
          <span class="portal-table-title">收藏与最近</span>
          <el-button link type="primary" size="small" @click="$router.push('/apps/opsflow')">管理模板</el-button>
        </div>
        <div class="portal-favorites-body">
          <!-- Favorite Templates -->
          <div class="portal-fav-section" v-if="favorites.templates?.length > 0">
            <div class="portal-fav-label">收藏的流程模板</div>
            <div class="portal-fav-items">
              <div v-for="tpl in favorites.templates" :key="'tpl-' + tpl.id"
                class="portal-fav-item" @click="$router.push(tpl.url)">
                <el-icon><StarFilled /></el-icon>
                <span class="portal-fav-name">{{ tpl.name }}</span>
                <span class="portal-fav-category" v-if="tpl.category">{{ tpl.category }}</span>
              </div>
            </div>
          </div>
          <!-- Recent Actions -->
          <div class="portal-fav-section" v-if="favorites.recent_actions?.length > 0">
            <div class="portal-fav-label">最近操作</div>
            <div class="portal-fav-items">
              <div v-for="act in favorites.recent_actions" :key="'act-' + act.id"
                class="portal-fav-item">
                <el-icon><Clock /></el-icon>
                <span class="portal-fav-name">{{ act.action || '操作' }}</span>
                <span class="portal-fav-time">{{ formatTime(act.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Module Health -->
      <div class="portal-table-card of-fade-in-up" v-if="Object.keys(moduleCounts).length > 0">
        <div class="portal-table-header">
          <span class="portal-table-title">系统概览</span>
        </div>
        <div class="portal-health-body">
          <div v-for="(count, key) in moduleCounts" :key="key" class="portal-health-item">
            <span class="portal-health-label">{{ formatModuleName(key) }}</span>
            <span class="portal-health-value" :class="{ 'text-muted': count === 0 }">{{ count }}</span>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="portal-actions-card of-fade-in-up">
        <div class="portal-actions-header">
          <span class="portal-table-title">快捷操作</span>
        </div>
        <div class="portal-actions-body">
          <el-button type="primary" size="default" @click="$router.push('/apps/itsm')">
            <el-icon><Plus /></el-icon> 创建工单
          </el-button>
          <el-button size="default" @click="$router.push('/apps/opsflow')">
            <el-icon><CaretRight /></el-icon> 执行流程
          </el-button>
          <el-button size="default" @click="$router.push('/apps/cmdb')">
            <el-icon><Monitor /></el-icon> 查看 CMDB
          </el-button>
          <el-button size="default" @click="$router.push('/apps/monitor')">
            <el-icon><WarningFilled /></el-icon> 告警中心
          </el-button>
          <el-button size="default" @click="$router.push('/apps/job-platform')">
            <el-icon><Tools /></el-icon> 作业平台
          </el-button>
          <el-button size="default" @click="$router.push('/open-api')">
            <el-icon><Connection /></el-icon> API 管理
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { GetDashboard, GetMyTasks, GetRecentActivity, GetFavorites } from '/@/api/portal/index'
import {
  WarningFilled, List, Monitor, Clock, Plus, CaretRight,
  Folder, Warning, StarFilled, Tools, Connection,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()

const loadingTasks = ref(false)
const loadingActivity = ref(false)
const stats = ref<any>({})
const tasks = ref<any[]>([])
const activities = ref<any[]>([])
const favorites = ref<any>({ templates: [], recent_actions: [] })
const moduleCounts = ref<Record<string, number>>({})
const userInfo = ref<any>(null)

function formatTime(val: string | null | undefined): string {
  if (!val) return ''
  try {
    const d = new Date(val)
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${d.getMonth() + 1}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return ''
  }
}

function formatModuleName(key: string): string {
  const map: Record<string, string> = {
    itsm_tickets: 'ITSM 工单',
    opsflow_templates: 'OpsFlow 模板',
    opsflow_executions: 'OpsFlow 执行',
    cmdb_hosts: 'CMDB 主机',
    incidents: '事件工单',
    alerts: '告警',
  }
  return map[key] || key
}

function handleTaskClick(row: any) {
  if (row.type === 'incident') {
    router.push(`/apps/itsm/incident/${row.id}`)
  } else if (row.type === 'approval') {
    router.push(`/apps/itsm/ticket/${row.id}`)
  } else if (row.type === 'execution_approval') {
    router.push(`/apps/opsflow/execution/${row.id}`)
  } else {
    router.push('/apps/itsm')
  }
}

function handleActivityClick(act: any) {
  if (act.url) {
    router.push(act.url)
  }
}

async function loadRecentActivity() {
  loadingActivity.value = true
  try {
    const res = await GetRecentActivity(15, 72)
    activities.value = res.data || []
  } catch {
    activities.value = []
  } finally {
    loadingActivity.value = false
  }
}

onMounted(async () => {
  try {
    const [dash, taskRes, favRes] = await Promise.all([
      GetDashboard(),
      GetMyTasks(),
      GetFavorites(),
    ])
    stats.value = dash.data || {}
    userInfo.value = dash.data?.user_info || null
    tasks.value = taskRes.data || []
    favorites.value = favRes.data || { templates: [], recent_actions: [] }
    moduleCounts.value = dash.data?.module_counts || {}
  } catch {
    /* modules not ready */
  }

  await loadRecentActivity()

  const key = 'opsflow_tour_portal'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '运维工作台 — 一站式总览告警、工单、作业状态，快速跳转各子系统', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../opsflow/styles/opsflow-global' as *;

.portal-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.portal-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: $of-gradient-hero;
  border-bottom: 1px solid $of-border-light;
}
.portal-hero-bg {
  position: absolute; inset: 0; opacity: 0.04;
  background-image: radial-gradient(circle at 15% 60%, #409EFF 2px, transparent 2px), radial-gradient(circle at 85% 40%, #667eea 2px, transparent 2px);
  background-size: 60px 60px;
}
.portal-hero-inner {
  position: relative; z-index: 1; padding: 24px 32px;
}
.portal-hero-content { max-width: 1200px; margin: 0 auto; }
.portal-hero-welcome { margin-bottom: 20px; }
.portal-hero-title { margin: 0; font-size: 26px; font-weight: 800; color: $of-text-primary; }
.portal-hero-user { font-weight: 400; font-size: 20px; color: $of-text-muted; }
.portal-hero-subtitle { margin: 6px 0 0; color: $of-text-muted; font-size: 14px; }

.portal-hero-stats { display: flex; align-items: center; gap: 0; }
.portal-stat-item { text-align: center; padding: 0 24px; }
.portal-stat-value { display: block; font-size: 24px; font-weight: 700; color: $of-text-primary; line-height: 1.3; }
.portal-stat-label { font-size: 12px; color: $of-text-muted; margin-top: 2px; }
.portal-stat-divider { width: 1px; height: 32px; background: $of-border-default; }

/* ===== Body ===== */
.portal-body {
  flex: 1; overflow-y: auto;
  padding: 20px 32px 32px;
  max-width: 1200px; margin: 0 auto; width: 100%; box-sizing: border-box;
}

/* ===== Quick Stats ===== */
.portal-quick-stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
@media (max-width: 1000px) {
  .portal-quick-stats { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 600px) {
  .portal-quick-stats { grid-template-columns: repeat(2, 1fr); }
}
.portal-qstat-card {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: $of-shadow-card;
  @include of-hover-lift;
  position: relative;
}
.portal-qstat-icon {
  width: 40px; height: 40px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--qstat-bg);
  color: var(--qstat-color);
  flex-shrink: 0;
}
.portal-qstat-body { flex: 1; }
.portal-qstat-value { font-size: 22px; font-weight: 700; line-height: 1.2; color: $of-text-primary; }
.portal-qstat-label { font-size: 11px; color: $of-text-muted; margin-top: 2px; }

/* ===== Two-column Grid ===== */
.portal-grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 800px) {
  .portal-grid-2col { grid-template-columns: 1fr; }
}

/* ===== Table Card ===== */
.portal-table-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: $of-shadow-card;
  overflow: hidden;
  margin-bottom: 16px;
}
.portal-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.portal-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; cursor: pointer; }
.portal-table-card :deep(.el-table__empty-text) { padding: 20px 0; }
.portal-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.portal-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }

/* ===== Type Badge ===== */
.portal-type-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px;
}
.portal-type-incident { background: #fef0f0; color: #F56C6C; }
.portal-type-change { background: #fdf6ec; color: #E6A23C; }
.portal-type-approval { background: #ecf5ff; color: #409EFF; }
.portal-type-execution_approval { background: #f0f9eb; color: #67C23A; }

/* ===== Priority Badge ===== */
.portal-prio-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px;
}
.portal-prio-p1 { background: #fef0f0; color: #F56C6C; }
.portal-prio-p2 { background: #fdf6ec; color: #E6A23C; }
.portal-prio-p3,
.portal-prio-p4 { background: #f0f9eb; color: #67C23A; }

/* ===== Status Badge ===== */
.portal-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.portal-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.portal-status-open .portal-status-dot,
.portal-status-pending .portal-status-dot,
.portal-status-pending_approval .portal-status-dot { background: #E6A23C; }
.portal-status-open { background: #fdf6ec; color: #E6A23C; }
.portal-status-pending { background: #fdf6ec; color: #E6A23C; }
.portal-status-pending_approval { background: #fdf6ec; color: #E6A23C; }
.portal-status-resolved .portal-status-dot,
.portal-status-completed .portal-status-dot,
.portal-status-finished .portal-status-dot { background: #67C23A; }
.portal-status-resolved { background: #f0f9eb; color: #67C23A; }
.portal-status-completed { background: #f0f9eb; color: #67C23A; }
.portal-status-finished { background: #f0f9eb; color: #67C23A; }
.portal-status-closed .portal-status-dot,
.portal-status-terminated .portal-status-dot { background: #909399; }
.portal-status-closed { background: #f5f7fa; color: #909399; }
.portal-status-terminated { background: #f5f7fa; color: #909399; }

/* ===== Activity List ===== */
.portal-activity-list {
  padding: 8px 0;
  max-height: 420px;
  overflow-y: auto;
}
.portal-empty { text-align: center; padding: 40px 0; color: #909399; font-size: 13px; }
.portal-activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.portal-activity-item:hover { background: #f5f7fa; }
.portal-activity-icon {
  flex-shrink: 0;
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  margin-top: 2px;
}
.act-icon-alert { background: #fef0f0; color: #F56C6C; }
.act-icon-ticket { background: #fdf6ec; color: #E6A23C; }
.act-icon-execution { background: #f0f9eb; color: #67C23A; }
.act-icon-cmdb { background: #ecf5ff; color: #409EFF; }
.portal-activity-body { flex: 1; min-width: 0; }
.portal-activity-title { font-size: 13px; font-weight: 500; color: $of-text-primary; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.portal-activity-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 11px; }
.portal-activity-status {
  display: inline-block; padding: 1px 8px; border-radius: 8px; font-weight: 500;
}
.act-status-firing,
.act-status-running,
.act-status-processing { background: #fef0f0; color: #F56C6C; }
.act-status-completed,
.act-status-resolved,
.act-status-finished { background: #f0f9eb; color: #67C23A; }
.act-status-pending { background: #fdf6ec; color: #E6A23C; }
.portal-activity-user { color: #909399; }
.portal-activity-time { color: #c0c4cc; margin-left: auto; }

/* ===== Favorites ===== */
.portal-favorites-body { padding: 12px 20px 16px; }
.portal-fav-section { margin-bottom: 12px; }
.portal-fav-section:last-child { margin-bottom: 0; }
.portal-fav-label { font-size: 12px; color: #909399; margin-bottom: 8px; }
.portal-fav-items { display: flex; flex-wrap: wrap; gap: 8px; }
.portal-fav-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  font-size: 13px;
  color: $of-text-primary;
  transition: background 0.15s;
}
.portal-fav-item:hover { background: #ecf5ff; color: #409EFF; }
.portal-fav-item .el-icon { font-size: 14px; color: #E6A23C; }
.portal-fav-category { font-size: 11px; color: #909399; margin-left: 4px; }
.portal-fav-time { font-size: 11px; color: #c0c4cc; margin-left: 4px; }

/* ===== Health ===== */
.portal-health-body {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 16px 20px;
}
.portal-health-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  background: #f5f7fa;
  min-width: 140px;
}
.portal-health-label { font-size: 12px; color: #606266; }
.portal-health-value { font-size: 16px; font-weight: 700; color: $of-text-primary; margin-left: auto; }
.portal-health-value.text-muted { color: #c0c4cc; }

/* ===== Actions Card ===== */
.portal-actions-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: $of-shadow-card;
  overflow: hidden;
}
.portal-actions-header { padding: 16px 20px 0; }
.portal-actions-body {
  display: flex; gap: 12px; padding: 12px 20px 20px; flex-wrap: wrap;
}

/* ===== Utilities ===== */
.text-danger { color: #F56C6C; }
.text-success { color: #67C23A; }
.text-muted { color: #c0c4cc; }
</style>
