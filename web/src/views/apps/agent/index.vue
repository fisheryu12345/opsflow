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
            <el-button text size="small" @click="showAgentDetail(row)">{{ $t('message.agentPage.actionDetail') }}</el-button>
            <el-button text size="small" @click="openExec(row)">{{ $t('message.agentPage.actionExec') }}</el-button>
            <el-button text size="small" @click="refreshToken(row)">{{ $t('message.agentPage.actionRefreshToken') }}</el-button>
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

    <!-- Detail Drawer -->
    <el-drawer v-model="showDetail" :title="$t('message.agentDetailPage.title')" size="600px">
      <template v-if="detailAgent">
        <!-- Basic Info -->
        <div class="g-card ag-detail-card">
          <div class="g-card-header">{{ $t('message.agentDetailPage.basicInfo') }}</div>
          <div class="g-card-body ag-detail-grid">
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.hostname') }}</label><span>{{ detailAgent.hostname }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.ip') }}</label><span>{{ detailAgent.ip }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.osType') }}</label><span>{{ detailAgent.os_type || '-' }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.osVersion') }}</label><span>{{ detailAgent.os_version || '-' }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.arch') }}</label><span>{{ detailAgent.arch || '-' }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.agentVersion') }}</label><span>{{ detailAgent.agent_version }}</span></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.status') }}</label><el-tag :type="detailAgent.status === 'online' ? 'success' : 'danger'" size="small">{{ statusLabel(detailAgent.status) }}</el-tag></div>
            <div class="ag-detail-field"><label>{{ $t('message.agentDetailPage.heartbeat') }}</label><span>{{ formatTime(detailAgent.last_heartbeat) || '-' }}</span></div>
            <div class="ag-detail-field ag-detail-field-full"><label>{{ $t('message.agentDetailPage.agentId') }}</label><span style="font-family:monospace;font-size:12px">{{ detailAgent.agent_id }}</span></div>
          </div>
        </div>

        <!-- Processes -->
        <div class="g-card ag-detail-card" style="margin-top:16px">
          <div class="g-card-header">
            <span>{{ $t('message.agentDetailPage.processes') }}</span>
            <el-button text size="small" :icon="Refresh" @click="loadProcesses" :loading="procLoading" />
          </div>
          <div class="g-card-body" v-loading="procLoading">
            <el-empty v-if="!processes.length && !procLoading" :description="$t('message.agentDetailPage.noProcesses')" />
            <el-table v-else :data="processes" stripe size="small" max-height="400">
              <el-table-column :label="$t('message.agentDetailPage.colName')" prop="name" min-width="100" />
              <el-table-column :label="$t('message.agentDetailPage.colPid')" prop="pid" width="60" />
              <el-table-column :label="$t('message.agentDetailPage.colStatus')" width="70">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small">{{ $t('message.agentDetailPage.' + (row.status === 'running' ? 'appRunning' : 'appStopped')) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="$t('message.agentDetailPage.colCpu')" width="65">
                <template #default="{ row }">{{ row.cpu_percent?.toFixed(1) }}</template>
              </el-table-column>
              <el-table-column :label="$t('message.agentDetailPage.colMem')" width="70">
                <template #default="{ row }">{{ row.memory_mb?.toFixed(0) }}</template>
              </el-table-column>
              <el-table-column :label="$t('message.agentDetailPage.colUser')" prop="user" width="80" />
              <el-table-column :label="$t('message.agentDetailPage.colSource')" prop="source" width="80" />
              <el-table-column :label="$t('message.agentDetailPage.colPorts')" min-width="100">
                <template #default="{ row }">
                  <span v-if="row.listen_addrs" style="font-size:11px">{{ parsePorts(row.listen_addrs) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- Config -->
        <div class="g-card ag-detail-card" style="margin-top:16px">
          <div class="g-card-header">
            <span>{{ $t('message.agentDetailPage.configSection') }}</span>
          </div>
          <div class="g-card-body">
            <div class="ag-detail-field">
              <label>{{ $t('message.agentDetailPage.appUsersLabel') }}</label>
              <el-select v-model="configAppUsers" multiple filterable allow-create default-first-option
                :placeholder="$t('message.agentDetailPage.appUserTip')" style="width:100%" @change="onConfigChanged">
                <el-option v-for="u in configAppUsers" :key="u" :label="u" :value="u" />
              </el-select>
              <div style="margin-top:8px">
                <el-button type="primary" size="small" :loading="configSaving" @click="saveConfig" :disabled="!configDirty">{{ $t('message.agentDetailPage.saveConfig') }}</el-button>
                <span v-if="configAppUsers.length === 0" style="font-size:11px;color:#909399;margin-left:8px">{{ $t('message.agentDetailPage.configEmptyHint') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Registered Apps -->
        <div class="g-card ag-detail-card" style="margin-top:16px">
          <div class="g-card-header">
            <span>{{ $t('message.agentDetailPage.regApps') }}</span>
            <el-button text size="small" :icon="Plus" @click="showRegApp = true">{{ $t('message.agentDetailPage.regNewApp') }}</el-button>
          </div>
          <div class="g-card-body">
            <el-empty v-if="!regApps.length" :description="$t('message.agentDetailPage.noRegApps')" />
            <div v-else v-for="app in regApps" :key="app.name" class="ag-reg-item">
              <div class="ag-reg-item-name">{{ app.name }}</div>
              <el-tag :type="app.running ? 'success' : 'info'" size="small">{{ app.running ? $t('message.agentDetailPage.appRunning') : $t('message.agentDetailPage.appStopped') }}</el-tag>
              <span style="color:#999;font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ app.command }}</span>
              <el-button text size="small" type="danger" :icon="Delete" @click="doUnregisterApp(app.name)" />
            </div>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- Register App Dialog -->
    <el-dialog v-model="showRegApp" :title="$t('message.agentDetailPage.regNewApp')" width="500px" class="opsflow-dialog">
      <el-form :label-width="120">
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.appNameTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.appName') }} <span style="color:#F56C6C">*</span></span>
            </el-tooltip>
          </template>
          <el-input v-model="regForm.name" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.commandTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.command') }} <span style="color:#F56C6C">*</span></span>
            </el-tooltip>
          </template>
          <el-input v-model="regForm.command" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.appUserTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.appUser') }} <span style="color:#909399;font-size:11px">{{ $t('message.agentDetailPage.optional') }}</span></span>
            </el-tooltip>
          </template>
          <el-input v-model="regForm.user" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.stopCommandTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.stopCommand') }} <span style="color:#909399;font-size:11px">{{ $t('message.agentDetailPage.optional') }}</span></span>
            </el-tooltip>
          </template>
          <el-input v-model="regForm.stop_command" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.pidFileTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.pidFile') }} <span style="color:#909399;font-size:11px">{{ $t('message.agentDetailPage.optional') }}</span></span>
            </el-tooltip>
          </template>
          <el-input v-model="regForm.pid_file" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip :content="$t('message.agentDetailPage.autoRestartTip')" placement="top">
              <span>{{ $t('message.agentDetailPage.autoRestart') }}</span>
            </el-tooltip>
          </template>
          <el-switch v-model="regForm.auto_restart" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRegApp = false">{{ $t('message.agentDetailPage.cancel') }}</el-button>
        <el-button type="primary" @click="doRegisterApp">{{ $t('message.agentDetailPage.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts" name="AgentPage">
import { markRaw, ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, UploadFilled, Refresh, Monitor, SuccessFilled, RemoveFilled, Top, Delete } from '@element-plus/icons-vue'
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

/* ── Detail Drawer ── */
const showDetail = ref(false)
const detailAgent = ref<AgentInstance | null>(null)
const processes = ref<any[]>([])
const procLoading = ref(false)
const regApps = ref<any[]>([])
const showRegApp = ref(false)
const regForm = reactive({ name: '', command: '', user: '', stop_command: '', pid_file: '', auto_restart: false })
const configAppUsers = ref<string[]>([])
const configSaving = ref(false)
const configDirty = ref(false)

function onConfigChanged() { configDirty.value = true }
function saveConfig() {
  if (!detailAgent.value?.id) return
  configSaving.value = true
  agentApi.setAgentConfig(detailAgent.value.id, { app_users: configAppUsers.value }).then(() => {
    ElMessage.success(t('message.agentDetailPage.configSaved'))
    configDirty.value = false
  }).catch(() => { ElMessage.error(t('message.agentDetailPage.configSaveFailed')) }).finally(() => { configSaving.value = false })
}

function openDetail(row: AgentInstance): void {
  detailAgent.value = row
  showDetail.value = true
  loadProcesses()
  loadRegApps()
  const tags = (row as any).tags || {}
  configAppUsers.value = Array.isArray(tags.app_users) ? tags.app_users : []
}

function loadProcesses(): void {
  if (!detailAgent.value?.ip) return
  procLoading.value = true
  agentApi.getAgentProcesses(detailAgent.value.ip).then((res: any) => {
    processes.value = Array.isArray(res.data) ? res.data : Array.isArray(res) ? res : []
  }).catch(() => { processes.value = [] }).finally(() => { procLoading.value = false })
}

function loadRegApps(): void {
  if (!detailAgent.value?.agent_id) return
  agentApi.getAgentApps(detailAgent.value.agent_id).then((res: any) => {
    regApps.value = res.data?.apps || []
  }).catch(() => { regApps.value = [] })
}

function parsePorts(addrs: any): string {
  if (!addrs) return '-'
  try {
    const list = typeof addrs === 'string' ? JSON.parse(addrs) : addrs
    return list.map((a: any) => `${a.ip}:${a.port}`).join(', ')
  } catch { return String(addrs || '-') }
}

function doRegisterApp(): void {
  if (!detailAgent.value?.agent_id || !regForm.name) return
  agentApi.registerAgentApp(detailAgent.value.agent_id, { ...regForm }).then(() => {
    ElMessage.success(t('message.agentDetailPage.registerSuccess'))
    showRegApp.value = false
    regForm.name = ''; regForm.command = ''; regForm.user = ''; regForm.stop_command = ''; regForm.pid_file = ''; regForm.auto_restart = false
    loadRegApps()
  }).catch(() => { /* ignore */ })
}

function doUnregisterApp(name: string): void {
  if (!detailAgent.value?.agent_id) return
  ElMessageBox.confirm(
    t('message.agentDetailPage.unregisterConfirm', { name }),
    t('message.agentDetailPage.unregisterTitle'),
    { confirmButtonText: t('message.agentDetailPage.submit'), cancelButtonText: t('message.agentDetailPage.cancel'), type: 'warning' },
  ).then(() => {
    agentApi.unregisterAgentApp(detailAgent.value!.agent_id!, name).then(() => {
      ElMessage.success(t('message.agentDetailPage.unregisterSuccess', { name }))
      loadRegApps()
    }).catch(() => { /* ignore */ })
  }).catch(() => { /* ignore */ })
}

function showAgentDetail(row: AgentInstance): void {
  openDetail(row)
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

/* Detail */
.ag-detail-card { margin-bottom:0; }
.ag-detail-grid { display:flex; flex-wrap:wrap; gap:0; }
.ag-detail-field { width:50%; padding:8px 0; border-bottom:1px solid $g-border-light; }
.ag-detail-field-full { width:100%; }
.ag-detail-field label { display:block; font-size:11px; color:$g-text-muted; margin-bottom:2px; }
.ag-detail-field span { font-size:13px; color:$g-text-primary; }
.ag-reg-item { display:flex; align-items:center; gap:8px; padding:8px 0; border-bottom:1px solid $g-border-light; }
.ag-reg-item-name { font-weight:600; min-width:80px; }
</style>
