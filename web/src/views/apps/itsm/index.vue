<template>
  <!-- Designer view -->
  <Designer v-if="designerMode" :workflow-id="designerWorkflowId" @back="onCloseDesigner" />
  <!-- List view -->
  <div v-else class="itsm-page">
    <!-- ===== Hero Section ===== -->
    <div class="itsm-hero">
      <div class="itsm-hero-bg" />
      <div class="itsm-hero-inner">
        <div class="itsm-hero-left">
          <h1 class="itsm-hero-title">ITSM</h1>
          <p class="itsm-hero-subtitle">{{ $t('message.itsmPage.subtitle') }}</p>
        </div>
        <div ref="heroSearchRef" class="itsm-hero-search" />
        <div class="itsm-hero-stats">
          <template v-for="(stat, i) in heroStats" :key="i">
            <div v-if="i > 0" class="itsm-stat-divider" />
            <div class="itsm-stat-item">
              <span class="itsm-stat-value">{{ stat.value }}</span>
              <span class="itsm-stat-label">{{ stat.label }}</span>
            </div>
          </template>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="itsm-hero-tabs">
        <div v-for="tab in pageConfig?.tabs" :key="tab.key"
          class="itsm-hero-tab"
          :class="{ active: activeTab === tab.key, locked: !tab.has_access }"
          @click="onTabClick(tab)">
          <el-icon><component :is="iconMap[tab.icon]" /></el-icon>
          {{ isEn ? tab.label_en : tab.label_zh }}
          <span v-if="!tab.has_access" class="tab-lock">🔒</span>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="itsm-body">

      <!-- TAB: Dashboard -->
      <div v-if="isVisited('dashboard')" v-show="activeTab === 'dashboard'" class="itsm-section g-fade-in-up">
        <Dashboard :active="activeTab === 'dashboard'" @view-ticket="onViewTicket" @switch-tab="activeTab = $event" />
      </div>

      <!-- TAB: Service Market -->
      <div v-if="isVisited('service-market')" v-show="activeTab === 'service-market'" class="itsm-section g-fade-in-up">
        <ServiceMarket :active="activeTab === 'service-market'" @goTicket="onGoTicket" />
      </div>

      <!-- TAB: Service Admin -->
      <div v-if="isVisited('service-admin')" v-show="activeTab === 'service-admin'" class="itsm-section g-fade-in-up">
        <ServiceAdmin :active="activeTab === 'service-admin'" />
      </div>

      <!-- TAB: Tickets -->
      <div v-if="isVisited('tickets')" v-show="activeTab === 'tickets'" class="itsm-section g-fade-in-up">
        <TicketList :active="activeTab === 'tickets'" @viewTicket="onViewTicket" />
      </div>

      <!-- TAB: Workflows -->
      <div v-if="isVisited('workflows')" v-show="activeTab === 'workflows'" class="itsm-section g-fade-in-up">
        <WorkflowList :active="activeTab === 'workflows'" @openDesigner="onOpenDesigner" />
      </div>

      <!-- TAB: SLA -->
      <div v-if="isVisited('sla')" v-show="activeTab === 'sla'" class="itsm-section g-fade-in-up">
        <SlaPolicyList :active="activeTab === 'sla'" />
      </div>

      <!-- TAB: Delegation -->
      <div v-if="isVisited('delegation')" v-show="activeTab === 'delegation'" class="itsm-section g-fade-in-up">
        <Delegation :active="activeTab === 'delegation'" />
      </div>

      <!-- TAB: Escalation -->
      <div v-if="isVisited('escalation')" v-show="activeTab === 'escalation'" class="itsm-section g-fade-in-up">
        <EscalationList :active="activeTab === 'escalation'" />
      </div>

      <!-- TAB: Presets -->
      <div v-if="isVisited('presets')" v-show="activeTab === 'presets'" class="itsm-section g-fade-in-up">
        <PresetList :active="activeTab === 'presets'" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'
