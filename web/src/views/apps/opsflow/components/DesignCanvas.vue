<template>
  <div class="design-canvas-wrapper">
    <div class="canvas-body">
      <div class="canvas-toolbar-float">
        <el-button-group>
          <el-button size="small" circle :disabled="!canUndo" @click="undo" :icon="RefreshLeft" />
          <el-button size="small" circle :disabled="!canRedo" @click="redo" :icon="RefreshRight" />
        </el-button-group>
        <el-button size="small" circle @click="$emit('diff')" :icon="CopyDocument" />
        <el-button size="small" circle @click="$emit('analyze')" :icon="DataAnalysis" />
        <el-button size="small" circle type="primary" @click="onSave" :icon="Upload" />
      </div>
      <div ref="stencilRef" class="stencil-panel" />
      <div id="design-canvas-container" ref="canvasRef" class="x6-canvas" />
      <div ref="minimapRef" class="minimap-container" />
      <PropertyPanel v-if="selectedNode" :node-data="selectedNode" @update="onNodeUpdate" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshLeft, RefreshRight, CopyDocument, Upload, DataAnalysis } from '@element-plus/icons-vue'
// X6 CSS — 必须导入否则 Stencil、Minimap 等插件容器不显示
import '@antv/x6/dist/index.css'
import '@antv/x6-plugin-stencil/dist/index.css'
import '@antv/x6-plugin-minimap/dist/index.css'
import { useDesignCanvas } from '../composables/useDesignCanvas'
import PropertyPanel from './PropertyPanel.vue'

const emit = defineEmits<{
  save: [data: any]
  diff: []
  analyze: []
}>()

const {
  graph, stencil, selectedNode,
  initGraph, initStencil, loadGraphData, getGraphData,
  aiLayout,
  undo, redo, canUndo, canRedo, destroy,
} = useDesignCanvas('design-canvas-container')

const stencilRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLElement | null>(null)
const minimapRef = ref<HTMLElement | null>(null)

// 接收外部传入的 pipeline 数据
function loadPipeline(data: any) {
  if (!data) {
    console.warn('[loadPipeline] called with empty data')
    return
  }
  nextTick(() => {
    try {
      loadGraphData(data)
    } catch (e) {
      console.error('[loadPipeline] loadGraphData error:', e)
      ElMessage.error('Failed to load pipeline data')
    }
  })
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
      node.setData(newData)
      // 自定义 Node.define shape 必须显式设置 attrs.label.text
      const label = newData.label || ''
      node.setLabel(label)
      node.setAttrs({ label: { text: label } })
    }
  }
}

onMounted(() => {
  initGraph(minimapRef.value)
  if (stencilRef.value) {
    initStencil(stencilRef.value)
  }
  // 窗口变化时通知画布自适应
  const ro = new ResizeObserver(() => {
    graph.value?.resize()
  })
  ro.observe(document.getElementById('design-canvas-container')!)
  // 清理
  onBeforeUnmount(() => {
    ro.disconnect()
    destroy()
  })
})

defineExpose({ loadPipeline, getGraphData, graph, aiLayout, undo, redo })
</script>

<style scoped>
.design-canvas-wrapper {
  height: 100%;
  width: 100%;
}
.canvas-toolbar-float {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 100;
  display: flex;
  gap: 6px;
  background: rgba(255, 255, 255, 0.95);
  padding: 6px 8px;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
}
.canvas-body {
  display: flex;
  height: 100%;
  overflow: hidden;
  position: relative;
}
.stencil-panel {
  width: 180px;
  border-right: 1px solid #e4e7ed;
  background: #fafafa;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
}
.x6-canvas {
  flex: 1;
  height: 100%;
}
.minimap-container {
  position: absolute;
  bottom: 8px;
  left: 195px;
  width: 200px;
  height: 140px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 100;
}
</style>
