<template>
  <div class="design-canvas-wrapper">
    <div class="canvas-body">
      <div class="canvas-toolbar-float" :class="{ collapsed: toolbarCollapsed }" :style="{ left: stencilCollapsed ? '32px' : '220px' }">
        <template v-if="!toolbarCollapsed">
          <el-tooltip :show-after="500" content="Switch project" placement="bottom">
            <ProjectSwitcher />
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Select template" placement="bottom">
            <el-select
              data-tour="template-selector"
              :model-value="templateId"
              placeholder="Select template"
              clearable filterable
              size="small"
              style="width: 200px"
              @change="(val: any) => emit('changeTemplate', val)"
            >
              <el-option-group v-if="projectTemplates.length" label="📁 Project Templates">
                <el-option v-for="t in projectTemplates" :key="t.id" :label="t.name" :value="t.id" />
              </el-option-group>
              <el-option-group v-if="publicTemplates.length" label="🌐 Public Templates">
                <el-option v-for="t in publicTemplates" :key="t.id" :value="t.id">
                  <span>{{ t.name }}</span>
                  <el-tag size="small" type="warning" style="margin-left: 6px;">Public</el-tag>
                </el-option>
              </el-option-group>
            </el-select>
          </el-tooltip>
          <div class="toolbar-divider" />
          <div class="zoom-controls">
            <el-tooltip :show-after="500" content="Zoom in" placement="bottom">
              <el-button size="small" text :icon="ZoomIn" @click="zoomIn" />
            </el-tooltip>
            <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
            <el-tooltip :show-after="500" content="Zoom out" placement="bottom">
              <el-button size="small" text :icon="ZoomOut" @click="zoomOut" />
            </el-tooltip>
            <el-tooltip :show-after="500" content="Fit canvas" placement="bottom">
              <el-button size="small" text :icon="FullScreen" @click="fitCanvas" />
            </el-tooltip>
          </div>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Diff with AI original" placement="bottom">
            <el-button size="small" circle type="info" @click="$emit('diff')" :icon="CopyDocument" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="AI analyze pipeline" placement="bottom">
            <el-button size="small" circle type="primary" @click="$emit('analyze')" :icon="DataAnalysis" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="Auto layout" placement="bottom">
            <el-button size="small" circle type="warning" @click="aiLayout" :icon="Operation" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="Validate pipeline" placement="bottom">
            <el-button size="small" circle @click="onValidate" :icon="CircleCheck" class="btn-validate" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="New template wizard" placement="bottom">
            <el-button size="small" circle type="success" @click="$emit('newTemplate')" :icon="Plus" />
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Global Variables" placement="bottom">
            <el-button size="small" circle type="danger" @click="showVarPanel = !showVarPanel" :icon="Coin" data-var-toggle />
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Submit Execution" placement="bottom">
            <el-button size="small" circle @click="onSubmitExecution" :icon="VideoPlay" class="btn-exec" data-tour="submit-exec" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="Dry Run - test with mock atoms" placement="bottom">
            <el-button size="small" circle @click="onDryRun" :icon="Monitor" class="btn-dryrun" />
          </el-tooltip>
          <el-tooltip :show-after="500" content="Save draft" placement="bottom">
            <el-button size="small" circle @click="onSave" :icon="Upload" class="btn-save" />
          </el-tooltip>
        </template>
        <el-tooltip :content="toolbarCollapsed ? 'Expand toolbar' : 'Collapse toolbar'" placement="bottom">
          <button class="toolbar-collapse-btn" @click="toolbarCollapsed = !toolbarCollapsed">
            <el-icon><component :is="toolbarCollapsed ? Expand : Fold" /></el-icon>
          </button>
        </el-tooltip>
      </div>
      <div class="stencil-wrapper" :class="{ collapsed: stencilCollapsed }">
        <div ref="stencilRef" class="stencil-panel" data-tour="stencil" />
      </div>
      <button class="stencil-toggle" :class="{ collapsed: stencilCollapsed }" @click="toggleStencil">
        <el-icon><component :is="stencilCollapsed ? 'DArrowRight' : 'DArrowLeft'" /></el-icon>
      </button>
      <div id="design-canvas-container" ref="canvasRef" class="x6-canvas" />
      <div ref="minimapRef" class="minimap-container" :style="{ left: stencilCollapsed ? '32px' : '250px' }" />
      <!-- Tour anchor for Step 3 (property panel area) — always present so the tour can find it -->
      <div data-tour="property-panel-anchor" class="tour-anchor-pp" />
      <PropertyPanel
        v-if="selectedNode"
        data-tour="property-panel"
        :node-data="selectedNode"
        :template-id="templateId"
        :get-graph-data="getGraphData"
        @update="onNodeUpdate"
      />
      <PropertyPanel
        v-else-if="selectedEdge"
        data-tour="property-panel"
        :edge-data="selectedEdge"
        :get-graph-data="getGraphData"
        @update="onEdgeUpdate"
      />
      <!-- Global Variable Panel toggle -->
      <GlobalVariablePanel
        ref="varPanelRef"
        v-if="templateId && showVarPanel"
        :template-id="templateId"
        @update="onGlobalVarsUpdated"
      />
      <!-- Subprocess Status Badge -->
      <SubprocessStatusBadge
        v-if="templateId"
        :template-id="templateId"
        @updated="onSubprocessUpdated"
      />
      <!-- Submit Execution Wizard -->
      <SubmitWizardDialog
        v-if="templateId"
        v-model="showExecDialog"
        :template-id="templateId"
        :template-name="templateName"
        :pipeline-nodes="pipelineData.nodes"
        :pipeline-edges="pipelineData.edges"
        @execution-created="onExecCreated"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Upload, DataAnalysis, Plus, Operation, DArrowLeft, DArrowRight, Fold, Expand, ZoomIn, ZoomOut, FullScreen, Coin, VideoPlay, CircleCheck, Monitor } from '@element-plus/icons-vue'
