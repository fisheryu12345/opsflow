<template>
  <div class="opsflow-page">
    <!-- AI 对话浮窗 -->
    <div v-if="chatExpanded" class="chat-float-panel">
      <div class="chat-float-header">
        <div class="chat-header-left">
          <el-icon size="16"><ChatDotSquare /></el-icon>
          <span>AI Design</span>
        </div>
        <el-button size="small" circle :icon="Fold" @click="chatExpanded = false" />
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
        <!-- 加载指示器 -->
        <div v-if="generating" class="chat-msg ai">
          <div class="chat-avatar chat-avatar-ai">
            <el-icon size="14"><ChatDotSquare /></el-icon>
          </div>
          <div class="chat-bubble chat-typing">
            <span class="typing-dot" /><span class="typing-dot" /><span class="typing-dot" />
          </div>
        </div>
        <div v-if="chatMessages.length === 0 && !generating" class="chat-placeholder">
          <el-icon size="24"><ChatLineSquare /></el-icon>
          <p>Hi! Describe the ops workflow you want to create, or start dragging nodes from the left panel.</p>
        </div>
      </div>
      <div class="chat-float-input">
        <el-input
          v-model="nlInput"
          placeholder="Describe your ops task..."
          :disabled="!selectedTemplateId || generating"
          type="textarea"
          :rows="2"
          resize="none"
          @keydown.enter.prevent="onGenerate"
        />
        <el-button type="primary" :loading="generating" :disabled="!selectedTemplateId" @click="onGenerate" class="chat-send-btn">
          Send
        </el-button>
      </div>
    </div>
    <el-button v-if="!chatExpanded" class="chat-float-trigger" round @click="chatExpanded = true">
      <el-icon><ChatDotSquare /></el-icon>
      AI Design
    </el-button>

    <!-- 主体 -->
    <div class="opsflow-body">
      <DesignCanvas ref="designCanvasRef" :templates="templates" :template-id="selectedTemplateId"
                    @change-template="onSelectTemplate" @save="onSaveDraft" @diff="onDiff"
                    @analyze="onAnalyze" @new-template="showNewTemplateDialog"
                    @node-select="onNodeSelect"
                    @node-need-plugin="onNodeNeedPlugin"
                    @submit-execution="onSubmitExecution" />
    </div>

    <!-- 插件选择器 -->
    <PluginPickerDialog v-model:visible="pickerVisible" @select="onPluginPicked" />

    <!-- 新建模板向导 -->
    <CreateTemplateWizard v-model="newDialogVisible" @created="onWizardCreated" />

    <!-- Diff 弹窗 -->
    <DiffModal ref="diffModalRef" :template-id="diffTemplateId" :ai-original="aiOriginal" :current="currentTree"
               @confirmed="onDiffConfirmed" />

    <!-- AI 分析弹窗 -->
    <el-dialog v-model="analyzeVisible" title="AI Pipeline Analysis" width="740px" top="5vh" class="opsflow-dialog">
      <div v-loading="analyzing" element-loading-text="AI analyzing..." class="analyze-body">
        <div v-if="analysisResult" class="analyze-content">
          <!-- Summary Hero -->
          <div class="summary-hero of-fade-in-up">
            <div class="summary-hero-icon"><el-icon size="22"><InfoFilled /></el-icon></div>
            <div class="summary-hero-text">
              <div class="summary-hero-label">Summary</div>
              <p>{{ analysisResult.summary }}</p>
            </div>
          </div>
          <!-- Steps Timeline -->
          <div class="section-card of-fade-in-up" v-if="analysisResult.steps?.length" :style="{ animationDelay: '0.15s' }">
            <div class="section-card-header">
              <el-icon size="16" color="#409EFF"><List /></el-icon>
              <span>Pipeline Steps</span>
              <el-tag size="small" type="primary" effect="plain">{{ analysisResult.steps.length }} steps</el-tag>
            </div>
            <div class="timeline">
              <div v-for="(step, i) in analysisResult.steps" :key="i" class="timeline-item of-stagger-item" :style="{ animationDelay: `${0.3 + i * 0.12}s` }">
                <div class="timeline-marker">
                  <div class="timeline-dot">{{ i + 1 }}</div>
                  <div v-if="i < analysisResult.steps.length - 1" class="timeline-line" />
                </div>
                <div class="timeline-card">
                  <div class="timeline-card-text">{{ step }}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="section-card-row">
            <div class="section-card section-card-half of-fade-in-up" v-if="analysisResult.risks?.length" :style="{ animationDelay: '0.3s' }">
              <div class="section-card-header">
                <el-icon size="16" color="#E6A23C"><WarningFilled /></el-icon>
                <span>Risks</span>
                <el-tag size="small" type="warning" effect="plain">{{ analysisResult.risks.length }}</el-tag>
              </div>
              <div class="risk-list">
                <div v-for="(risk, i) in analysisResult.risks" :key="i" class="risk-item of-stagger-item" :style="{ animationDelay: `${0.5 + i * 0.08}s` }">
                  <div class="risk-severity risk-severity-warning" />
                  <span>{{ risk }}</span>
                </div>
              </div>
            </div>
            <div class="section-card section-card-half of-fade-in-up" v-if="analysisResult.suggestions?.length" :style="{ animationDelay: '0.45s' }">
              <div class="section-card-header">
                <el-icon size="16" color="#409EFF"><Lightning /></el-icon>
                <span>Suggestions</span>
                <el-tag size="small" type="primary" effect="plain">{{ analysisResult.suggestions.length }}</el-tag>
              </div>
              <div class="suggestion-list">
                <div v-for="(sug, i) in analysisResult.suggestions" :key="i" class="suggestion-item of-stagger-item" :style="{ animationDelay: `${0.6 + i * 0.08}s` }">
                  <el-icon size="14" color="#409EFF"><CircleCheck /></el-icon>
                  <span>{{ sug }}</span>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-if="!analysisResult.steps?.length && !analysisResult.risks?.length && !analysisResult.suggestions?.length"
                    description="No analysis data available" :image-size="60" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Fold,
  ChatDotSquare, ChatLineSquare, User, InfoFilled,
  WarningFilled, Lightning, List, CircleCheck,
} from '@element-plus/icons-vue'
import { useOpsflowStore } from './stores/opsflowStore'
import { GetTemplates, GetTemplateDetail, CreateFromAi, CreateTemplate, GetDiff, AnalyzePipeline, RefinePipeline, AiLayout, UpdateTemplate } from '/@/api/opsflow/templates'
import DesignCanvas from './components/DesignCanvas.vue'
import DiffModal from './components/DiffModal.vue'
import PluginPickerDialog from './components/PluginPickerDialog.vue'
import CreateTemplateWizard from './components/CreateTemplateWizard.vue'

