<template>
  <div class="portal-page">
    <!-- ===== Hero Section ===== -->
    <div class="portal-hero">
      <div class="portal-hero-bg" />
      <div class="portal-hero-inner">
        <div class="portal-hero-content">
          <div class="portal-hero-welcome">
            <h1 class="portal-hero-title">运维工作台</h1>
            <p class="portal-hero-subtitle">Welcome back — 这里聚合了你的待办、系统概览和快捷操作</p>
          </div>
          <div class="portal-hero-stats">
            <div class="portal-stat-item">
              <span class="portal-stat-value" :class="{ 'text-danger': stats.alerts?.firing > 0 }">{{ stats.alerts?.firing ?? '--' }}</span>
              <span class="portal-stat-label">告警中</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value">{{ stats.incidents?.open ?? '--' }}</span>
              <span class="portal-stat-label">开放工单</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value">{{ stats.executions?.running ?? '--' }}</span>
              <span class="portal-stat-label">执行中</span>
            </div>
            <div class="portal-stat-divider" />
            <div class="portal-stat-item">
              <span class="portal-stat-value" :class="{ 'text-danger': stats.incidents?.overdue > 0 }">{{ stats.incidents?.overdue ?? '--' }}</span>
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
          <div class="portal-qstat-trend" v-if="stats.alerts?.trend !== undefined">
            <span :class="stats.alerts.trend >= 0 ? 'text-danger' : 'text-success'">
              {{ stats.alerts.trend >= 0 ? '+' : '' }}{{ stats.alerts.trend }}
            </span>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #E6A23C; --qstat-bg: #fdf6ec;">
          <div class="portal-qstat-icon"><el-icon :size="22"><List /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.incidents?.open ?? '--' }}</div>
            <div class="portal-qstat-label">开放工单</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #67C23A; --qstat-bg: #f0f9eb;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Monitor /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value">{{ stats.executions?.running ?? '--' }}</div>
            <div class="portal-qstat-label">执行中作业</div>
          </div>
        </div>
        <div class="portal-qstat-card" style="--qstat-color: #409EFF; --qstat-bg: #ecf5ff;">
          <div class="portal-qstat-icon"><el-icon :size="22"><Clock /></el-icon></div>
          <div class="portal-qstat-body">
            <div class="portal-qstat-value" :class="{ 'text-danger': stats.incidents?.overdue > 0 }">{{ stats.incidents?.overdue ?? '--' }}</div>
            <div class="portal-qstat-label">SLA 违例</div>
          </div>
        </div>
      </div>

      <!-- My Tasks -->
      <div class="portal-table-card of-fade-in-up">
        <div class="portal-table-header">
          <span class="portal-table-title">我的待办</span>
          <el-button link type="primary" size="small" @click="$router.push('/apps/itsm')">查看全部</el-button>
        </div>
        <el-table :data="tasks" v-loading="loadingTasks" stripe style="width:100%" size="small"
          :empty-text="loadingTasks ? '加载中...' : '暂无待办事项'">
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <span class="portal-type-badge" :class="'portal-type-' + (row.type || 'incident')">
                {{ row.type === 'incident' ? '工单' : '变更' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="编号" width="130" />
          <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="90">
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
          <el-table-column prop="created_at" label="创建时间" width="170" />
        </el-table>
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
          <el-button size="default" @click="$router.push('/apps/job-platform')">
            <el-icon><CaretRight /></el-icon> 执行作业
          </el-button>
          <el-button size="default" @click="$router.push('/apps/cmdb')">
            <el-icon><Monitor /></el-icon> 查看 CMDB
          </el-button>
          <el-button size="default" @click="$router.push('/apps/monitor')">
            <el-icon><WarningFilled /></el-icon> 告警中心
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { GetDashboard, GetMyTasks, GetQuickStats } from '/@/api/portal/index'
import { WarningFilled, List, Monitor, Clock, Plus, CaretRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const loadingTasks = ref(false)
const stats = ref<any>({})
const tasks = ref<any[]>([])

onMounted(async () => {
  try {
    const [dash, taskRes] = await Promise.all([
      GetDashboard(),
      GetMyTasks(),
    ])
    stats.value = dash.data || {}
    tasks.value = taskRes.data || []
  } catch { /* modules not ready */ }

  const key = 'opsflow_tour_portal'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🏠 运维工作台 — 一站式总览告警、工单、作业状态，快速跳转各子系统', duration: 6000 })
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
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.portal-qstat-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: $of-shadow-card;
  @include of-hover-lift;
  position: relative;
}
.portal-qstat-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--qstat-bg);
  color: var(--qstat-color);
  flex-shrink: 0;
}
.portal-qstat-body { flex: 1; }
.portal-qstat-value { font-size: 26px; font-weight: 700; line-height: 1.2; color: $of-text-primary; }
.portal-qstat-label { font-size: 12px; color: $of-text-muted; margin-top: 2px; }
.portal-qstat-trend {
  position: absolute; top: 12px; right: 14px;
  font-size: 12px; font-weight: 600;
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
.portal-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
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
.portal-status-pending .portal-status-dot { background: #E6A23C; }
.portal-status-open { background: #fdf6ec; color: #E6A23C; }
.portal-status-pending { background: #fdf6ec; color: #E6A23C; }
.portal-status-resolved .portal-status-dot,
.portal-status-completed .portal-status-dot { background: #67C23A; }
.portal-status-resolved { background: #f0f9eb; color: #67C23A; }
.portal-status-completed { background: #f0f9eb; color: #67C23A; }
.portal-status-closed .portal-status-dot { background: #909399; }
.portal-status-closed { background: #f5f7fa; color: #909399; }

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
</style>