// X6 CSS — v3 auto-injects CSS via JS, no need for separate CSS imports
import { useDesignCanvas } from '../../composables/useDesignCanvas'
import PropertyPanel from '../panels/PropertyPanel.vue'
import GlobalVariablePanel from '../panels/GlobalVariablePanel.vue'
import SubprocessStatusBadge from '../badges/SubprocessStatusBadge.vue'
import ProjectSwitcher from '../common/ProjectSwitcher.vue'
import SubmitWizardDialog from '../dialogs/SubmitWizardDialog.vue'
import { ConfirmDraft } from '../../api/templates'
import { DryRunExecution } from '../../api/executions'
import { useGraphValidator } from '../../composables/useGraphValidator'

const props = defineProps<{
  templates?: any[]
  templateId?: number | null
}>()

const emit = defineEmits<{
  save: [data: any]
  diff: []
  analyze: []
  newTemplate: []
  changeTemplate: [id: number | null]
  nodeSelect: [node: any]
  nodeNeedPlugin: [nodeId: string]
  submitExecution: [execId: number]
  dryRun: [execId: number]
}>()

const showVarPanel = ref(false)
const showExecDialog = ref(false)
const pipelineData = ref<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })

// Capture current graph data when opening the wizard
watch(showExecDialog, (val) => {
  if (val) {
    pipelineData.value = getGraphData()
  }
})
const toolbarCollapsed = ref(false)
const varPanelRef = ref<HTMLElement | null>(null)

// Click outside GlobalVariablePanel to close
function onDocMousedown(e: MouseEvent) {
  if (!showVarPanel.value) return
  const target = e.target as Node
  // Don't close if clicking inside the panel or the toggle button
  const panelEl = varPanelRef.value?.$el as HTMLElement | undefined
  const toggleBtn = document.querySelector('[data-var-toggle]')
  if (panelEl && !panelEl.contains(target) && toggleBtn && !toggleBtn.contains(target)) {
    showVarPanel.value = false
  }
}
onMounted(() => document.addEventListener('mousedown', onDocMousedown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocMousedown))