const store = useOpsflowStore()

const designCanvasRef = ref<InstanceType<typeof DesignCanvas> | null>(null)
const diffModalRef = ref<InstanceType<typeof DiffModal> | null>(null)

// 模板相关
const templates = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const nlInput = ref('')
const generating = ref(false)

// 新建模板向导
const newDialogVisible = ref(false)

// Diff
const diffTemplateId = ref(0)
const aiOriginal = ref<any>({})
const currentTree = ref<any>({})

// AI 分析
const analyzeVisible = ref(false)
const analyzing = ref(false)
const analysisResult = ref<any>(null)

// 插件选择器
const pickerVisible = ref(false)
const pendingTaskNode = ref<string | null>(null)

function onSubmitExecution(execId: number) {
  // SubmitWizardDialog already shows its own success message
}

// 选中节点 → 折叠 AI 面板
const chatExpanded = ref(true)
const chatMessages = ref<{ role: 'user' | 'ai'; content: string }[]>([])

function onNodeSelect(node: any) {
  if (node) chatExpanded.value = false  // 选中节点 → 折叠 AI 对话框
  // 取消选中时不自动展开，由用户手动控制
}

function onPluginPicked(plugin: { code: string; name: string; risk_level: string }) {
  if (!pendingTaskNode.value || !designCanvasRef.value?.graph) return
  const node = designCanvasRef.value.graph.getCellById(pendingTaskNode.value)
  if (node && node.isNode()) {
    const oldData = node.getData() || {}
    node.setData({
      ...oldData,
      atom_type: plugin.code,
      plugin_code: plugin.code,
      risk_level: plugin.risk_level,
      label: plugin.name,
    })
    node.setLabel(plugin.name)
    node.setAttrs({ label: { text: plugin.name } })
  }
  pendingTaskNode.value = null
}

