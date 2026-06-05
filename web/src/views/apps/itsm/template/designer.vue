<template>
  <div class="itsm-designer">
    <!-- Top bar -->
    <div class="itsm-designer-topbar">
      <div class="des-topbar-left">
        <el-button text size="small" @click="$emit('back')">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <el-tag v-if="workflow" :type="workflow.is_draft ? 'warning' : 'success'" size="small" style="margin-left:8px;">
          {{ workflow.is_draft ? '草稿' : '已发布' }}
        </el-tag>
      </div>
      <div class="des-topbar-center">
        <el-input v-if="workflow" v-model="workflow.name" size="small" style="width:300px;font-weight:600;"
          placeholder="流程名称" @blur="onSaveWorkflow" />
      </div>
      <div class="des-topbar-right">
        <el-button size="small" @click="showAIDialog = true">
          <el-icon><MagicStick /></el-icon> AI 生成
        </el-button>
        <el-button size="small" type="primary" @click="onSaveWorkflow" :loading="saving">
          <el-icon><Check /></el-icon> 保存
        </el-button>
        <el-button v-if="workflow?.is_draft" size="small" type="success" @click="onDeploy">
          <el-icon><Upload /></el-icon> 部署
        </el-button>
      </div>
    </div>

    <div class="itsm-designer-body">
      <!-- Left: Palette -->
      <div class="des-palette" v-if="!paletteCollapsed">
        <div class="des-palette-title">节点类型</div>
        <div class="des-palette-list">
          <div v-for="nt in nodeTypes" :key="nt.type" class="des-palette-item"
            :class="'palette-' + nt.type.toLowerCase()" draggable="true"
            @dragstart="onDragStart($event, nt)">
            <span class="palette-icon">{{ nt.icon }}</span>
            <div class="palette-info">
              <div class="palette-name">{{ nt.label }}</div>
              <div class="palette-desc">{{ nt.desc }}</div>
            </div>
          </div>
        </div>
        <button class="des-palette-collapse" @click="paletteCollapsed = true">◀</button>
      </div>
      <button v-else class="des-palette-expand" @click="paletteCollapsed = false">▶ 节点</button>

      <!-- Center: Canvas -->
      <div class="des-canvas" ref="canvasRef"
        @dragover.prevent="onDragOver"
        @drop="onDrop"
        @mousedown="onCanvasClick"
        @contextmenu.prevent="onCanvasContext">
        <!-- SVG connection lines -->
        <svg class="des-svg" :width="svgW" :height="svgH" ref="svgRef">
          <template v-for="(edge) in edges" :key="'e'+edge.fromId+'-'+edge.toId">
            <path :d="edge.path || ''" class="des-edge"
              :class="{ 'des-edge-selected': selectedEdge === edge._idx }"
              :stroke="edge.fromId === 'reject' ? '#F56C6C' : edge.condition ? '#E6A23C' : '#409EFF'"
              stroke-width="2" fill="none" stroke-dasharray="8,4"
              @click="onEdgeClick(edge._idx, $event)" />
            <foreignObject v-if="(edge.label || edge.condition) && edge.labelX != null"
              :x="(edge.labelX || 0) - 40" :y="(edge.labelY || 0) - 10" width="80" height="24">
              <div class="des-edge-label" :class="{ 'reject': edge.fromId === 'reject' }"
                @click="onEdgeClick(edge._idx, $event)">
                {{ edge.condition ? '条件' : (edge.label || '连线') }}
              </div>
            </foreignObject>
          </template>
        </svg>
        <!-- Nodes rendered as position-absolute divs -->
        <div v-for="(node, ni) in nodes" :key="node.id"
          class="des-node"
          :class="{ 'des-node-selected': selectedNode === ni }"
          :style="{ left: node.x + 'px', top: node.y + 'px' }"
          @mousedown.stop="onNodeMouseDown($event, ni)"
          @click.stop="onNodeClick(ni)">
          <div class="des-node-header" :class="'hdr-' + (node.type || 'normal').toLowerCase()">
            <span class="des-node-icon">{{ nodeIcon(node.type) }}</span>
            <span class="des-node-type">{{ nodeTypeLabel(node.type) }}</span>
            <span class="des-node-del" @click.stop="onDeleteNode(ni)" v-if="node.type !== 'START' && node.type !== 'END'">×</span>
          </div>
          <div class="des-node-body">
            <div class="des-node-name">{{ node.name || nodeTypeLabel(node.type) }}</div>
            <div class="des-node-meta" v-if="node.fields?.length">表单: {{ node.fields.length }} 字段</div>
            <div class="des-node-meta" v-else-if="node.type === 'APPROVAL' || node.type === 'SIGN'">
              {{ node.processors_type === 'STARTER_LEADER' ? '提单人上级' :
                 node.processors_type === 'ROLE' ? (node.processors || '角色') :
                 node.processors_type === 'STARTER' ? '提单人' :
                 node.processors || '待配置' }}
            </div>
          </div>
          <!-- Connection endpoints -->
          <div class="des-endpoint des-endpoint-out" @mousedown.stop @mouseup.stop
            @mousedown="onEndpointMouseDown($event, node, 'out', ni)"
            v-if="node.type !== 'END'" />
          <div class="des-endpoint des-endpoint-in" v-if="node.type !== 'START'" />
        </div>
        <!-- Canvas hint -->
        <div v-if="!nodes.length" class="des-canvas-hint">
          {{ paletteCollapsed ? '从左侧展开面板拖入节点' : '从左侧拖入节点开始设计流程' }}
        </div>
        <!-- Context menu -->
        <div v-if="contextMenu.show" class="des-context-menu"
          :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
          <div class="des-cm-item" @click="onContextAction('add_approval')">添加审批</div>
          <div class="des-cm-item" @click="onContextAction('add_normal')">添加填单</div>
          <div class="des-cm-item" @click="onContextAction('add_task')">添加自动任务</div>
          <div class="des-cm-divider" />
          <div class="des-cm-item des-cm-danger" @click="onContextAction('delete')">删除选中</div>
        </div>
      </div>

      <!-- Right: Node Config Panel -->
      <div class="des-config" v-if="configNode && !configCollapsed">
        <div class="des-config-header">
          <span>节点配置</span>
          <el-button text size="small" @click="configCollapsed = true">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="des-config-body">
          <el-form label-position="top" size="small">
            <el-form-item label="节点名称">
              <el-input v-model="configNode.name" @input="onConfigChange" />
            </el-form-item>
            <el-form-item label="节点类型">
              <el-tag size="small">{{ nodeTypeLabel(configNode.type) }}</el-tag>
            </el-form-item>
            <!-- Approval specific -->
            <template v-if="configNode.type === 'APPROVAL' || configNode.type === 'SIGN'">
              <el-form-item label="处理人类型">
                <el-select v-model="configNode.processors_type" @change="onConfigChange" style="width:100%">
                  <el-option label="提单人上级" value="STARTER_LEADER" />
                  <el-option label="指定人员" value="PERSON" />
                  <el-option label="角色" value="ROLE" />
                  <el-option label="提单人" value="STARTER" />
                  <el-option label="变量引用" value="VARIABLE" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="configNode.processors_type === 'ROLE'" label="角色名称">
                <el-input v-model="configNode.processorsRaw" @input="onConfigChange" placeholder="如 财务主管" />
              </el-form-item>
              <el-form-item v-if="configNode.processors_type === 'PERSON'" label="处理人">
                <el-input v-model="configNode.processorsRaw" @input="onConfigChange" placeholder="用户名，逗号分隔" />
              </el-form-item>
              <el-form-item label="审批方式">
                <el-radio-group v-model="configNode.is_multi" @change="onConfigChange">
                  <el-radio :label="false">单签</el-radio>
                  <el-radio :label="true">多签(会签)</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="审批字段">
                <el-button size="small" @click="showFieldEditor = true">
                  <el-icon><Edit /></el-icon> 编辑 ({{ configNode.fields?.length || 0 }})
                </el-button>
              </el-form-item>
            </template>
            <!-- Normal node -->
            <template v-if="configNode.type === 'NORMAL'">
              <el-form-item label="处理人类型">
                <el-select v-model="configNode.processors_type" @change="onConfigChange" style="width:100%">
                  <el-option label="提单人" value="STARTER" />
                  <el-option label="指定人员" value="PERSON" />
                  <el-option label="角色" value="ROLE" />
                  <el-option label="变量引用" value="VARIABLE" />
                </el-select>
              </el-form-item>
              <el-form-item label="表单字段">
                <el-button size="small" @click="showFieldEditor = true">
                  <el-icon><Edit /></el-icon> 编辑 ({{ configNode.fields?.length || 0 }})
                </el-button>
              </el-form-item>
            </template>
            <!-- Transition condition -->
            <el-form-item label="拒绝连线" v-if="selectedEdge !== null && edges[selectedEdge]">
              <el-switch v-model="edges[selectedEdge].isReject" @change="onEdgeConditionChange" />
              <div v-if="edges[selectedEdge]?.condition" class="des-edge-cond-text">
                条件: {{ JSON.stringify(edges[selectedEdge].condition) }}
              </div>
            </el-form-item>
          </el-form>
        </div>
        <button class="des-config-collapse" @click="configCollapsed = true">▶</button>
      </div>
      <div v-else-if="configCollapsed" class="des-config-expand" @click="configCollapsed = false">
        ◀ 配置
      </div>
    </div>

    <!-- Field Editor Dialog -->
    <el-dialog v-model="showFieldEditor" title="表单字段编辑" width="620px" top="5vh" class="des-field-dialog">
      <div class="des-field-toolbar">
        <el-select v-model="newFieldType" size="small" style="width:140px;margin-right:8px;">
          <el-option v-for="ft in fieldTypes" :key="ft.value" :label="ft.label" :value="ft.value" />
        </el-select>
        <el-input v-model="newFieldKey" size="small" placeholder="字段标识" style="width:120px;margin-right:8px;" />
        <el-input v-model="newFieldName" size="small" placeholder="显示名称" style="width:140px;margin-right:8px;" />
        <el-button size="small" type="primary" @click="onAddField">
          <el-icon><Plus /></el-icon> 添加
        </el-button>
      </div>
      <div class="des-field-list" v-if="(configNode?.fields || []).length">
        <div v-for="(f, fi) in (configNode?.fields || [])" :key="fi" class="des-field-item">
          <div class="des-field-info">
            <span class="des-field-name">{{ f.name }}</span>
            <span class="des-field-key">{{ f.key }}</span>
            <el-tag size="small">{{ f.type }}</el-tag>
            <el-tag v-if="f.required" size="small" type="danger">必填</el-tag>
          </div>
          <div class="des-field-actions">
            <el-button size="small" text @click="editFieldChoices(f)">
              <el-icon><Setting /></el-icon>
            </el-button>
            <el-button size="small" text type="danger" @click="onDeleteField(fi)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
      <div v-else class="des-field-empty">暂无字段，请添加</div>
      <!-- Choices editor for SELECT/RADIO/CHECKBOX -->
      <div v-if="editingChoices" class="des-choices-editor">
        <div class="des-choices-title">编辑选项 ({{ editingChoicesName }})</div>
        <div v-for="(c, ci) in editingChoicesList" :key="ci" class="des-choice-row">
          <el-input v-model="c.label" size="small" placeholder="显示名" style="width:140px;margin-right:4px;" />
          <el-input v-model="c.value" size="small" placeholder="值" style="width:120px;margin-right:4px;" />
          <el-button size="small" text type="danger" @click="editingChoicesList.splice(ci, 1)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" @click="editingChoicesList.push({label:'', value:''})">
          <el-icon><Plus /></el-icon> 添加选项
        </el-button>
        <el-button size="small" type="primary" @click="onSaveChoices">完成</el-button>
      </div>
      <template #footer>
        <el-button @click="showFieldEditor = false">关闭</el-button>
        <el-button type="primary" @click="onSaveFields">保存字段</el-button>
      </template>
    </el-dialog>

    <!-- AI Generate Dialog -->
    <el-dialog v-model="showAIDialog" title="🤖 AI 生成流程" width="560px" top="5vh">
      <el-form label-position="top">
        <el-form-item label="描述审批需求">
          <el-input v-model="aiPrompt" type="textarea" :rows="4"
            placeholder="例如: 创建一个服务器采购审批流程，需主管→财务→总监三级审批" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAIDialog = false">取消</el-button>
        <el-button type="primary" :loading="aiLoading" @click="onAIGenerate">
          <el-icon><MagicStick /></el-icon> 生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, MagicStick, Check, Upload, Plus, Close, Edit, Delete, Setting } from '@element-plus/icons-vue'
