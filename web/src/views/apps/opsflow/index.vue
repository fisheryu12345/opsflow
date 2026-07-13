<template>
  <!-- ===== Canvas Mode: full-screen pipeline designer ===== -->
  <div v-if="canvasMode" class="opsflow-canvas-page">
    <!-- AI chat float panel -->
    <div v-if="chatExpanded" class="chat-float-panel">
      <div class="chat-float-header">
        <div class="chat-header-left">
          <el-icon size="16"><ChatDotSquare /></el-icon>
          <span>{{ $t("message.ai.title") }}</span>
        </div>
        <div class="chat-header-actions">
          <el-tooltip :show-after="500" :content="$t('message.ai.quickStart')" placement="bottom">
            <el-button size="small" circle :icon="Reading" @click="store.openHelpDrawer()" class="chat-hdr-btn" />
          </el-tooltip>
          <el-button size="small" circle :icon="Fold" @click="chatExpanded = false" class="chat-hdr-btn" />
        </div>
      </div>
      <div class="chat-float-history" ref="chatScrollRef">
        <div v-for="(msg, i) in chatMessages" :key="i" :class="['chat-msg', msg.role]">
          <div v-if="msg.role === 'ai'" class="chat-avatar chat-avatar-ai">
            <el-icon size="14"><ChatDotSquare /></el-icon>
          </div>
          <div class="chat-bubble" v-html="renderContent(msg.content)" />
          <div v-if="msg.role === 'user'" class="chat-avatar chat-avatar-user">
            <el-icon size="14"><User /></el-icon>
          </div>
        </div>
        <div v-if="generating" class="chat-msg ai">
          <div class="chat-avatar chat-avatar-ai"><el-icon size="14"><ChatDotSquare /></el-icon></div>
          <div class="chat-bubble chat-typing"><span class="typing-dot" /><span class="typing-dot" /><span class="typing-dot" /></div>
        </div>
        <div v-if="chatMessages.length === 0 && !generating" class="chat-placeholder">
          <el-icon size="24"><ChatLineSquare /></el-icon>
          <p>{{ $t("message.ai.chatPlaceholder") }}</p>
          <div v-if="!store.isOnboarded" class="quick-suggestions">
            <el-tag @click="quickFill($t('message.ai.suggestionDisk'))" effect="plain" class="qs-tag">💾 {{ $t("message.ai.suggestionDiskShort") }}</el-tag>
            <el-tag @click="quickFill($t('message.ai.suggestionHealth'))" effect="plain" class="qs-tag">🔄 {{ $t("message.ai.suggestionHealthShort") }}</el-tag>
            <el-tag @click="quickFill($t('message.ai.suggestionSchedule'))" effect="plain" class="qs-tag">⏰ {{ $t("message.ai.suggestionScheduleShort") }}</el-tag>
          </div>
        </div>
      </div>
      <div class="chat-float-input">
        <el-input v-model="nlInput" :placeholder="$t('message.ai.placeholder')" :disabled="!selectedTemplateId || generating"
          type="textarea" :rows="2" resize="none" @keydown.enter.prevent="onGenerate" />
        <el-button type="primary" :loading="generating" :disabled="!selectedTemplateId" @click="onGenerate" class="chat-send-btn">
          {{ $t("message.common.send") }}
        </el-button>
      </div>
    </div>
    <el-button v-if="!chatExpanded" class="chat-float-trigger" round @click="chatExpanded = true">
      <el-icon><ChatDotSquare /></el-icon> {{ $t("message.ai.title") }}
    </el-button>

    <!-- Main body / Designer canvas -->
    <div class="opsflow-body">
      <DesignCanvas ref="designCanvasRef" :templates="templates" :template-id="selectedTemplateId"
        show-back @back="canvasMode = false"
        @change-template="onSelectTemplate" @save="onSaveDraft" @diff="onDiff"
        @analyze="onAnalyze" @new-template="showNewTemplateDialog"
        @node-select="onNodeSelect" @node-need-plugin="onNodeNeedPlugin"
        @submit-execution="onSubmitExecution" @dry-run="onDryRun" />
    </div>

    <!-- Dialogs (same as original) -->
    <PluginPickerDialog v-model:visible="pickerVisible" @select="onPluginPicked" />
    <CreateTemplateWizard v-model="newDialogVisible" @created="onWizardCreated" />
    <DryRunDialog v-model="showDryRunDialog" :execution-id="dryRunExecId" />
    <DiffModal ref="diffModalRef" :template-id="diffTemplateId" :ai-original="aiOriginal" :current="currentTree" @confirmed="onDiffConfirmed" />
    <el-dialog v-model="analyzeVisible" :title="$t('message.opsflowPage.aiAnalysis')" width="960px" top="5vh" class="opsflow-dialog">
      <div v-loading="analyzing" element-loading-text="AI analyzing..." class="analyze-body">
        <div v-if="analysisResult" class="analyze-content">
          <div class="summary-hero g-fade-in-up">
            <div class="summary-hero-icon"><el-icon size="22"><InfoFilled /></el-icon></div>
            <div class="summary-hero-text">
              <div class="summary-hero-label">{{ $t("message.opsflowPage.aiSummary") }}</div>
              <p>{{ analysisResult.summary }}</p>
            </div>
          </div>
          <div class="section-card g-fade-in-up" v-if="analysisResult.steps?.length" :style="{ animationDelay: '0.15s' }">
            <div class="section-card-header">
              <el-icon size="16" color="#409EFF"><List /></el-icon>
              <span>{{ $t("message.opsflowPage.aiSteps") }}</span>
              <el-tag size="small" type="primary" effect="plain">{{ analysisResult.steps.length }} steps</el-tag>
            </div>
            <div class="timeline">
              <div v-for="(step, i) in analysisResult.steps" :key="i" class="timeline-item g-stagger-item" :style="{ animationDelay: `${0.3 + i * 0.12}s` }">
                <div class="timeline-marker"><div class="timeline-dot">{{ i + 1 }}</div><div v-if="i < analysisResult.steps.length - 1" class="timeline-line" /></div>
                <div class="timeline-card"><div class="timeline-card-text">{{ step }}</div></div>
              </div>
            </div>
          </div>
          <div class="section-card-row">
            <div class="section-card section-card-half g-fade-in-up" v-if="analysisResult.risks?.length" :style="{ animationDelay: '0.3s' }">
              <div class="section-card-header"><el-icon size="16" color="#E6A23C"><WarningFilled /></el-icon><span>{{ $t("message.opsflowPage.aiRisks") }}</span><el-tag size="small" type="warning" effect="plain">{{ analysisResult.risks.length }}</el-tag></div>
              <div class="risk-list"><div v-for="(risk, i) in analysisResult.risks" :key="i" class="risk-item g-stagger-item" :style="{ animationDelay: `${0.5 + i * 0.08}s` }"><div class="risk-severity risk-severity-warning" /><span>{{ risk }}</span></div></div>
            </div>
            <div class="section-card section-card-half g-fade-in-up" v-if="analysisResult.suggestions?.length" :style="{ animationDelay: '0.45s' }">
              <div class="section-card-header"><el-icon size="16" color="#409EFF"><Lightning /></el-icon><span>{{ $t("message.opsflowPage.aiSuggestions") }}</span><el-tag size="small" type="primary" effect="plain">{{ analysisResult.suggestions.length }}</el-tag></div>
              <div class="suggestion-list"><div v-for="(sug, i) in analysisResult.suggestions" :key="i" class="suggestion-item g-stagger-item" :style="{ animationDelay: `${0.6 + i * 0.08}s` }"><el-icon size="14" color="#409EFF"><CircleCheck /></el-icon><span>{{ sug }}</span></div></div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
    <HelpDrawer v-model:visible="store.showHelpDrawer" />
  </div>

  <!-- ===== Tab Mode: hero + tabs + embedded sub-pages ===== -->
  <div v-else class="opsflow-page">
    <!-- Hero Section -->
    <div class="opsflow-hero">
      <div class="opsflow-hero-bg" />
      <div class="opsflow-hero-inner">
        <div class="opsflow-hero-left">
          <h1 class="opsflow-hero-title">OPSflow</h1>
          <p class="opsflow-hero-subtitle">运维流程编排与自动化 — pipeline design, execution & monitoring</p>
        </div>
        <div ref="heroSearchRef" class="opsflow-hero-search" />
        <div class="opsflow-hero-stats">
          <template v-for="(stat, i) in heroStats" :key="i">
            <div v-if="i > 0" class="opsflow-stat-divider" />
            <div class="opsflow-stat-item">
              <span class="opsflow-stat-value">{{ stat.value }}</span>
              <span class="opsflow-stat-label">{{ stat.label }}</span>
            </div>
          </template>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="opsflow-hero-tabs">
        <div v-for="tab in pageConfig?.tabs" :key="tab.key"
          class="opsflow-hero-tab"
          :class="{ active: activeTab === tab.key, locked: !tab.has_access }"
          @click="onTabClick(tab)">
          <el-icon><component :is="iconMap[tab.icon]" /></el-icon>
          {{ isEn ? tab.label_en : tab.label_zh }}
          <span v-if="!tab.has_access" class="tab-lock">🔒</span>
        </div>
      </div>
    </div>

    <!-- Hero filter bar area (populated by embedded sub-pages) -->
    <div ref="heroFilterRef" class="opsflow-hero-filter" />

    <!-- Body -->
    <div class="opsflow-body-wrap">
      <template v-if="pageConfig">
        <template v-for="tab in pageConfig.tabs" :key="tab.key">
          <div v-if="tab.has_access && isVisited(tab.key)" v-show="activeTab === tab.key" class="opsflow-section g-fade-in-up">
            <component :is="componentMap[tab.key]" embedded :active="activeTab === tab.key" />
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch, reactive } from 'vue'
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'
import { useHeroProvider } from '/@/composables/useHeroProvider'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Fold, Reading,
  ChatDotSquare, ChatLineSquare, User, InfoFilled,
  WarningFilled, Lightning, List, CircleCheck,
  EditPen, Document, VideoPlay, Clock, Collection, Link, DataAnalysis, Setting,
} from '@element-plus/icons-vue'
import { useOpsflowStore } from './stores/opsflowStore'
import { usePermissionStore } from '/@/stores/permission'
import { request } from '/@/utils/service'
import { GetTemplates, GetTemplateDetail, CreateFromAi, CreateTemplate, GetDiff, AnalyzePipeline, RefinePipeline, AiLayout, UpdateTemplate, AcquireLock, ReleaseLock, HeartbeatLock } from './api/templates'
import DesignCanvas from './components/canvas/DesignCanvas.vue'
import DiffModal from './components/dialogs/DiffModal.vue'
import PluginPickerDialog from './components/pickers/PluginPickerDialog.vue'
import CreateTemplateWizard from './components/dialogs/CreateTemplateWizard.vue'
import DryRunDialog from './components/dialogs/DryRunDialog.vue'
import HelpDrawer from './components/common/HelpDrawer.vue'
import OpsflowTemplate from '../opsflow-template/index.vue'
import OpsflowExecution from '../opsflow-execution/index.vue'
import OpsflowKnowledge from '../opsflow-knowledge/index.vue'
import OpsflowLog from '../opsflow-log/index.vue'
import OpsflowWebhook from '../opsflow-webhook/index.vue'
import OpsflowDashboard from '../opsflow-dashboard/index.vue'
import OpsflowProject from '../opsflow-project/index.vue'

