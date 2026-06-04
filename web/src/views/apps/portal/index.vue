<template>
  <div class="portal-page">
    <!-- Welcome -->
    <div class="portal-welcome of-card">
      <h1 class="portal-title">运维工作台</h1>
      <p class="portal-subtitle">Welcome back — 这里聚合了你的待办、系统概览和快捷操作</p>
    </div>

    <!-- Quick Stats -->
    <div class="portal-stats">
      <div class="portal-stat-card">
        <div class="stat-icon" style="background:#fef0f0;color:#f56c6c;">
          <el-icon :size="24"><WarningFilled /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.alerts?.firing ?? '--' }}</div>
          <div class="stat-label">进行中告警</div>
        </div>
      </div>
      <div class="portal-stat-card">
        <div class="stat-icon" style="background:#fdf6ec;color:#e6a23c;">
          <el-icon :size="24"><List /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.incidents?.open ?? '--' }}</div>
          <div class="stat-label">开放工单</div>
        </div>
      </div>
      <div class="portal-stat-card">
        <div class="stat-icon" style="background:#f0f9eb;color:#67c23a;">
          <el-icon :size="24"><Monitor /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.executions?.running ?? '--' }}</div>
          <div class="stat-label">执行中作业</div>
        </div>
      </div>
      <div class="portal-stat-card">
        <div class="stat-icon" style="background:#ecf5ff;color:#409eff;">
          <el-icon :size="24"><Clock /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.incidents?.overdue ?? '--' }}</div>
          <div class="stat-label">SLA 违例</div>
        </div>
      </div>
    </div>

    <!-- My Tasks -->
    <div class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">我的待办</h3>
        <el-button link type="primary" @click="$router.push('/apps/itsm')">查看全部</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="tasks" v-loading="loadingTasks" stripe>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.type === 'incident' ? 'danger' : 'warning'" size="small">
                {{ row.type === 'incident' ? '工单' : '变更' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="编号" width="130" />
          <el-table-column prop="title" label="标题" min-width="220" />
          <el-table-column prop="priority" label="优先级" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.priority" :type="row.priority==='P1'?'danger':'warning'" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="170" />
        </el-table>
        <el-empty v-if="!loadingTasks && tasks.length === 0" description="暂无待办事项" />
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="of-card" style="margin-top:16px;">
      <div class="of-card-header"><h3 class="of-card-title">快捷操作</h3></div>
      <div class="of-card-body" style="display:flex;gap:12px;">
        <el-button type="primary" @click="$router.push('/apps/itsm')">创建工单</el-button>
        <el-button @click="$router.push('/apps/job-platform')">执行作业</el-button>
        <el-button @click="$router.push('/apps/cmdb')">查看 CMDB</el-button>
        <el-button @click="$router.push('/apps/monitor')">告警中心</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { GetDashboard, GetMyTasks, GetQuickStats } from '/@/api/portal/index'
import { WarningFilled, List, Monitor, Clock } from '@element-plus/icons-vue'

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
})
</script>

<style scoped>
.portal-page { padding: 20px; max-width: 1200px; margin: 0 auto; }
.portal-welcome { padding: 32px; margin-bottom: 24px; }
.portal-title { font-size: 24px; font-weight: 700; margin: 0; }
.portal-subtitle { color: #8b949e; margin: 8px 0 0; }
.portal-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.portal-stat-card { background: #fff; border-radius: 8px; padding: 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-label { color: #8b949e; font-size: 13px; margin-top: 2px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
