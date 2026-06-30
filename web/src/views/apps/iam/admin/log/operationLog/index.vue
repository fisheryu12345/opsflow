<template>
  <div class="oplog-page">
    <div class="oplog-body">
      <!-- ===== Search / Filter Bar ===== -->
      <div class="oplog-filter-bar">
        <el-input v-model="searchForm.request_modular" placeholder="模块" clearable size="small" style="width:120px" @keyup.enter="onSearch" />
        <el-input v-model="searchForm.request_path" placeholder="请求地址" clearable size="small" style="width:180px" @keyup.enter="onSearch" />
        <el-input v-model="searchForm.request_method" placeholder="方法" clearable size="small" style="width:90px" @keyup.enter="onSearch" />
        <el-input v-model="searchForm.request_ip" placeholder="IP" clearable size="small" style="width:130px" @keyup.enter="onSearch" />
        <el-input v-model="searchForm.creator_name" placeholder="操作人" clearable size="small" style="width:120px" @keyup.enter="onSearch" />
        <el-button type="primary" :icon="Search" size="small" @click="onSearch">搜索</el-button>
        <el-button :icon="Refresh" size="small" @click="onReset" class="btn-reset">重置</el-button>
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
              <el-button size="small" text @click="showDetail(row)">{{ $t('message.operationLogPage.view') }}</el-button>
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
import { ref, onMounted } from 'vue'
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
@use '/@/styles/global' as *;

.oplog-page {
  display: flex; flex-direction: column;
  background: $g-bg-page; overflow: hidden;
  min-height: 400px;
}

/* ===== Body ===== */
.oplog-body {
  flex: 1; overflow-y: auto; padding: 0 16px 24px;
}

/* ===== Filter Bar ===== */
.oplog-filter-bar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 12px 0; position: sticky; top: 0; z-index: 10;
  background: $g-bg-page;
}
.btn-reset { min-width: 56px; }

/* ===== Table Card ===== */
.oplog-table-card {
  background: #fff; border-radius: 14px; box-shadow: $g-shadow-card; overflow: hidden;
}
.oplog-table-card :deep(.el-table th.el-table__cell) {
  background: $g-bg-header; color: $g-text-secondary; font-weight: 600; font-size: 12px;
}
.oplog-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.oplog-table-card :deep(.el-table__body tr.current-row > td) { background: $g-bg-light-blue; }

/* ===== Response Code Badge ===== */
.oplog-code-badge {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 2px 10px; border-radius: 10px; min-width: 40px; text-align: center;
}
.code-success { background: $g-bg-success; color: #67C23A; }
.code-redirect { background: $g-bg-light-blue; color: #409EFF; }
.code-client-err { background: $g-bg-warning; color: #E6A23C; }
.code-server-err { background: $g-bg-danger; color: #F56C6C; }

/* ===== Pagination ===== */
.oplog-pagination {
  display: flex; justify-content: flex-end; padding: 12px 16px;
}

/* ===== Detail Drawer ===== */
.oplog-detail-drawer {
  --el-drawer-padding-primary: 0;
}
.oplog-detail-drawer :deep(.el-drawer__header) {
  margin-bottom: 0; padding: $g-padding-dialog-header;
  border-bottom: 1px solid $g-border-light;
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
  font-weight: 500; color: $g-text-secondary;
}
.oplog-detail-section {
  margin-top: 4px;
}
.oplog-detail-label {
  font-size: 13px; font-weight: 600; color: $g-text-primary;
  margin-bottom: 8px;
}
.oplog-detail-code {
  background: $g-bg-card; border-radius: $g-radius-sm;
  padding: 12px; font-size: 12px; line-height: 1.5;
  max-height: 280px; overflow: auto; white-space: pre-wrap; word-break: break-all;
  margin: 0; border: 1px solid $g-border-card;
}
</style>