const store = useOpsflowStore()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))

// ===== Tab mode state =====
const activeTab = ref<string>('dashboard')
const canvasMode = ref(false)
const pageConfig = ref<any>(null)
const userPerms = ref<string[]>([])

// ===== Hero stats (provided to sub-pages via useHeroProvider) =====
const { stats: heroStats, filterRef: heroFilterRef, searchRef: heroSearchRef, updateStats } = useHeroProvider()

// Initialize default stats
heroStats.push(
  { value: 0, label: '模板' },
  { value: '-', label: '执行' },
)

// ===== Tab lazy loading =====
const projectChangedTrigger = ref(0)

const { isVisited } = useTabLazyLoad({
  tabs: [], // tabs are data-driven from pageConfig; keys are validated at runtime
  activeTab,
  resetOn: projectChangedTrigger,
})

// Reset hero stats to defaults when switching to dashboard (no sub-page stats)
watch(activeTab, (tab) => {
  if (tab === 'dashboard') {
    updateStats([
      { value: templates.value.length, label: '模板' },
      { value: '-', label: '执行' },
    ])
  }
  // Other tabs: sub-components report their own stats via useHeroConsumer
})

const permissionStore = usePermissionStore()
const requestPerm = permissionStore.requestPerm

async function loadPageConfig() {
  try {
    const res = await request({ url: '/api/iam/page-permissions/', params: { app: 'opsflow' } })
    pageConfig.value = res.data
    userPerms.value = res.data.user_permissions || []
    const defaultTab = res.data.tabs.find((t: any) => t.is_default) || res.data.tabs[0]
    if (defaultTab) activeTab.value = defaultTab.key
  } catch { /* show empty */ }
}

