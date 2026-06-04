<template>
  <div class="job-platform-page">
    <div class="of-card" style="margin-bottom:16px;">
      <el-tabs v-model="activeTab" class="of-tabs" style="padding:0 24px;">
        <el-tab-pane label="作业执行" name="run" />
        <el-tab-pane label="脚本管理" name="scripts" />
        <el-tab-pane label="执行记录" name="history" />
        <el-tab-pane label="高危命令规则" name="dangerous" />
      </el-tabs>
    </div>

    <!-- Run Jobs -->
    <div v-show="activeTab === 'run'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">执行作业</h3>
        <el-button type="primary" @click="showCreateJob = true">+ 新建作业</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="jobs" v-loading="loading" stripe>
          <el-table-column prop="name" label="作业名称" min-width="180" />
          <el-table-column prop="executor" label="执行方式" width="120" />
          <el-table-column prop="timeout_seconds" label="超时(s)" width="90" />
          <el-table-column prop="need_approval" label="需要审批" width="100">
            <template #default="{ row }"><el-tag v-if="row.need_approval" type="warning">是</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="runJob(row)">执行</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Scripts -->
    <div v-show="activeTab === 'scripts'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">脚本管理</h3>
        <el-button type="primary" @click="showCreateScript = true">+ 新建脚本</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="scripts" v-loading="loading" stripe>
          <el-table-column prop="name" label="脚本名称" min-width="180" />
          <el-table-column prop="script_type" label="类型" width="100" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="is_public" label="公开" width="80">
            <template #default="{ row }"><el-tag v-if="row.is_public" size="small">公开</el-tag></template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Execution History -->
    <div v-show="activeTab === 'history'" class="of-card">
      <div class="of-card-body">
        <el-table :data="executions" v-loading="loading" stripe>
          <el-table-column prop="job_name" label="作业" min-width="160" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status==='success'?'success':row.status==='running'?'primary':row.status==='failed'?'danger':'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result_summary" label="结果摘要" min-width="200" />
          <el-table-column prop="started_at" label="开始时间" width="170" />
          <el-table-column prop="finished_at" label="完成时间" width="170" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.status==='running'||row.status==='pending'" size="small" type="danger" @click="cancelExec(row)">取消</el-button>
              <el-button size="small" link @click="showLog(row)">日志</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Dangerous Rules -->
    <div v-show="activeTab === 'dangerous'" class="of-card">
      <div class="of-card-body">
        <el-table :data="dangerousRules" v-loading="loading" stripe>
          <el-table-column prop="name" label="规则名称" />
          <el-table-column prop="pattern" label="匹配模式" min-width="200" />
          <el-table-column prop="action" label="处理方式" width="120" />
          <el-table-column prop="severity" label="级别" width="80" />
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
import { jobApi, scriptApi, executionApi, dangerousRuleApi, RunJob, CancelExecution, GetExecutionLog } from '/@/api/job-platform/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('run')
const loading = ref(false)
const jobs = ref<any[]>([])
const scripts = ref<any[]>([])
const executions = ref<any[]>([])
const dangerousRules = ref<any[]>([])
const showCreateJob = ref(false)
const showCreateScript = ref(false)

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

onMounted(loadData)
</script>

<style scoped>
.job-platform-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