function onNodeNeedPlugin(nodeId: string) {
  pendingTaskNode.value = nodeId
  pickerVisible.value = true
}
const chatScrollRef = ref<HTMLElement | null>(null)
function scrollChatBottom() {
  nextTick(() => {
    if (chatScrollRef.value) {
      chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
    }
  })
}

function renderContent(text: string): string {
  return text
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

// 获取模板列表
async function fetchTemplates() {
  try {
    const res = await GetTemplates({ limit: 500 })
    templates.value = res.data || res.results || []
    store.setTemplates(templates.value)
  } catch (e) {
    console.error('Failed to fetch templates', e)
  }
}

// 选择模板
async function onSelectTemplate(id: any) {
  selectedTemplateId.value = id
  if (!id) return
  try {
    const res = await GetTemplateDetail(id)
    console.log('[onSelectTemplate] raw response:', res)
    const template = res.data?.data || res.data || res
    console.log('[onSelectTemplate] template:', template, 'pipeline_tree:', template?.pipeline_tree)
    if (template?.pipeline_tree) {
      console.log('[onSelectTemplate] pipeline_tree nodes:', template.pipeline_tree.nodes?.length, 'edges:', template.pipeline_tree.edges?.length)
    }
    store.setCurrentTemplate(template)
    if (designCanvasRef.value) {
      console.log('[onSelectTemplate] designCanvasRef exists, calling loadPipeline')
      if (template?.pipeline_tree && typeof template.pipeline_tree === 'object') {
        designCanvasRef.value.loadPipeline(template.pipeline_tree)
      } else {
        // pipeline_tree 为 null/非对象时加载空白画布（自动显示 Start→End）
        console.log('[onSelectTemplate] pipeline_tree null or not object, loading empty')
        designCanvasRef.value.loadPipeline({ nodes: [], edges: [] })
      }
    } else {
      console.warn('[onSelectTemplate] designCanvasRef is null!')
    }
  } catch (e: any) {
    console.error('[onSelectTemplate] Failed to load template', e)
    ElMessage.error(e?.msg || e?.message || 'Failed to load template')
  }
}

// AI 生成/多轮对话
const LAYOUT_KEYWORDS = ['layout', 'arrange', 'align', 'organize']

async function onGenerate() {
  if (!nlInput.value.trim()) {
    ElMessage.warning('Please describe your ops task')
    return
  }
  if (!selectedTemplateId.value) {
    ElMessage.warning('Please select a template first')
    return
  }
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
          for (const pos of positions) {
            const cell = g.getCellById(pos.id)
            if (cell && cell.isNode()) {
              cell.setPosition(pos.x, pos.y)
            }
          }
          g.centerContent()
        }
        chatMessages.value.push({ role: 'ai', content: 'Layout optimized.' })
      } else {
        chatMessages.value.push({ role: 'ai', content: 'Layout optimization returned no results. Please try again.' })
      }
    } else if (isFirst && !selectedTemplateId.value) {
      const res = await CreateFromAi({ input })
      const data = res.data?.data || res.data
      if (data?.template) {
        store.setCurrentTemplate(data.template)
        selectedTemplateId.value = data.template.id
        diffTemplateId.value = data.template.id
        aiOriginal.value = data.template.ai_original_tree || {}
        currentTree.value = data.template.pipeline_tree || {}
        if (designCanvasRef.value) {
          designCanvasRef.value.loadPipeline(data.template.pipeline_tree)
          nextTick(() => designCanvasRef.value?.aiLayout())
        }
        chatMessages.value.push({ role: 'ai', content: 'Pipeline generated. You can modify it on the canvas or continue with more requirements.' })
        if (data?.validation?.warnings?.length) {
          ElMessage.warning(`Safety warning: ${data.validation.warnings.join('; ')}`)
        }
      }
      await fetchTemplates()
    } else {
      const canvasData = designCanvasRef.value!.getGraphData()
      const res = await RefinePipeline({ input, nodes: canvasData.nodes, edges: canvasData.edges })
      const data = res.data?.data || res.data
      const pipelineTree = data?.pipeline_tree
      if (pipelineTree && designCanvasRef.value) {
        designCanvasRef.value.loadPipeline(pipelineTree)
        nextTick(() => designCanvasRef.value?.aiLayout())
        chatMessages.value.push({ role: 'ai', content: 'Pipeline updated according to your instructions.' })
        if (data?.validation?.warnings?.length) {
          ElMessage.warning(`Safety warning: ${data.validation.warnings.join('; ')}`)
        }
      }
    }
  } catch (e: any) {
    console.error('AI processing failed', e)
    ElMessage.error(e?.response?.data?.msg || e?.msg || 'AI processing failed')
  } finally {
    generating.value = false
    scrollChatBottom()
  }
}