const iconMap: Record<string, any> = {
  EditPen, Document, VideoPlay, Clock, Collection, List, Link, DataAnalysis, Setting,
}

const componentMap: Record<string, any> = {
  designer: DesignCanvas,
  templates: OpsflowTemplate,
  executions: OpsflowExecution,
  knowledge: OpsflowKnowledge,
  logs: OpsflowLog,
  webhooks: OpsflowWebhook,
  dashboard: OpsflowDashboard,
  project: OpsflowProject,
}

function onTabClick(tab: any) {
  if (!tab.has_access) {
    permissionStore.requestPerm(tab.label_zh, tab.required_perm)
    return
  }
  if (tab.key === 'designer') {
    canvasMode.value = true
    if (!templates.value.length) fetchTemplates()
  } else {
    activeTab.value = tab.key
  }
}

// ===== Original designer state (unchanged) =====
const designCanvasRef = ref<InstanceType<typeof DesignCanvas> | null>(null)
const diffModalRef = ref<InstanceType<typeof DiffModal> | null>(null)
const templates = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const nlInput = ref('')
const generating = ref(false)
const newDialogVisible = ref(false)
const diffTemplateId = ref(0)
const aiOriginal = ref<any>({})
const currentTree = ref<any>({})
const analyzeVisible = ref(false)
const analyzing = ref(false)
const analysisResult = ref<any>(null)
const pickerVisible = ref(false)
const pendingTaskNode = ref<string | null>(null)
const showDryRunDialog = ref(false)
const dryRunExecId = ref<number | null>(null)
const isLockedByMe = ref(false)
let heartbeatTimer: number | null = null

