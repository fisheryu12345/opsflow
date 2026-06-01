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
              :model-value="templateId"
              placeholder="Select template"
              clearable filterable
              size="small"
              style="width: 180px"
              @change="(val: any) => emit('changeTemplate', val)"
            >
              <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-button-group>
            <el-tooltip :show-after="500" content="Undo" placement="bottom">
              <el-button size="small" circle :disabled="!canUndo" @click="undo" :icon="RefreshLeft" />
            </el-tooltip>
            <el-tooltip :show-after="500" content="Redo" placement="bottom">
              <el-button size="small" circle :disabled="!canRedo" @click="redo" :icon="RefreshRight" />
            </el-tooltip>
          </el-button-group>
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
          <el-tooltip :show-after="500" content="New template" placement="bottom">
            <el-button size="small" circle type="success" @click="$emit('newTemplate')" :icon="Plus" />
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Global Variables" placement="bottom">
            <el-button size="small" circle type="danger" @click="showVarPanel = !showVarPanel" :icon="Coin" data-var-toggle />
          </el-tooltip>
          <div class="toolbar-divider" />
          <el-tooltip :show-after="500" content="Submit Execution" placement="bottom">
            <el-button size="small" circle @click="showExecDialog = true" :icon="VideoPlay" class="btn-exec" />
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
        <div ref="stencilRef" class="stencil-panel" />
      </div>
      <button class="stencil-toggle" :class="{ collapsed: stencilCollapsed }" @click="toggleStencil">
        <el-icon><component :is="stencilCollapsed ? 'DArrowRight' : 'DArrowLeft'" /></el-icon>
      </button>
      <div id="design-canvas-container" ref="canvasRef" class="x6-canvas" />
      <div ref="minimapRef" class="minimap-container" :style="{ left: stencilCollapsed ? '32px' : '250px' }" />
      <PropertyPanel
        v-if="selectedNode"
        :node-data="selectedNode"
        :template-id="templateId"
        @update="onNodeUpdate"
      />
      <PropertyPanel
        v-else-if="selectedEdge"
        :edge-data="selectedEdge"
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
      <!-- Submit Execution Dialog -->
      <SubmitExecutionDialog
        v-if="templateId"
        v-model="showExecDialog"
        :template-id="templateId"
        :template-name="templateName"
        @execution-created="onExecCreated"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshLeft, RefreshRight, CopyDocument, Upload, DataAnalysis, Plus, Operation, DArrowLeft, DArrowRight, Fold, Expand, ZoomIn, ZoomOut, FullScreen, Coin, VideoPlay } from '@element-plus/icons-vue'
// X6 CSS — 必须导入否则 Stencil、Minimap 等插件容器不显示
import '@antv/x6/dist/index.css'
import '@antv/x6-plugin-stencil/dist/index.css'
import '@antv/x6-plugin-minimap/dist/index.css'
import { useDesignCanvas } from '../composables/useDesignCanvas'
import PropertyPanel from './PropertyPanel.vue'
import GlobalVariablePanel from './GlobalVariablePanel.vue'
import SubprocessStatusBadge from './SubprocessStatusBadge.vue'
import ProjectSwitcher from './ProjectSwitcher.vue'
import SubmitExecutionDialog from './SubmitExecutionDialog.vue'

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
}>()

const showVarPanel = ref(false)
const showExecDialog = ref(false)
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

function onExecCreated(execId: number) {
  emit('submitExecution', execId)
}

function onGlobalVarsUpdated() {
  // Variables panel will re-fetch via watcher on templateId
}

function onSubprocessUpdated() {
  // Subprocess refs updated — trigger re-fetch from badge component
}

const {
  graph, stencil, selectedNode, selectedEdge,
  initGraph, initStencil, loadGraphData, getGraphData,
  aiLayout, onTaskNodeDropped,
  zoomIn, zoomOut, fitCanvas, zoomLevel,
  undo, redo, canUndo, canRedo, destroy,
  enableResize, enableVisibilityRefresh,
} = useDesignCanvas('design-canvas-container', emit)

const stencilRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLElement | null>(null)
const minimapRef = ref<HTMLElement | null>(null)
const stencilCollapsed = ref(true)

function toggleStencil() {
  stencilCollapsed.value = !stencilCollapsed.value
  nextTick(() => graph.value?.resize())
}

// 接收外部传入的 pipeline 数据
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
  emit('save', data)
  ElMessage.success('Draft saved')
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

function onEdgeUpdate(newData: any) {
  if (graph.value && selectedEdge.value) {
    const edge = graph.value.getCellById(selectedEdge.value.id)
    if (edge) {
      const prev = edge.getData() || {}
      edge.setData({ ...prev, condition: newData.condition || '' })
      // 更新本地 selectedEdge 引用
      selectedEdge.value = { ...selectedEdge.value, condition: newData.condition || '' }
    }
  }
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
  // 使用共享的 resize/visibility 自适应
  enableResize()
  enableVisibilityRefresh()
})

// 选中节点变化时通知父组件（AI 面板折叠/展开）
watch(selectedNode, (val) => {
  emit('nodeSelect', val)
})

defineExpose({ loadPipeline, getGraphData, graph, aiLayout, onTaskNodeDropped, zoomIn, zoomOut, fitCanvas, undo, redo })
</script>

<style scoped>
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
  overflow: hidden;
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
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: transparent; color: #fff;
}
.canvas-toolbar-right .el-button--primary:hover {
  box-shadow: 0 4px 12px rgba(102,126,234,0.35);
}
/* Unique custom colors for buttons without type */
.btn-exec { color: #67C23A; background: #f0f9eb; }
.btn-exec:hover { color: #85ce61; background: #e1f3d8; }
.btn-save { color: #667eea; background: #eef0ff; }
.btn-save:hover { color: #8596f0; background: #dde0fa; }
</style>