// 保存草稿
async function onSaveDraft(data: any) {
  if (!selectedTemplateId.value) {
    ElMessage.warning('Please select or create a template first')
    return
  }
  try {
    await UpdateTemplate(selectedTemplateId.value, { pipeline_tree: data })
    ElMessage.success('Draft saved')
    await fetchTemplates()
  } catch (e: any) {
    console.error('Save failed', e)
    ElMessage.error(e?.msg || e?.message || 'Save failed')
  }
}

// Diff
function onDiff() {
  if (!designCanvasRef.value) return
  currentTree.value = designCanvasRef.value.getGraphData()
  diffModalRef.value?.show()
}

// AI 分析
async function onAnalyze() {
  if (!designCanvasRef.value) return
  const data = designCanvasRef.value.getGraphData()
  if (!data.nodes.length) {
    ElMessage.warning('Canvas is empty, nothing to analyze')
    return
  }
  analyzing.value = true
  analyzeVisible.value = true
  analysisResult.value = null
  try {
    const res = await AnalyzePipeline({ nodes: data.nodes, edges: data.edges })
    analysisResult.value = res.data?.data || res.data
  } catch (e: any) {
    console.error('AI analysis failed', e)
    ElMessage.error(e?.msg || e?.message || 'AI analysis failed')
    analyzeVisible.value = false
  } finally {
    analyzing.value = false
  }
}

// 新建模板向导
function showNewTemplateDialog() {
  newDialogVisible.value = true
}

async function onWizardCreated(template: any) {
  await fetchTemplates()
  selectedTemplateId.value = template.id
  await onSelectTemplate(template.id)
  if (designCanvasRef.value && template?.pipeline_tree?.nodes?.length) {
    nextTick(() => designCanvasRef.value?.aiLayout())
  }
}

// Diff 确认
async function onDiffConfirmed() {
  try {
    if (selectedTemplateId.value && currentTree.value) {
      await UpdateTemplate(selectedTemplateId.value, { pipeline_tree: currentTree.value })
    }
    ElMessage.success('Confirmed and saved')
    await fetchTemplates()
  } catch (e: any) {
    console.error('Save failed', e)
    ElMessage.error(e?.msg || e?.message || 'Save failed')
  }
}



onMounted(async () => {
  await store.fetchMyProjects()
  await fetchTemplates()
  // Auto-load template passed from template management via store
  const pending = store.currentTemplate
  if (pending && pending.id) {
    selectedTemplateId.value = pending.id
    onSelectTemplate(pending.id)
  }
})