function startHeartbeat(tplId: number) {
  stopHeartbeat()
  heartbeatTimer = window.setInterval(async () => {
    try { await HeartbeatLock(tplId) } catch {
      isLockedByMe.value = false
      ElMessage.warning(t('message.opsflowPage.lockedExpired'))
      stopHeartbeat()
    }
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatTimer !== null) { clearInterval(heartbeatTimer); heartbeatTimer = null }
}

async function tryAcquireLock(tplId: number): Promise<boolean> {
  try {
    await AcquireLock(tplId)
    isLockedByMe.value = true
    startHeartbeat(tplId)
    return true
  } catch (e: any) {
    if (e?.response?.status === 409) {
      const data = e.response.data?.data
      const username = data?.locked_by?.username || ''
      await ElMessageBox.alert(
        `${t('message.opsflowPage.lockedBy')} ${username}${t('message.opsflowPage.lockedRetry')}`,
        t('message.opsflowPage.lockedTitle'),
        { type: 'warning', confirmButtonText: t('message.common.confirm') }
      )
    } else {
      ElMessage.warning(t('message.opsflowPage.operateFailed'))
    }
    return false
  }
}

function releaseLock(tplId: number) { stopHeartbeat(); ReleaseLock(tplId).catch(() => {}) }
function onSubmitExecution(execId: number) { /* SubmitWizardDialog shows its own success message */ }
function onDryRun(execId: number) { dryRunExecId.value = execId; showDryRunDialog.value = true }
function quickFill(text: string) { nlInput.value = text; onGenerate() }

const chatExpanded = ref(false)
const chatMessages = ref<{ role: 'user' | 'ai'; content: string }[]>([])

function onNodeSelect(node: any) { if (node) chatExpanded.value = false }

function onPluginPicked(plugin: { code: string; name: string; name_en: string; risk_level: string; group?: string }) {
  if (!pendingTaskNode.value || !designCanvasRef.value?.graph) return
  const node = designCanvasRef.value.graph.getCellById(pendingTaskNode.value)
  if (node && node.isNode()) {
    const oldData = node.getData() || {}
    const displayName = isEn.value && plugin.name_en ? plugin.name_en : plugin.name
    node.setData({ ...oldData, atom_type: plugin.code, plugin_code: plugin.code, risk_level: plugin.risk_level, label: displayName, group: plugin.group || oldData.group || '', name_en: plugin.name_en })
    node.setLabel(displayName)
    node.setAttrs({ label: { text: displayName } })
  }
  pendingTaskNode.value = null
}

function onNodeNeedPlugin(nodeId: string) { pendingTaskNode.value = nodeId; pickerVisible.value = true }

const chatScrollRef = ref<HTMLElement | null>(null)
function scrollChatBottom() {
  nextTick(() => { if (chatScrollRef.value) chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight })
}
function renderContent(text: string): string { return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }

async function fetchTemplates() {
  try {
    const res = await GetTemplates({ limit: 500 })
    templates.value = res.data || res.results || []
    store.setTemplates(templates.value)
  } catch (e) { console.error('Failed to fetch templates', e) }
}

async function onSelectTemplate(id: any) {
  selectedTemplateId.value = id
  if (!id) return
  if (isLockedByMe.value) releaseLock(id)
  const locked = await tryAcquireLock(id)
  if (!locked) { selectedTemplateId.value = null; return }
  try {
    const res = await GetTemplateDetail(id)
    const template = res.data?.data || res.data || res
    store.setCurrentTemplate(template)
    if (designCanvasRef.value) {
      if (template?.pipeline_tree && typeof template.pipeline_tree === 'object') {
        designCanvasRef.value.loadPipeline(template.pipeline_tree)
      } else {
        designCanvasRef.value.loadPipeline({ nodes: [], edges: [] })
      }
      nextTick(async () => { try { await designCanvasRef.value?.aiLayout() } catch {} })
    }
  } catch (e: any) {
    console.error('[onSelectTemplate] Failed to load template', e)
    ElMessage.error(e?.msg || e?.message || t('message.template.operationFailed'))
  }
}

const LAYOUT_KEYWORDS = ['layout', 'arrange', 'align', 'organize']

async function onGenerate() {
  if (!nlInput.value.trim()) { ElMessage.warning(t('message.opsflowPage.describeTask')); return }
  if (!selectedTemplateId.value) { ElMessage.warning(t('message.opsflowPage.selectTemplateFirst')); return }
  const input = nlInput.value.trim()
  const isFirst = chatMessages.value.filter(m => m.role === 'user').length === 0
  const isLayoutIntent = !isFirst && LAYOUT_KEYWORDS.some(k => input.includes(k))
  generating.value = true
  chatMessages.value.push({ role: 'user', content: input })
  nlInput.value = ''
  scrollChatBottom()
  try {
    if (isLayoutIntent) {
      const canvasData = designCanvasRef.value!.getGraphData()
      const res = await AiLayout({ nodes: canvasData.nodes, edges: canvasData.edges })
      const data = res.data?.data || res.data
      const positions = data?.positions || []
      if (positions.length && designCanvasRef.value) {
        const g = designCanvasRef.value.graph
        if (g) {
          for (const pos of positions) { const cell = g.getCellById(pos.id); if (cell && cell.isNode()) cell.setPosition(pos.x, pos.y) }
          g.centerContent()
        }
        chatMessages.value.push({ role: 'ai', content: 'Layout optimized.' })
      } else { chatMessages.value.push({ role: 'ai', content: 'Layout optimization returned no results. Please try again.' }) }
    } else if (isFirst && !selectedTemplateId.value) {
      const res = await CreateFromAi({ input })
      const data = res.data?.data || res.data
      if (data?.template) {
        store.setCurrentTemplate(data.template)
        selectedTemplateId.value = data.template.id
        diffTemplateId.value = data.template.id
        aiOriginal.value = data.template.ai_original_tree || {}
        currentTree.value = data.template.pipeline_tree || {}
        if (designCanvasRef.value) { designCanvasRef.value.loadPipeline(data.template.pipeline_tree); nextTick(() => designCanvasRef.value?.aiLayout()) }
        chatMessages.value.push({ role: 'ai', content: 'Pipeline generated. You can modify it on the canvas or continue with more requirements.' })
        if (data?.validation?.warnings?.length) ElMessage.warning(`Safety warning: ${data.validation.warnings.join('; ')}`)
      }
      await fetchTemplates()
    } else {
      const canvasData = designCanvasRef.value!.getGraphData()
      const chatHistory = chatMessages.value.map(m => ({ role: m.role, content: m.content }))
      const res = await RefinePipeline({ input, nodes: canvasData.nodes, edges: canvasData.edges, chat_history: chatHistory })
      const data = res.data?.data || res.data
      const pipelineTree = data?.pipeline_tree
      if (pipelineTree && designCanvasRef.value && selectedTemplateId.value) {
        designCanvasRef.value.loadPipeline(pipelineTree)
        nextTick(() => designCanvasRef.value?.aiLayout())
        chatMessages.value.push({ role: 'ai', content: data?.message || 'Pipeline updated according to your instructions.' })
        if (data?.validation?.warnings?.length) ElMessage.warning(`Safety warning: ${data.validation.warnings.join('; ')}`)
      }
    }
  } catch (e: any) { console.error('AI processing failed', e); ElMessage.error(e?.response?.data?.msg || e?.msg || t('message.opsflowPage.aiProcessingFailed')) }
  finally { generating.value = false; scrollChatBottom() }
}

async function onSaveDraft(data: any) {
  if (!selectedTemplateId.value) { ElMessage.warning(t('message.opsflowPage.selectTemplateFirst')); return }
  try { await UpdateTemplate(selectedTemplateId.value, { pipeline_tree: data }); ElMessage.success(t('message.opsflowPage.saveDraft')); await fetchTemplates() }
  catch (e: any) { console.error('Save failed', e); ElMessage.error(e?.msg || e?.message || t('message.opsflowPage.saveFailed')) }
}

function onDiff() {
  if (!designCanvasRef.value) return
  currentTree.value = designCanvasRef.value.getGraphData()
  diffModalRef.value?.show()
}

async function onAnalyze() {
  if (!designCanvasRef.value) return
  const data = designCanvasRef.value.getGraphData()
  if (!data.nodes.length) { ElMessage.warning(t('message.opsflowPage.canvasEmpty')); return }
  analyzing.value = true; analyzeVisible.value = true; analysisResult.value = null
  try { const res = await AnalyzePipeline({ nodes: data.nodes, edges: data.edges }); analysisResult.value = res.data?.data || res.data }
  catch (e: any) { console.error('AI analysis failed', e); ElMessage.error(e?.msg || e?.message || t('message.opsflowPage.aiProcessingFailed')); analyzeVisible.value = false }
  finally { analyzing.value = false }
}

function showNewTemplateDialog() { newDialogVisible.value = true }

async function onWizardCreated(template: any) {
  await fetchTemplates()
  selectedTemplateId.value = template.id
  await onSelectTemplate(template.id)
  if (designCanvasRef.value && template?.pipeline_tree?.nodes?.length) nextTick(() => designCanvasRef.value?.aiLayout())
}

async function onDiffConfirmed() {
  try { if (selectedTemplateId.value && currentTree.value) await UpdateTemplate(selectedTemplateId.value, { pipeline_tree: currentTree.value }); ElMessage.success(t('message.opsflowPage.confirmSave')); await fetchTemplates() }
  catch (e: any) { console.error('Save failed', e); ElMessage.error(e?.msg || e?.message || t('message.opsflowPage.saveFailed')) }
}

function onProjectChanged() {
  projectChangedTrigger.value++ // reset tab lazy load state
  fetchTemplates()
  if (store.currentTemplate?.is_public) return
  const stillExists = templates.value.some(t => t.id === selectedTemplateId.value)
  if (!stillExists) { selectedTemplateId.value = null; store.setCurrentTemplate(null); if (designCanvasRef.value) designCanvasRef.value.loadPipeline({ nodes: [], edges: [] }) }
}

onMounted(async () => {
  await store.fetchMyProjects()
  await loadPageConfig()
  // Read initial tab from URL query param
  const tabParam = route.query.tab as string
  if (tabParam) {
    const tabConfig = pageConfig.value?.tabs?.find((t: any) => t.key === tabParam)
    if (tabConfig && (tabConfig.has_access || tabParam === 'dashboard' || tabParam === 'logs')) {
      if (tabParam === 'designer' && tabConfig.has_access) {
        canvasMode.value = true
      } else {
        activeTab.value = tabParam
      }
    }
  }
  // Auto-load designer if template passed from template management
  const pending = store.currentTemplate
  if (pending && pending.id) {
    canvasMode.value = true
    await fetchTemplates()
    selectedTemplateId.value = pending.id
    onSelectTemplate(pending.id)
  }
})

onMounted(() => { window.addEventListener('project-changed', onProjectChanged) })
onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
  if (selectedTemplateId.value) releaseLock(selectedTemplateId.value)
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

/* ===== Canvas Mode Layout ===== */
.opsflow-canvas-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: $g-bg-page; overflow: hidden;
}