const templateName = computed(() => {
  if (!props.templateId || !props.templates) return ''
  const tpl = props.templates.find((t: any) => t.id === props.templateId)
  return tpl?.name || ''
})

const templateIsDraft = computed(() => {
  if (!props.templateId || !props.templates) return true
  const tpl = props.templates.find((t: any) => t.id === props.templateId)
  return tpl?.is_draft !== false
})

const projectTemplates = computed(() => {
  return (props.templates || []).filter((t: any) => !t.is_public)
})

const publicTemplates = computed(() => {
  return (props.templates || []).filter((t: any) => t.is_public)
})

function onExecCreated(execId: number) {
  emit('submitExecution', execId)
}

function onGlobalVarsUpdated() {
  // Variables panel will re-fetch via watcher on templateId
}

function onSubprocessUpdated() {
  // Subprocess refs updated — trigger re-fetch from badge component
}

async function onSubmitExecution() {
  if (!props.templateId) return

  // Validate before submit
  const pipeline = getGraphData()
  const result = validate(pipeline.nodes, pipeline.edges)
  if (!showValidation(result)) return

  if (templateIsDraft.value) {
    try {
      await ElMessageBox.confirm(
        'This template is still a draft. Only published templates can create executions. Publish it now?',
        'Publish Required',
        { confirmButtonText: 'Publish', cancelButtonText: 'Cancel', type: 'warning' }
      )
      await ConfirmDraft(props.templateId)
      ElMessage.success('Template published')
      // Update local draft status
      const tpl = props.templates?.find((t: any) => t.id === props.templateId)
      if (tpl) tpl.is_draft = false
    } catch {
      return // User cancelled or publish failed
    }
  }
  showExecDialog.value = true
}

async function onDryRun() {
  if (!props.templateId) {
    ElMessage.warning('请先选择一个模板')
    return
  }
  const { nodes, edges } = getGraphData()
  // 替换所有任务节点为 test 原子
  for (const node of nodes) {
    if (node.node_type === 'atom' || (!node.node_type && node.atom_type)) {
      node.atom_type = 'test_print_time'
      node.plugin_code = 'test_print_time'
      node.params = {}
    }
  }
  try {
    const res = await DryRunExecution({ template: props.templateId, pipeline_tree: { nodes, edges } })
    const execId = res.data?.data?.id || res.data?.id
    if (!execId) throw new Error('创建失败，未返回执行 ID')
    ElMessage.success(`Dry Run #${execId} 已启动`)
    emit('dryRun', execId)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.msg || 'Dry Run 创建失败')
  }
}

const {
  graph, stencil, selectedNode, selectedEdge,
  initGraph, initStencil, loadGraphData, getGraphData,
  aiLayout, onTaskNodeDropped,
  zoomIn, zoomOut, fitCanvas, zoomLevel,
  destroy,
  enableResize, enableVisibilityRefresh,
} = useDesignCanvas('design-canvas-container', emit)

const { validate, showValidation } = useGraphValidator()

const stencilRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLElement | null>(null)
const minimapRef = ref<HTMLElement | null>(null)
const stencilCollapsed = ref(true)

function toggleStencil() {
  stencilCollapsed.value = !stencilCollapsed.value
  nextTick(() => graph.value?.resize())
}

// Load pipeline data from external source / 接收外部传入的 pipeline 数据
function loadPipeline(data: any) {
  console.log('[loadPipeline] called, data:', !!data, 'nodes:', data?.nodes?.length, 'edges:', data?.edges?.length, 'graph exists:', !!graph.value)
  if (!data) {
    console.warn('[loadPipeline] called with empty data')
    return
  }
  const doLoad = () => {
    if (!graph.value) {
      console.warn('[loadPipeline] graph not ready, retrying...')
      setTimeout(() => doLoad(), 100)
      return
    }
    try {
      loadGraphData(data)
    } catch (e) {
      console.error('[loadPipeline] loadGraphData error:', e)
      ElMessage.error('Failed to load pipeline data')
    }
  }
  nextTick(doLoad)
}