import { workflowApi, stateApi, transitionApi, fieldApi, DeployWorkflow, AIGenerateWorkflow } from '/@/api/itsm/index'

const emit = defineEmits<{ (e: 'back'): void; (e: 'saved'): void }>()

// ===== Props =====
const props = withDefaults(defineProps<{ workflowId?: number }>(), { workflowId: 0 })

// ===== State =====
const workflow = ref<any>(null)
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const saving = ref(false)
const paletteCollapsed = ref(false)
const configCollapsed = ref(false)
const selectedNode = ref<number | null>(null)
const selectedEdge = ref<number | null>(null)
const configNode = ref<any>(null)
const showFieldEditor = ref(false)
const showAIDialog = ref(false)
const aiPrompt = ref('')
const aiLoading = ref(false)
const svgW = ref(2000)
const svgH = ref(2000)
const canvasRef = ref<HTMLElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)
const contextMenu = reactive({ show: false, x: 0, y: 0 })
const editingChoices = ref(false)
const editingChoicesName = ref('')
const editingChoicesList = ref<any[]>([])
const editingChoicesField = ref<any>(null)

// ===== Node types =====
const nodeTypes = [
  { type: 'NORMAL', icon: '📋', label: '填单节点', desc: '用户填写表单' },
  { type: 'APPROVAL', icon: '✅', label: '审批节点', desc: '单签/会签审批' },
  { type: 'SIGN', icon: '✍️', label: '会签节点', desc: '多审批人会签' },
  { type: 'TASK', icon: '⚡', label: '自动任务', desc: 'API 自动执行' },
  { type: 'ROUTER_P', icon: '🔀', label: '并行网关', desc: '并行分支' },
  { type: 'COVERAGE', icon: '🔃', label: '汇聚网关', desc: '合并分支' },
]