/* ===== Tab Mode Layout ===== */
.opsflow-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow-y: auto; overflow-x: hidden;
}

/* ===== Hero (ITSM pattern) ===== */
.opsflow-hero { @include g-hero-container; }
.opsflow-hero-bg { @include g-hero-bg-dots; }
.opsflow-hero-inner { @include g-hero-inner; justify-content: space-between; }
.opsflow-hero-left { flex: 1; }
.opsflow-hero-title { @include g-hero-title; letter-spacing: 0.5px; }
.opsflow-hero-subtitle { @include g-hero-subtitle; }
.opsflow-hero-stats {
  display: flex; align-items: center; gap: 12px;
}
.opsflow-stat-item { display: flex; flex-direction: column; align-items: center; }
.opsflow-stat-value { @include g-hero-stat-value; }
.opsflow-stat-label { @include g-hero-stat-label; }
.opsflow-stat-divider { @include g-hero-stat-divider; }

/* Hero tabs */
.opsflow-hero-tabs { @include g-hero-tabs; }
.opsflow-hero-tab { @include g-hero-tab;
  .el-icon { font-size: 15px; }
  &.locked { opacity: 0.6; }
  &.locked:hover { opacity: 0.9; background: rgba(255,193,7,0.1); border-bottom-color: #ffc107; }
  .tab-lock { font-size: 11px; margin-left: 3px; }
}

/* Hero search (populated by sub-pages via Teleport, sits between title and stats) */
.opsflow-hero-search {
  margin-left: auto;
  margin-right: 60px;
  display: flex; align-items: center;
  :deep(.pj-search-input),
  :deep(.exec-search-input) {
    width: 280px;
  }
  :deep(.el-input__wrapper) {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: none; border-radius: 10px;
  }
  :deep(.el-input__inner) { color: #fff; font-size: 14px; }
  :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
  :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
}

/* Hero filter bar (populated by sub-pages via Teleport) */
.opsflow-hero-filter {
  padding: 0 24px;
  background: #f5f6fa;
  min-height: 0;
  &:not(:empty) {
    padding-top: 12px;
    padding-bottom: 12px;
  }
  :deep(.pj-filter-bar),
  :deep(.exec-filter-bar) {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0 0 0 0; gap: 16px;
  }
  :deep(.pj-filter-tabs),
  :deep(.exec-filter-tabs) {
    display: flex; gap: 4px; flex-wrap: wrap;
  }
  :deep(.pj-tab),
  :deep(.exec-tab) {
    display: flex; align-items: center; gap: 6px;
    padding: 7px 16px; border-radius: 20px;
    font-size: 13px; font-weight: 500; color: #606266;
    cursor: pointer; transition: all 0.2s; user-select: none;
  }
  :deep(.pj-tab:hover),
  :deep(.exec-tab:hover) {
    background: rgba(64,158,255,0.06); color: #409EFF;
  }
  :deep(.pj-tab.active),
  :deep(.exec-tab.active) {
    background: #409EFF; color: #fff;
    box-shadow: 0 2px 8px rgba(64,158,255,0.3);
  }
  :deep(.pj-tab-dot),
  :deep(.exec-tab-dot) {
    width: 7px; height: 7px; border-radius: 50%; display: inline-block;
  }
  :deep(.pj-filter-actions),
  :deep(.exec-filter-actions) {
    display: flex; gap: 8px; align-items: center; flex-shrink: 0;
  }
  :deep(.pj-search-input),
  :deep(.exec-search-input) {
    width: 240px;
  }
}

/* ===== Body ===== */
.opsflow-body-wrap {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
}
.opsflow-section {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
  // Sub-pages use absolute positioning; override for embedded mode
  :deep(.tpl-page),
  :deep(.opsflow-exec-page),
  :deep(.app-page),
  :deep(.kb-page),
  :deep(.log-page),
  :deep(.wh-page),
  :deep(.db-page),
  :deep(.sc-page) {
    position: relative !important;
    top: auto !important; left: auto !important; right: auto !important; bottom: auto !important;
    height: 100%;
  }
}

/* ===== Canvas body ===== */
.opsflow-body {
  flex: 1; overflow: hidden; position: relative;
  margin: 8px; border-radius: $g-radius-sm;
  background: #fff; box-shadow: $g-shadow-card;
}

/* ===== Chat Float Panel (preserved) ===== */
.chat-float-panel {
  position: absolute; bottom: 20px; right: 20px; width: 380px; max-height: 520px;
  background: #fff; border: 1px solid $g-border-default; border-radius: $g-radius-lg;
  box-shadow: 0 8px 32px rgba(0,0,0,0.14); z-index: 200;
  display: flex; flex-direction: column; overflow: hidden;
  animation: chatSlideIn 0.25s ease;
}
@keyframes chatSlideIn { from { opacity: 0; transform: translateY(16px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.chat-float-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: $g-gradient-primary; background-size: 200% 100%;
  color: #fff; animation: headerShimmer 4s ease-in-out infinite;
  position: relative; overflow: hidden;
}
.chat-float-header::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
  background-size: 200% 100%; animation: headerGlide 3s ease-in-out infinite; pointer-events: none;
}
@keyframes headerShimmer { 0%,100% { background-position: 0% center; } 50% { background-position: 100% center; } }
@keyframes headerGlide { 0% { transform: translateX(-100%); } 100% { transform: translateX(200%); } }
.chat-header-left { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; position: relative; z-index: 1; }
.chat-header-left :deep(.el-icon) { color: #fff; }
.chat-float-header :deep(.el-button) { color: #fff; border-color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.15); position: relative; z-index: 1; }
.chat-float-header :deep(.el-button:hover) { background: rgba(255,255,255,0.3); }
.chat-header-actions { display: flex; align-items: center; gap: 4px; position: relative; z-index: 1; }
.chat-hdr-btn { font-size: 13px !important; }
.chat-float-history { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; min-height: 120px; max-height: 320px; background: $g-bg-card; }
.chat-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; color: #bbb; font-size: 13px; padding: 40px 0; gap: 8px; animation: fadeInUp 0.5s ease both; }
.chat-placeholder :deep(.el-icon) { animation: placeholderFloat 3s ease-in-out infinite; }
@keyframes placeholderFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
.chat-float-input { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid $g-border-default; background: #fff; align-items: flex-end; }
.chat-float-input :deep(.el-textarea__inner) { border-radius: 8px; font-size: 13px; padding: 8px 12px; transition: border-color 0.25s, box-shadow 0.25s; }
.chat-float-input :deep(.el-textarea__inner:focus) { border-color: #409EFF; box-shadow: 0 0 0 3px rgba(64,158,255,0.12); }
.chat-send-btn { height: 36px; flex-shrink: 0; transition: all 0.2s; }
.chat-send-btn:not(:disabled):hover { transform: scale(1.04); }
.chat-send-btn:not(:disabled):active { transform: scale(0.96); }
.chat-float-trigger {
  position: absolute !important; bottom: 20px; right: 20px; z-index: 200;
  display: inline-flex; align-items: center; gap: 6px;
  box-shadow: 0 4px 16px rgba(64,158,255,0.3); transition: transform 0.2s, box-shadow 0.2s;
  animation: triggerPulse 2.5s ease-in-out infinite;
}
@keyframes triggerPulse { 0%,100% { box-shadow: 0 4px 16px rgba(64,158,255,0.3); } 50% { box-shadow: 0 4px 28px rgba(64,158,255,0.55); } }
.chat-float-trigger:hover { transform: translateY(-3px) scale(1.02); }
.chat-msg { display: flex; align-items: flex-start; gap: 8px; animation: msgFadeIn 0.35s ease both; }
.chat-msg.user { justify-content: flex-end; animation-name: msgSlideInRight; }
.chat-msg.ai { justify-content: flex-start; animation-name: msgSlideInLeft; }
@keyframes msgSlideInLeft { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: translateX(0); } }
@keyframes msgSlideInRight { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: translateX(0); } }
@keyframes msgFadeIn { from { opacity: 0; } to { opacity: 1; } }
.chat-avatar { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.chat-avatar-ai { background: $g-gradient-primary; color: #fff; }
.chat-avatar-user { background: #a0cfff; color: #fff; }
.chat-bubble { max-width: 75%; padding: 8px 14px; border-radius: $g-radius-lg; font-size: 13px; line-height: 1.6; word-break: break-word; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.chat-msg.user .chat-bubble { background: $g-gradient-primary; color: #fff; border-bottom-right-radius: 4px; }
.chat-msg.ai .chat-bubble { background: #fff; color: #333; border: 1px solid #e8eaed; border-bottom-left-radius: 4px; }
.chat-typing { display: flex; align-items: center; gap: 4px; padding: 12px 18px !important; }
.typing-dot { width: 7px; height: 7px; border-radius: 50%; background: #bbb; animation: typingBounce 1.4s infinite ease-in-out both; }
.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0s; }
@keyframes typingBounce { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
.quick-suggestions { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 10px; }
.qs-tag { cursor: pointer; font-size: 11px; padding: 4px 10px; border-radius: 14px; transition: all 0.2s; }
.qs-tag:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(64,158,255,0.2); }

/* ===== Dialog ===== */
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
.analyze-body { min-height: 280px; }
.analyze-content { display: flex; flex-direction: column; gap: 18px; }
.summary-hero { display: flex; gap: 14px; background: $g-gradient-hero; border-left: 4px solid $g-color-primary; border-radius: $g-radius-card; padding: $g-padding-card; align-items: flex-start; }
.summary-hero-icon { width: 40px; height: 40px; border-radius: $g-radius-card; background: $g-gradient-primary; color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.summary-hero-text { flex: 1; min-width: 0; }
.summary-hero-label { font-size: 13px; font-weight: 600; color: $g-color-primary; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; }
.summary-hero-text p { margin: 0; font-size: 14px; line-height: 1.8; color: #333; }
.section-card { background: $g-bg-card; border-radius: $g-radius-card; padding: $g-padding-card; border: 1px solid $g-border-card; }
.section-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; font-size: 14px; font-weight: 600; color: #333; }
.section-card-header .el-tag { margin-left: auto; }
.section-card-row { display: flex; gap: 18px; }
.section-card-half { flex: 1; min-width: 0; }
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item { display: flex; gap: 14px; }
.timeline-marker { display: flex; flex-direction: column; align-items: center; width: 28px; flex-shrink: 0; }
.timeline-dot { width: 28px; height: 28px; border-radius: 50%; background: $g-gradient-primary; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(64,158,255,0.35); }
.timeline-line { width: 2px; flex: 1; min-height: 16px; background: linear-gradient(to bottom, #c0d9f5, #e8eef7); }
.timeline-card { flex: 1; padding: 6px 0 18px 0; min-width: 0; }
.timeline-card-text { background: #fff; border: 1px solid #e8eaed; border-radius: 8px; padding: 10px 14px; font-size: 13px; line-height: 1.6; color: #444; transition: box-shadow 0.2s; }
.timeline-card-text:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.risk-list { display: flex; flex-direction: column; gap: 8px; }
.risk-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; background: #fff; border-radius: 6px; border: 1px solid $g-border-danger; font-size: 13px; line-height: 1.5; color: #555; }
.risk-severity { width: 4px; height: 100%; min-height: 20px; border-radius: 4px; flex-shrink: 0; margin-top: 2px; }
.risk-severity-warning { background: #E6A23C; }
.suggestion-list { display: flex; flex-direction: column; gap: 8px; }
.suggestion-item { display: flex; align-items: flex-start; gap: 8px; padding: 10px 12px; background: #fff; border-radius: 6px; border: 1px solid #e8eaed; font-size: 13px; line-height: 1.5; color: #555; }
.summary-hero-icon { animation: heroPulse 2s ease-in-out infinite; }
@keyframes heroPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(64,158,255,0.35); } 50% { box-shadow: 0 0 0 8px rgba(64,158,255,0); } }
.opsflow-dialog :deep(.el-overlay) { animation: dialogOverlayIn 0.2s ease both; }
.opsflow-dialog :deep(.el-dialog) { animation: dialogBounceIn 0.3s ease both; }
@keyframes dialogOverlayIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes dialogBounceIn { from { opacity: 0; transform: scale(0.92) translateY(-20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
.section-card { @extend .g-card; }
.section-card:hover { @include g-hover-lift; }
.timeline-dot { transition: transform 0.2s, box-shadow 0.2s; }
.timeline-item:hover .timeline-dot { transform: scale(1.15); box-shadow: 0 3px 10px rgba(64,158,255,0.5); }
.risk-item, .suggestion-item { transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s; }
.risk-item:hover { transform: translateX(3px); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.suggestion-item:hover { transform: translateX(3px); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
</style>