import { useHeroProvider, type HeroStatItem } from '/@/composables/useHeroProvider'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'
import Designer from './designer/index.vue'
import { useI18n } from 'vue-i18n'
import { usePermissionStore } from '/@/stores/permission'
import Dashboard from './Dashboard.vue'
import Delegation from './Delegation.vue'
import ServiceMarket from './catalog/ServiceMarket.vue'
import ServiceAdmin from './catalog/ServiceAdmin.vue'
import TicketList from './components/TicketList.vue'
import WorkflowList from './components/WorkflowList.vue'
import SlaPolicyList from './components/SlaPolicyList.vue'
import EscalationList from './components/EscalationList.vue'
import PresetList from './components/PresetList.vue'
import { DataAnalysis, List, Setting, WarningFilled, Edit, Clock, User, Collection } from '@element-plus/icons-vue'

// ===== Page Config (data-driven tabs) =====
const pageConfig = ref<any>(null)
const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))
const permissionStore = usePermissionStore()

function getTab(key: string) {
  return pageConfig.value?.tabs?.find((t: any) => t.key === key)
}

async function loadPageConfig() {
  try {
    const res = await request({ url: '/api/iam/page-permissions/', params: { app: 'itsm' } })
    pageConfig.value = res.data
    const defaultTab = res.data.tabs.find((t: any) => t.is_default) || res.data.tabs[0]
    if (defaultTab) activeTab.value = defaultTab.key
    const savedTab = sessionStorage.getItem('itsm_active_tab')
    if (savedTab && getTab(savedTab)) {
      activeTab.value = savedTab
      sessionStorage.removeItem('itsm_active_tab')
    }
  } catch { /* show empty */ }
}

const iconMap: Record<string, any> = {
  DataAnalysis, List, Setting, WarningFilled, Edit, Clock, User, Collection,
}

function onTabClick(tab: any) {
  if (!tab.has_access) {
    permissionStore.requestPerm(tab.label_zh, tab.required_perm)
    return
  }
  activeTab.value = tab.key
}

// ===== Tab state =====
const activeTab = ref('tickets')
const router = useRouter()

// ===== Designer =====
const designerMode = ref(false)
const designerWorkflowId = ref(0)

function onOpenDesigner(wfId?: number) {
  designerWorkflowId.value = wfId || 0
  designerMode.value = true
}

function onCloseDesigner() {
  designerMode.value = false
  // Force tab remount to reload workflow list
  projectChangedTrigger.value++
}

// ===== Navigation =====
function onGoTicket(ticketId: number) {
  router.push('/apps/itsm/ticket/' + ticketId)
}

function onViewTicket(row: any) {
  if (row?.id) router.push('/apps/itsm/ticket/' + row.id)
}

// ===== Project change trigger =====
const projectChangedTrigger = ref(0)
function onProjectChanged() { projectChangedTrigger.value++ }

// ===== Tab lazy loading (all tabs are component-based, self-load on mount) =====
const { isVisited } = useTabLazyLoad({
  tabs: ['dashboard', 'service-market', 'service-admin', 'tickets', 'workflows', 'sla', 'delegation', 'escalation'],
  activeTab,
  resetOn: projectChangedTrigger,
})

// ===== Hero stats =====
const { stats: heroStats, searchRef: heroSearchRef, updateStats } = useHeroProvider()

updateStats([
  { value: 0, label: '工单' },
  { value: 0, label: '流程' },
  { value: 0, label: 'SLA' },
])

watch(activeTab, (tab) => {
  if (tab === 'dashboard') {
    updateStats([
      { value: '-', label: '待处理' },
      { value: '-', label: '已逾期' },
      { value: '-', label: '今日解决' },
      { value: '-', label: '平均解决(h)' },
    ])
  } else if (tab === 'service-market') {
    updateStats([
      { value: '-', label: '服务总数' },
      { value: '-', label: '流程模式' },
      { value: '-', label: '轻量模式' },
    ])
  } else if (tab === 'service-admin') {
    updateStats([
      { value: '-', label: '服务总数' },
      { value: '-', label: '已启用' },
      { value: '-', label: '已禁用' },
    ])
  } else if (tab === 'tickets') {
    updateStats([
      { value: '-', label: '工单总数' },
      { value: '-', label: '处理中' },
      { value: '-', label: '草稿' },
      { value: '-', label: '已完成' },
    ])
  } else if (tab === 'workflows') {
    updateStats([
      { value: '-', label: '模板总数' },
      { value: '-', label: '已发布' },
      { value: '-', label: '草稿' },
    ])
  } else if (tab === 'sla') {
    updateStats([
      { value: '-', label: '策略总数' },
      { value: '-', label: '已启用' },
    ])
  } else if (tab === 'delegation') {
    updateStats([
      { value: '-', label: '规则总数' },
      { value: '-', label: '已启用' },
    ])
  } else if (tab === 'escalation') {
    updateStats([
      { value: '-', label: '层级总数' },
      { value: '-', label: '已启用' },
    ])
  }
})

