<template>
  <div class="job-platform-page">
    <!-- ===== Hero ===== -->
    <div class="job-hero">
      <div class="job-hero-bg" />
      <div class="job-hero-inner">
        <div class="job-hero-left">
          <h1 class="job-hero-title">作业平台</h1>
          <p class="job-hero-subtitle">Batch job execution &amp; script management</p>
        </div>
        <div class="job-hero-center">
          <el-input v-model="searchQuery" placeholder="Search job, script, template..." clearable size="default"
            class="job-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="job-hero-stats">
          <div class="job-stat-item"><span class="job-stat-value">{{ scripts.length }}</span><span class="job-stat-label">Scripts</span></div>
          <div class="job-stat-divider" />
          <div class="job-stat-item"><span class="job-stat-value">{{ templates.length }}</span><span class="job-stat-label">Templates</span></div>
          <div class="job-stat-divider" />
          <div class="job-stat-item"><span class="job-stat-value">{{ runningCount }}</span><span class="job-stat-label">Running</span></div>
        </div>
      </div>
      <div class="job-hero-tabs">
        <div v-for="tab in tabs" :key="tab.key" class="job-hero-tab"
          :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
          <el-icon><component :is="tab.icon" /></el-icon> {{ tab.label }}
        </div>
      </div>
    </div>

    <div class="job-body">
      <!-- ─── Tab 1: 快速执行 ─── -->
      <div v-show="activeTab === 'quick'" class="job-section g-fade-in-up">
        <div class="job-quick-grid">
          <div class="job-table-card">
            <div class="job-table-header"><span class="job-table-title">快速执行脚本</span></div>
            <div style="padding:16px;">
              <el-select v-model="quickScriptRef" placeholder="引用脚本库" style="width:100%;margin-bottom:12px;" size="small"
                filterable clearable @change="loadQuickScript">
                <el-option v-for="s in scripts" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
              <el-input v-model="quickContent" type="textarea" :rows="6" placeholder="#!/bin/bash&#10;echo hello" style="margin-bottom:12px;font-family:monospace;" />
              <el-input v-model="quickHosts" placeholder="目标主机 IP（逗号分隔）" style="margin-bottom:12px;" size="small" />
              <el-select v-model="quickExecutor" style="width:150px;margin-right:8px;" size="small">
                <el-option label="SSH" value="ssh" />
                <el-option label="Ansible" value="ansible" />
                <el-option label="Local" value="local" />
              </el-select>
              <el-button type="primary" size="small" :loading="quickRunning" @click="doQuickExec">执行</el-button>
            </div>
          </div>
          <div class="job-table-card">
            <div class="job-table-header"><span class="job-table-title">结果</span></div>
            <div style="padding:16px;max-height:400px;overflow:auto;">
              <pre v-if="quickResult" style="font-size:12px;margin:0;white-space:pre-wrap;">{{ quickResult }}</pre>
              <span v-else style="color:#909399;">执行结果将显示在此处</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 2: 模板管理 ─── -->
      <div v-show="activeTab === 'templates'" class="job-section g-fade-in-up">
        <div class="job-tpl-layout">
          <div class="job-tpl-sidebar">
            <div class="job-table-card">
              <div class="job-table-header">
                <span class="job-table-title">模板</span>
                <el-button size="small" type="primary" @click="showAddTemplate = true"><el-icon><Plus /></el-icon></el-button>
              </div>
              <el-table :data="filteredTemplates" v-loading="loading" size="small" stripe style="width:100%"
                highlight-current-row @row-click="selectTemplate">
                <el-table-column prop="name" label="名称" min-width="140" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }"><el-tag :type="row.status==='published'?'success':'info'" size="small">{{ row.status }}</el-tag></template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          <div class="job-tpl-detail">
            <div v-if="selectedTemplate" class="job-table-card">
              <div class="job-table-header">
                <span class="job-table-title">{{ selectedTemplate.name }} — 步骤</span>
                <div style="display:flex;gap:8px;">
                  <el-button size="small" @click="publishTemplate" v-if="selectedTemplate.status==='draft'">发布</el-button>
                  <el-button size="small" type="primary" :icon="Plus" @click="showAddPlan = true">创建方案</el-button>
                </div>
              </div>
              <div style="padding:16px;">
                <div v-for="(step, i) in templateSteps" :key="step.id" class="job-step-item">
                  <div class="job-step-index">{{ i + 1 }}</div>
                  <div class="job-step-info">
                    <span class="job-step-name">{{ step.name || '未命名步骤' }}</span>
                    <el-tag size="small">{{ step.type }}</el-tag>
                  </div>
                  <div class="job-step-actions">
                    <el-button size="small" text @click="editStep(step)"><el-icon><Edit /></el-icon></el-button>
                  </div>
                </div>
                <div v-if="!templateSteps.length" style="color:#909399;text-align:center;padding:20px;">暂无步骤</div>
              </div>
            </div>
            <div v-else class="job-empty"><el-icon :size="48" color="#dcdfe6"><List /></el-icon><p>请选择一个模板</p></div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 3: 脚本管理 ─── -->
      <div v-show="activeTab === 'scripts'" class="job-section g-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">脚本库</span>
            <el-button type="primary" size="small" @click="showAddScript = true"><el-icon><Plus /></el-icon> 新建</el-button>
          </div>
          <el-table :data="filteredScripts" v-loading="loading" stripe size="small" style="width:100%">
            <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="script_type" label="类型" width="100" />
            <el-table-column prop="current_version" label="版本" width="80" />
            <el-table-column prop="category" label="分类" width="80" />
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" text @click="viewScript(row)"><el-icon><View /></el-icon></el-button>
                <el-button size="small" text @click="editScript(row)"><el-icon><Edit /></el-icon></el-button>
                <el-button size="small" text @click="showPublishDialog(row)"><el-icon><Top /></el-icon></el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ─── Tab 4: 执行记录 ─── -->
      <div v-show="activeTab === 'history'" class="job-section g-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">执行记录</span>
            <el-button :icon="Refresh" text size="small" @click="loadExecutions" :loading="loading">刷新</el-button>
          </div>
          <el-table :data="executions" v-loading="loading" stripe size="small" style="width:100%">
            <el-table-column label="ID" width="70" prop="id" />
            <el-table-column label="来源" min-width="140">
              <template #default="{ row }">{{ row.plan?.name || row.template?.name || `#${row.id}` }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <span class="job-status-badge" :class="'job-status-' + row.status">
                  <span class="job-status-dot" />{{ statusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="result_summary" label="结果" min-width="180" show-overflow-tooltip />
            <el-table-column label="触发方式" width="100" prop="triggered_by" />
            <el-table-column label="耗时" width="80">
              <template #default="{ row }">{{ row.total_time ? row.total_time + 's' : '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="showExecDetail(row)"><el-icon><View /></el-icon> 详情</el-button>
                <el-button v-if="row.status==='running'||row.status==='pending'" size="small" text type="danger" @click="stopExec(row)">
                  <el-icon><Close /></el-icon> 停止
                </el-button>
                <el-button v-if="row.status==='failed'" size="small" text type="warning" @click="retryExec(row)">
                  <el-icon><Refresh /></el-icon> 重试
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ─── Tab 5: 账号管理 ─── -->
      <div v-show="activeTab === 'accounts'" class="job-section g-fade-in-up">
        <div class="job-table-card">
          <div class="job-table-header">
            <span class="job-table-title">执行账号</span>
            <el-button type="primary" :icon="Plus" size="small" @click="showAddAccount = true"><el-icon><Plus /></el-icon> 新增</el-button>
          </div>
          <el-table :data="accounts" v-loading="loading" stripe size="small" style="width:100%">
            <el-table-column prop="name" label="别名" width="140" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="protocol" label="协议" width="80" />
            <el-table-column prop="port" label="端口" width="60" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="scope" label="作用域" width="80" />
            <el-table-column prop="is_active" label="启用" width="70" align="center">
              <template #default="{ row }"><el-tag v-if="row.is_active" type="success" size="small">是</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" text @click="editAccount(row)"><el-icon><Edit /></el-icon></el-button>
                <el-button size="small" text type="danger" @click="deleteAccount(row)"><el-icon><Delete /></el-icon></el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ─── Tab 6: 高危规则 + 定时作业 ─── -->
      <div v-show="activeTab === 'settings'" class="job-section g-fade-in-up">
        <div class="job-settings-grid">
          <div class="job-table-card">
            <div class="job-table-header">
              <span class="job-table-title">高危命令规则</span>
              <el-button size="small" type="danger" @click="showAddRule = true"><el-icon><Plus /></el-icon> 新增</el-button>
            </div>
            <el-table :data="dangerousRules" size="small" stripe style="width:100%">
              <el-table-column prop="name" label="规则" min-width="140" />
              <el-table-column prop="pattern" label="模式" min-width="160" show-overflow-tooltip />
              <el-table-column prop="action" label="处理" width="80" />
              <el-table-column prop="severity" label="级别" width="70">
                <template #default="{ row }"><span class="job-severity-badge" :class="'job-severity-' + (row.severity||'').toLowerCase()">{{ row.severity }}</span></template>
              </el-table-column>
              <el-table-column label="启用" width="60" align="center">
                <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="toggleRule(row)" /></template>
              </el-table-column>
            </el-table>
          </div>
          <div class="job-table-card">
            <div class="job-table-header">
              <span class="job-table-title">定时作业</span>
              <el-button size="small" type="primary" :icon="Plus" @click="showAddCron = true"><el-icon><Plus /></el-icon> 新增</el-button>
            </div>
            <el-table :data="cronJobs" size="small" stripe style="width:100%">
              <el-table-column prop="name" label="名称" min-width="140" />
              <el-table-column prop="cron_expression" label="Cron" width="120" />
              <el-table-column label="状态" width="70" align="center">
                <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="toggleCron(row)" /></template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" text @click="runCronNow(row)"><el-icon><CaretRight /></el-icon></el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Dialogs ── -->
    <el-dialog v-model="showAddTemplate" title="新建模板" width="500px" destroy-on-close>
      <el-form :model="newTemplate" label-width="80" size="small">
        <el-form-item label="名称"><el-input v-model="newTemplate.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="newTemplate.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="newTemplate.category" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddTemplate = false">取消</el-button><el-button type="primary" :loading="saving" @click="doAddTemplate">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddScript" title="新建脚本" width="600px" destroy-on-close>
      <el-form :model="newScript" label-width="80" size="small">
        <el-form-item label="名称"><el-input v-model="newScript.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newScript.script_type" style="width:100%;">
            <el-option v-for="t in ['shell','python','powershell','bat','sql']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容"><el-input v-model="newScript.content" type="textarea" :rows="6" style="font-family:monospace;" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddScript = false">取消</el-button><el-button type="primary" :loading="saving" @click="doAddScript">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddAccount" title="新增账号" width="500px" destroy-on-close>
      <el-form :model="newAccount" label-width="80" size="small">
        <el-form-item label="别名"><el-input v-model="newAccount.name" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="newAccount.username" /></el-form-item>
        <el-form-item label="协议">
          <el-select v-model="newAccount.protocol" style="width:100%;">
            <el-option v-for="t in ['ssh','winrm','mysql','postgresql']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码"><el-input v-model="newAccount.password" type="password" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="newAccount.port" :min="1" :max="65535" style="width:100%;" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddAccount = false">取消</el-button><el-button type="primary" :loading="saving" @click="doAddAccount">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddRule" title="新增高危规则" width="500px" destroy-on-close>
      <el-form :model="newRule" label-width="80" size="small">
        <el-form-item label="名称"><el-input v-model="newRule.name" /></el-form-item>
        <el-form-item label="模式"><el-input v-model="newRule.pattern" placeholder="rm -rf" /></el-form-item>
        <el-form-item label="正则"><el-switch v-model="newRule.is_regex" /></el-form-item>
        <el-form-item label="处理">
          <el-select v-model="newRule.action" style="width:100%;">
            <el-option v-for="t in [{v:'reject',l:'拦截'},{v:'approval',l:'审批'},{v:'warn',l:'警告'}]" :key="t.v" :label="t.l" :value="t.v" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="newRule.severity" style="width:100%;">
            <el-option v-for="t in [{v:'low',l:'低'},{v:'medium',l:'中'},{v:'high',l:'高'},{v:'critical',l:'严重'}]" :key="t.v" :label="t.l" :value="t.v" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddRule = false">取消</el-button><el-button type="primary" :loading="saving" @click="doAddRule">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddCron" title="新增定时作业" width="500px" destroy-on-close>
      <el-form :model="newCron" label-width="100" size="small">
        <el-form-item label="名称"><el-input v-model="newCron.name" /></el-form-item>
        <el-form-item label="Cron 表达式"><el-input v-model="newCron.cron_expression" placeholder="0 2 * * *" /></el-form-item>
        <el-form-item label="关联方案">
          <el-select v-model="newCron.plan_id" filterable style="width:100%;">
            <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddCron = false">取消</el-button><el-button type="primary" :loading="saving" @click="doAddCron">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="showExecDetailDialog" :title="'执行详情 #' + (detailExec?.id || '')" width="800px" destroy-on-close>
      <div v-if="detailLoading" style="text-align:center;padding:40px;"><el-icon :size="36" class="is-loading"><Loading /></el-icon></div>
      <div v-else>
        <el-descriptions :column="3" border size="small" style="margin-bottom:16px;">
          <el-descriptions-item label="状态">{{ detailExec?.status }}</el-descriptions-item>
          <el-descriptions-item label="触发方式">{{ detailExec?.triggered_by }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detailExec?.total_time ? detailExec.total_time + 's' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="结果摘要">{{ detailExec?.result_summary || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="detailSteps" size="small" stripe style="width:100%">
          <el-table-column prop="step_name" label="步骤" min-width="140" />
          <el-table-column prop="step_type" label="类型" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }"><span class="job-status-badge" :class="'job-status-' + row.status">{{ row.status }}</span></template>
          </el-table-column>
          <el-table-column label="结果" prop="result_summary" min-width="160" show-overflow-tooltip />
          <el-table-column label="耗时" width="60">
            <template #default="{ row }">{{ row.finished_at && row.started_at ? Math.round((new Date(row.finished_at).getTime() - new Date(row.started_at).getTime())/1000) + 's' : '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Search, Plus, CaretRight, Document, Timer, WarningFilled,
  Refresh, Close, Edit, Delete, View, Top, List, Setting, Key, Loading,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  scriptsApi, ScriptVersions, PublishScript,
  templatesApi, PublishTemplate, TemplatePlans, ExecutePlan, MoveStep,
  plansApi, variablesApi, stepsApi,
  executionsApi, StopExecution, RetryExecution, ExecutionSteps, ExecutionLog,
  quickExecApi, CheckDangerousCommand,
  accountsApi, dangerousRulesApi,
  cronJobsApi, ToggleCronJob, ExecuteCronNow, CronJobHistory,
  GetJobDashboard,
} from '/@/api/job-platform/index'

const tabs = [
  { key: 'quick', label: '快速执行', icon: CaretRight },
  { key: 'templates', label: '模板管理', icon: Document },
  { key: 'scripts', label: '脚本管理', icon: Timer },
  { key: 'history', label: '执行记录', icon: List },
  { key: 'accounts', label: '账号管理', icon: Key },
  { key: 'settings', label: '设置', icon: Setting },
]

const activeTab = ref('quick')
const searchQuery = ref('')
const loading = ref(false)
const saving = ref(false)
const quickRunning = ref(false)

// ── Data ──
const templates = ref<any[]>([])
const scripts = ref<any[]>([])
const executions = ref<any[]>([])
const accounts = ref<any[]>([])
const dangerousRules = ref<any[]>([])
const cronJobs = ref<any[]>([])
const plans = ref<any[]>([])
const runningCount = ref(0)

// ── Quick Exec ──
const quickScriptRef = ref<number | null>(null)
const quickContent = ref('')
const quickHosts = ref('')
const quickExecutor = ref('ssh')
const quickResult = ref('')
const quickScriptCache = ref<Record<number, string>>({})

// ── Template ──
const selectedTemplate = ref<any>(null)
const templateSteps = ref<any[]>([])
const showAddTemplate = ref(false)
const showAddPlan = ref(false)
const newTemplate = ref({ name: '', description: '', category: '' })

// ── Script ──
const showAddScript = ref(false)
const newScript = ref({ name: '', script_type: 'shell', content: '' })

// ── Account ──
const showAddAccount = ref(false)
const newAccount = ref({ name: '', username: 'root', protocol: 'ssh', password: '', port: 22 })

// ── Dangerous ──
const showAddRule = ref(false)
const newRule = ref({ name: '', pattern: '', is_regex: false, action: 'reject', severity: 'high', description: '', script_type: 'all' })

// ── Cron ──
const showAddCron = ref(false)
const newCron = ref({ name: '', cron_expression: '0 2 * * *', plan_id: null })

// ── Execution Detail ──
const showExecDetailDialog = ref(false)
const detailExec = ref<any>(null)
const detailSteps = ref<any[]>([])
const detailLoading = ref(false)

// ── Computed ──
const filteredScripts = computed(() => {
  if (!searchQuery.value) return scripts.value
  const q = searchQuery.value.toLowerCase()
  return scripts.value.filter(s => s.name?.toLowerCase().includes(q))
})
const filteredTemplates = computed(() => {
  if (!searchQuery.value) return templates.value
  const q = searchQuery.value.toLowerCase()
  return templates.value.filter(t => t.name?.toLowerCase().includes(q))
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    success: '成功', running: '运行中', failed: '失败', pending: '等待',
    stopped: '已停止', timeout: '超时', approving: '待审批',
    confirmed_terminated: '审批终止', ignore_error: '已忽略',
  }
  return map[s] || s || '未知'
}

function onSearch() {}

// ── Quick Exec ──
async function loadQuickScript(id: number) {
  if (quickScriptCache.value[id]) {
    quickContent.value = quickScriptCache.value[id]
    return
  }
  try {
    const res = await scriptsApi.detail(id)
    const script = res.data || {}
    quickContent.value = script.content || ''
    quickScriptCache.value[id] = quickContent.value
  } catch { /* ignore */ }
}

async function doQuickExec() {
  if (!quickContent.value && !quickScriptRef.value) {
    ElMessage.warning('请输入脚本或选择引用脚本')
    return
  }
  quickRunning.value = true
  quickResult.value = ''
  try {
    const data: any = { target_hosts: quickHosts.value.split(',').map(s => s.trim()).filter(Boolean), executor: quickExecutor.value }
    if (quickScriptRef.value) data.script_id = quickScriptRef.value
    if (quickContent.value && !quickScriptRef.value) data.content = quickContent.value
    const res = await quickExecApi.script(data)
    quickResult.value = JSON.stringify(res.data || res, null, 2)
    ElMessage.success('已提交执行')
  } catch (e: any) {
    quickResult.value = `Error: ${e?.msg || e?.message || '执行失败'}`
  } finally {
    quickRunning.value = false
  }
}

// ── Template ──
function selectTemplate(row: any) {
  selectedTemplate.value = row
  loadTemplateSteps(row)
}

async function loadTemplateSteps(tpl: any) {
  try {
    const res = await stepsApi.list({ template: tpl.id })
    templateSteps.value = res.data?.items || res.data || []
  } catch { templateSteps.value = [] }
}

async function publishTemplate() {
  if (!selectedTemplate.value) return
  await PublishTemplate(selectedTemplate.value.id)
  ElMessage.success('已发布')
  await loadTemplates()
}

async function doAddTemplate() {
  saving.value = true
  try {
    await templatesApi.create(newTemplate.value)
    ElMessage.success('创建成功')
    showAddTemplate.value = false
    await loadTemplates()
  } catch (e: any) { ElMessage.error(e?.msg || '创建失败') } finally { saving.value = false }
}

// ── Script ──
async function doAddScript() {
  saving.value = true
  try {
    await scriptsApi.create(newScript.value)
    ElMessage.success('创建成功')
    showAddScript.value = false
    await loadScripts()
  } catch (e: any) { ElMessage.error(e?.msg || '创建失败') } finally { saving.value = false }
}

function viewScript(row: any) {
  quickContent.value = row.content || ''
  activeTab.value = 'quick'
  ElMessage.info('脚本内容已加载到快速执行')
}

function editScript(row: any) {
  newScript.value = { name: row.name, script_type: row.script_type, content: row.content }
  showAddScript.value = true
}

async function showPublishDialog(row: any) {
  try {
    const { value } = await ElMessageBox.prompt('变更说明', `发布 ${row.name}`, { inputType: 'textarea' })
    await PublishScript(row.id, { changelog: value || '' })
    ElMessage.success('发布成功')
    await loadScripts()
  } catch { /* cancelled */ }
}

// ── Account ──
async function doAddAccount() {
  saving.value = true
  try {
    await accountsApi.create(newAccount.value)
    ElMessage.success('创建成功')
    showAddAccount.value = false
    await loadAccounts()
  } catch (e: any) { ElMessage.error(e?.msg || '创建失败') } finally { saving.value = false }
}

function editAccount(row: any) {
  newAccount.value = { ...row }
  showAddAccount.value = true
}

async function deleteAccount(row: any) {
  try {
    await accountsApi.delete(row.id)
    ElMessage.success('已删除')
    await loadAccounts()
  } catch (e: any) { ElMessage.error('删除失败') }
}

// ── Execution ──
async function showExecDetail(row: any) {
  detailExec.value = row
  detailSteps.value = []
  showExecDetailDialog.value = true
  detailLoading.value = true
  try {
    const [detailRes, stepsRes] = await Promise.all([
      executionsApi.detail(row.id),
      ExecutionSteps(row.id),
    ])
    detailExec.value = detailRes.data || row
    detailSteps.value = stepsRes.data || []
  } catch { /* ignore */ } finally { detailLoading.value = false }
}

async function stopExec(row: any) {
  await StopExecution(row.id)
  ElMessage.success('已停止')
  await loadExecutions()
}

async function retryExec(row: any) {
  await RetryExecution(row.id)
  ElMessage.success('已重新执行')
  await loadExecutions()
}

// ── Dangerous ──
async function toggleRule(row: any) {
  await dangerousRulesApi.update(row.id, { is_active: row.is_active })
}

async function doAddRule() {
  saving.value = true
  try {
    await dangerousRulesApi.create(newRule.value)
    ElMessage.success('创建成功')
    showAddRule.value = false
    await loadDangerousRules()
  } catch (e: any) { ElMessage.error(e?.msg || '创建失败') } finally { saving.value = false }
}

// ── Cron ──
async function toggleCron(row: any) {
  await ToggleCronJob(row.id)
}

async function runCronNow(row: any) {
  await ExecuteCronNow(row.id)
  ElMessage.success('已触发执行')
}

async function doAddCron() {
  saving.value = true
  try {
    const data: any = {
      name: newCron.value.name,
      cron_expression: newCron.value.cron_expression,
      plan_id: newCron.value.plan_id,
    }
    await cronJobsApi.create(data)
    ElMessage.success('创建成功')
    showAddCron.value = false
    await loadCronJobs()
  } catch (e: any) { ElMessage.error(e?.msg || '创建失败') } finally { saving.value = false }
}

// ── Load Data ──
async function loadTemplates() {
  const res = await templatesApi.list()
  templates.value = res.data || []
}
async function loadScripts() {
  const res = await scriptsApi.list()
  scripts.value = res.data || []
}
async function loadExecutions() {
  const res = await executionsApi.list()
  executions.value = res.data?.items || res.data || []
}
async function loadAccounts() {
  const res = await accountsApi.list()
  accounts.value = res.data || []
}
async function loadDangerousRules() {
  const res = await dangerousRulesApi.list()
  dangerousRules.value = res.data || []
}
async function loadCronJobs() {
  const res = await cronJobsApi.list()
  cronJobs.value = res.data || []
}
async function loadPlans() {
  const res = await plansApi.list()
  plans.value = res.data || []
}
async function loadDashboard() {
  try {
    const res = await GetJobDashboard()
    runningCount.value = res.data?.running_executions || 0
  } catch { /* ignore */ }
}

onMounted(async () => {
  loading.value = true
  await Promise.all([
    loadTemplates(), loadScripts(), loadExecutions(),
    loadAccounts(), loadDangerousRules(), loadCronJobs(),
    loadPlans(), loadDashboard(),
  ])
  loading.value = false
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.job-platform-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}
.job-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a2e1a 0%, #163e16 50%, #1a4a1a 100%);
}
.job-hero-bg { position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.job-hero-inner { position: relative; z-index: 1; padding: 14px 24px; display: flex; align-items: center; gap: 16px; }
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
.job-hero-tabs { position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px; }
.job-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px 10px 0;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
}
.job-hero-tab:hover { color: rgba(255,255,255,0.9); }
.job-hero-tab.active { color: #fff; border-bottom-color: #67C23A; }

.job-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.job-section { padding-top: 16px; }

.job-table-card { background: #fff; border-radius: 14px; box-shadow: $g-shadow-card; overflow: hidden; }
.job-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.job-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.job-table-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0; }
.job-table-title { font-size: 15px; font-weight: 600; color: $g-text-primary; }

.job-status-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px; }
.job-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.job-status-success .job-status-dot { background: #67C23A; }
.job-status-success { background: #f0f9eb; color: #67C23A; }
.job-status-running .job-status-dot { background: #409EFF; }
.job-status-running { background: #ecf5ff; color: #409EFF; }
.job-status-failed .job-status-dot { background: #F56C6C; }
.job-status-failed { background: #fef0f0; color: #F56C6C; }
.job-status-pending .job-status-dot { background: #E6A23C; }
.job-status-pending { background: #fdf6ec; color: #E6A23C; }
.job-status-stopped .job-status-dot { background: #909399; }
.job-status-stopped { background: #f5f7fa; color: #909399; }

.job-severity-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; }
.job-severity-high, .job-severity-critical { background: #fef0f0; color: #F56C6C; }
.job-severity-medium { background: #fdf6ec; color: #E6A23C; }
.job-severity-low { background: #f0f9eb; color: #67C23A; }

.job-quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.job-settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.job-tpl-layout { display: flex; gap: 16px; min-height: 400px; }
.job-tpl-sidebar { flex: 0 0 300px; }
.job-tpl-detail { flex: 1; min-width: 0; }
.job-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; gap: 16px; color: #909399; }
.job-step-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-radius: 8px; margin-bottom: 6px; background: #fafafa; }
.job-step-index { width: 24px; height: 24px; border-radius: 50%; background: #409EFF; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.job-step-info { flex: 1; display: flex; align-items: center; gap: 8px; }
.job-step-name { font-size: 13px; font-weight: 500; }
.job-step-actions { flex-shrink: 0; }
</style>
