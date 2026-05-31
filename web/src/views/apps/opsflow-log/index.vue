<template>
  <div class="opsflow-log-page">
    <div class="log-page-body">
      <!-- Filter bar -->
      <div class="filter-bar">
        <el-select v-model="filterRisk" placeholder="Risk level" clearable filterable style="width: 150px"
                   @change="onFilter">
          <el-option label="Low" value="low" />
          <el-option label="Medium" value="medium" />
          <el-option label="High" value="high" />
          <el-option label="Critical" value="critical" />
        </el-select>
        <el-input v-model="filterStep" placeholder="Search step..." clearable style="width: 200px"
                  @keyup.enter="onFilter" @clear="onFilter" />
        <el-button :icon="Refresh" @click="fetchData" :loading="loading">Refresh</el-button>
        <div class="filter-spacer" />
        <span v-if="useMock" class="mock-badge">Mock Data</span>
      </div>

      <!-- Table -->
      <el-table :data="list" v-loading="loading" stripe highlight-current-row style="width: 100%"
                :empty-text="emptyText">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="Risk" width="110" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <span class="status-dot" :style="{ background: riskColor(row.risk_level) }" />
              <el-tag :type="riskTagType(row.risk_level)" size="small" effect="dark">
                {{ row.risk_level }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="step" label="Step" min-width="160" show-overflow-tooltip />
        <el-table-column label="Command" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.command || '-' }}</template>
        </el-table-column>
        <el-table-column prop="returncode" label="Return" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.returncode === 0 ? '#67C23A' : '#F56C6C', fontWeight: 600 }">
              {{ row.returncode ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Execution" width="100" align="center">
          <template #default="{ row }">#{{ row.execution }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="Time" width="170" />
        <el-table-column label="Actions" width="90" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="showDetail(row)">
              <el-icon style="margin-right: 3px"><View /></el-icon>View
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                       layout="prev, pager, next, total" @current-change="onPageChange" />
      </div>
    </div>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" title="Log Detail" width="720px" top="5vh">
      <template v-if="detailRow">
        <div class="detail-section">
          <div class="detail-meta">
            <span>ID: {{ detailRow.id }}</span>
            <el-tag :type="riskTagType(detailRow.risk_level)" size="small">{{ detailRow.risk_level }}</el-tag>
            <span>Step: {{ detailRow.step }}</span>
            <span>Return: {{ detailRow.returncode ?? '-' }}</span>
            <span>{{ detailRow.created_at }}</span>
          </div>
        </div>
        <div class="detail-section" v-if="detailRow.command">
          <div class="detail-label">Command</div>
          <pre class="detail-pre">{{ detailRow.command }}</pre>
        </div>
        <div class="detail-section" v-if="detailRow.stdout">
          <div class="detail-label">Stdout</div>
          <pre class="detail-pre">{{ detailRow.stdout }}</pre>
        </div>
        <div class="detail-section" v-if="detailRow.stderr">
          <div class="detail-label">Stderr</div>
          <pre class="detail-pre stderr">{{ detailRow.stderr }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, View } from '@element-plus/icons-vue'
import { GetLogs } from '/@/api/opsflow/logs'

const loading = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterRisk = ref('')
const filterStep = ref('')
const useMock = ref(false)
const detailVisible = ref(false)
const detailRow = ref<any>(null)

const emptyText = computed(() => loading.value ? 'Loading...' : useMock.value ? 'No data' : 'No logs yet')

const mockData = computed<any[]>(() => {
  const steps = ['check_disk', 'check_memory', 'deploy_app', 'restart_service', 'health_check',
    'backup_db', 'sync_config', 'rollback_release', 'scale_up', 'update_dns']
  const cmds = ['df -h', 'free -m', 'kubectl apply -f deploy.yaml', 'systemctl restart nginx',
    'curl -f http://localhost:8080/health', 'pg_dump -Fc db > backup.dump',
    'rsync -avz config/ node:/etc/app/', 'helm rollback release 2', 'kubectl scale deploy app --replicas=5',
    'curl -X PATCH https://api.cloudflare.com/dns/record']
  const items: any[] = []
  for (let i = 0; i < 15; i++) {
    const idx = i % steps.length
    const failed = i === 3 || i === 7
    items.push({
      id: 100 + i,
      execution: Math.floor(Math.random() * 5) + 1,
      step: steps[idx],
      command: cmds[idx],
      stdout: failed ? '' : `[INFO] Task completed successfully\n[INFO] Duration: ${Math.floor(Math.random() * 30) + 1}s`,
      stderr: failed ? `[ERROR] Command failed with exit code 1\n[ERROR] ${['Permission denied', 'Timeout', 'Connection refused', 'Resource not found'][i % 4]}` : '',
      returncode: failed ? 1 : 0,
      risk_level: ['low', 'low', 'medium', 'high', 'low', 'low', 'medium', 'critical', 'low', 'medium'][idx],
      approved_by: failed ? null : 'admin',
      created_at: new Date(Date.now() - i * 3600000).toISOString().replace('T', ' ').substring(0, 19),
    })
  }
  return items
})

function riskColor(level: string) {
  const map: Record<string, string> = { low: '#67C23A', medium: '#E6A23C', high: '#F56C6C', critical: '#F56C6C' }
  return map[level] || '#909399'
}
function riskTagType(level: string) {
  const map: Record<string, string> = { low: 'success', medium: 'warning', high: 'danger', critical: 'danger' }
  return map[level] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterRisk.value) params.risk_level = filterRisk.value
    if (filterStep.value) params.step__icontains = filterStep.value
    const res = await GetLogs(params)
    const items = res.data?.results || res.data || res.results || []
    if (items.length > 0) {
      list.value = items
      total.value = res.data?.count || res.count || items.length
      useMock.value = false
    } else {
      fallbackMock()
    }
  } catch {
    fallbackMock()
  }
  loading.value = false
}

function fallbackMock() {
  list.value = mockData.value
  total.value = mockData.value.length
  useMock.value = true
}

function onFilter() { page.value = 1; fetchData() }
function onPageChange() { fetchData() }
function showDetail(row: any) { detailRow.value = row; detailVisible.value = true }

onMounted(fetchData)
</script>

<style scoped>
.opsflow-log-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; background: #f0f2f5; overflow: hidden;
}
.log-page-body {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
  margin: 8px; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.filter-bar {
  display: flex; gap: 12px; align-items: center; padding: 12px 16px;
  background: #fff; border-bottom: 1px solid #ebeef5; flex-shrink: 0;
}
.filter-spacer { flex: 1; }
.status-cell { display: flex; align-items: center; gap: 6px; justify-content: center; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.mock-badge {
  font-size: 11px; color: #E6A23C; background: #fdf6ec;
  padding: 2px 8px; border-radius: 4px;
}
.pagination-wrap {
  display: flex; justify-content: flex-end; padding: 12px 16px;
  background: #fff; flex-shrink: 0; border-top: 1px solid #ebeef5;
}
.detail-section { margin-bottom: 16px; }
.detail-meta { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; font-size: 13px; color: #606266; }
.detail-label { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 6px; }
.detail-pre {
  background: #f5f7fa; border-radius: 6px; padding: 12px; font-size: 12px;
  line-height: 1.5; max-height: 300px; overflow: auto; white-space: pre-wrap; word-break: break-all;
  margin: 0;
}
.stderr { color: #F56C6C; }
</style>
