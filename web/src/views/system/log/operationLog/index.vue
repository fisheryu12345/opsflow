<template>
  <div class="oplog-page">
    <!-- ===== Hero Section ===== -->
    <div class="oplog-hero">
      <div class="oplog-hero-bg" />
      <div class="oplog-hero-inner">
        <div class="oplog-hero-left">
          <h1 class="oplog-hero-title">{{ $t('message.operationLogPage.title') }}</h1>
          <p class="oplog-hero-subtitle">Operation Log</p>
        </div>
        <div class="oplog-hero-stats">
          <div class="oplog-stat-item">
            <span class="oplog-stat-value">{{ total }}</span>
            <span class="oplog-stat-label">Total</span>
          </div>
          <div class="oplog-stat-divider" />
          <div class="oplog-stat-item">
            <span class="oplog-stat-value" style="color:#67C23A">{{ successCount }}</span>
            <span class="oplog-stat-label">Success</span>
          </div>
          <div class="oplog-stat-divider" />
          <div class="oplog-stat-item">
            <span class="oplog-stat-value" style="color:#F56C6C">{{ failCount }}</span>
            <span class="oplog-stat-label">Failure</span>
          </div>
          <div class="oplog-stat-divider" />
          <div class="oplog-stat-item">
            <span class="oplog-stat-value" style="color:#E6A23C">{{ todayCount }}</span>
            <span class="oplog-stat-label">Today</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="oplog-body">
      <!-- ===== Search / Filter Bar ===== -->
      <div class="oplog-filter-bar">
        <el-form :model="searchForm" inline size="small" @keyup.enter="onSearch">
          <el-form-item :label="$t('message.operationLogPage.filterModular')">
            <el-input v-model="searchForm.request_modular" :placeholder="$t('message.operationLogPage.filterModularPlaceholder')" clearable style="width:140px" />
          </el-form-item>
          <el-form-item :label="$t('message.operationLogPage.filterPath')">
            <el-input v-model="searchForm.request_path" :placeholder="$t('message.operationLogPage.filterPathPlaceholder')" clearable style="width:180px" />
          </el-form-item>
          <el-form-item :label="$t('message.operationLogPage.filterMethod')">
            <el-input v-model="searchForm.request_method" :placeholder="$t('message.operationLogPage.filterMethodPlaceholder')" clearable style="width:120px" />
          </el-form-item>
          <el-form-item :label="$t('message.operationLogPage.filterIp')">
            <el-input v-model="searchForm.request_ip" :placeholder="$t('message.operationLogPage.filterIpPlaceholder')" clearable style="width:150px" />
          </el-form-item>
          <el-form-item :label="$t('message.operationLogPage.filterCreator')">
            <el-input v-model="searchForm.creator_name" :placeholder="$t('message.operationLogPage.filterCreatorPlaceholder')" clearable style="width:120px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="onSearch">{{ $t('message.operationLogPage.search') }}</el-button>
            <el-button :icon="Refresh" @click="onReset">{{ $t('message.operationLogPage.reset') }}</el-button>
          </el-form-item>
        </el-form>
        <div class="oplog-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">{{ $t('message.operationLogPage.refresh') }}</el-button>
        </div>
      </div>

      <!-- ===== Table Card ===== -->
      <div class="oplog-table-card">
        <el-table :data="list" v-loading="loading" stripe style="width:100%"
          :empty-text="loading ? $t('message.operationLogPage.loading') : $t('message.operationLogPage.empty')" size="small" highlight-current-row>
          <el-table-column type="index" label="#" width="60" align="center">
            <template #default="{ $index }">
              {{ (page - 1) * pageSize + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" :label="$t('message.operationLogPage.colCreator')" width="120" show-overflow-tooltip />
          <el-table-column prop="request_modular" :label="$t('message.operationLogPage.colModule')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="request_path" :label="$t('message.operationLogPage.colPath')" min-width="220" show-overflow-tooltip />
          <el-table-column prop="request_method" :label="$t('message.operationLogPage.colMethod')" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="methodTagType(row.request_method)" size="small" effect="plain">
                {{ row.request_method || '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="response_code" :label="$t('message.operationLogPage.colCode')" width="90" align="center">
            <template #default="{ row }">
              <span class="oplog-code-badge" :class="codeClass(row.response_code)">
                {{ row.response_code ?? '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="create_datetime" :label="$t('message.operationLogPage.colTime')" width="170" />
          <el-table-column :label="$t('message.operationLogPage.colActions')" width="80" fixed="right" align="center">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="showDetail(row)">{{ $t('message.operationLogPage.view') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="oplog-pagination" v-if="total > 0">
          <el-pagination v-model:currentPage="page" v-model:pageSize="pageSize" :total="total"
            :page-sizes="[15, 30, 50, 100]" layout="total, sizes, prev, pager, next, jumper"
            @update:currentPage="onPageChange" @update:pageSize="onSizeChange" size="small" />
        </div>
      </div>
    </div>

    <!-- ===== Detail Drawer ===== -->
    <el-drawer v-model="detailVisible" :title="$t('message.operationLogPage.drawerTitle')" size="560px" destroy-on-close class="oplog-detail-drawer">
      <template v-if="detailRow">
        <div class="oplog-detail-body">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('message.operationLogPage.descCreator')" :span="1">{{ detailRow.creator_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descModule')" :span="1">{{ detailRow.request_modular || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descPath')" :span="2">{{ detailRow.request_path || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descMethod')" :span="1">
              <el-tag :type="methodTagType(detailRow.request_method)" size="small" effect="plain">
                {{ detailRow.request_method || '-' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descCode')" :span="1">
              <span class="oplog-code-badge" :class="codeClass(detailRow.response_code)">
                {{ detailRow.response_code ?? '-' }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descIp')" :span="1">{{ detailRow.request_ip || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descBrowser')" :span="1">{{ detailRow.request_browser || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descOs')" :span="1">{{ detailRow.request_os || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descMsg')" :span="2">{{ detailRow.request_msg || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('message.operationLogPage.descTime')" :span="2">{{ detailRow.create_datetime || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="oplog-detail-section">
            <div class="oplog-detail-label">{{ $t('message.operationLogPage.sectionRequestBody') }}</div>
            <pre class="oplog-detail-code">{{ formatJson(detailRow.request_body) }}</pre>
          </div>
          <div class="oplog-detail-section">
            <div class="oplog-detail-label">{{ $t('message.operationLogPage.sectionResult') }}</div>
            <pre class="oplog-detail-code">{{ formatJson(detailRow.json_result) }}</pre>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetList } from './api'

const { t } = useI18n()

// ── State ──
const loading = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(15)
const total = ref(0)
const detailVisible = ref(false)
const detailRow = ref<any>(null)

const searchForm = ref({
  request_modular: '',
  request_path: '',
  request_method: '',
  request_ip: '',
  creator_name: '',
})

// ── Computed ──
const successCount = computed(() => list.value.filter((l: any) => {
  const code = Number(l.response_code)
  return code >= 200 && code < 300
}).length)

const failCount = computed(() => list.value.filter((l: any) => {
  const code = Number(l.response_code)
  return (code >= 400 && code < 600) || (!l.response_code && l.response_code !== 0)
}).length)

const todayCount = computed(() => {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  return list.value.filter((l: any) => {
    if (!l.create_datetime) return false
    return l.create_datetime.startsWith(todayStr)
  }).length
})

// ── Methods ──
function methodTagType(method: string): string {
  if (!method) return 'info'
  const m = method.toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function codeClass(code: any): string {
  const n = Number(code)
  if (isNaN(n)) return ''
  if (n >= 200 && n < 300) return 'code-success'
  if (n >= 300 && n < 400) return 'code-redirect'
  if (n >= 400 && n < 500) return 'code-client-err'
  if (n >= 500) return 'code-server-err'
  return ''
}

function formatJson(val: any): string {
  if (!val) return '-'
  try {
    const obj = typeof val === 'string' ? JSON.parse(val) : val
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(val)
  }
}

function buildParams() {
  const params: any = {
    page: page.value,
    limit: pageSize.value,
  }
  const s = searchForm.value
  if (s.request_modular) params.request_modular = s.request_modular
  if (s.request_path) params.request_path = s.request_path
  if (s.request_method) params.request_method = s.request_method
  if (s.request_ip) params.request_ip = s.request_ip
  if (s.creator_name) params.creator_name = s.creator_name
  return params
}

async function fetchData() {
  loading.value = true
  try {
    const res = await GetList(buildParams())
    // Response format: { code: 2000, data: [...], total: N, page: N, limit: N, msg: "success" }
    const data = res.data || []
    list.value = Array.isArray(data) ? data : []
    total.value = res.total || 0
  } catch (e: any) {
    list.value = []
    total.value = 0
    console.error('Failed to fetch operation logs:', e)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  fetchData()
}

function onReset() {
  searchForm.value = {
    request_modular: '',
    request_path: '',
    request_method: '',
    request_ip: '',
    creator_name: '',
  }
  page.value = 1
  fetchData()
}

function onPageChange() {
  fetchData()
}

function onSizeChange(val: number) {
  pageSize.value = val
  page.value = 1
  fetchData()
}

function showDetail(row: any) {
  detailRow.value = row
  detailVisible.value = true
}

// ── Lifecycle ──
onMounted(() => {
  fetchData()

  const key = 'opsflow_tour_operation_log'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: t('message.operationLogPage.tourTip'), duration: 5000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../../../../styles/opsflow-global' as *;

.oplog-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: $of-bg-page; overflow: hidden;
}

/* ===== Hero ===== */
.oplog-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.oplog-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.oplog-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.oplog-hero-left { flex: 0 0 auto; }
.oplog-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.oplog-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.oplog-hero-stats { flex: 0 0 auto; display: flex; align-items: center; margin-left: auto; }
.oplog-stat-item { text-align: center; padding: 0 18px; }
.oplog-stat-value { display: block; font-size: 20px; font-weight: 700; color: #fff; line-height: 1.2; }
.oplog-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.oplog-stat-divider { width: 1px; height: 28px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.oplog-body {
  flex: 1; overflow-y: auto; padding: 0 16px 24px;
}

/* ===== Filter Bar ===== */
.oplog-filter-bar {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 14px 0 10px; gap: 12px;
  position: sticky; top: 0; z-index: 10;
  background: $of-bg-page;
}
.oplog-filter-bar :deep(.el-form-item) { margin-bottom: 4px; }
.oplog-filter-bar :deep(.el-form-item__label) { font-size: 12px; color: $of-text-secondary; }
.oplog-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; padding-top: 2px; }

/* ===== Table Card ===== */
.oplog-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.oplog-table-card :deep(.el-table th.el-table__cell) {
  background: $of-bg-header; color: $of-text-secondary; font-weight: 600; font-size: 12px;
}
.oplog-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.oplog-table-card :deep(.el-table__body tr.current-row > td) { background: $of-bg-light-blue; }

/* ===== Response Code Badge ===== */
.oplog-code-badge {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px; min-width: 40px; text-align: center;
}
.code-success { background: $of-bg-success; color: #67C23A; }
.code-redirect { background: $of-bg-light-blue; color: #409EFF; }
.code-client-err { background: $of-bg-warning; color: #E6A23C; }
.code-server-err { background: $of-bg-danger; color: #F56C6C; }

/* ===== Pagination ===== */
.oplog-pagination {
  display: flex; justify-content: flex-end; padding: 12px 16px;
}

/* ===== Detail Drawer ===== */
.oplog-detail-drawer {
  --el-drawer-padding-primary: 0;
}
.oplog-detail-drawer :deep(.el-drawer__header) {
  margin-bottom: 0; padding: $of-padding-dialog-header;
  border-bottom: 1px solid $of-border-light;
}
.oplog-detail-drawer :deep(.el-drawer__body) {
  padding: 20px;
}
.oplog-detail-body {
  display: flex; flex-direction: column; gap: 16px;
}
.oplog-detail-body :deep(.el-descriptions__cell) {
  padding: 6px 10px !important;
}
.oplog-detail-body :deep(.el-descriptions__label.is-bordered-label) {
  font-weight: 500; color: $of-text-secondary;
}
.oplog-detail-section {
  margin-top: 4px;
}
.oplog-detail-label {
  font-size: 13px; font-weight: 600; color: $of-text-primary;
  margin-bottom: 8px;
}
.oplog-detail-code {
  background: $of-bg-card; border-radius: $of-radius-sm;
  padding: 12px; font-size: 12px; line-height: 1.5;
  max-height: 280px; overflow: auto; white-space: pre-wrap; word-break: break-all;
  margin: 0; border: 1px solid $of-border-card;
}
</style>
