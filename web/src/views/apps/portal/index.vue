<template>
  <div class="portal-page">
    <!-- ===== Hero Section ===== -->
    <div class="portal-hero">
      <div class="portal-hero-bg" />
      <div class="portal-hero-inner">
        <div class="portal-hero-left">
          <h1 class="portal-hero-title">
            {{ $t('message.portal.title') }}
            <span class="portal-hero-user" v-if="userInfo?.name">— {{ userInfo.name }}</span>
          </h1>
          <p class="portal-hero-subtitle">{{ $t('message.portal.subtitle') }}</p>
        </div>
        <div class="portal-hero-spacer" />
        <div class="portal-hero-stats">
          <div class="portal-stat-item">
            <span class="portal-stat-value" :class="{ 'text-danger': stats.alerts?.firing > 0 }">{{ stats.alerts?.firing ?? '--' }}</span>
            <span class="portal-stat-label">{{ $t('message.portal.alertsFiring') }}</span>
          </div>
          <div class="portal-stat-divider" />
          <div class="portal-stat-item">
            <span class="portal-stat-value">{{ stats.itsm_ticket_stats?.running ?? stats.incidents?.open ?? '--' }}</span>
            <span class="portal-stat-label">{{ $t('message.portal.activeTickets') }}</span>
          </div>
          <div class="portal-stat-divider" />
          <div class="portal-stat-item">
            <span class="portal-stat-value">{{ stats.execution_stats?.running ?? '--' }}</span>
            <span class="portal-stat-label">{{ $t('message.portal.runningJobs') }}</span>
          </div>
          <div class="portal-stat-divider" />
          <div class="portal-stat-item">
            <span class="portal-stat-value" :class="{ 'text-danger': stats.incident_stats?.overdue > 0 }">{{ stats.incident_stats?.overdue ?? '--' }}</span>
            <span class="portal-stat-label">{{ $t('message.portal.slaViolation') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="portal-body">

      <!-- Quick Stats Cards -->
      <div class="portal-quick-stats g-fade-in-up">
        <div v-for="(s, si) in quickStats" :key="s.key" class="portal-qstat-card" :style="{ '--qstat-color': s.color, '--qstat-bg': s.bg, '--i': si }">
          <div class="portal-qstat-icon"><el-icon :size="22"><component :is="s.icon" /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value" :class="{ 'text-danger': s.danger }">{{ s.label }}</div>
            <div class="portal-qstat-num">{{ s.value }}</div>
          </div>
        </div>
      </div>

      <!-- Two-column layout -->
      <div class="portal-grid-2col">

        <!-- Left: My Tasks -->
        <div class="portal-card g-fade-in-up">
          <div class="portal-card-header">
            <div class="portal-card-header-left">
              <el-icon size="15" color="#409EFF"><List /></el-icon>
              <span class="portal-card-title">{{ $t('message.portal.myTasks') }}</span>
              <el-tag v-if="tasks.length > 0" size="small" type="primary" effect="plain" class="portal-card-count">{{ tasks.length }}</el-tag>
            </div>
            <el-button text size="small" @click="$router.push('/apps/itsm')">
              {{ $t('message.portal.viewAll') }} <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
          <el-table :data="tasks" v-loading="loadingTasks" stripe style="width:100%" size="small"
            :empty-text="loadingTasks ? $t('message.portal.loading') : $t('message.portal.noTasks')"
            @row-click="(row: any) => handleTaskClick(row)">
            <el-table-column :label="$t('message.portal.type')" width="90">
              <template #default="{ row }">
                <span class="portal-type-badge" :class="'portal-type-' + (row.type || 'incident')">
                  {{ $t('message.portal.types.' + (row.type === 'incident' ? 'incident' : row.type === 'approval' ? 'approval' : row.type === 'execution_approval' ? 'executionApproval' : 'change')) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="id" :label="$t('message.portal.ticketId')" width="110" />
            <el-table-column prop="title" :label="$t('message.portal.titleLabel')" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" :label="$t('message.portal.priority')" width="80">
              <template #default="{ row }">
                <span class="portal-prio-badge" :class="'portal-prio-' + (row.priority || '').toLowerCase()" v-if="row.priority">{{ row.priority }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('message.portal.status')" width="100">
              <template #default="{ row }">
                <span class="portal-status-badge" :class="'portal-status-' + row.status">
                  <span class="portal-status-dot" />{{ row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('message.portal.createdAt')" width="160" />
          </el-table>
        </div>

        <!-- Right: Recent Activity -->
        <div class="portal-card g-fade-in-up">
          <div class="portal-card-header">
            <div class="portal-card-header-left">
              <el-icon size="15" color="#E6A23C"><Timer /></el-icon>
              <span class="portal-card-title">{{ $t('message.portal.recentActivity') }}</span>
            </div>
            <el-button text size="small" :icon="Refresh" @click="loadRecentActivity">{{ $t("message.common.refresh") || '' }}</el-button>
          </div>
          <div class="portal-activity-list" v-loading="loadingActivity">
            <div v-if="activities.length === 0 && !loadingActivity" class="portal-empty">{{ $t('message.portal.noActivity') }}</div>
            <div v-for="(act, ai) in activities" :key="act.type + '-' + act.id"
              class="portal-activity-item g-stagger-item"
              :style="{ animationDelay: `${ai * 0.06}s` }"
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
      <div class="portal-card g-fade-in-up" v-if="favorites.templates?.length > 0 || favorites.recent_actions?.length > 0">
        <div class="portal-card-header">
          <div class="portal-card-header-left">
            <el-icon size="15" color="#E6A23C"><StarFilled /></el-icon>
            <span class="portal-card-title">{{ $t('message.portal.favorites') }}</span>
          </div>
          <el-button text size="small" @click="$router.push('/apps/opsflow')">
            {{ $t('message.portal.manageTemplates') }} <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="portal-favorites-body">
          <div class="portal-fav-section" v-if="favorites.templates?.length > 0">
            <div class="portal-fav-label">
              <el-icon size="12"><StarFilled /></el-icon>
              {{ $t('message.portal.favTemplates') }}
            </div>
            <div class="portal-fav-items">
              <div v-for="(tpl, ti) in favorites.templates" :key="'tpl-' + tpl.id"
                class="portal-fav-item g-stagger-item"
                :style="{ animationDelay: `${ti * 0.06}s` }"
                @click="$router.push(tpl.url)">
                <el-icon><StarFilled /></el-icon>
                <span class="portal-fav-name">{{ tpl.name }}</span>
                <span class="portal-fav-category" v-if="tpl.category">{{ tpl.category }}</span>
              </div>
            </div>
          </div>
          <div class="portal-fav-section" v-if="favorites.recent_actions?.length > 0">
            <div class="portal-fav-label">
              <el-icon size="12"><Clock /></el-icon>
              {{ $t('message.portal.recentActions') }}
            </div>
            <div class="portal-fav-items">
              <div v-for="(act, ai) in favorites.recent_actions" :key="'act-' + act.id"
                class="portal-fav-item g-stagger-item"
                :style="{ animationDelay: `${ai * 0.06}s` }">
                <el-icon><Clock /></el-icon>
                <span class="portal-fav-name">{{ act.action || '' }}</span>
                <span class="portal-fav-time">{{ formatTime(act.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Module Health & Quick Actions -->
      <div class="portal-grid-2col">
        <!-- Module Health -->
        <div class="portal-card g-fade-in-up" v-if="Object.keys(moduleCounts).length > 0">
          <div class="portal-card-header">
            <div class="portal-card-header-left">
              <el-icon size="15" color="#67C23A"><Monitor /></el-icon>
              <span class="portal-card-title">{{ $t('message.portal.systemOverview') }}</span>
            </div>
          </div>
          <div class="portal-health-body">
            <div v-for="(count, key) in moduleCounts" :key="key" class="portal-health-item g-stagger-item" :style="{ animationDelay: `${Object.keys(moduleCounts).indexOf(key) * 0.06}s` }">
              <span class="portal-health-icon">{{ formatModuleIcon(key) }}</span>
              <div class="portal-health-info">
                <span class="portal-health-label">{{ formatModuleName(key) }}</span>
                <span class="portal-health-value" :class="{ 'text-muted': count === 0 }">{{ count }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="portal-card g-fade-in-up">
          <div class="portal-card-header">
            <div class="portal-card-header-left">
              <el-icon size="15" color="#409EFF"><Lightning /></el-icon>
              <span class="portal-card-title">{{ $t('message.portal.quickActions') }}</span>
            </div>
          </div>
          <div class="portal-actions-body">
            <el-button type="primary" size="default" class="portal-action-btn" @click="$router.push('/apps/itsm')">
              <el-icon><Plus /></el-icon> {{ $t('message.portal.createTicket') }}
            </el-button>
            <el-button size="default" class="portal-action-btn" @click="$router.push('/apps/opsflow')">
              <el-icon><CaretRight /></el-icon> {{ $t('message.portal.executePipeline') }}
            </el-button>
            <el-button size="default" class="portal-action-btn" @click="$router.push('/apps/cmdb')">
              <el-icon><Monitor /></el-icon> {{ $t('message.portal.viewCmdb') }}
            </el-button>
            <el-button size="default" class="portal-action-btn" @click="$router.push('/apps/monitor')">
              <el-icon><WarningFilled /></el-icon> {{ $t('message.portal.alertCenter') }}
            </el-button>
            <el-button size="default" class="portal-action-btn" @click="$router.push('/apps/job-platform')">
              <el-icon><Tools /></el-icon> {{ $t('message.portal.jobPlatform') }}
            </el-button>
            <el-button size="default" class="portal-action-btn" @click="$router.push('/open-api')">
              <el-icon><Connection /></el-icon> {{ $t('message.portal.apiManagement') }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { i18n } from '/@/i18n/index'
import { GetDashboard, GetMyTasks, GetRecentActivity, GetFavorites } from '/@/api/portal/index'
import {
  WarningFilled, List, Monitor, Clock, Plus, CaretRight,
  Folder, Warning, StarFilled, Tools, Connection,
  ArrowRight, Refresh, Lightning, Timer,
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

// Quick stats card definitions / 快捷统计卡片定义
const t = (k: string) => i18n.global.t(k)
const quickStats = computed(() => [
  { key: 'alerts', value: stats.value.alerts?.firing ?? '--', label: t('message.portal.alertsFiring'), icon: WarningFilled, color: '#F56C6C', bg: '#fef0f0', danger: (stats.value.alerts?.firing ?? 0) > 0 },
  { key: 'tickets', value: stats.value.itsm_ticket_stats?.running ?? stats.value.incidents?.open ?? '--', label: t('message.portal.activeTickets'), icon: List, color: '#E6A23C', bg: '#fdf6ec' },
  { key: 'exec', value: stats.value.execution_stats?.running ?? '--', label: t('message.portal.runningJobs'), icon: Monitor, color: '#67C23A', bg: '#f0f9eb' },
  { key: 'sla', value: stats.value.incident_stats?.overdue ?? '--', label: t('message.portal.slaViolation'), icon: Timer, color: '#409EFF', bg: '#ecf5ff', danger: (stats.value.incident_stats?.overdue ?? 0) > 0 },
  { key: 'tpl', value: stats.value.opsflow_template_stats?.published ?? '--', label: t('message.portal.publishedTemplates'), icon: Folder, color: '#909399', bg: '#f5f7fa' },
  { key: 'fail', value: stats.value.execution_stats?.failed_today ?? '--', label: t('message.portal.failedToday'), icon: Warning, color: '#F56C6C', bg: '#fef0f0', danger: (stats.value.execution_stats?.failed_today ?? 0) > 0 },
])

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
  const t = (k: string) => i18n.global.t(k)
  return t(`message.portal.moduleNames.${key}`) || key
}

function formatModuleIcon(key: string): string {
  const map: Record<string, string> = {
    itsm_tickets: '📋',
    opsflow_templates: '📁',
    opsflow_executions: '⚡',
    cmdb_hosts: '🖥',
    incidents: '🚨',
    alerts: '🔔',
  }
  return map[key] || '📊'
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
    ElMessage.info({ message: t('message.portal.tourMessage'), duration: 1500 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.portal-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: $g-bg-page; overflow: hidden;
}

/* ===== Hero — dark gradient (matching ITSM pattern) ===== */
.portal-hero { @include g-hero-container; }
.portal-hero-bg { @include g-hero-bg-dots; }
.portal-hero-inner { @include g-hero-inner; }
.portal-hero-left { flex: 0 0 auto; }
.portal-hero-title { @include g-hero-title; white-space: nowrap; }
.portal-hero-user { font-weight: 400; font-size: 16px; color: rgba(255,255,255,0.55); }
.portal-hero-subtitle { @include g-hero-subtitle; white-space: nowrap; }
.portal-hero-spacer { flex: 1; }
.portal-hero-stats { flex: 0 0 auto; display: flex; align-items: center; gap: 0; }
.portal-stat-item { text-align: center; padding: 0 14px; }
.portal-stat-value { @include g-hero-stat-value; }
.portal-stat-label { @include g-hero-stat-label; }
.portal-stat-divider { @include g-hero-stat-divider; }

/* ===== Body ===== */
.portal-body {
  flex: 1; overflow-y: auto;
  padding: 20px 32px 32px;
  box-sizing: border-box;
  display: flex; flex-direction: column; gap: 16px;
}

/* ===== Quick Stats ===== */
.portal-quick-stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
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
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: $g-shadow-card;
  border: 1px solid $g-border-card;
  position: relative;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  // Gradient accent line on hover (matching opsflow-dashboard pattern) / 悬停时渐变色描边
  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--qstat-color);
    opacity: 0;
    transition: opacity 0.25s;
  }
  &:hover {
    transform: translateY(-2px);
    box-shadow: $g-shadow-hover;
    border-color: transparent;
    &::before { opacity: 1; }
  }
}
.portal-qstat-icon {
  width: 40px; height: 40px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--qstat-bg);
  color: var(--qstat-color);
  flex-shrink: 0;
}
.portal-qstat-body { flex: 1; display: flex; flex-direction: column; }
.portal-qstat-value { font-size: 11px; color: $g-text-muted; order: 2; margin-top: 2px; }
.portal-qstat-num { font-size: 22px; font-weight: 700; line-height: 1.2; color: $g-text-primary; order: 1; }

/* ===== Card (standard OPSflow card with header/body) ===== */
.portal-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: $g-shadow-card;
  border: 1px solid $g-border-card;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    box-shadow: $g-shadow-hover;
    border-color: transparent;
  }
}
.portal-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid $g-border-light;
}
.portal-card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.portal-card-title {
  font-size: 14px;
  font-weight: 600;
  color: $g-text-primary;
}
.portal-card-count {
  font-weight: 600;
}
.portal-card :deep(.el-table th.el-table__cell) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
  font-size: 12px;
}
.portal-card :deep(.el-table__body tr:hover td) {
  background: #f5f7fa;
  cursor: pointer;
}
.portal-card :deep(.el-table__empty-text) {
  padding: 24px 0;
}
.portal-card :deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: #fafbfc;
}
.portal-card :deep(.el-table) {
  border-top: none;
}

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

/* ===== Two-column Grid ===== */
.portal-grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 800px) {
  .portal-grid-2col { grid-template-columns: 1fr; }
}

/* ===== Activity List ===== */
.portal-activity-list {
  padding: 4px 0;
  max-height: 420px;
  overflow-y: auto;
}
.portal-empty { text-align: center; padding: 40px 0; color: $g-text-placeholder; font-size: 13px; }
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
.portal-activity-title { font-size: 13px; font-weight: 500; color: $g-text-primary; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
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
.portal-fav-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: $g-text-muted; margin-bottom: 8px;
  .el-icon { font-size: 13px; color: $g-text-placeholder; }
}
.portal-fav-items { display: flex; flex-wrap: wrap; gap: 8px; }
.portal-fav-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: $g-bg-card;
  border: 1px solid $g-border-card;
  cursor: pointer;
  font-size: 13px;
  color: $g-text-primary;
  transition: all 0.2s;
}
.portal-fav-item:hover {
  background: $g-bg-light-blue;
  border-color: $g-border-blue;
  color: $g-color-primary;
  transform: translateY(-1px);
}
.portal-fav-item .el-icon { font-size: 14px; color: #E6A23C; }
.portal-fav-category { font-size: 11px; color: $g-text-placeholder; margin-left: 4px; }
.portal-fav-time { font-size: 11px; color: $g-text-placeholder; margin-left: 4px; }

/* ===== Health ===== */
.portal-health-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 20px 16px;
}
.portal-health-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background: $g-bg-card;
  transition: background 0.2s;
}
.portal-health-item:hover { background: $g-bg-card-hover; }
.portal-health-icon { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; }
.portal-health-info {
  display: flex;
  align-items: center;
  flex: 1;
}
.portal-health-label { font-size: 13px; color: $g-text-secondary; }
.portal-health-value {
  font-size: 16px; font-weight: 700;
  color: $g-text-primary;
  margin-left: auto;
  padding: 1px 10px;
  border-radius: 6px;
  background: #fff;
}
.portal-health-value.text-muted { color: $g-text-placeholder; background: transparent; }

/* ===== Actions Body ===== */
.portal-actions-body {
  display: flex; gap: 10px; padding: 14px 20px 18px; flex-wrap: wrap;
}
.portal-action-btn {
  transition: all 0.2s;
  &:hover {
    transform: translateY(-1px);
  }
}

/* ===== Scrollbar ===== */
.portal-body::-webkit-scrollbar { width: 4px; }
.portal-body::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 2px; }
.portal-body::-webkit-scrollbar-track { background: transparent; }

.portal-activity-list::-webkit-scrollbar { width: 3px; }
.portal-activity-list::-webkit-scrollbar-thumb { background: #e0e2e6; border-radius: 2px; }
.portal-activity-list::-webkit-scrollbar-track { background: transparent; }

/* ===== Utilities ===== */
.text-danger { color: #F56C6C; }
.text-success { color: #67C23A; }
.text-muted { color: $g-text-placeholder; }
</style>
