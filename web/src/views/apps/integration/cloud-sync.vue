<template>
  <div class="int-section g-fade-in-up cs-wrap">

    <!-- Provider Status Cards -->
    <div class="cs-cards" v-if="loaded && providers.length">
      <div v-for="p in providers" :key="p.code" class="cs-card" :class="{ 'cs-card-inactive': !p.active }">
        <div class="cs-card-header">
          <span class="cs-card-name">{{ isEn ? p.name_en : p.name }}</span>
          <el-tag v-if="p.active" size="small" type="success">{{ t('message.cloudSync.active') }}</el-tag>
          <el-tag v-else size="small" type="info">{{ t('message.cloudSync.inactive') }}</el-tag>
        </div>
        <div class="cs-card-body">
          <template v-if="p.last_sync">
            <div class="cs-row"><span class="cs-label">{{ t('message.cloudSync.lastSync') }}:</span><span>{{ formatTime(p.last_sync.started_at) || '-' }}</span></div>
            <div class="cs-row"><span class="cs-label">{{ t('message.cloudSync.total') }}:</span><span>{{ p.last_sync.total }}</span></div>
            <div class="cs-row">
              <span class="cs-label">{{ t('message.cloudSync.status') }}:</span>
              <el-tag :type="statusTag(p.last_sync.status)" size="small">{{ statusLabel(p.last_sync.status) }}</el-tag>
            </div>
          </template>
          <div v-else class="cs-muted">{{ t('message.cloudSync.noSync') }}</div>
        </div>
        <div class="cs-card-footer">
          <el-button size="small" type="primary" :loading="syncing === p.code" @click="triggerSync(p.code)">
            {{ t('message.cloudSync.syncNow') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="!loaded" class="cs-loading">{{ t('message.cloudSync.loading') }}</div>

    <!-- Empty state -->
    <div v-if="loaded && !providers.length" class="cs-empty">
      <el-empty :description="t('message.cloudSync.noProvider')" :image-size="60" />
    </div>

    <!-- Sync Actions Toolbar -->
    <div class="int-table-card cs-toolbar" v-if="loaded">
      <div class="cs-toolbar-inner">
        <div class="cs-toolbar-left">
          <span class="cs-toolbar-label">{{ t('message.cloudSync.title') }}</span>
          <span class="cs-toolbar-hint">{{ t('message.cloudSync.subtitle') }}</span>
        </div>
        <div class="cs-toolbar-right">
          <el-button type="primary" :icon="Refresh" :loading="syncing === 'all'" @click="triggerSyncAll" :disabled="!providers.length">
            {{ t('message.cloudSync.syncAll') }}
          </el-button>
          <el-button :icon="Refresh" text size="small" @click="loadAll" :disabled="!loaded">
            {{ t('message.cloudSync.refresh') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Sync History -->
    <div class="int-table-card" style="margin-top:12px" v-if="loaded">
      <div class="int-table-header">
        <span class="int-table-title">{{ t('message.cloudSync.history') }}</span>
      </div>
      <el-table :data="historyItems" v-loading="historyLoading" stripe size="small" style="width:100%"
        :empty-text="t('message.cloudSync.noHistory')">
        <el-table-column :label="t('message.cloudSync.colTime')" min-width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('message.cloudSync.colProvider')" min-width="80">
          <template #default="{ row }">{{ providerLabel(row.provider) }}</template>
        </el-table-column>
        <el-table-column :label="t('message.cloudSync.colStatus')" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('message.cloudSync.colTotal')" width="60" prop="total" />
        <el-table-column :label="t('message.cloudSync.colErrors')" width="60" prop="error_count" />
        <el-table-column :label="t('message.cloudSync.colTrigger')" width="80">
          <template #default="{ row }">{{ triggerLabel(row.triggered_by) }}</template>
        </el-table-column>
        <el-table-column label="" min-width="200">
          <template #default="{ row }">
            <span v-if="row.errors?.length" style="color:#F56C6C;font-size:12px">{{ row.errors[0]?.error || JSON.stringify(row.errors[0]) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'

const { t, locale } = useI18n()
const isEn = computed(() => locale.value === 'en')

const loaded = ref(false)
const providers = ref<any[]>([])
const syncing = ref('')
const historyItems = ref<any[]>([])
const historyLoading = ref(false)

async function fetchProviders() {
  try {
    const res = await request({ url: '/api/cmdb/cloud-sync/providers/', method: 'get' })
    providers.value = res?.data || []
  } catch (e: any) {
    ElMessage.error(t('message.cloudSync.loadFailed'))
    providers.value = []
  } finally {
    loaded.value = true
  }
}

async function triggerSync(code: string) {
  syncing.value = code
  try {
    await request({ url: `/api/cmdb/cloud-sync/${code}/trigger/`, method: 'post' })
    ElMessage.success(t('message.cloudSync.syncTriggered'))
    setTimeout(() => {
      fetchProviders()
      fetchHistory()
    }, 3000)
  } catch {
    ElMessage.error(t('message.cloudSync.syncFailed'))
  } finally {
    syncing.value = ''
  }
}

async function triggerSyncAll() {
  syncing.value = 'all'
  try {
    const codes = providers.value.map(p => p.code)
    if (!codes.length) {
      ElMessage.warning(t('message.cloudSync.noProvider'))
      return
    }
    await Promise.all(codes.map(code =>
      request({ url: `/api/cmdb/cloud-sync/${code}/trigger/`, method: 'post' })
    ))
    ElMessage.success(t('message.cloudSync.syncTriggered'))
    setTimeout(() => {
      fetchProviders()
      fetchHistory()
    }, 3000)
  } catch {
    ElMessage.error(t('message.cloudSync.syncFailed'))
  } finally {
    syncing.value = ''
  }
}

async function loadAll() {
  loaded.value = false
  await Promise.all([fetchProviders(), fetchHistory()])
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await request({ url: '/api/cmdb/cloud-sync/aliyun/history/', method: 'get', params: { page_size: 20 } })
    historyItems.value = res?.data?.items || []
  } catch {
    historyItems.value = []
  } finally {
    historyLoading.value = false
  }
}

function providerLabel(code: string): string {
  const labels: Record<string, string> = { aliyun: '阿里云', aws: 'AWS', tencent: '腾讯云' }
  return labels[code] || code
}

function statusTag(status: string): string {
  return { running: 'warning', success: 'success', failed: 'danger' }[status] || 'info'
}

function statusLabel(status: string): string {
  return { running: t('message.cloudSync.running'), success: t('message.cloudSync.success'), failed: t('message.cloudSync.failed') }[status] || status
}

function triggerLabel(t: string): string {
  return { schedule: t('message.cloudSync.schedule'), manual: t('message.cloudSync.manual'), pipeline: t('message.cloudSync.pipeline') }[t] || t
}

function formatTime(tm: string): string {
  if (!tm) return '-'
  return tm.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  fetchProviders()
  fetchHistory()
})
</script>

<style scoped>
.cs-wrap { padding-top: 16px; }
.cs-loading { padding: 60px 0; text-align: center; color: #909399; font-size: 14px; }
.cs-empty { margin: 20px 0; }
.cs-toolbar { margin-bottom: 12px; }
.cs-toolbar-inner { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; }
.cs-toolbar-left { display: flex; align-items: center; gap: 12px; }
.cs-toolbar-label { font-size: 15px; font-weight: 600; color: #303133; }
.cs-toolbar-hint { font-size: 12px; color: #909399; }
.cs-toolbar-right { display: flex; align-items: center; gap: 8px; }
.cs-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-bottom: 12px; }
.cs-card { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; }
.cs-card-inactive { opacity: 0.55; }
.cs-card-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #f2f2f2; }
.cs-card-name { flex: 1; font-weight: 600; font-size: 14px; color: #303133; }
.cs-card-body { padding: 12px 16px; display: flex; flex-direction: column; gap: 6px; }
.cs-row { font-size: 13px; display: flex; gap: 4px; }
.cs-label { color: #909399; min-width: 70px; flex-shrink: 0; }
.cs-muted { color: #ccc; font-size: 13px; }
.cs-card-footer { padding: 8px 16px; border-top: 1px solid #f2f2f2; }
</style>