const fieldTypes = [
  { value: 'STRING', label: '单行文本' }, { value: 'TEXT', label: '多行文本' },
  { value: 'INT', label: '数字' }, { value: 'SELECT', label: '下拉框' },
  { value: 'RADIO', label: '单选框' }, { value: 'CHECKBOX', label: '多选框' },
  { value: 'DATE', label: '日期' }, { value: 'DATETIME', label: '日期时间' },
  { value: 'MEMBERS', label: '人员选择' },
]

const newFieldType = ref('STRING')
const newFieldKey = ref('')
const newFieldName = ref('')

// ===== Init =====
onMounted(async () => {
  if (props.workflowId) await loadWorkflow(props.workflowId)
  document.addEventListener('mouseup', onGlobalMouseUp)
  document.addEventListener('mousemove', onGlobalMouseMove)
})
onBeforeUnmount(() => {
  document.removeEventListener('mouseup', onGlobalMouseUp)
  document.removeEventListener('mousemove', onGlobalMouseMove)
})

async function loadWorkflow(id: number) {
  try {
    const res = await workflowApi.detail(id.toString())
    workflow.value = res?.data || res
    // Load states
    const sRes = await stateApi.list({ workflow: id })
    const states: any[] = sRes?.results || sRes?.data || sRes || []
    // Load transitions
    const tRes = await transitionApi.list({ workflow: id })
    const trans: any[] = tRes?.results || tRes?.data || tRes || []
    // Layout nodes in a simple grid
    layoutNodes(states, trans)
  } catch (e) {
    // New workflow — create default START/END
    createDefaultNodes()
  }
}