// Re-fetch templates when project switches via ProjectSwitcher
function onProjectChanged() {
  fetchTemplates()
  // 公共模板不受项目切换影响，保留当前选中
  if (store.currentTemplate?.is_public) return
  const stillExists = templates.value.some(t => t.id === selectedTemplateId.value)
  if (!stillExists) {
    selectedTemplateId.value = null
    store.setCurrentTemplate(null)
    if (designCanvasRef.value) {
      designCanvasRef.value.loadPipeline({ nodes: [], edges: [] })
    }
  }
}

onMounted(() => {
  window.addEventListener('project-changed', onProjectChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
})
</script>

<style lang="scss" scoped>
@import './styles/opsflow-global';
/* ===== Layout ===== */
.opsflow-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: $of-bg-page;
  overflow: hidden;
}

/* ===== Chat Float Panel ===== */
.chat-float-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 380px;
  max-height: 520px;
  background: #fff;
  border: 1px solid $of-border-default;
  border-radius: $of-radius-lg;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.14);
  z-index: 200;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: chatSlideIn 0.25s ease;
}
@keyframes chatSlideIn {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.chat-float-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: $of-gradient-blue;
  background-size: 200% 100%;
  color: #fff;
  animation: headerShimmer 4s ease-in-out infinite;
  position: relative;
  overflow: hidden;
}
.chat-float-header::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
  background-size: 200% 100%;
  animation: headerGlide 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes headerShimmer {
  0%, 100% { background-position: 0% center; }
  50% { background-position: 100% center; }
}
@keyframes headerGlide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  position: relative;
  z-index: 1;
}
.chat-header-left :deep(.el-icon) {
  color: #fff;
}
.chat-float-header :deep(.el-button) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.15);
  position: relative;
  z-index: 1;
}
.chat-float-header :deep(.el-button:hover) {
  background: rgba(255, 255, 255, 0.3);
}
.chat-float-history {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
  max-height: 320px;
  background: $of-bg-card;
}
.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bbb;
  font-size: 13px;
  padding: 40px 0;
  gap: 8px;
  animation: fadeInUp 0.5s ease both;
}
.chat-placeholder :deep(.el-icon) {
  animation: placeholderFloat 3s ease-in-out infinite;
}
@keyframes placeholderFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.chat-float-input {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid $of-border-default;
  background: #fff;
  align-items: flex-end;
}
.chat-float-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 13px;
  padding: 8px 12px;
  transition: border-color 0.25s, box-shadow 0.25s;
}
.chat-float-input :deep(.el-textarea__inner:focus) {
  border-color: #409EFF;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.12);
}
.chat-send-btn {
  height: 36px;
  flex-shrink: 0;
  transition: all 0.2s;
}
.chat-send-btn:not(:disabled):hover {
  transform: scale(1.04);
}
.chat-send-btn:not(:disabled):active {
  transform: scale(0.96);
}
.chat-float-trigger {
  position: absolute !important;
  bottom: 20px;
  right: 20px;
  z-index: 200;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
  transition: transform 0.2s, box-shadow 0.2s;
  animation: triggerPulse 2.5s ease-in-out infinite;
}
@keyframes triggerPulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3); }
  50% { box-shadow: 0 4px 28px rgba(64, 158, 255, 0.55); }
}
.chat-float-trigger:hover {
  transform: translateY(-3px) scale(1.02);
}

