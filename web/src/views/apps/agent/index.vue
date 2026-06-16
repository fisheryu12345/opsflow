<!--
  Agent 管理主页面：列表/安装/执行/文件推送
  /agent → apps/agent/index
-->
<template>
  <div class="ag-page">
    <!-- Hero -->
    <div class="ag-hero">
      <div class="ag-hero-bg" />
      <div class="ag-hero-inner">
        <div class="ag-hero-left">
          <h1 class="ag-hero-title">{{ $t('message.agentPage.title') }}</h1>
          <p class="ag-hero-subtitle">{{ $t('message.agentPage.subtitle') }}</p>
        </div>
        <div class="ag-hero-actions">
          <el-button type="primary" :icon="Plus" @click="showInstall = true">
            {{ $t('message.agentPage.batchInstall') }}
          </el-button>
          <el-button :icon="UploadFilled" @click="$router.push('/apps/agent/upgrade')">
            {{ $t('message.agentPage.upgrade') }}
          </el-button>
          <el-button :icon="Refresh" circle @click="loadStats" />
        </div>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="ag-stats g-fade-in-up" style="--i:0">
      <div v-for="(s, si) in statsCards" :key="s.key" class="g-card ag-stat-card" :style="{ '--i': si }">
        <div class="ag-stat-icon" :style="{ background: s.color }"><el-icon :size="24"><component :is="s.icon" /></el-icon></div>
        <div class="ag-stat-body">
          <div class="ag-stat-value">{{ s.value }}</div>
          <div class="ag-stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="ag-toolbar">
      <el-select v-model="filter.status" :placeholder="$t('message.agentPage.filterStatus')" clearable class="ag-filter-select">
        <el-option :label="$t('message.agentPage.statusOnline')" value="online" />
        <el-option :label="$t('message.agentPage.statusOffline')" value="offline" />
        <el-option :label="$t('message.agentPage.statusUnknown')" value="unknown" />
      </el-select>
      <el-select v-model="filter.os_type" :placeholder="$t('message.agentPage.filterOs')" clearable class="ag-filter-select">
        <el-option :label="$t('message.agentPage.osLinux')" value="linux" />
        <el-option :label="$t('message.agentPage.osWindows')" value="windows" />
        <el-option :label="$t('message.agentPage.osAix')" value="aix" />
      </el-select>
      <el-input v-model="filter.search" :placeholder="$t('message.agentPage.filterSearch')" clearable class="ag-search-input" @clear="loadList">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button :icon="Refresh" @click="loadList" />
    </div>

    <!-- Agent Table -->
    <div class="g-card" style="padding:0">
      <el-table :data="agents" v-loading="loading" stripe style="width:100%">
        <el-table-column :label="$t('message.agentPage.colHostname')" prop="hostname" min-width="120" />
        <el-table-column :label="$t('message.agentPage.colIp')" prop="ip" min-width="130" />
        <el-table-column :label="$t('message.agentPage.colOs')" min-width="70">
          <template #default="{ row }">
            <el-tag :type="row.os_type === 'linux' ? 'success' : row.os_type === 'windows' ? 'primary' : 'warning'" size="small">
              {{ row.os_type || $t('message.agentPage.emptyDash') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.agentPage.colStatus')" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : row.status === 'offline' ? 'danger' : 'info'" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.agentPage.colVersion')" prop="agent_version" min-width="70" />
        <el-table-column :label="$t('message.agentPage.colHeartbeat')" min-width="140">
          <template #default="{ row }">
            <span class="ag-hb-time">{{ row.last_heartbeat ? formatTime(row.last_heartbeat) : $t('message.agentPage.emptyDash') }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.agentPage.colActions')" min-width="210" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="showDetail(row)">{{ $t('message.agentPage.actionDetail') }}</el-button>
            <el-button text size="small" @click="openExec(row)">{{ $t('message.agentPage.actionExec') }}</el-button>
            <el-button text size="small" @click="refreshToken(row)">Token</el-button>
            <el-button text size="small" @click="openFilePush(row)">{{ $t('message.agentPage.push') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="ag-pagination">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total,prev,pager,next" @current-change="loadList" />
      </div>
    </div>

    <!-- Dialogs -->
    <AgentInstallDialog v-model="showInstall" @installed="onInstalled" />
    <AgentExecDialog v-model="showExec" :target="execTarget" />
    <AgentFilePushDialog v-model="showFile" :target="fileTarget" />
  </div>
</template>

<script setup lang="ts" name="AgentPage">
import { markRaw, ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, Plus, UploadFilled, Refresh, Monitor, SuccessFilled, RemoveFilled, Top } from '@element-plus/icons-vue'
import * as agentApi from '/@/api/agent'
import type { AgentInstance, AgentStats, DetailResponse } from '/@/api/agent'
import AgentInstallDialog from './components/AgentInstallDialog.vue'
import AgentExecDialog from './components/AgentExecDialog.vue'
import AgentFilePushDialog from './components/AgentFilePushDialog.vue'

const { t } = useI18n()

/* ── List state ── */
const agents = ref<AgentInstance[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filter = reactive<{ status: string; os_type: string; search: string }>({ status: '', os_type: '', search: '' })
const stats = reactive<AgentStats>({ total: 0, online: 0, offline: 0, upgrading: 0 })

/* ── Dialog state ── */
const showInstall = ref(false)
const showExec = ref(false)
const showFile = ref(false)
const execTarget = ref<AgentInstance | null>(null)
const fileTarget = ref<AgentInstance | null>(null)

function openExec(row: AgentInstance) { execTarget.value = row; showExec.value = true }
function openFilePush(row: AgentInstance) { fileTarget.value = row; showFile.value = true }

onMounted(() => { loadStats(); loadList() })

const statsCards = computed(() => [
  { key: 'total', label: t('message.agentPage.statTotal'), value: stats.total, icon: markRaw(Monitor), color: '#409EFF' },
  { key: 'online', label: t('message.agentPage.statOnline'), value: stats.online, icon: markRaw(SuccessFilled), color: '#67C23A' },
  { key: 'offline', label: t('message.agentPage.statOffline'), value: stats.offline, icon: markRaw(RemoveFilled), color: '#F56C6C' },
  { key: 'upgrading', label: t('message.agentPage.statUpgrading'), value: stats.upgrading, icon: markRaw(Top), color: '#E6A23C' },
])

function statusLabel(status: string): string {
  if (status === 'online') return t('message.agentPage.statusOnline')
  if (status === 'offline') return t('message.agentPage.statusOffline')
  return t('message.agentPage.statusUnknown')
}

function loadStats(): void {
  agentApi.getAgentStats().then((res: DetailResponse<AgentStats>) => {
    Object.assign(stats, res.data || res)
  }).catch(() => { /* ignore */ })
}

function loadList(): void {
  loading.value = true
  const cleanFilter = Object.fromEntries(
    Object.entries(filter).filter(([_, v]) => v !== '')
  )
  agentApi.getAgentList({ page: page.value, ...cleanFilter }).then((res: any) => {
    agents.value = res.data || []
    total.value = res.total || agents.value.length
  }).catch(() => { /* ignore */ }).finally(() => { loading.value = false })
}

function showDetail(row: AgentInstance): void {
  window.open(`/apps/agent/detail/${row.id}`)
}

function refreshToken(row: AgentInstance): void {
  agentApi.refreshAgentToken(row.id).then((res: any) => {
    const token = res?.data?.token || ''
    ElMessage.success(`${t('message.agentPage.msgTokenSuccess')}: ${token}`)
  }).catch(() => { /* ignore */ })
}

function onInstalled(): void {
  loadList()
  loadStats()
}

function formatTime(tm: string): string {
  return tm?.replace('T', ' ')?.substring(0, 19) || ''
}
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

.ag-page { padding: 0; }

/* Hero */
.ag-hero { position:relative; flex-shrink:0; overflow:hidden; background:linear-gradient(135deg,#1a1a2e,#16213e); }
.ag-hero-bg { position:absolute; inset:0; opacity:0.06; background-image:radial-gradient(circle at 20% 50%,#fff 1px,transparent 1px),radial-gradient(circle at 80% 30%,#fff 1px,transparent 1px); background-size:40px 40px; }
.ag-hero-inner { position:relative; z-index:1; padding:14px 24px; display:flex; justify-content:space-between; align-items:center; }
.ag-hero-title { margin:0; font-size:22px; font-weight:800; color:#fff; }
.ag-hero-subtitle { margin:0; font-size:11px; color:rgba(255,255,255,0.5); }
.ag-hero-actions { display:flex; gap:8px; flex-shrink:0; }

/* Stats */
.ag-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; padding:0 24px; margin-bottom:24px; }
.ag-stat-card { display:flex; align-items:center; padding:20px; }
.ag-stat-icon { width:48px; height:48px; border-radius:$g-radius; display:flex; align-items:center; justify-content:center; color:#fff; margin-right:16px; flex-shrink:0; }
.ag-stat-value { font-size:28px; font-weight:700; line-height:1.2; }
.ag-stat-label { font-size:13px; color:$g-text-muted; margin-top:2px; }

/* Toolbar */
.ag-toolbar { display:flex; align-items:center; padding:0 24px; margin-bottom:16px; gap:12px; }
.ag-filter-select { width:120px; }
.ag-search-input { width:220px; }

/* Table */
.ag-hb-time { font-size:12px; color:$g-text-muted; }
.ag-pagination { display:flex; justify-content:flex-end; padding:12px 24px; }
</style>