function onSave() {
  const data = getGraphData()
  const result = validate(data.nodes, data.edges)
  if (!showValidation(result)) return
  emit('save', data)
}

function onNodeUpdate(newData: any) {
  if (graph.value && selectedNode.value) {
    const node = graph.value.getCellById(selectedNode.value.id)
    if (node) {
      const nodeType = newData?.node_type || node.getData()?.node_type
      const isEvent = nodeType === 'start_event' || nodeType === 'end_event'
      node.setData(newData)
      if (!isEvent) {
        const label = newData.label || ''
        node.setLabel(label)
        node.setAttrs({ label: { text: label } })
      }
    }
  }
}

/** Validate condition expression ${node_id} references / 校验条件表达式中的 ${node_id} 引用 */
function checkConditionRefs(condition: string) {
  const data = getGraphData()
  const nodeIds = new Set(data.nodes.map(n => n.id))
  const EXPR_PATTERN = /\$\{([^}]*)\}/g
  const VAR_REF_PATTERN = /([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)/g
  let match: RegExpExecArray | null
  EXPR_PATTERN.lastIndex = 0
  while ((match = EXPR_PATTERN.exec(condition)) !== null) {
    const expr = match[1]
    let varMatch: RegExpExecArray | null
    VAR_REF_PATTERN.lastIndex = 0
    while ((varMatch = VAR_REF_PATTERN.exec(expr)) !== null) {
      if (!nodeIds.has(varMatch[1])) {
        ElMessage.warning(`条件引用不存在的节点 '${varMatch[1]}'`)
      }
    }
  }
}

function onEdgeUpdate(newData: any) {
  if (graph.value && selectedEdge.value) {
    const edge = graph.value.getCellById(selectedEdge.value.id)
    if (edge) {
      const prev = edge.getData() || {}
      const label = newData.label || ''
      // success/failure labels need no condition expression / success/failure 不需要 condition
      const condition = label === 'custom' ? (newData.condition || prev.condition || '') : ''
      const conditionStruct = label === 'custom' ? (newData.conditionStruct || prev.conditionStruct || null) : null
      edge.setData({ ...prev, condition, conditionStruct, label })
      // Display label on the edge line / 标签显示在连线上
      if (label === 'custom') {
        edge.setLabels([{ attrs: { text: { text: 'custom' } } }])
      } else if (label) {
        edge.setLabels([{ attrs: { text: { text: label } } }])
      } else {
        edge.setLabels([])
      }
      // Update local selectedEdge reference / 更新本地 selectedEdge 引用
      selectedEdge.value = {
        ...selectedEdge.value,
        label,
        condition,
      }
      // Validate condition variable references / 校验条件变量引用
      if (condition) checkConditionRefs(condition)
    }
  }
}

function onValidate() {
  const data = getGraphData()
  const result = validate(data.nodes, data.edges)
  showValidation(result)
}

onMounted(() => {
  try {
    initGraph(minimapRef.value)
  } catch (e) {
    console.error('[DesignCanvas] initGraph error:', e)
  }
  if (stencilRef.value) {
    try {
      initStencil(stencilRef.value)
    } catch (e) {
      console.error('[DesignCanvas] initStencil error:', e)
    }
  }
  // 使用共享的 resize/visibility 自适应 / Shared resize & visibility adapters
  enableResize()
  enableVisibilityRefresh()
})

// Notify parent when selected node changes (collapses AI panel) / 选中节点变化时通知父组件（AI 面板折叠/展开）
watch(selectedNode, (val) => {
  emit('nodeSelect', val)
})

defineExpose({ loadPipeline, getGraphData, graph, aiLayout, onTaskNodeDropped, zoomIn, zoomOut, fitCanvas })
</script>

<style lang="scss" scoped>
@use '../../styles/opsflow-global' as *;

