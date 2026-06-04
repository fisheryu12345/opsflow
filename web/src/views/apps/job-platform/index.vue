<template>
  <div class="job-platform-page">
    <!-- ===== Hero Section ===== -->
    <div class="job-hero">
      <div class="job-hero-bg" />
      <div class="job-hero-inner">
        <div class="job-hero-left">
          <h1 class="job-hero-title">作业平台</h1>
          <p class="job-hero-subtitle">Batch job execution & script management</p>
        </div>
        <div class="job-hero-center">
          <el-input v-model="searchQuery" placeholder="Search job, script..." clearable size="default"
            class="job-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="job-hero-stats">
          <div class="job-stat-item"><span class="job-stat-value">{{ jobs.length }}</span><span class="job-stat-label">Jobs</span></div>
          <div class="job-stat-divider" />
          <div class="job-stat-item"><span class="job-stat-value">{{ scripts.length }}</span><span class="job-stat-label">Scripts</span></div>
          <div class="job-stat-divider" />
          <div class="job-stat-item"><span class="job-stat-value">{{ runningExecs }}</span><span class="job-stat-label">Running</span></div>
          <div class="job-stat-divider" />
          <div class="job-stat-item"><span class="job-stat-value">{{ dangerousRules.length }}</span><span class="job-stat-label">Risky Rules</span></div>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="job-hero-tabs">
        <div class="job-hero-tab" :class="{ active: activeTab === 'run' }" @click="activeTab = 'run'">
          <el-icon><CaretRight /></el-icon> 作业执行
        </div>
        <div class="job-hero-tab" :class="{ active: activeTab === 'scripts' }" @click="activeTab = 'scripts'">
          <el-icon><Document /></el-icon> 脚本管理
        </div>
        <div class="job-hero-tab" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
          <el-icon><Timer /></el-icon> 执行记录
        </div>
        <div class="job-hero-tab" :class="{ active: activeTab === 'dangerous' }" @click="activeTab = 'dangerous'">
          <el-icon><WarningFilled /></el-icon> 高危命令规则
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="job-body">

      <!-- ── Run Jobs ── -->
      <div v-show="activeTab === 'run'" class="job-section of-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">执行作业</span>
            <el-button type="primary" size="small" @click="showCreateJob = true">
              <el-icon><Plus /></el-icon> 新建作业
            </el-button>
          </div>
          <el-table :data="filteredJobs" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无作业'">
            <el-table-column prop="name" label="作业名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="executor" label="执行方式" width="120" />
            <el-table-column prop="timeout_seconds" label="超时(s)" width="90" />
            <el-table-column prop="need_approval" label="需要审批" width="100" align="center">
              <template #default="{ row }"><el-tag v-if="row.need_approval" type="warning" size="small">是</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" text @click="runJob(row)">
                  <el-icon><CaretRight /></el-icon> 执行
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Scripts ── -->
      <div v-show="activeTab === 'scripts'" class="job-section of-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">脚本管理</span>
            <el-button type="primary" size="small" @click="showCreateScript = true">
              <el-icon><Plus /></el-icon> 新建脚本
            </el-button>
          </div>
          <el-table :data="filteredScripts" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无脚本'">
            <el-table-column prop="name" label="脚本名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="script_type" label="类型" width="100" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="is_public" label="公开" width="80" align="center">
              <template #default="{ row }"><el-tag v-if="row.is_public" size="small" type="success">公开</el-tag></template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Execution History ── -->
      <div v-show="activeTab === 'history'" class="job-section of-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">执行记录</span>
            <el-button :icon="Refresh" text size="small" @click="loadData" :loading="loading">刷新</el-button>
          </div>
          <el-table :data="executions" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无执行记录'">
            <el-table-column prop="job_name" label="作业" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="job-status-badge" :class="'job-status-' + row.status">
                  <span class="job-status-dot" />{{ statusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="result_summary" label="结果摘要" min-width="200" show-overflow-tooltip />
            <el-table-column prop="started_at" label="开始时间" width="170" />
            <el-table-column prop="finished_at" label="完成时间" width="170" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status==='running'||row.status==='pending'" size="small" text type="danger" @click="cancelExec(row)">
                  <el-icon><Close /></el-icon> 取消
                </el-button>
                <el-button size="small" text type="primary" @click="showLog(row)">
                  <el-icon><Document /></el-icon> 日志
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Dangerous Rules ── -->
      <div v-show="activeTab === 'dangerous'" class="job-section of-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">高危命令规则</span>
          </div>
          <el-table :data="dangerousRules" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无高危命令规则'">
            <el-table-column prop="name" label="规则名称" min-width="180" />
            <el-table-column prop="pattern" label="匹配模式" min-width="200" show-overflow-tooltip />
            <el-table-column prop="action" label="处理方式" width="120" />
            <el-table-column prop="severity" label="级别" width="80">
              <template #default="{ row }">
                <span class="job-severity-badge" :class="'job-severity-' + (row.severity || '').toLowerCase()">{{ row.severity }}</span>
              </template>
            </el-table-column>
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
import { ref, computed, onMounted } from 'vue'
import { jobApi, scriptApi, executionApi, dangerousRuleApi, RunJob, CancelExecution, GetExecutionLog } from '/@/api/job-platform/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CaretRight, Document, Timer, WarningFilled, Search, Plus, Refresh, Close } from '@element-plus/icons-vue'

const activeTab = ref('run')
const searchQuery = ref('')
const loading = ref(false)
const jobs = ref<any[]>([])
const scripts = ref<any[]>([])
const executions = ref<any[]>([])
const dangerousRules = ref<any[]>([])
const showCreateJob = ref(false)
const showCreateScript = ref(false)

const runningExecs = computed(() => executions.value.filter(e => e.status === 'running').length)

const filteredJobs = computed(() => {
  if (!searchQuery.value) return jobs.value
  const q = searchQuery.value.toLowerCase()
  return jobs.value.filter(j => j.name?.toLowerCase().includes(q))
})

const filteredScripts = computed(() => {
  if (!searchQuery.value) return scripts.value
  const q = searchQuery.value.toLowerCase()
  return scripts.value.filter(s => s.name?.toLowerCase().includes(q))
})

function onSearch() {
  // Reactive via computed
}

function statusLabel(s: string) {
  const map: Record<string, string> = { success: '成功', running: '运行中', failed: '失败', pending: '等待', cancelled: '已取消' }
  return map[s] || s || '未知'
}

async function loadData() {
  loading.value = true
  try {
    const [j, s, e, d] = await Promise.all([
      jobApi.list(), scriptApi.list(), executionApi.list(), dangerousRuleApi.list(),
    ])
    jobs.value = j.data || []
    scripts.value = s.data || []
    executions.value = e.data || []
    dangerousRules.value = d.data || []
  } finally { loading.value = false }
}

async function runJob(row: any) {
  const { value } = await ElMessageBox.prompt('输入目标主机(逗号分隔)', '执行作业')
  const hosts = value.split(',').map((h: string) => h.trim()).filter(Boolean)
  await RunJob(row.id, hosts)
  ElMessage.success('作业已提交执行')
}

async function cancelExec(row: any) { await CancelExecution(row.id); ElMessage.success('已取消'); await loadData() }
async function showLog(row: any) { const res = await GetExecutionLog(row.id); ElMessage.info(JSON.stringify(res.data)) }

onMounted(async () => {
  await loadData()

  const key = 'opsflow_tour_job_platform'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '⚡ 作业平台 — 批量命令执行、脚本管理与高危命令拦截', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../opsflow/styles/opsflow-global' as *;

.job-platform-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.job-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a2e1a 0%, #163e16 50%, #1a4a1a 100%);
}
.job-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.job-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.job-hero-left { flex: 0 0 auto; }
.job-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.job-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.job-hero-center { flex: 1 1 auto; min-width: 0; max-width: 360px; }
.job-search-input { width: 100%; }
.job-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none; border-radius: 10px; padding: 2px 12px;
}
.job-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.job-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.job-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.job-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.job-stat-item { text-align: center; padding: 0 14px; }
.job-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.job-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.job-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.job-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.job-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.job-hero-tab:hover { color: rgba(255,255,255,0.9); }
.job-hero-tab.active { color: #fff; border-bottom-color: #67C23A; }

/* ===== Body ===== */
.job-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.job-section { padding-top: 16px; }

/* ===== Table Card ===== */
.job-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.job-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.job-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.job-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.job-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }

/* ===== Status Badge ===== */
.job-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.job-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.job-status-success .job-status-dot { background: #67C23A; }
.job-status-success { background: #f0f9eb; color: #67C23A; }
.job-status-running .job-status-dot { background: #409EFF; }
.job-status-running { background: #ecf5ff; color: #409EFF; }
.job-status-failed .job-status-dot { background: #F56C6C; }
.job-status-failed { background: #fef0f0; color: #F56C6C; }
.job-status-pending .job-status-dot { background: #E6A23C; }
.job-status-pending { background: #fdf6ec; color: #E6A23C; }
.job-status-cancelled .job-status-dot { background: #909399; }
.job-status-cancelled { background: #f5f7fa; color: #909399; }

/* ===== Severity Badge ===== */
.job-severity-badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px;
}
.job-severity-high,
.job-severity-critical { background: #fef0f0; color: #F56C6C; }
.job-severity-medium { background: #fdf6ec; color: #E6A23C; }
.job-severity-low { background: #f0f9eb; color: #67C23A; }
</style>