/* ===== Chat Messages ===== */
.chat-msg {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  animation: msgFadeIn 0.35s ease both;
}
.chat-msg.user {
  justify-content: flex-end;
  animation-name: msgSlideInRight;
}
.chat-msg.ai {
  justify-content: flex-start;
  animation-name: msgSlideInLeft;
}
@keyframes msgSlideInLeft {
  from { opacity: 0; transform: translateX(-16px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes msgSlideInRight {
  from { opacity: 0; transform: translateX(16px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes msgFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.chat-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.chat-avatar-ai {
  background: $of-gradient-blue;
  color: #fff;
}
.chat-avatar-user {
  background: #a0cfff;
  color: #fff;
}
.chat-bubble {
  max-width: 75%;
  padding: 8px 14px;
  border-radius: $of-radius-lg;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.chat-msg.user .chat-bubble {
  background: $of-gradient-blue;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg.ai .chat-bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e8eaed;
  border-bottom-left-radius: 4px;
}

/* Typing indicator */
.chat-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 18px !important;
}
.typing-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #bbb;
  animation: typingBounce 1.4s infinite ease-in-out both;
}
.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0s; }
@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}


/* ===== Body ===== */
.opsflow-body {
  flex: 1;
  overflow: hidden;
  position: relative;
  margin: 8px;
  border-radius: $of-radius-sm;
  background: #fff;
  box-shadow: $of-shadow-card;
}

/* ===== Dialog ===== */
.opsflow-dialog :deep(.el-dialog__header) { @include of-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include of-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include of-dialog-footer; }
.form-tip {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

/* ===== AI Analyze ===== */
.analyze-body {
  min-height: 280px;
}
.analyze-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* Summary hero */
.summary-hero {
  display: flex;
  gap: 14px;
  background: $of-gradient-hero;
  border-left: 4px solid $of-color-primary;
  border-radius: $of-radius-card;
  padding: $of-padding-card;
  align-items: flex-start;
}
.summary-hero-icon {
  width: 40px;
  height: 40px;
  border-radius: $of-radius-card;
  background: $of-gradient-blue;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.summary-hero-text {
  flex: 1;
  min-width: 0;
}
.summary-hero-label {
  font-size: 13px;
  font-weight: 600;
  color: $of-color-primary;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.summary-hero-text p {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

/* Section cards */
.section-card {
  background: $of-bg-card;
  border-radius: $of-radius-card;
  padding: $of-padding-card;
  border: 1px solid $of-border-card;
}
.section-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}
.section-card-header .el-tag {
  margin-left: auto;
}
.section-card-row {
  display: flex;
  gap: 18px;
}
.section-card-half {
  flex: 1;
  min-width: 0;
}

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.timeline-item {
  display: flex;
  gap: 14px;
}
.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
  flex-shrink: 0;
}
.timeline-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $of-gradient-blue;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.35);
}
.timeline-line {
  width: 2px;
  flex: 1;
  min-height: 16px;
  background: linear-gradient(to bottom, #c0d9f5, #e8eef7);
}
.timeline-card {
  flex: 1;
  padding: 6px 0 18px 0;
  min-width: 0;
}
.timeline-card-text {
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #444;
  transition: box-shadow 0.2s;
}
.timeline-card-text:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* Risks */
.risk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.risk-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid $of-border-danger;
  font-size: 13px;
  line-height: 1.5;
  color: #555;
}
.risk-severity {
  width: 4px;
  height: 100%;
  min-height: 20px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-top: 2px;
}
.risk-severity-warning {
  background: #E6A23C;
}
.risk-severity-danger {
  background: #F56C6C;
}

/* Suggestions */
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e8eaed;
  font-size: 13px;
  line-height: 1.5;
  color: #555;
}

/* Summary hero icon pulse */
.summary-hero-icon {
  animation: heroPulse 2s ease-in-out infinite;
}
@keyframes heroPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.35); }
  50% { box-shadow: 0 0 0 8px rgba(64, 158, 255, 0); }
}

/* Dialog enter animation */
.opsflow-dialog :deep(.el-overlay) {
  animation: dialogOverlayIn 0.2s ease both;
}
.opsflow-dialog :deep(.el-dialog) {
  animation: dialogBounceIn 0.3s ease both;
}
@keyframes dialogOverlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes dialogBounceIn {
  from { opacity: 0; transform: scale(0.92) translateY(-20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Section card — extends .of-card */
.section-card {
  @extend .of-card;
}
.section-card:hover {
  @include of-hover-lift;
}

/* Timeline dot pulse on hover */
.timeline-dot {
  transition: transform 0.2s, box-shadow 0.2s;
}
.timeline-item:hover .timeline-dot {
  transform: scale(1.15);
  box-shadow: 0 3px 10px rgba(64, 158, 255, 0.5);
}

/* Risk & suggestion item hover */
.risk-item, .suggestion-item {
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.risk-item:hover {
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.suggestion-item:hover {
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>