.design-canvas-wrapper {
  height: 100%;
  width: 100%;
}
.canvas-toolbar-float {
  position: absolute;
  top: 12px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.95);
  padding: 6px 8px;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
  transition: all 0.25s ease;
}
.canvas-toolbar-float.collapsed {
  padding: 4px 6px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  min-width: auto;
}
.toolbar-collapse-btn {
  border: none;
  background: transparent;
  color: #909399;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  border-radius: 4px;
  transition: color 0.2s, background 0.2s;
}
.toolbar-collapse-btn:hover {
  color: #409EFF;
  background: #e8f0fe;
}
.zoom-controls { display: flex; align-items: center; gap: 2px; background: #f5f7fa; border-radius: 6px; padding: 2px; }
.zoom-level { font-size: 11px; color: #909399; min-width: 36px; text-align: center; font-family: monospace; }
.toolbar-divider { width: 1px; height: 20px; background: #e4e7ed; margin: 0 2px; }
.canvas-body {
  display: flex;
  height: 100%;
  overflow: hidden;
  position: relative;
}
.stencil-wrapper {
  flex-shrink: 0;
  width: 180px;
  overflow: hidden;
  transition: width 0.25s ease;
  position: relative;
}
.stencil-wrapper.collapsed {
  width: 0;
}
.stencil-panel {
  width: 180px;
  height: 100%;
  border-right: 1px solid #e4e7ed;
  background: #fafafa;
  overflow-y: auto;
  overflow-x: hidden;
}
.stencil-toggle {
  flex-shrink: 0;
  width: 16px;
  border: none;
  border-right: 1px solid #e4e7ed;
  background: #f5f7fa;
  color: #909399;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 10px;
  transition: color 0.2s, background 0.2s, width 0.25s ease;
  outline: none;
  writing-mode: vertical-lr;
}
.stencil-toggle:hover {
  color: #409EFF;
  background: #e8f0fe;
}
.stencil-toggle.collapsed {
  border-right-color: transparent;
  border-left: 1px solid #e4e7ed;
}
.x6-canvas {
  flex: 1;
  height: 100%;
}
.minimap-container {
  position: absolute;
  bottom: 8px;
  width: 200px;
  height: 140px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 100;
  transition: left 0.25s ease;
}
.canvas-toolbar-right {
  position: absolute; top: 12px; right: 12px; z-index: 100;
  display: flex; align-items: center; gap: 8px;
}
.canvas-toolbar-right .el-button {
  background: rgba(255,255,255,0.9);
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  backdrop-filter: blur(8px);
  padding: 6px 14px;
}
.canvas-toolbar-right .el-button:hover {
  border-color: #409EFF; color: #409EFF;
  box-shadow: 0 4px 12px rgba(64,158,255,0.2);
}
.canvas-toolbar-right .el-button--primary {
  background: $of-gradient-accent;
  border-color: transparent; color: #fff;
}
.canvas-toolbar-right .el-button--primary:hover {
  box-shadow: 0 4px 12px rgba(102,126,234,0.35);
}
/* Unique custom colors for buttons without type */
.btn-exec { color: #67C23A; background: #f0f9eb; }
.btn-exec:hover { color: #85ce61; background: #e1f3d8; }
.btn-dryrun { color: #9B59B6; background: #f3e8ff; }
.btn-dryrun:hover { color: #b07cd6; background: #edddfa; }
.btn-save { color: #667eea; background: #eef0ff; }
.btn-save:hover { color: #8596f0; background: #dde0fa; }
.btn-validate { color: #E6A23C; background: #fdf6ec; }
.btn-validate:hover { color: #ebb563; background: #faecd8; }
.btn-validate:hover { color: #ebb563; background: #faecd8; }
/* Tour anchor for property panel — positioned where PropertyPanel sits */
.tour-anchor-pp {
  position: absolute;
  right: 0;
  top: 60px;
  width: 360px;
  height: 40px;
  pointer-events: none;
}
</style>

<style lang="scss">
/* X6 连接端口（magnet）hover 动画 — 非 scoped 确保穿透 X6 SVG */
.x6-graph {
  .x6-port-body circle {
    transition: opacity 0.2s ease, r 0.2s ease, stroke-width 0.2s ease;
    cursor: crosshair;
  }
}
</style>