onMounted(async () => {
  await loadPageConfig()
  window.addEventListener('project-changed', onProjectChanged)
  const key = 'opsflow_tour_itsm'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🎫 ITSM — 全新 pipeline 驱动工单引擎，支持 AI 创建审批流程', duration: 1500 })
    localStorage.setItem(key, 'true')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.itsm-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.itsm-hero { @include g-hero-container; }
.itsm-hero-bg { @include g-hero-bg-dots; }
.itsm-hero-inner { @include g-hero-inner; flex-direction: row; }
.itsm-hero-left { flex: 1 1 auto; }
.itsm-hero-title { @include g-hero-title; }
.itsm-hero-subtitle { @include g-hero-subtitle; }
.itsm-hero-search {
  margin-left: auto; margin-right: 20px;
  display: flex; align-items: center;
  :deep(.sm-search-input),
  :deep(.sa-search-input) { width: 280px; }
  :deep(.el-input__wrapper) {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: none; border-radius: 10px;
  }
  :deep(.el-input__inner) { color: #fff; font-size: 14px; }
  :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
  :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
}
.itsm-hero-stats { flex: 0 0 auto; display: flex; align-items: center; gap: 6px; }
.itsm-stat-item { text-align: center; padding: 0 10px; }
.itsm-stat-value { @include g-hero-stat-value; }
.itsm-stat-label { @include g-hero-stat-label; text-transform: uppercase; letter-spacing: 0.5px; }
.itsm-stat-divider { @include g-hero-stat-divider; flex-shrink: 0; }

.itsm-hero-tabs { @include g-hero-tabs; }
.itsm-hero-tab { @include g-hero-tab;
  .el-icon { font-size: 16px; }
  &.locked { opacity: 0.6; }
  &.locked:hover { opacity: 0.9; background: rgba(255,193,7,0.1); border-bottom-color: #ffc107; }
  .tab-lock { font-size: 11px; margin-left: 3px; }
}

/* ===== Body ===== */
.itsm-body { flex: 1; display: flex; flex-direction: column; padding: 0; }
.itsm-section { flex: 1; min-height: 0; padding: 16px 20px 0; overflow-y: auto; }
</style>

<!-- Shared utility styles for tab components (non-scoped so child components can use them) -->
<style lang="scss">
@use '/@/styles/global' as *;

/* ===== Filter bar ===== */
.itsm-filter-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 0 12px; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa;
}
.itsm-filter-tabs { display: flex; gap: 2px; }
.itsm-tab {
  display: flex; align-items: center; gap: 6px; padding: 7px 16px;
  border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266;
  cursor: pointer; transition: all 0.2s; user-select: none;
}
.itsm-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.itsm-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.itsm-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.itsm-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table Card ===== */
.itsm-table-card {
  background: #fff; border-radius: 14px; box-shadow: $g-shadow-card; overflow: hidden;
}
.itsm-table-card .el-table th.el-table__cell { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.itsm-table-card .el-table__body tr:hover td { background: #f5f7fa; }
.itsm-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.itsm-table-title { font-size: 15px; font-weight: 600; color: $g-text-primary; }

/* ===== Status Badge ===== */
.itsm-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.itsm-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.it-status-draft .itsm-status-dot { background: #c0c4cc; }
.it-status-draft { background: #f5f7fa; color: #909399; }
.it-status-running .itsm-status-dot { background: #409EFF; }
.it-status-running { background: #ecf5ff; color: #409EFF; }
.it-status-finished .itsm-status-dot,
.it-status-success .itsm-status-dot,
.it-status-resolved .itsm-status-dot { background: #67C23A; }
.it-status-finished { background: #f0f9eb; color: #67C23A; }
.it-status-success { background: #f0f9eb; color: #67C23A; }
.it-status-resolved { background: #f0f9eb; color: #67C23A; }
.it-status-terminated .itsm-status-dot,
.it-status-failed .itsm-status-dot,
.it-status-danger .itsm-status-dot,
.it-status-escalated .itsm-status-dot { background: #F56C6C; }
.it-status-terminated { background: #fef0f0; color: #F56C6C; }
.it-status-failed { background: #fef0f0; color: #F56C6C; }
.it-status-suspended .itsm-status-dot { background: #E6A23C; }
.it-status-suspended { background: #fdf6ec; color: #E6A23C; }
.it-status-new .itsm-status-dot,
.it-status-open .itsm-status-dot { background: #409EFF; }
.it-status-new { background: #ecf5ff; color: #409EFF; }
.it-status-open { background: #ecf5ff; color: #409EFF; }
.it-status-assigned .itsm-status-dot,
.it-status-pending_approval .itsm-status-dot { background: #E6A23C; }
.it-status-assigned { background: #fdf6ec; color: #E6A23C; }
.it-status-pending_approval { background: #fdf6ec; color: #E6A23C; }
.it-status-closed .itsm-status-dot { background: #c0c4cc; }
.it-status-closed { background: #f5f7fa; color: #909399; }

/* ===== SLA Badge ===== */
.sla-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 8px; }
.sla-normal { background: #f0f9eb; color: #67C23A; }
.sla-warning { background: #fdf6ec; color: #E6A23C; }
.sla-violated { background: #fef0f0; color: #F56C6C; }

/* ===== Priority Badge ===== */
.itsm-prio-badge {
  display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px;
}
.it-prio-p1 { background: #fef0f0; color: #F56C6C; }
.it-prio-p2 { background: #fdf6ec; color: #E6A23C; }
.it-prio-p3,
.it-prio-p4 { background: #f0f9eb; color: #67C23A; }
.it-prio-low { background: #f0f9eb; color: #67C23A; }
.it-prio-medium { background: #fdf6ec; color: #E6A23C; }
.it-prio-high { background: #fef0f0; color: #F56C6C; }
.it-prio-critical { background: #fbe9e7; color: #D32F2F; }

/* ===== Workflow Grid ===== */
.itsm-wf-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(315px, 1fr)); gap: 14px;
}
.itsm-wf-card {
  border-radius: $g-radius-card; overflow: hidden;
  &:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); transition: all 0.2s; }
}
.itsm-wf-card-inner {
  background: #fff; border: 1px solid $g-border-default; border-radius: $g-radius-card;
  padding: 18px; height: 100%; display: flex; flex-direction: column;
}
.itsm-wf-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.itsm-wf-type-tag {
  display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.wf-type-change { background: #fdf6ec; color: #E6A23C; }
.wf-type-incident { background: #fef0f0; color: #F56C6C; }
.itsm-wf-name { font-weight: 600; font-size: 15px; color: $g-text-primary; margin-bottom: 6px; }
.itsm-wf-desc { font-size: 12px; color: $g-text-secondary; line-height: 1.5; flex: 1; margin-bottom: 10px; }
.itsm-wf-meta { font-size: 11px; color: $g-text-muted; display: flex; justify-content: space-between; margin-bottom: 10px; }
.itsm-wf-actions { display: flex; gap: 0px; padding-top: 8px; border-top: 1px solid $g-border-light; flex-wrap: nowrap; font-size: 11px; }
.itsm-wf-actions .el-button { padding: 2px 6px; height: auto; font-size: 12px; }
.itsm-wf-empty { grid-column: 1 / -1; }

/* ===== Dialog ===== */
.itsm-dialog .el-dialog__header { @include g-dialog-header; }
.itsm-dialog .el-dialog__body { @include g-dialog-body; }
.itsm-dialog .el-dialog__footer { @include g-dialog-footer; }

/* ===== AI Preview ===== */
.itsm-ai-preview {
  border: 1px solid #d9ecff; border-radius: 8px; padding: 14px; background: #ecf5ff;
}
.itsm-ai-preview-header { font-size: 13px; font-weight: 600; margin-bottom: 10px; color: $g-text-primary; }
.itsm-ai-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.itsm-ai-node { display: inline-flex; align-items: center; gap: 2px; font-size: 12px; }
.itsm-ai-node-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px;
}
.node-approval { background: #fdf6ec; color: #E6A23C; }
.node-normal { background: #ecf5ff; color: #409EFF; }
.node-task { background: #f0f9eb; color: #67C23A; }
</style>