function createDefaultNodes() {
  nodes.value = [
    { id: 's1', name: '开始', type: 'START', is_builtin: true, x: 100, y: 200 },
    { id: 'e1', name: '结束', type: 'END', is_builtin: true, x: 700, y: 200 },
  ]
}

function layoutNodes(states: any[], trans: any[]) {
  const centerY = 200
  const spacing = 200
  // Map state → node
  const stateMap: Record<string, any> = {}
  const list = states.filter(s => !['START', 'END'].includes(s.type))
  const start = states.find(s => s.type === 'START')
  const end = states.find(s => s.type === 'END')

  const items: any[] = []
  if (start) items.push({ ...start, x: 60, y: centerY })
  list.forEach((s, i) => {
    items.push({ ...s, x: 200 + i * spacing, y: centerY + (i % 2 ? 60 : -60) })
  })
  if (end) items.push({ ...end, x: 200 + list.length * spacing, y: centerY })

  nodes.value = items
	  edges.value = trans.map(t => ({
	    fromId: stateMap[t.from_state]?.id || `s_${t.from_state}`,
	    toId: stateMap[t.to_state]?.id || `s_${t.to_state}`,
	    label: t.name || "",
	    condition: t.condition || null,
	    isReject: t.condition_type === "branch" && t.condition?.approve_result?.eq === "false",
	    path: "",
	    labelX: 0,
	    labelY: 0,
	  }))
  updateSvgPaths()
}

