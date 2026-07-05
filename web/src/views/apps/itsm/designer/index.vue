<template>
  <div class="itsm-designer">
    <DesignerToolbar
      :workflow="designer.workflow.value"
      :saving="designer.saving.value"
      :zoom-level="zoomLevel"
      @back="$emit('back')"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @fit-canvas="fitCanvas"
      @auto-layout="designer.autoLayout()"
      @ai-generate="showAIDialog = true"
      @validate="doValidate"
      @save="onSave"
      @deploy="designer.deployWorkflow()"
      @name-change="onNameChange"
    />

    <div class="canvas-body">
      <div class="stencil-wrapper" :class="{ collapsed: stencilCollapsed }">
        <div ref="stencilRef" class="stencil-panel" />
      </div>
      <button class="stencil-toggle" :class="{ collapsed: stencilCollapsed }" @click="toggleStencil">
        <el-icon><component :is="stencilCollapsed ? DArrowRight : DArrowLeft" /></el-icon>
      </button>
      <div id="itsm-canvas-container" ref="canvasRef" class="x6-canvas" />
      <div ref="minimapRef" class="minimap-container" :style="{ left: stencilCollapsed ? '32px' : '250px' }" />

      <DesignerConfigPanel
        :node="designer.selectedNode.value"
        :edge="designer.selectedEdge.value"
        @close="onConfigClose"
        @change="onConfigChange"
        @open-field-editor="onOpenFieldEditor"
      />
    </div>

    <el-dialog v-model="showFieldEditor" title="工单设计" width="960px" top="3vh" class="fd-dialog">
      <FormDesigner :fields="editingFields" @save="onFieldsSave" @cancel="showFieldEditor = false" />
    </el-dialog>

    <el-dialog v-model="showAIDialog" title="AI 生成流程" width="560px" top="5vh">
      <el-form label-position="top">
        <el-form-item label="描述审批需求">
          <el-input v-model="aiPrompt" type="textarea" :rows="4" placeholder="例如: 创建一个服务器采购审批流程，需主管→财务→总监三级审批" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAIDialog = false">取消</el-button>
        <el-button type="primary" :loading="aiLoading" @click="onAIGenerate">AI 生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { useDesigner } from './useDesigner'
import DesignerToolbar from './DesignerToolbar.vue'
import DesignerConfigPanel from './DesignerConfigPanel.vue'
import FormDesigner from './FormDesigner.vue'
import { AIGenerateWorkflow } from '/@/api/itsm/index'

const props = defineProps<{ workflowId?: number }>()
const emit = defineEmits<{ back: [] }>()

const designer = useDesigner('itsm-canvas-container', props.workflowId)
const stencilRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLElement | null>(null)
const minimapRef = ref<HTMLElement | null>(null)
const stencilCollapsed = ref(true)
const zoomLevel = ref(100)
const showFieldEditor = ref(false)
const showAIDialog = ref(false)
const editingFields = ref<any[]>([])
const aiPrompt = ref('')
const aiLoading = ref(false)

function toggleStencil() {
  stencilCollapsed.value = !stencilCollapsed.value
  nextTick(() => designer.graph.value?.resize())
}

function zoomIn() { designer.graph.value?.zoom(0.1); updateZoomLevel() }
function zoomOut() { designer.graph.value?.zoom(-0.1); updateZoomLevel() }
function fitCanvas() { designer.graph.value?.centerContent(); designer.graph.value?.zoomToFit(); updateZoomLevel() }
function updateZoomLevel() {
  const g = designer.graph.value
  if (g) zoomLevel.value = Math.round(g.zoom() * 100)
}

function onConfigClose() { designer.selectedNode.value = null; designer.selectedEdge.value = null }
function onConfigChange() { /* manual save only */ }

function onOpenFieldEditor() {
  editingFields.value = designer.selectedNode.value?.fields ? [...designer.selectedNode.value.fields] : []
  showFieldEditor.value = true
}
function onNameChange(name: string) {
  if (designer.workflow.value) designer.workflow.value.name = name
}
async function onSave() {
  if (!designer.workflow.value) return
  const g = designer.graph.value
  const nodeList: any[] = []
  const edgeList: any[] = []
  if (g) {
    for (const cell of g.getCells()) {
      if (cell.isNode()) {
        const data = cell.getData()
        if (data) nodeList.push(data)
      } else if (cell.isEdge()) {
        const data = cell.getData()
        if (data) edgeList.push(data)
      }
    }
  }
  await designer.saveDesigner(designer.workflow.value, nodeList, edgeList)
}

function doValidate() {
  const errs = designer.validateWorkflow()
  if (errs.length === 0) ElMessage.success('校验通过 ✅')
  else ElMessage.warning(`校验未通过 (${errs.length} 项)`)
}

function onFieldsSave(fields: any[]) {
  editingFields.value = fields
  if (designer.selectedNode.value) designer.selectedNode.value.fields = fields
  showFieldEditor.value = false
}

async function onAIGenerate() {
  if (!aiPrompt.value) return
  aiLoading.value = true
  try {
    await AIGenerateWorkflow(aiPrompt.value)
    ElMessage.success('AI 生成成功')
  } catch { ElMessage.error('AI 生成失败') }
  aiLoading.value = false
  showAIDialog.value = false
}

onMounted(() => {
  designer.initGraph(minimapRef.value)
  if (stencilRef.value) designer.initStencil(stencilRef.value)
  if (props.workflowId) designer.loadWorkflow(props.workflowId)
})

onBeforeUnmount(() => { designer.destroy() })
</script>

<style scoped>
.itsm-designer {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}
.canvas-body {
  flex: 1; display: flex; overflow: hidden;
  position: relative;
}
.stencil-wrapper {
  flex-shrink: 0; width: 180px;
  overflow: hidden; transition: width 0.25s ease;
  position: relative;
}
.stencil-wrapper.collapsed { width: 0; }
.stencil-panel {
  width: 180px; height: 100%;
  border-right: 1px solid #e4e7ed; background: #fafafa;
  overflow-y: auto; overflow-x: hidden;
}
.stencil-toggle {
  flex-shrink: 0; width: 16px;
  border: none; border-right: 1px solid #e4e7ed;
  background: #f5f7fa; cursor: pointer;
  color: #909399;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; transition: color 0.2s, background 0.2s;
  outline: none; writing-mode: vertical-lr;
}
.stencil-toggle:hover { color: #409EFF; background: #e8f0fe; }
.stencil-toggle.collapsed { border-right-color: transparent; border-left: 1px solid #e4e7ed; }
.x6-canvas { flex: 1; height: 100%; }
.fd-dialog :deep(.el-dialog__body) { padding: 0; }
.fd-dialog { max-width: 98vw; }
.minimap-container {
  position: absolute; bottom: 8px;
  width: 200px; height: 140px;
  border-radius: 8px; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  transition: left 0.25s ease;
}
</style>
