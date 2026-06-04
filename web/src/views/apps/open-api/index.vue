<template>
  <div class="open-api-page">
    <div class="of-card" style="margin-bottom:16px;">
      <el-tabs v-model="activeTab" class="of-tabs" style="padding:0 24px;">
        <el-tab-pane label="第三方应用" name="apps" />
        <el-tab-pane label="访问凭证" name="tokens" />
        <el-tab-pane label="事件订阅" name="webhooks" />
        <el-tab-pane label="调用日志" name="logs" />
      </el-tabs>
    </div>

    <!-- Apps -->
    <div v-show="activeTab === 'apps'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">第三方应用管理</h3>
        <el-button type="primary" @click="showAddApp = true">+ 添加应用</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="apps" v-loading="loading" stripe>
          <el-table-column prop="name" label="应用名称" min-width="160" />
          <el-table-column prop="company" label="公司" width="140" />
          <el-table-column prop="contact_email" label="联系邮箱" min-width="180" />
          <el-table-column prop="rate_limit" label="QPS" width="80" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status==='active'?'success':'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" link @click="editApp(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Tokens -->
    <div v-show="activeTab === 'tokens'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">访问凭证</h3>
        <el-button type="primary" @click="showAddToken = true">+ 生成凭证</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="tokens" v-loading="loading" stripe>
          <el-table-column prop="access_key" label="Access Key" width="160" />
          <el-table-column prop="app.name" label="所属应用" width="160" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status==='active'?'success':'danger'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="expire_at" label="过期时间" width="170" />
          <el-table-column prop="last_used_at" label="最后使用" width="170" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.status==='active'" size="small" type="danger" @click="revokeToken(row)">吊销</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Call Logs -->
    <div v-show="activeTab === 'logs'" class="of-card">
      <div class="of-card-body">
        <el-table :data="callLogs" v-loading="loading" stripe>
          <el-table-column prop="request_method" label="方法" width="80" />
          <el-table-column prop="request_path" label="路径" min-width="240" />
          <el-table-column prop="response_status" label="状态码" width="90" />
          <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
          <el-table-column prop="ip_address" label="来源 IP" width="140" />
          <el-table-column prop="create_datetime" label="时间" width="170" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiAppApi, apiTokenApi, webhookSubApi, openApiLogApi, RevokeToken } from '/@/api/open-api/index'
import { ElMessage } from 'element-plus'

const activeTab = ref('apps')
const loading = ref(false)
const apps = ref<any[]>([])
const tokens = ref<any[]>([])
const webhooks = ref<any[]>([])
const callLogs = ref<any[]>([])
const showAddApp = ref(false)
const showAddToken = ref(false)

async function loadData() {
  loading.value = true
  try {
    const [a, t, l] = await Promise.all([
      apiAppApi.list(),
      apiTokenApi.list(),
      openApiLogApi.list({ limit: 50 }),
    ])
    apps.value = a.data || []
    tokens.value = t.data || []
    callLogs.value = l.data || []
  } finally { loading.value = false }
}

async function revokeToken(row: any) {
  await RevokeToken(row.id)
  ElMessage.success('凭证已吊销')
  await loadData()
}

function editApp(row: any) { /* TODO */ }

onMounted(loadData)
</script>

<style scoped>
.open-api-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
