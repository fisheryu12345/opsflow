<!--
  Identity Sync Tab — 身份数据源同步管理
  复用 cloud-sync 的卡片+历史模式
-->
<template>
  <div class="int-section g-fade-in-up is-wrap">
    <!-- Provider Status Cards -->
    <div class="is-cards" v-if="loaded && sources.length">
      <div v-for="s in sources" :key="s.instance_id" class="is-card" :class="{ 'is-card-inactive': s.status !== 'online' }">
        <div class="is-card-header">
          <span class="is-card-name">{{ s.instance_name }}</span>
          <el-tag size="small" :type="s.status === 'online' ? 'success' : 'info'">
            {{ s.status === 'online' ? $t('message.identitySync.active') : $t('message.identitySync.inactive') }}
          </el-tag>
        </div>
        <div class="is-card-body">
          <div class="is-row">
            <span class="is-label">{{ $t('message.identitySync.lastSync') }}:</span>
            <span>{{ s.last_sync_at ? formatTime(s.last_sync_at) : '-' }}</span>
          </div>
          <div class="is-row">
            <span class="is-label">{{ $t('message.identitySync.deptCount') }}:</span>
            <span>{{ s.dept_count }}</span>
          </div>
          <div class="is-row">
            <span class="is-label">{{ $t('message.identitySync.userCount') }}:</span>
            <span>{{ s.user_count }}</span>
          </div>
        </div>
        <div class="is-card-footer">
          <el-button size="small" type="primary" :loading="syncing === s.instance_id" @click="triggerSync(s.instance_id)" style="margin-right:8px">
            {{ $t('message.identitySync.syncNow') }}
          </el-button>
          <el-button size="small" @click="testConnection(s.instance_id)" :loading="testing === s.instance_id">
            {{ $t('message.identitySync.testConnect') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="!loaded" class="is-empty">{{ $t('message.identitySync.loading') }}</div>

    <!-- Empty state -->
    <div v-if="loaded && !sources.length" class="is-empty">
      <el-empty :description="$t('message.identitySync.noSource')" :image-size="60" />
    </div>

    <!-- Sync History -->
    <div class="int-table-card" style="margin-top:12px" v-if="loaded && sources.length">
      <div class="int-table-header">
        <span class="int-table-title">{{ $t('message.identitySync.history') }}</span>
        <el-button :icon="Refresh" text size="small" @click="loadAll" :disabled="!loaded">
          {{ $t('message.identitySync.refresh') }}
        </el-button>
      </div>
      <el-table :data="historyItems" v-loading="historyLoading" stripe size="small" style="width:100%"
        :empty-text="$t('message.identitySync.noHistory')">
        <el-table-column :label="$t('message.identitySync.colTime')" min-width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.identitySync.colStatus')" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.identitySync.colTotal')" width="60" prop="total" />
        <el-table-column :label="$t('message.identitySync.colErrors')" width="60" prop="error_count" />
        <el-table-column :label="$t('message.identitySync.colTrigger')" width="80">
          <template #default="{ row }">{{ triggerLabel(row.triggered_by) }}</template>
        </el-table-column>
        <el-table-column label="" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_message" style="color:#F56C6C;font-size:12px">{{ row.error_message }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSyncStatus, triggerSync as triggerSyncApi, testConnection as testConnApi, getSyncHistory } from '/@/api/integration/identity-sync'

const { t } = useI18n()

const loaded = ref(false)
const sources = ref<any[]>([])
const syncing = ref<number | null>(null)
const testing = ref<number | null>(null)
const historyItems = ref<any[]>([])
const historyLoading = ref(false)

async function loadAll() {
  loaded.value = false
  await Promise.all([fetchSources(), fetchHistory()])
}

async function fetchSources() {
  try {
    const res = await getSyncStatus()
    sources.value = res?.data || []
  } catch {
    sources.value = []
  } finally {
    loaded.value = true
  }
}

async function triggerSync(instanceId: number) {
  syncing.value = instanceId
  try {
    const res = await triggerSyncApi(instanceId)
    ElMessage.success(t('message.identitySync.syncDone'))
    setTimeout(() => {
      fetchSources()
      fetchHistory()
    }, 2000)
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.identitySync.syncFailed'))
  } finally {
    syncing.value = null
  }
}

async function testConnection(instanceId: number) {
  testing.value = instanceId
  try {
    const res = await testConnApi(instanceId)
    ElMessage.success(t('message.identitySync.testConnectSuccess'))
    fetchSources()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.identitySync.testConnectFailed'))
  } finally {
    testing.value = null
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    // 默认使用第一个来源的历史
    if (sources.value.length) {
      const res = await getSyncHistory(sources.value[0].instance_id)
      historyItems.value = res?.data || []
    }
  } catch {
    historyItems.value = []
  } finally {
    historyLoading.value = false
  }
}

function statusTag(status: string): string {
  return { running: 'warning', success: 'success', failed: 'danger' }[status] || 'info'
}

function statusLabel(status: string): string {
  return {
    running: t('message.identitySync.running'),
    success: t('message.identitySync.success'),
    failed: t('message.identitySync.failed'),
  }[status] || status
}

function triggerLabel(t: string): string {
  return { schedule: t('message.identitySync.schedule'), manual: t('message.identitySync.manual') }[t] || t
}

function formatTime(tm: string): string {
  if (!tm) return '-'
  return tm.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  fetchSources()
})
</script>

<style scoped>
.is-wrap { padding-top: 16px; }
.is-empty { padding: 60px 0; text-align: center; color: #909399; font-size: 14px; }
.is-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 12px; }
.is-card { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; }
.is-card-inactive { opacity: 0.55; }
.is-card-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #f2f2f2; }
.is-card-name { flex: 1; font-weight: 600; font-size: 14px; color: #303133; }
.is-card-body { padding: 12px 16px; display: flex; flex-direction: column; gap: 6px; }
.is-row { font-size: 13px; display: flex; gap: 4px; }
.is-label { color: #909399; min-width: 70px; flex-shrink: 0; }
.is-card-footer { padding: 8px 16px; border-top: 1px solid #f2f2f2; display: flex; flex-wrap: wrap; }
</style>