// ===== SVG Path Drawing =====
function updateSvgPaths() {
  const nds = nodes.value
  edges.value.forEach((edge, i) => { edge._idx = i })
  if (selectedEdge.value !== null && (selectedEdge.value >= edges.value.length || !edges.value[selectedEdge.value])) {
    selectedEdge.value = null
  }
  for (const edge of edges.value) {
    const from = nds.find(n => n.id === edge.fromId)
    const to = nds.find(n => n.id === edge.toId)
    if (from && to) {
      const fx = from.x + 120, fy = from.y + 40
      const tx = to.x, ty = to.y + 40
      const mx = (fx + tx) / 2
      const my = (fy + ty) / 2 - 30
      edge.path = `M ${fx} ${fy} Q ${mx} ${my} ${tx} ${ty}`
      edge.labelX = mx
      edge.labelY = my - 5
    }
  }
}

// ===== Node Operations =====
function onDragStart(e: DragEvent, nt: any) {
  e.dataTransfer?.setData('text/plain', nt.type)
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}

function onDrop(e: DragEvent) {
  const type = e.dataTransfer?.getData('text/plain')
  if (!type || !canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left - 60
  const y = e.clientY - rect.top - 25
  const id = `n${Date.now()}`
  const node: any = { id, name: nodeTypeLabel(type), type, x, y, fields: [], processors_type: 'PERSON' }
  if (type === 'START') { node.is_builtin = true; node.name = '开始' }
  if (type === 'END') { node.is_builtin = true; node.name = '结束' }
  nodes.value.push(node)
  updateSvgPaths()
}

function onNodeClick(idx: number) {
  selectedNode.value = idx
  selectedEdge.value = null
  configNode.value = nodes.value[idx]
  configCollapsed.value = false
}

function onCanvasClick() {
  selectedNode.value = null
  selectedEdge.value = null
  configNode.value = null
  contextMenu.show = false
}

function onCanvasContext(e: MouseEvent) {
  contextMenu.show = true
  contextMenu.x = e.offsetX
  contextMenu.y = e.offsetY
}

function onContextAction(action: string) {
  contextMenu.show = false
  if (action === 'delete' && selectedNode.value !== null) {
    onDeleteNode(selectedNode.value)
  } else if (action.startsWith('add_')) {
    const type = action.replace('add_', '').toUpperCase() === 'APPROVAL' ? 'APPROVAL' :
                 action.replace('add_', '').toUpperCase()
    const y = contextMenu.y
    const x = contextMenu.x
    const id = `n${Date.now()}`
    nodes.value.push({ id, name: nodeTypeLabel(type), type, x, y, fields: [], processors_type: 'PERSON' })
    updateSvgPaths()
  }
}

function onDeleteNode(idx: number) {
  const node = nodes.value[idx]
  if (!node || node.is_builtin) return
  edges.value = edges.value.filter(e => e.fromId !== node.id && e.toId !== node.id)
  nodes.value.splice(idx, 1)
  if (selectedNode.value === idx) { selectedNode.value = null; configNode.value = null }
  updateSvgPaths()
}

// ===== Node Dragging =====
let dragState: { idx: number; startX: number; startY: number; origX: number; origY: number } | null = null

function onNodeMouseDown(e: MouseEvent, idx: number) {
  const node = nodes.value[idx]
  dragState = { idx, startX: e.clientX, startY: e.clientY, origX: node.x, origY: node.y }
}

function onGlobalMouseMove(e: MouseEvent) {
  if (!dragState) return
  const dx = e.clientX - dragState.startX
  const dy = e.clientY - dragState.startY
  const node = nodes.value[dragState.idx]
  node.x = Math.max(0, dragState.origX + dx)
  node.y = Math.max(0, dragState.origY + dy)
  updateSvgPaths()
}

function onGlobalMouseUp() {
  if (dragState) {
    updateSvgPaths()
    dragState = null
  }
}

// ===== Edge/Connection Logic =====
let connectState: { fromNode: any; fromIdx: number } | null = null

function onEndpointMouseDown(e: MouseEvent, node: any, dir: string, idx: number) {
  if (dir === 'out') {
    connectState = { fromNode: node, fromIdx: idx }
    e.stopPropagation()
  }
}

// Click canvas to complete connection (simplified)
watch(selectedNode, (idx) => {
  if (connectState && idx !== null && idx !== connectState.fromIdx) {
    const toNode = nodes.value[idx]
    if (toNode && toNode.type !== 'START') {
      edges.value.push({
        fromId: connectState.fromNode.id,
        toId: toNode.id,
        label: '',
        condition: null,
        isReject: false,
        path: '',
        labelX: 0,
        labelY: 0,
      })
      nextTick(() => updateSvgPaths())
    }
    connectState = null
  }
})

function onEdgeClick(idx: number, e: MouseEvent) {
  selectedEdge.value = idx
  selectedNode.value = null
  e.stopPropagation()
}

function onEdgeConditionChange() {
  if (selectedEdge.value === null) return
  const edge = edges.value[selectedEdge.value]
  if (!edge) return
  if (edge.isReject) {
    edge.condition = { approve_result: { eq: 'false' } }
  } else {
    edge.condition = null
  }
  updateSvgPaths()
}

// ===== Node Configuration =====
function onConfigChange() {
  // Auto-update processors JSON
  const node = configNode.value
  if (node.processorsRaw && (node.processors_type === 'ROLE' || node.processors_type === 'PERSON')) {
    try { node.processors = JSON.stringify(node.processorsRaw.split(',').map((s: string) => s.trim())) }
    catch { node.processors = node.processorsRaw }
  }
}

// ===== Field Editor =====
function onAddField() {
  if (!newFieldKey.value || !newFieldName.value) return
  if (!configNode.value.fields) configNode.value.fields = []
  configNode.value.fields.push({
    key: newFieldKey.value,
    name: newFieldName.value,
    type: newFieldType.value,
    required: false,
    choice: [],
  })
  newFieldKey.value = ''
  newFieldName.value = ''
}

function onDeleteField(idx: number) {
  configNode.value?.fields?.splice(idx, 1)
}

function editFieldChoices(field: any) {
  if (field.type === 'SELECT' || field.type === 'RADIO' || field.type === 'CHECKBOX') {
    editingChoicesField.value = field
    editingChoicesName.value = field.name
    editingChoicesList.value = field.choice || []
    editingChoices.value = true
  }
}

function onSaveChoices() {
  if (editingChoicesField.value) {
    editingChoicesField.value.choice = editingChoicesList.value
  }
  editingChoices.value = false
}

function onSaveFields() {
  showFieldEditor.value = false
}

// ===== Save/Publish =====
async function onSaveWorkflow() {
  if (!workflow.value || !workflow.value.name) {
    ElMessage.warning('请输入流程名称')
    return
  }
  saving.value = true
  try {
    let wf = workflow.value
    if (wf.id) {
      await workflowApi.update(wf.id, { name: wf.name, description: wf.description, itsm_type: wf.itsm_type || 'change', is_draft: wf.is_draft })
    } else {
      const res = await workflowApi.create({ name: wf.name, description: wf.description || '', itsm_type: 'change' })
      wf = { ...wf, ...(res?.data || res) }
      workflow.value = wf
    }
    // Save states
    for (const node of nodes.value) {
      if (node.saved) continue
      if (node.id && node.id.toString().startsWith('s')) continue // already has server ID
      try {
        const payload = {
          workflow: wf.id,
          name: node.name, type: node.type,
          is_builtin: node.is_builtin || false,
          processors_type: node.processors_type || 'PERSON',
          processors: node.processors || '',
          fields: node.fields || [],
        }
        await stateApi.create(payload)
      } catch (e: any) { /* ignore dupes */ }
    }
    // Save transitions
    for (const edge of edges.value) {
      try {
        await transitionApi.create({
          workflow: wf.id,
          from_state: edge.fromId,
          to_state: edge.toId,
          condition: edge.condition || {},
          condition_type: edge.condition ? 'branch' : 'default',
        })
      } catch (e: any) { /* ignore dupes */ }
    }
    ElMessage.success('保存成功')
    emit('saved')
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e?.msg || ''))
  } finally { saving.value = false }
}

