<template>
  <div class="integration-page">
    <div class="of-card">
      <div class="of-card-header">
        <div>
          <h2 class="of-card-title">集成中心</h2>
          <p class="of-card-desc">统一管理所有外部系统的连接器、凭证和调用审计</p>
        </div>
        <div class="of-card-header-actions">
          <el-tabs v-model="activeTab" class="of-tabs">
            <el-tab-pane label="连接器实例" name="instances" />
            <el-tab-pane label="凭证管理" name="credentials" />
            <el-tab-pane label="调用日志" name="logs" />
          </el-tabs>
        </div>
      </div>

      <!-- Connector Instances -->
      <div v-show="activeTab === 'instances'" class="of-card-body">
        <el-table :data="instances" v-loading="loading" stripe>
          <el-table-column prop="name" label="实例名称" min-width="160" />
          <el-table-column prop="definition.name" label="连接器类型" min-width="140" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : row.status === 'error' ? 'danger' : 'info'" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="启用" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" @change="toggleInstance(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="runHealthCheck(row)">健康检查</el-button>
              <el-button size="small" type="primary" link @click="editInstance(row)">配置</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="of-table-footer">
          <el-button type="primary" size="default" @click="showAddInstance = true">+ 添加实例</el-button>
        </div>
      </div>

      <!-- Credentials -->
      <div v-show="activeTab === 'credentials'" class="of-card-body">
        <el-table :data="credentials" v-loading="loading" stripe>
          <el-table-column prop="name" label="凭证名称" min-width="160" />
          <el-table-column prop="instance.name" label="所属实例" min-width="140" />
          <el-table-column prop="cred_type" label="类型" width="140" />
          <el-table-column prop="expire_at" label="过期时间" width="180" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="warning" link @click="showDecrypt(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Call Logs -->
      <div v-show="activeTab === 'logs'" class="of-card-body">
        <el-table :data="callLogs" v-loading="loading" stripe>
          <el-table-column prop="instance" label="实例" min-width="140" />
          <el-table-column prop="action" label="操作" min-width="160" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
          <el-table-column prop="create_datetime" label="时间" width="180" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { connectorInstanceApi, credentialApi, callLogApi, HealthCheck, ToggleInstance, DecryptCredential } from '/@/api/integration/index'
import { ElMessage } from 'element-plus'

const activeTab = ref('instances')
const loading = ref(false)
const instances = ref<any[]>([])
const credentials = ref<any[]>([])
const callLogs = ref<any[]>([])
const showAddInstance = ref(false)

async function loadData() {
  loading.value = true
  try {
    const [insRes, credRes, logRes] = await Promise.all([
      connectorInstanceApi.list(),
      credentialApi.list(),
      callLogApi.list({ limit: 50 }),
    ])
    instances.value = insRes.data || []
    credentials.value = credRes.data || []
    callLogs.value = logRes.data || []
  } finally {
    loading.value = false
  }
}

async function runHealthCheck(row: any) {
  await HealthCheck(row.id)
  ElMessage.success('健康检查完成')
  await loadData()
}

async function toggleInstance(row: any) {
  await ToggleInstance(row.id)
  ElMessage.success('操作成功')
}

async function showDecrypt(row: any) {
  const res = await DecryptCredential(row.id)
  ElMessage.info(`凭证值: ${res.data.decrypted_value}`)
}

function editInstance(row: any) { /* TODO */ }

onMounted(loadData)
</script>

<style scoped>
.integration-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 24px 0; }
.of-card-title { font-size: 18px; font-weight: 600; margin: 0; }
.of-card-desc { color: #8b949e; font-size: 13px; margin: 4px 0 0; }
.of-card-body { padding: 16px 24px 24px; }
.of-table-footer { margin-top: 16px; }
</style>
