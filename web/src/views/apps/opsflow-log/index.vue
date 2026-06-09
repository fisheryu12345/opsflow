<template>
  <div class="log-page">
    <!-- Hero Section -->
    <div class="log-hero">
      <div class="log-hero-bg" />
      <div class="log-hero-inner">
        <div class="log-hero-left">
          <h1 class="log-hero-title">{{ $t('message.opsflowPage.auditLogTitle') }}</h1>
          <p class="log-hero-subtitle">{{ $t('message.opsflowPage.auditLogSubtitle') }}</p>
        </div>
        <ProjectSwitcher :dark="true" />
        <div class="log-hero-center">
          <el-input v-model="searchQuery" :placeholder="$t('message.opsflowPage.auditSearchPlaceholder')" clearable size="default"
            class="log-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="log-hero-stats">
          <div class="log-stat-item"><span class="log-stat-value">{{ total }}</span><span class="log-stat-label">{{ $t('message.opsflowPage.auditStatTotal') }}</span></div>
          <div class="log-stat-divider" />
          <div class="log-stat-item"><span class="log-stat-value">{{ errCount }}</span><span class="log-stat-label">{{ $t('message.opsflowPage.auditStatErrors') }}</span></div>
          <div class="log-stat-divider" />
          <div class="log-stat-item"><span class="log-stat-value">{{ highRiskCount }}</span><span class="log-stat-label">{{ $t('message.opsflowPage.auditStatHighRisk') }}</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="log-body">
      <!-- Filter bar -->
      <div class="log-filter-bar">
        <div class="log-filter-tabs">
          <div class="log-tab" :class="{ active: filterRisk === '' }" @click="filterRisk = ''; onSearch()">
            <span class="log-tab-dot" style="background:#409EFF" />{{ $t('message.opsflowPage.auditFilterAll') }}
          </div>
          <div class="log-tab" :class="{ active: filterRisk === 'low' }" @click="filterRisk = 'low'; onSearch()">
            <span class="log-tab-dot" style="background:#67C23A" />{{ $t('message.opsflowPage.auditFilterLow') }}
          </div>
          <div class="log-tab" :class="{ active: filterRisk === 'medium' }" @click="filterRisk = 'medium'; onSearch()">
            <span class="log-tab-dot" style="background:#E6A23C" />{{ $t('message.opsflowPage.auditFilterMedium') }}
          </div>
          <div class="log-tab" :class="{ active: filterRisk === 'high' }" @click="filterRisk = 'high'; onSearch()">
            <span class="log-tab-dot" style="background:#F56C6C" />{{ $t('message.opsflowPage.auditFilterHigh') }}
          </div>
          <div class="log-tab" :class="{ active: filterRisk === 'critical' }" @click="filterRisk = 'critical'; onSearch()">
            <span class="log-tab-dot" style="background:#F56C6C" />{{ $t('message.opsflowPage.auditFilterCritical') }}
          </div>
        </div>
        <div class="log-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">{{ $t('message.common.refresh') }}</el-button>
        </div>
      </div>

      <!-- Table card -->
      <div class="log-table-card">
        <el-table :data="list" v-loading="loading" stripe style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column :label="$t('message.opsflowPage.auditColRisk')" width="90" align="center">
            <template #default="{ row }">
              <span class="log-risk-badge" :class="'risk-' + row.risk_level">{{ row.risk_level }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="step" :label="$t('message.opsflowPage.auditColStep')" min-width="150" show-overflow-tooltip />
          <el-table-column :label="$t('message.opsflowPage.auditColCommand')" min-width="220" show-overflow-tooltip>
            <template #default="{ row }"><code class="log-cmd">{{ row.command || '-' }}</code></template>
          </el-table-column>
          <el-table-column :label="$t('message.opsflowPage.auditColReturn')" width="70" align="center">
            <template #default="{ row }">
              <span class="log-return" :class="row.returncode === 0 ? 'ok' : 'err'">{{ row.returncode ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('message.opsflowPage.auditColExecution')" width="90" align="center">
            <template #default="{ row }">#{{ row.execution }}</template>
          </el-table-column>
          <el-table-column prop="created_at" :label="$t('message.opsflowPage.auditColTime')" width="160" />
          <el-table-column :label="$t('message.execution.colActions')" width="70" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="showDetail(row)">{{ $t('message.opsflowPage.auditView') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="log-pagination" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @current-change="onPageChange" small />
        </div>
      </div>
    </div>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" :title="$t('message.opsflowPage.auditDetailTitle')" width="740px" top="5vh" destroy-on-close class="log-detail-dialog">
      <template v-if="detailRow">
        <div class="log-detail-meta">
          <span class="log-risk-badge" :class="'risk-' + detailRow.risk_level">{{ detailRow.risk_level }}</span>
          <span class="log-detail-info">{{ $t('message.opsflowPage.auditDetailStep') }}: <b>{{ detailRow.step }}</b></span>
          <span class="log-detail-info">{{ $t('message.opsflowPage.auditDetailReturn') }}: <b :class="detailRow.returncode === 0 ? 'text-green' : 'text-red'">{{ detailRow.returncode ?? '-' }}</b></span>
          <span class="log-detail-info">{{ detailRow.created_at }}</span>
        </div>
        <div class="log-detail-section" v-if="detailRow.command">
          <div class="log-detail-label">{{ $t('message.opsflowPage.auditColCommand') }}</div>
          <pre class="log-detail-code">{{ detailRow.command }}</pre>
        </div>
        <div class="log-detail-section" v-if="detailRow.stdout">
          <div class="log-detail-label">{{ $t('message.opsflowPage.auditStdout') }}</div>
          <pre class="log-detail-code">{{ detailRow.stdout }}</pre>
        </div>
        <div class="log-detail-section" v-if="detailRow.stderr">
          <div class="log-detail-label">{{ $t('message.opsflowPage.auditStderr') }}</div>
          <pre class="log-detail-code log-stderr">{{ detailRow.stderr }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { GetLogs } from '../opsflow/api/logs'

import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'
const { t } = useI18n()
const loading = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterRisk = ref('')
const searchQuery = ref('')
const detailVisible = ref(false)
const detailRow = ref<any>(null)

const errCount = computed(() => list.value.filter(l => l.returncode !== 0 && l.returncode != null).length)
const highRiskCount = computed(() => list.value.filter(l => l.risk_level === 'high' || l.risk_level === 'critical').length)
const emptyText = computed(() => loading.value ? t('message.common.loading') : t('message.opsflowPage.auditNoLogs'))

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterRisk.value) params.risk_level = filterRisk.value
    const res = await GetLogs(params)
    const items = res.data?.results || res.data || res.results || []
    list.value = items
    total.value = res.data?.count || res.count || items.length || 0
  } catch { /* ignore */ }
  loading.value = false
}

function onSearch() { page.value = 1; fetchData() }
function onPageChange() { fetchData() }
function showDetail(row: any) { detailRow.value = row; detailVisible.value = true }

onMounted(async () => {
  const { useOpsflowStore } = await import('/@/views/apps/opsflow/stores/opsflowStore');
  const store = useOpsflowStore();
  if (!store.myProjects.length) await store.fetchMyProjects();
  fetchData()

  const key = 'opsflow_tour_log'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: t('message.opsflowPage.auditTourMsg'), duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style scoped>
.log-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.log-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.log-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.log-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.log-hero-left { flex: 0 0 auto; }
.log-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.log-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.log-hero-center { flex: 1 1 auto; min-width: 0; }
.log-search-input { width: 100%; max-width: 320px; }
.log-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.log-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.log-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.log-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.log-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.log-stat-item { text-align: center; padding: 0 14px; }
.log-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.log-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.log-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.log-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.log-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.log-filter-tabs { display: flex; gap: 4px; }
.log-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.log-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.log-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.log-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.log-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table card ===== */
.log-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.log-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.log-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.log-risk-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; text-transform: uppercase; }
.risk-low { background: #f0f9eb; color: #67C23A; }
.risk-medium { background: #fdf6ec; color: #E6A23C; }
.risk-high { background: #fef0f0; color: #F56C6C; }
.risk-critical { background: #fbe9e7; color: #D32F2F; }
.log-cmd { font-size: 11px; font-family: 'SF Mono', monospace; color: #606266; }
.log-return { font-weight: 700; font-size: 13px; }
.log-return.ok { color: #67C23A; }
.log-return.err { color: #F56C6C; }
.log-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }

/* ===== Detail ===== */
.log-detail-dialog :deep(.el-dialog__header) { padding-bottom: 8px; }
.log-detail-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.log-detail-info { font-size: 13px; color: #606266; }
.text-green { color: #67C23A; }
.text-red { color: #F56C6C; }
.log-detail-section { margin-bottom: 16px; }
.log-detail-label { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 6px; }
.log-detail-code { background: #f5f7fa; border-radius: 8px; padding: 12px; font-size: 12px; line-height: 1.5; max-height: 300px; overflow: auto; white-space: pre-wrap; word-break: break-all; margin: 0; border: 1px solid #f0f0f0; }
.log-stderr { color: #F56C6C; }
</style>
