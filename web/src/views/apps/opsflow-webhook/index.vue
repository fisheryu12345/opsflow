<template>
  <div class="wh-page">
    <!-- Hero Section -->
    <div v-if="!embedded" class="wh-hero">
      <div class="wh-hero-bg" />
      <div class="wh-hero-inner">
        <div class="wh-hero-left">
          <h1 class="wh-hero-title">{{ $t("message.opsflowPage.webhookTitle") }}</h1>
          <p class="wh-hero-subtitle">{{ $t("message.opsflowPage.webhookSubtitle") }}</p>
        </div>
        <div class="wh-hero-center">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('message.opsflowPage.webhookSearch')"
            clearable
            size="default"
            class="wh-search-input"
            @keyup.enter="onSearch"
            @clear="onSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="wh-hero-stats">
          <div class="wh-stat-item"><span class="wh-stat-value">{{ total }}</span><span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatTotal") }}</span></div>
          <div class="wh-stat-divider" />
          <div class="wh-stat-item"><span class="wh-stat-value">{{ activeCount }}</span><span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatActive") }}</span></div>
          <div class="wh-stat-divider" />
          <div class="wh-stat-item"><span class="wh-stat-value">{{ failedLogs }}</span><span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatErr") }}</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="wh-body">
      <!-- Filter bar -->
      <div class="wh-filter-bar">
        <div class="wh-filter-tabs">
          <div class="wh-tab" :class="{ active: filterEvent === '' }" @click="filterEvent = ''; onSearch()">
            <span class="wh-tab-dot" style="background:#409EFF" />{{ $t("message.opsflowPage.webhookFilterAll") }}
          </div>
          <div class="wh-tab" :class="{ active: filterEvent === 'completed' }" @click="filterEvent = 'completed'; onSearch()">
            <span class="wh-tab-dot" style="background:#67C23A" />{{ $t("message.execution.statCompleted") }}
          </div>
          <div class="wh-tab" :class="{ active: filterEvent === 'failed' }" @click="filterEvent = 'failed'; onSearch()">
            <span class="wh-tab-dot" style="background:#F56C6C" />{{ $t("message.execution.statFailed") }}
          </div>
        </div>
        <div class="wh-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">{{ $t("message.common.refresh") }}</el-button>
          <el-button type="primary" :icon="Plus" @click="showForm(null)" size="small">{{ $t("message.opsflowPage.webhookAdd") }}</el-button>
        </div>
      </div>

      <!-- Grid -->
      <div class="wh-grid" v-loading="loading">
        <el-empty v-if="!loading && webhooks.length === 0" :description="emptyText" :image-size="80" />
        <div
          v-for="w in webhooks" :key="w.id"
          class="wh-card"
          @click="showDetail(w)"
        >
          <div class="wh-card-top">
            <div class="wh-card-header">
              <div class="wh-card-badge" :class="w.enabled ? 'badge-active' : 'badge-paused'">
                {{ w.enabled ? $t('message.opsflowPage.webhookActive') : $t('message.opsflowPage.webhookPaused') }}
              </div>
              <div class="wh-card-event-tags">
                <span v-for="ev in (w.trigger_events || [])" :key="ev"
                  class="wh-event-tag" :class="'event-' + ev">{{ ev }}</span>
              </div>
            </div>
            <div class="wh-card-name">{{ w.name }}</div>
            <div class="wh-card-url">{{ w.url }}</div>
          </div>
          <div class="wh-card-bottom">
            <div class="wh-card-meta">
              <span class="wh-card-template">📋 {{ w.template_name || '-' }}</span>
              <span class="wh-card-secret" v-if="w.has_secret">🔐 {{ $t("message.opsflowPage.webhookSigned") }}</span>
            </div>
            <div class="wh-card-actions">
              <el-tag type="info" size="small" effect="plain">Retry {{ w.retry_count }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit dialog -->
    <el-dialog v-model="formVisible" :title="formId ? $t('message.opsflowPage.webhookEdit') : $t('message.opsflowPage.webhookAdd')" width="560px" top="5vh" destroy-on-close>
      <el-form label-width="100px" size="small">
        <el-form-item :label="$t('message.common.name')" required>
          <el-input v-model="form.name" :placeholder="$t('message.opsflowPage.webhookNamePlaceholder')" maxlength="128" />
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.webhookUrl')" required>
          <el-input v-model="form.url" :placeholder="$t('message.opsflowPage.webhookUrlPlaceholder')" maxlength="1024" />
        </el-form-item>
        <el-form-item :label="$t('message.execution.colTemplate')" required>
          <el-select v-model="form.template_id" :placeholder="$t('message.opsflowPage.webhookSelectTemplate')" filterable style="width:100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.webhookEvents')">
          <el-checkbox-group v-model="form.trigger_events">
            <el-checkbox value="completed" size="small">{{ $t("message.execution.statCompleted") }}</el-checkbox>
            <el-checkbox value="failed" size="small">{{ $t("message.execution.statFailed") }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.webhookSecret')">
          <el-input v-model="form.secret" :placeholder="$t('message.opsflowPage.webhookSecretPlaceholder')" type="password" show-password maxlength="256" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('message.properties.maxRetries')">
              <el-input-number v-model="form.retry_count" :min="0" :max="10" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('message.opsflowPage.webhookInterval')">
              <el-input-number v-model="form.retry_interval" :min="5" :max="3600" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false" >{{ $t("message.common.cancel") }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" >{{ formId ? $t('message.opsflowPage.webhookUpdate') : $t('message.opsflowPage.webhookCreate') }}</el-button>
      </template>
    </el-dialog>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" :title="detail?.name || ''" width="680px" top="5vh" destroy-on-close class="wh-detail-dialog">
      <template v-if="detail">
        <div class="wh-detail-meta">
          <span class="wh-detail-badge" :class="detail.enabled ? 'badge-active' : 'badge-paused'">
            {{ detail.enabled ? $t('message.opsflowPage.webhookActive') : $t('message.opsflowPage.webhookPaused') }}
          </span>
          <span class="wh-detail-events">
            <span v-for="ev in (detail.trigger_events || [])" :key="ev" class="wh-event-tag" :class="'event-' + ev">{{ ev }}</span>
          </span>
        </div>
        <el-descriptions :column="1" border size="small" class="wh-detail-descs">
          <el-descriptions-item :label="$t('message.opsflowPage.webhookUrl')">{{ detail.url }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.execution.colTemplate')">{{ detail.template_name }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.opsflowPage.webhookRetry')">{{ detail.retry_count }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.opsflowPage.webhookInterval')">{{ detail.retry_interval }}s</el-descriptions-item>
          <el-descriptions-item :label="$t('message.opsflowPage.webhookSecret')">{{ detail.has_secret ? $t('message.opsflowPage.webhookConfigured') : '—' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.opsflowPage.webhookCreated')">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <!-- {{ $t("message.opsflowPage.webhookDeliveryLogs") }} -->
        <div class="wh-detail-section">
          <div class="wh-detail-section-title">{{ $t("message.opsflowPage.webhookDeliveryLogs") }}</div>
          <el-table :data="logs" v-loading="logLoading" stripe size="small" :empty-text="$t('message.opsflowPage.webhookNoLogs')">
            <el-table-column :label="$t('message.opsflowPage.webhookEvent')" width="90">
              <template #default="{ row }">
                <span class="wh-event-tag" :class="'event-' + row.event" style="font-size:11px">{{ row.event }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.execution.status')" width="90">
              <template #default="{ row }">
                <span :class="'wh-log-status status-' + row.status">{{ row.status }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.opsflowPage.webhookHttp')" width="60" align="center">
              <template #default="{ row }">{{ row.response_status || '—' }}</template>
            </el-table-column>
            <el-table-column :label="$t('message.execution.retry')" width="50" align="center">{{ row.retry_count }}</el-table-column>
            <el-table-column :label="$t('message.opsflowPage.webhookError')" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.error_message || '—' }}</template>
            </el-table-column>
            <el-table-column :label="$t('message.opsflowPage.webhookTime')" width="160">
              <template #default="{ row }">{{ row.created_at }}</template>
            </el-table-column>
          </el-table>
        </div>

        <div class="wh-detail-actions">
          <el-button size="small" :icon="Edit" @click="showForm(detail); detailVisible = false">{{ $t("message.common.edit") }}</el-button>
          <el-popconfirm title="Delete this webhook?" @confirm="handleDelete(detail)">
            <template #reference>
              <el-button size="small" type="danger" :icon="Delete">{{ $t("message.common.delete") }}</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Link } from '@element-plus/icons-vue'
import { GetTemplates } from '../opsflow/api/templates'
import {
  GetWebhooks, CreateWebhook, UpdateWebhook, DeleteWebhook, GetWebhookLogs,
} from '../opsflow/api/webhooks'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

const { t } = useI18n()
const loading = ref(false)
const saving = ref(false)
const webhooks = ref<any[]>([])
const templates = ref<any[]>([])
const searchQuery = ref('')
const filterEvent = ref('')

const total = computed(() => webhooks.value.length)
const activeCount = computed(() => webhooks.value.filter(w => w.enabled).length)
const failedLogs = computed(() => 0)  // placeholder

const emptyText = computed(() => t('message.opsflowPage.webhookEmptyText'))

// Form
const formVisible = ref(false)
const formId = ref<number | null>(null)
const form = ref({ name: '', url: '', trigger_events: ['completed'], secret: '', template_id: null, retry_count: 3, retry_interval: 10 })

// Detail
const detailVisible = ref(false)
const detail = ref<any>(null)
const logLoading = ref(false)
const logs = ref<any[]>([])

async function fetchData() {
  loading.value = true
  try {
    const tmplRes = await GetTemplates()
    const allTemplates = tmplRes.data || tmplRes.results || []
    templates.value = allTemplates

    const results: any[] = []
    for (const t of allTemplates) {
      const res = await GetWebhooks(t.id)
      const items = (res as any).data || []
      results.push(...items.map((h: any) => ({ ...h, template_name: t.name, template_id: t.id })))
    }
    webhooks.value = searchQuery.value
      ? results.filter(w => w.name.toLowerCase().includes(searchQuery.value.toLowerCase()) || w.url.includes(searchQuery.value))
      : results
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.opsflowPage.webhookLoadFailed'))
  } finally {
    loading.value = false
  }
}

function showForm(row: any | null) {
  if (row) {
    formId.value = row.id
    form.value = {
      name: row.name, url: row.url, trigger_events: row.trigger_events || ['completed'],
      secret: '', template_id: row.template_id, retry_count: row.retry_count ?? 3, retry_interval: row.retry_interval ?? 10,
    }
  } else {
    formId.value = null
    form.value = { name: '', url: '', trigger_events: ['completed'], secret: '', template_id: null, retry_count: 3, retry_interval: 10 }
  }
  formVisible.value = true
}

async function handleSave() {
  if (!form.value.name || !form.value.url || !form.value.template_id) {
    ElMessage.warning(t('message.opsflowPage.webhookRequired')); return
  }
  saving.value = true
  try {
    if (formId.value) {
      await UpdateWebhook(form.value.template_id, formId.value, form.value)
      ElMessage.success(t('message.opsflowPage.webhookUpdated'))
    } else {
      await CreateWebhook(form.value.template_id, form.value)
      ElMessage.success(t('message.opsflowPage.webhookCreated'))
    }
    formVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.opsflowPage.webhookSaveFailed'))
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await DeleteWebhook(row.template_id, row.id)
    ElMessage.success(t('message.opsflowPage.webhookDeleted'))
    detailVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.opsflowPage.webhookDeleteFailed'))
  }
}

async function showDetail(row: any) {
  detail.value = row
  logs.value = []
  detailVisible.value = true
  logLoading.value = true
  try {
    const res = await GetWebhookLogs(row.template_id, row.id)
    logs.value = (res as any).data || []
  } catch { /* ignore */ }
  logLoading.value = false
}

async function onSearch() { fetchData() }

onMounted(async () => {
  const { useOpsflowStore } = await import('/@/views/apps/opsflow/stores/opsflowStore');
  const store = useOpsflowStore();
  if (!store.myProjects.length) await store.fetchMyProjects();
  fetchData()
})
</script>

<style scoped>
/* ===== Layout ===== */
.wh-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.wh-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.wh-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.wh-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.wh-hero-left { flex: 0 0 auto; }
.wh-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.wh-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.wh-hero-center { flex: 1 1 auto; min-width: 0; }
.wh-search-input { width: 100%; max-width: 320px; }
.wh-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.wh-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.wh-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.wh-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.wh-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.wh-stat-item { text-align: center; padding: 0 14px; }
.wh-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.wh-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.wh-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.wh-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.wh-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.wh-filter-tabs { display: flex; gap: 4px; }
.wh-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.wh-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.wh-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.wh-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.wh-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Grid ===== */
.wh-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; padding-bottom: 24px; min-height: 200px; }

/* ===== Card ===== */
.wh-card { display: flex; flex-direction: column; justify-content: space-between; background: #fff; border-radius: 14px; padding: 20px; cursor: pointer; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); border: 1px solid #f0f0f0; position: relative; overflow: hidden; }
.wh-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1); border-color: transparent; }
.wh-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; opacity: 0; transition: opacity 0.25s; }
.wh-card:hover::before { opacity: 1; }
.wh-card:nth-child(4n+1)::before { background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.wh-card:nth-child(4n+2)::before { background: linear-gradient(90deg, #67C23A, #95de64); }
.wh-card:nth-child(4n+3)::before { background: linear-gradient(90deg, #E6A23C, #f5d76e); }
.wh-card:nth-child(4n+4)::before { background: linear-gradient(90deg, #9B59B6, #c39bd3); }

.wh-card-top { flex: 1; }
.wh-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.wh-card-badge { display: inline-flex; align-items: center; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
.badge-active { background: #f0f9eb; color: #67C23A; }
.badge-paused { background: #f5f5f5; color: #909399; }
.wh-card-event-tags { display: flex; gap: 4px; }
.wh-event-tag { display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.3px; }
.event-completed { background: #f0f9eb; color: #67C23A; }
.event-failed { background: #fef0f0; color: #F56C6C; }

.wh-card-name { font-size: 16px; font-weight: 700; color: #1a1a2e; line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.wh-card-url { font-size: 12px; color: #909399; line-height: 1.5; font-family: 'SF Mono', monospace; word-break: break-all; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.wh-card-bottom { margin-top: 14px; padding-top: 14px; border-top: 1px solid #f5f5f5; display: flex; justify-content: space-between; align-items: center; }
.wh-card-template { font-size: 12px; color: #909399; }
.wh-card-secret { font-size: 11px; color: #E6A23C; margin-left: 8px; }
.wh-card-actions { display: flex; gap: 6px; }

/* ===== Detail dialog ===== */
.wh-detail-dialog :deep(.el-dialog__header) { padding-bottom: 8px; }
.wh-detail-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.wh-detail-badge { display: inline-flex; align-items: center; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; }
.wh-detail-descs { margin-bottom: 16px; }
.wh-detail-section { margin-bottom: 16px; }
.wh-detail-section-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
.wh-detail-actions { display: flex; gap: 8px; margin-top: 12px; }
.wh-log-status { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 8px; }
.status-success { background: #f0f9eb; color: #67C23A; }
.status-pending { background: #fdf6ec; color: #E6A23C; }
.status-failed { background: #fef0f0; color: #F56C6C; }
</style>