async function onDeploy() {
  if (!workflow.value?.id) { ElMessage.warning('请先保存'); return }
  try {
    await DeployWorkflow(workflow.value.id, '部署')
    workflow.value.is_draft = false
    ElMessage.success('部署成功')
  } catch (e: any) { ElMessage.error(e?.msg || '部署失败') }
}

async function onAIGenerate() {
  if (!aiPrompt.value) return
  aiLoading.value = true
  try {
    const res = await AIGenerateWorkflow(aiPrompt.value)
    const result = res?.data || res
    // Create workflow
    const wfRes = await workflowApi.create({
      name: result.workflow?.name || aiPrompt.value.slice(0, 128),
      itsm_type: result.workflow?.itsm_type || 'change',
      description: aiPrompt.value,
    })
    const wf = wfRes?.data || wfRes
    // Create states
    const stateMap: Record<string, string> = {}
    for (const s of result.states || []) {
      try {
        const sr = await stateApi.create({ workflow: wf.id, name: s.name, type: s.type, is_builtin: s.is_builtin || false, processors_type: s.processors_type || 'PERSON', processors: s.processors || '', fields: s.fields || [] })
        const sd = sr?.data || sr
        stateMap[s.name] = sd?.id || s.id
      } catch { /* ignore */ }
    }
    // Create transitions
    for (const t of result.transitions || []) {
      try {
        const fromName = typeof t.from === 'string' ? t.from : result.states?.find((s: any) => s.id === t.from_state_id)?.name
        const toName = typeof t.to === 'string' ? t.to : result.states?.find((s: any) => s.id === t.to_state_id)?.name
      } catch { /* ignore */ }
    }
    showAIDialog.value = false
    await loadWorkflow(wf.id)
    ElMessage.success('AI 流程已创建')
  } catch (e: any) { ElMessage.error('AI 生成失败: ' + (e?.msg || '')) }
  finally { aiLoading.value = false }
}

