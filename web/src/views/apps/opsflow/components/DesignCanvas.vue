<template>
  <div class="design-canvas-wrapper">
    <div class="canvas-body">
      <div class="canvas-toolbar-float" :style="{ left: stencilCollapsed ? '32px' : '220px' }">
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
        <div class="toolbar-divider" />
        <el-button-group>
          <el-button size="small" circle :disabled="!canUndo" @click="undo" :icon="RefreshLeft" />
          <el-button size="small" circle :disabled="!canRedo" @click="redo" :icon="RefreshRight" />
        </el-button-group>
        <div class="toolbar-divider" />
        <div class="zoom-controls">
          <el-button size="small" text :icon="ZoomIn" @click="zoomIn" />
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button size="small" text :icon="ZoomOut" @click="zoomOut" />
          <el-button size="small" text :icon="FullScreen" @click="fitCanvas" />
        </div>
        <div class="toolbar-divider" />
        <el-button size="small" circle @click="$emit('diff')" :icon="CopyDocument" />
        <el-button size="small" circle @click="$emit('analyze')" :icon="DataAnalysis" />
        <el-button size="small" circle @click="aiLayout" :icon="Operation" />
        <el-button size="small" circle @click="$emit('newTemplate')" :icon="Plus" />
        <el-button size="small" circle type="primary" @click="onSave" :icon="Upload" />
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
        @update="onNodeUpdate"
      />
      <PropertyPanel
        v-else-if="selectedEdge"
        :edge-data="selectedEdge"
        @update="onEdgeUpdate"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshLeft, RefreshRight, CopyDocument, Upload, DataAnalysis, Plus, Operation, DArrowLeft, DArrowRight, ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
// X6 CSS — 必须导入否则 Stencil、Minimap 等插件容器不显示
import '@antv/x6/dist/index.css'
import '@antv/x6-plugin-stencil/dist/index.css'
import '@antv/x6-plugin-minimap/dist/index.css'
import { useDesignCanvas } from '../composables/useDesignCanvas'
import PropertyPanel from './PropertyPanel.vue'

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
}>()

const {
  graph, stencil, selectedNode, selectedEdge,
  initGraph, initStencil, loadGraphData, getGraphData,
  aiLayout, onTaskNodeDropped,
  zoomIn, zoomOut, fitCanvas, zoomLevel,
  undo, redo, canUndo, canRedo, destroy,
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
  console.log('[DesignCanvas] onMounted, container exists:', !!document.getElementById('design-canvas-container'))
  if (document.getElementById('design-canvas-container')) {
    const rect = document.getElementById('design-canvas-container')!.getBoundingClientRect()
    console.log('[DesignCanvas] container rect:', rect)
  }
  try {
    initGraph(minimapRef.value)
    console.log('[DesignCanvas] initGraph complete, graph exists:', !!graph.value)
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
  // 窗口变化时通知画布自适应
  const ro = new ResizeObserver(() => {
    graph.value?.resize()
  })
  const containerEl = document.getElementById('design-canvas-container')
  if (containerEl) ro.observe(containerEl)
  // 清理
  onBeforeUnmount(() => {
    ro.disconnect()
    destroy()
  })
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
</style>