// ===== Helpers =====
function nodeIcon(type: string) {
  const map: Record<string, string> = { START: '▶', END: '◼', NORMAL: '📋', APPROVAL: '✅', SIGN: '✍️', TASK: '⚡', ROUTER_P: '🔀', COVERAGE: '🔃' }
  return map[type] || '📄'
}

function nodeTypeLabel(type: string) {
  const map: Record<string, string> = { START: '开始', END: '结束', NORMAL: '填单', APPROVAL: '审批', SIGN: '会签', TASK: '自动', ROUTER_P: '并行', COVERAGE: '汇聚' }
  return map[type] || type
}
</script>

<style scoped>
.itsm-designer { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* Top Bar */
.itsm-designer-topbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e4e7ed; z-index: 10; gap: 12px; }
.des-topbar-left, .des-topbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* Body */
.itsm-designer-body { flex: 1; display: flex; overflow: hidden; position: relative; }

/* Palette */
.des-palette { width: 200px; background: #fff; border-right: 1px solid #e4e7ed; display: flex; flex-direction: column; position: relative; z-index: 5; flex-shrink: 0; }
.des-palette-title { padding: 12px 14px; font-weight: 600; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.des-palette-list { flex: 1; overflow-y: auto; padding: 8px; }
.des-palette-item { display: flex; align-items: center; gap: 8px; padding: 8px; margin-bottom: 4px; border-radius: 8px; cursor: grab; transition: all 0.15s; border: 1px solid transparent; }
.des-palette-item:hover { background: #f0f5ff; border-color: #d9ecff; }
.des-palette-item:active { cursor: grabbing; }
.palette-icon { font-size: 20px; width: 32px; text-align: center; flex-shrink: 0; }
.palette-info { flex: 1; min-width: 0; }
.palette-name { font-size: 12px; font-weight: 500; }
.palette-desc { font-size: 10px; color: #909399; }
.des-palette-collapse { position: absolute; right: 0; top: 50%; transform: translate(50%, -50%); width: 16px; height: 32px; border: none; background: #fff; cursor: pointer; border-radius: 0 4px 4px 0; box-shadow: 1px 0 4px rgba(0,0,0,.08); z-index: 6; font-size: 10px; padding: 0; }
.des-palette-expand { position: absolute; left: 0; top: 50%; z-index: 5; writing-mode: vertical-lr; padding: 8px 4px; background: #fff; border: 1px solid #e4e7ed; border-left: none; border-radius: 0 4px 4px 0; cursor: pointer; font-size: 11px; }

/* Canvas */
.des-canvas { flex: 1; position: relative; overflow: auto; background: #f5f6fa; background-image: radial-gradient(circle, #dcdfe6 1px, transparent 1px); background-size: 20px 20px; min-height: 100%; }
.des-svg { position: absolute; top: 0; left: 0; pointer-events: none; }
.des-edge { cursor: pointer; pointer-events: stroke; }
.des-edge:hover { stroke-width: 3; }
.des-edge-selected { stroke-width: 3; filter: drop-shadow(0 0 4px rgba(64,158,255,.5)); }
.des-edge-label { background: rgba(255,255,255,.9); border: 1px solid #e4e7ed; border-radius: 4px; padding: 1px 6px; font-size: 10px; cursor: pointer; text-align: center; pointer-events: all; }
.des-edge-label.reject { border-color: #F56C6C; color: #F56C6C; }

/* Nodes */
.des-node { position: absolute; width: 120px; min-height: 60px; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); cursor: move; user-select: none; z-index: 2; transition: box-shadow .15s; border: 2px solid transparent; }
.des-node:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); }
.des-node-selected { border-color: #409EFF; box-shadow: 0 0 0 2px rgba(64,158,255,.2); }
.des-node-header { display: flex; align-items: center; gap: 4px; padding: 6px 8px; border-radius: 8px 8px 0 0; font-size: 11px; color: #fff; }
.hdr-start { background: #67C23A; }
.hdr-end { background: #909399; }
.hdr-normal { background: #409EFF; }
.hdr-approval { background: #E6A23C; }
.hdr-sign { background: #722ed1; }
.hdr-task { background: #13c2c2; }
.hdr-router_p { background: #fa8c16; }
.hdr-coverage { background: #eb2f96; }
.des-node-icon { font-size: 14px; }
.des-node-type { flex: 1; font-weight: 500; }
.des-node-del { cursor: pointer; opacity: 0.6; font-size: 14px; line-height: 1; }
.des-node-del:hover { opacity: 1; }
.des-node-body { padding: 6px 8px; }
.des-node-name { font-size: 12px; font-weight: 500; color: #303133; }
.des-node-meta { font-size: 10px; color: #909399; margin-top: 2px; }
.des-endpoint { position: absolute; width: 10px; height: 10px; border-radius: 50%; border: 2px solid #409EFF; background: #fff; z-index: 3; }
.des-endpoint-out { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: crosshair; }
.des-endpoint-out:hover { background: #409EFF; }
.des-endpoint-in { top: -5px; left: 50%; transform: translateX(-50%); background: #f0f5ff; }
.des-canvas-hint { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #c0c4cc; font-size: 14px; text-align: center; pointer-events: none; }

/* Context Menu */
.des-context-menu { position: absolute; background: #fff; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,.12); z-index: 100; min-width: 120px; padding: 4px; }
.des-cm-item { padding: 6px 12px; font-size: 12px; cursor: pointer; border-radius: 4px; }
.des-cm-item:hover { background: #f5f7fa; }
.des-cm-divider { height: 1px; background: #f0f0f0; margin: 4px 0; }
.des-cm-danger { color: #F56C6C; }

/* Config Panel */
.des-config { width: 280px; background: #fff; border-left: 1px solid #e4e7ed; display: flex; flex-direction: column; position: relative; z-index: 5; flex-shrink: 0; overflow-y: auto; }
.des-config-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; font-weight: 600; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.des-config-body { padding: 14px; flex: 1; overflow-y: auto; }
.des-config-body :deep(.el-form-item) { margin-bottom: 12px; }
.des-config-body :deep(.el-form-item__label) { font-size: 12px; padding: 0; }
.des-config-collapse { position: absolute; left: 0; top: 50%; transform: translate(-50%, -50%); width: 16px; height: 32px; border: none; background: #fff; cursor: pointer; border-radius: 4px 0 0 4px; box-shadow: -1px 0 4px rgba(0,0,0,.08); font-size: 10px; padding: 0; }
.des-config-expand { position: absolute; right: 0; top: 50%; z-index: 5; writing-mode: vertical-lr; padding: 8px 4px; background: #fff; border: 1px solid #e4e7ed; border-right: none; cursor: pointer; font-size: 11px; }
.des-edge-cond-text { font-size: 10px; color: #E6A23C; margin-top: 4px; }

/* Field Dialog */
.des-field-toolbar { display: flex; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 4px; }
.des-field-list { max-height: 360px; overflow-y: auto; }
.des-field-item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border: 1px solid #f0f0f0; border-radius: 6px; margin-bottom: 4px; }
.des-field-info { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.des-field-name { font-weight: 500; }
.des-field-key { color: #909399; font-size: 11px; }
.des-field-actions { display: flex; gap: 4px; }
.des-field-empty { text-align: center; color: #909399; padding: 20px; font-size: 13px; }
.des-choices-editor { border-top: 1px solid #f0f0f0; padding: 12px; margin-top: 12px; }
.des-choices-title { font-weight: 600; font-size: 12px; margin-bottom: 8px; }
.des-choice-row { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; }
</style>
