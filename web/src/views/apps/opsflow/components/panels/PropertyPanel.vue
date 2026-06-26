<template>
  <div class="property-panel">
    <div class="panel-header">
      <el-icon size="16"><Setting /></el-icon>
      <span>{{ $t("message.properties.basic") }}</span>
    </div>

    <template v-if="form.id">
      <div class="panel-section">
        <div class="section-title">{{ $t("message.properties.basicInfo") }}</div>
        <div class="prop-row">
          <span class="prop-label">ID</span>
          <span class="prop-value prop-id">{{ form.id }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">{{ $t("message.properties.label") }}</span>
          <el-input v-model="form.label" size="small" @change="emitUpdate" class="prop-input" />
        </div>
      </div>

      <template v-if="isAtom">
        <div class="panel-section">
          <div class="section-title">{{ $t("message.properties.actionConfig") }}</div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.plugin") }}</span>
            <el-select v-model="form.plugin_code" size="small" style="width:100%"
              filterable @change="onPluginChange" :loading="pluginsLoading">
              <el-option-group v-for="(items, group) in pluginGroups" :key="group" :label="group">
                <el-option v-for="p in items" :key="p.code" :label="(isEn && p.name_en ? p.name_en : p.name) + ' (' + p.versions?.join(', ') + ')'" :value="p.code" />
              </el-option-group>
            </el-select>
          </div>
          <!-- 版本选择器 -->
          <div class="prop-row" v-if="isAtom && pluginVersions.length > 1">
            <span class="prop-label">{{ $t("message.properties.version") }}</span>
            <el-select v-model="form._plugin_version" size="small" style="width:120px" @change="emitUpdate">
              <el-option v-for="v in pluginVersions" :key="v" :label="v" :value="v" />
            </el-select>
          </div>
        </div>

        <!-- Input Parameters -->
        <div class="panel-section" v-if="isAtom && pluginFormSchema.length">
          <div class="section-title">{{ $t("message.properties.inputs") }}</div>
          <!-- 动态表单渲染（传递 templateId + nodeId 供 TagVariableInput 使用） -->
          <div class="prop-row-vertical">
            <RenderForm
              ref="renderFormRef"
              :schema="pluginFormSchema"
              :initial-data="form.plugin_params"
              :context="contextWithVars"
              @change="onFormChange"
            />
          </div>
        </div>

        <!-- Output Parameters -->
        <OutputParamSection
          v-if="isAtom"
          :schema="outputSchema"
          :node-id="form.id || ''"
          :template-id="templateId"
        />

        <!-- Variable References in this node -->
        <div class="panel-section" v-if="varReferences.length">
          <div class="section-title">{{ $t("message.properties.variableRefs") }}</div>
          <div class="var-ref-list">
            <el-tag v-for="ref in varReferences" :key="ref" size="small" type="warning" effect="light" class="var-ref-tag">
              {{ ref }}
            </el-tag>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-title">{{ $t("message.properties.executionControl") }}</div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.maxRetries") }}</span>
            <el-input-number v-model="form.max_retries" :min="0" :max="10" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.retryDelay") }}</span>
            <el-input-number v-model="form.retry_delay" :min="0" :max="300" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.timeoutSeconds") }}</span>
            <el-input-number v-model="form.timeout_seconds" :min="5" :max="600" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.riskLevel") }}</span>
            <el-tag :type="riskTagType" size="small" effect="dark" class="risk-tag">
              {{ riskLevelText }}
            </el-tag>
          </div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.optional") }}</span>
            <el-switch v-model="form.optional" @change="emitUpdate" size="small" />
          </div>
        </div>
      </template>

      <!-- SubProcess 配置 -->
      <template v-else-if="isSubprocess">
        <div class="panel-section">
          <div class="section-title">{{ $t("message.properties.subprocessConfig") }}</div>
          <div class="prop-row-vertical">
            <span class="prop-label">{{ $t("message.properties.targetTemplate") }}</span>
            <el-select v-model="form.target_template_id" size="small" filterable style="width:100%"
              @change="emitUpdate" :loading="templatesLoading">
              <el-option v-for="t in publishedTemplates" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </div>
          <!-- Version status alert -->
          <div v-if="subprocessVersion" class="prop-row-vertical" style="margin-top:6px">
            <el-alert
              v-if="subprocessVersion.stale"
              type="warning" :closable="false" show-icon size="small"
              :title="`Version outdated: v${subprocessVersion.referenced_version} → v${subprocessVersion.current_version}`"
            />
            <el-alert
              v-else
              type="success" :closable="false" show-icon size="small"
              :title="`Up-to-date: v${subprocessVersion.current_version}`"
            />
          </div>
          <!-- Mode toggle (Phase 5) -->
          <div class="prop-row" style="margin-top:8px">
            <span class="prop-label">{{ $t("message.properties.mode") }}</span>
            <el-switch
              v-model="form.independent"
              :active-text="$t('message.properties.independent')"
              :inactive-text="$t('message.properties.embedded')"
              @change="emitUpdate"
              size="small"
            />
          </div>
          <div class="prop-row-vertical" style="margin-top:8px">
            <span class="prop-label">{{ $t("message.properties.variableMapping") }}</span>
            <TagVariableMapping v-model="form.variable_mapping" />
          </div>
          <div class="prop-row-vertical" style="margin-top:8px">
            <span class="prop-label">{{ $t("message.properties.outputMapping") }}</span>
            <TagVariableMapping v-model="form.output_mapping" />
          </div>
        </div>
      </template>

      <!-- Approval 配置 -->
      <template v-else-if="isApproval">
        <div class="panel-section">
          <div class="section-title">{{ $t("message.properties.approvalConfig") }}</div>
          <div class="prop-row-vertical">
            <span class="prop-label">{{ $t("message.properties.approvers") }}</span>
            <el-select v-model="form.approvers" multiple filterable size="small" style="width:100%"
              :placeholder="$t('message.properties.selectApprovers')" @change="emitUpdate">
              <el-option v-for="u in userList" :key="u" :label="u" :value="u" />
            </el-select>
          </div>
          <div class="prop-row">
            <span class="prop-label">{{ $t("message.properties.timeout") }}</span>
            <el-input-number v-model="form.approval_timeout" :min="300" :max="604800" :step="3600" size="small" controls-position="right" style="width:140px" @change="emitUpdate" />
            <span style="font-size:11px;color:#909399">sec</span>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="panel-section">
          <div class="section-title">{{ $t("message.opsflowPage.dashboardNodeType") }}</div>
          <div class="gateway-info">
            <el-tag :type="gatewayTagType" size="default" effect="plain">
              <el-icon size="14" style="margin-right:4px"><component :is="gatewayIcon" /></el-icon>
              {{ nodeTypeLabel }}
            </el-tag>
            <p class="gateway-desc">{{ gatewayDescription }}</p>
          </div>
        </div>
      </template>
    </template>

    <template v-else-if="edgeData && edgeData.id">
      <div class="panel-section">
        <div class="section-title">{{ $t("message.properties.condition") }}</div>
        <div class="prop-row">
          <span class="prop-label">{{ $t("message.opsflowPage.from") }}</span>
          <span class="prop-value prop-id">{{ edgeData.from }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">{{ $t("message.opsflowPage.to") }}</span>
          <span class="prop-value prop-id">{{ edgeData.to }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">{{ $t("message.properties.label") }}</span>
          <el-select v-model="edgeForm.label" size="small" style="width:100%" @change="onEdgeLabelChange" clearable :placeholder="$t('message.properties.select')">
            <el-option label="success（成功路径）" value="success" />
            <el-option label="failure（失败路径）" value="failure" />
            <el-option label="custom（自定义条件）" value="custom" />
          </el-select>
        </div>
        <!-- 自定义条件（结构化编辑器） -->
        <div class="prop-row-vertical" v-if="edgeForm.label === 'custom'">
          <span class="prop-label">{{ $t("message.properties.condition") }}</span>
          <div class="condition-preview" @click="openConditionDialog">
            <template v-if="edgeForm.condition">
              <code class="condition-code">{{ edgeForm.condition }}</code>
              <el-button size="small" text>
                <el-icon><EditPen /></el-icon>
                Edit
              </el-button>
            </template>
            <template v-else>
              <span class="condition-placeholder">{{ $t("message.condition.expressionPlaceholder") }}</span>
              <el-button size="small" text>Add</el-button>
            </template>
          </div>
          <!-- 引用变量标签 -->
          <div class="cond-refs" v-if="conditionRefs.length > 0">
            <el-tag
              v-for="ref in conditionRefs"
              :key="ref"
              size="small"
              type="info"
              effect="plain"
              class="cond-ref-tag"
            >
              {{ ref }}
            </el-tag>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="panel-empty">
      <el-icon size="28" color="#c0c4cc"><Pointer /></el-icon>
      <p>Click a node or edge to view properties</p>
    </div>

    <!-- 条件编辑器弹窗 -->
    <ConditionDialog
      :visible="conditionDialogVisible"
      :initial-struct="conditionStruct"
      :available-vars="availableVars"
      :source-node-label="edgeData?.from || ''"
      :target-node-label="edgeData?.to || ''"
      @update:visible="conditionDialogVisible = $event"
      @save="onConditionSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Setting, Pointer, WarnTriangleFilled, CircleCheckFilled, InfoFilled, Aim, Connection, Switch, EditPen } from '@element-plus/icons-vue'
import RenderForm from '/@/components/RenderForm/RenderForm.vue'
import TagVariableMapping from '/@/components/RenderForm/tags/TagVariableMapping.vue'
import OutputParamSection from './OutputParamSection.vue'
import { GetPluginGroups, GetPluginDetail } from '../../api/plugins'
import { GetTemplates, HookVariable } from '../../api/templates'
import { useOpsflowStore } from '../../stores/opsflowStore'
import ConditionDialog from '../gates/ConditionDialog.vue'
import { generateConditionExpr, extractAvailableVariables as getAvailableVars } from '../../composables/useGraphCanvas'
import type { ConditionStruct } from '../../utils/shapes'

const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))

const props = defineProps<{
  nodeData?: any
  edgeData?: any
  templateId?: number | null
  subprocessVersion?: any | null
  getGraphData?: () => { nodes: any[]; edges: any[] }
}>()

const emit = defineEmits<{
  update: [data: any]
}>()

/* ── Form state (MUST be before any computed/watcher that references them) ── */
const form = ref<any>({})
const edgeForm = ref<any>({ condition: '' })
/** 修订计数器 — 每次 form 属性变更时递增，驱动 contextWithVars 重算 */
const formRevision = ref(0)

/* ── Condition editor state ── */
const conditionDialogVisible = ref(false)
const conditionStruct = ref<ConditionStruct | null>(null)
const availableVars = ref<any[]>([])
const opsflowStore = useOpsflowStore()

const conditionRefs = computed(() => {
  const cond = edgeForm.value?.condition || ''
  if (!cond) return []
  const refs = new Set<string>()
  const m = cond.match(/\$\{([^}]+)\}/g)
  if (m) m.forEach(r => refs.add(r.replace(/\$\{|\}/g, '')))
  return [...refs]
})

/** BFS 反向遍历 edges 计算上游节点 ID */
function getUpstreamNodeIds(edges: { from: string; to: string }[], nodeId: string): Set<string> {
  const ids = new Set<string>()
  const queue = [nodeId]
  const visited = new Set<string>()
  while (queue.length) {
    const nid = queue.shift()!
    for (const e of edges) {
      if (e.to === nid && !visited.has(e.from)) {
        visited.add(e.from); queue.push(e.from); ids.add(e.from)
      }
    }
  }
  return ids
}

/** 传递给 RenderForm 的上下文（含可用变量列表，供 TagVariableInput 内联建议） */
const contextWithVars = computed(() => {
  // 依赖 formRevision — 每当 form 属性变更时重算
  void formRevision.value
  const base: Record<string, any> = {
    templateId: props.templateId,
    nodeId: form.value?.id || '',
    tagCode: '',
    onPromote: promoteInput,
  }
  if (form.value?.id && typeof props.getGraphData === 'function') {
    const gd = props.getGraphData()
    if (gd?.nodes?.length) {
      base.availableVars = getAvailableVars(gd.nodes, opsflowStore, {
        currentNodeId: form.value.id,
        edges: gd.edges || [],
      })
      const upstreamIds = form.value.id && gd.edges?.length ? getUpstreamNodeIds(gd.edges, form.value.id) : null
      base.graphNodes = upstreamIds ? gd.nodes.filter(n => upstreamIds.has(n.id)) : gd.nodes
      base.allGraphNodes = gd.nodes
    }
  }
  return base
})

/* ---------- Variable references detection ---------- */
const varReferences = computed(() => {
  const params = form.value?.plugin_params || {}
  const refs = new Set<string>()
  function scan(obj: any) {
    if (!obj) return
    if (typeof obj === 'string') {
      const m = obj.match(/\$\{([^}]+)\}/g)
      if (m) m.forEach(r => refs.add(r))
    } else if (Array.isArray(obj)) {
      obj.forEach(scan)
    } else if (typeof obj === 'object') {
      Object.values(obj).forEach(scan)
    }
  }
  scan(params)
  return [...refs]
})

/* ---------- Plugin loading ---------- */
const pluginsLoading = ref(false)
const pluginGroups = ref<Record<string, { code: string; name: string; name_en?: string }[]>>({})
const pluginFormSchema = ref<any[]>([])
const outputSchema = ref<any[]>([])
const pluginVersions = ref<string[]>([])
const pluginRiskMap = ref<Record<string, string>>({})
const renderFormRef = ref<InstanceType<typeof RenderForm> | null>(null)
const publishedTemplates = ref<any[]>([])
const templatesLoading = ref(false)
const userList = ref<string[]>(['admin', 'operator'])

async function loadPlugins() {
  pluginsLoading.value = true
  try {
    const res = await GetPluginGroups()
    pluginGroups.value = res.data || {}
  } catch {
    pluginGroups.value = {}
  }
  pluginsLoading.value = false
}

async function loadPluginSchema(code: string) {
  try {
    const res = await GetPluginDetail(code)
    const schema = res.data?.form_schema || []
    pluginFormSchema.value = isEn.value
      ? schema.map((item: any) => ({ ...item, name: item.name_en || item.name }))
      : schema
    outputSchema.value = res.data?.output_schema || []
    pluginVersions.value = res.data?.versions || []
    if (res.data?.versions?.length && !form.value._plugin_version) {
      form.value._plugin_version = res.data.versions[res.data.versions.length - 1]
    }
    if (res.data?.risk_level) {
      pluginRiskMap.value[code] = res.data.risk_level
    }
  } catch {
    pluginFormSchema.value = []
    outputSchema.value = []
    pluginVersions.value = []
  }
}

/* ---------- Subprocess version tracking ---------- */
const subprocessVersion = computed(() => {
  if (!form.value.target_template_id || !publishedTemplates.value.length) return null
  const target = publishedTemplates.value.find((t: any) => t.id === form.value.target_template_id)
  if (!target) return null
  const refVersion = form.value._referenced_version ?? target.version
  const currentVersion = target.version
  if (refVersion && currentVersion && refVersion !== currentVersion) {
    return { referenced_version: refVersion, current_version: currentVersion, stale: true }
  }
  return { referenced_version: refVersion, current_version: currentVersion, stale: false }
})

watch(() => form.value.target_template_id, (newId) => {
  if (!newId) return
  const target = publishedTemplates.value.find((t: any) => t.id === newId)
  if (target && !form.value._referenced_version) {
    form.value._referenced_version = target.version
  }
})

/* ---------- Form state ---------- */
const typeLabels: Record<string, string> = {
  start_event: 'Start Event',
  end_event: 'End Event',
  exclusive_gateway: 'Exclusive Gateway',
  parallel_gateway: 'Parallel Gateway',
  conditional_parallel_gateway: 'Conditional Parallel Gateway',
  converge_gateway: 'Converge Gateway',
  approval: 'Approval',
  subprocess: 'SubProcess',
}

const gatewayDescriptions: Record<string, string> = {
  start_event: 'Start of the pipeline. Only one per pipeline.',
  end_event: 'End of the pipeline. All paths converge here.',
  exclusive_gateway: 'Select one path based on condition.',
  parallel_gateway: 'Execute all branches in parallel.',
  conditional_parallel_gateway: 'Execute matching branches in parallel.',
  converge_gateway: 'Merge parallel branches into one path.',
  approval: 'Pauses pipeline execution pending human approval.',
  subprocess: 'Execute another workflow template as a sub-process.',
}

const gatewayIcons: Record<string, any> = {
  start_event: Aim,
  end_event: CircleCheckFilled,
  exclusive_gateway: WarnTriangleFilled,
  parallel_gateway: Connection,
  conditional_parallel_gateway: Switch,
  converge_gateway: InfoFilled,
}


const isAtom = computed(() => !form.value.node_type || form.value.node_type === 'atom')
const isSubprocess = computed(() => form.value.node_type === 'subprocess')
const isApproval = computed(() => form.value.node_type === 'approval')
const nodeTypeLabel = computed(() => typeLabels[form.value.node_type] || form.value.node_type || 'Atom')
const gatewayDescription = computed(() => gatewayDescriptions[form.value.node_type] || '')
const gatewayIcon = computed(() => gatewayIcons[form.value.node_type] || InfoFilled)

const riskLevelText = computed(() => {
  const risk = form.value.risk_level || pluginRiskMap.value[form.value.plugin_code] || ''
  const map: Record<string, string> = { high: t('message.wizard.high'), medium: t('message.wizard.medium'), low: t('message.wizard.low') }
  return map[risk] || risk || t('message.opsflowPage.unknown')
})

const riskTagType = computed(() => {
  const risk = form.value.risk_level || pluginRiskMap.value[form.value.plugin_code] || ''
  switch (risk) {
    case 'high': return 'danger'
    case 'medium': return 'warning'
    case 'low': return 'success'
    default: return 'info'
  }
})

const gatewayTagType = computed(() => {
  switch (form.value.node_type) {
    case 'start_event': return 'success'
    case 'end_event': return 'danger'
    case 'exclusive_gateway': return 'warning'
    case 'parallel_gateway': return 'primary'
    case 'conditional_parallel_gateway': return 'primary'
    case 'converge_gateway': return 'info'
    default: return 'info'
  }
})

watch(() => props.nodeData, (val) => {
  if (val) {
    const data = { ...val }
    // AI 生成的节点使用 atom_type，映射到 plugin_code
    if (!data.plugin_code && data.atom_type) {
      data.plugin_code = data.atom_type
    }
    // AI 返回的 params 映射为 plugin_params，供 RenderForm 初始渲染
    if (data.params && !data.plugin_params) {
      data.plugin_params = { ...data.params }
    }
    form.value = data

    if (data.plugin_code) {
      loadPluginSchema(data.plugin_code)
    } else {
      pluginFormSchema.value = []
    }
  } else {
    form.value = {}
    pluginFormSchema.value = []
  }
}, { immediate: true, deep: true })

watch(() => props.edgeData, (val) => {
  if (val) {
    edgeForm.value = { condition: val.condition || '', label: val.label || '' }
    // 回填条件结构化数据
    conditionStruct.value = val.conditionStruct || null
  } else {
    edgeForm.value = { condition: '' }
    conditionStruct.value = null
  }
}, { immediate: true, deep: true })

async function onPluginChange(code: string) {
  form.value.plugin_code = code
  pluginFormSchema.value = []
  outputSchema.value = []
  pluginVersions.value = []
  form.value._plugin_version = ''
  form.value.plugin_params = {}
  if (code) {
    await loadPluginSchema(code)
    form.value._outputSchema = outputSchema.value
  }
  formRevision.value++  // 驱动 contextWithVars 重算
  emitUpdate()
}

function onFormChange(data: Record<string, any>) {
  form.value.plugin_params = data
  form.value._outputSchema = outputSchema.value  // 保持 _outputSchema 同步
  formRevision.value++  // 驱动 contextWithVars 重算
  emitUpdate()
}

function emitUpdate() {
  const updated = { ...form.value }
  updated.params = form.value.plugin_params || {}
  // 同步 plugin_code → atom_type（bamboo_builder 用 atom_type 路由执行）
  if (updated.plugin_code) {
    updated.atom_type = updated.plugin_code
  }
  formRevision.value++
  emit('update', updated)
}

/** 将节点输入参数提权为全局变量 */
async function promoteInput(config: any, currentValue: any) {
  if (!props.templateId || !form.value?.id) return
  const defaultVarName = config.tag_code || 'var'
  let varKey = ''
  try {
    const { value } = await ElMessageBox.prompt(
      'Enter a name for the global variable:',
      'Promote Input to Global Variable',
      {
        inputValue: defaultVarName,
        inputPlaceholder: 'Variable name (used as ${name})',
        confirmButtonText: 'Promote',
        cancelButtonText: 'Cancel',
      },
    )
    if (!value?.trim()) return
    varKey = value.trim()
    // 构建 meta（提取 select/async_select 选项等）
    const meta: Record<string, any> = {}
    if (config.attrs?.options) meta.options = config.attrs.options
    if (config.attrs?.multiple) meta.multiple = config.attrs.multiple
    // async_select: 记录 API 端点信息，SubmitWizard 中实时请求
    if (config.type === 'async_select' && config.attrs?.api_endpoint) {
      meta.apiEndpoint = config.attrs.api_endpoint
      if (config.attrs?.depends_on) meta.dependsOn = config.attrs.depends_on
    }

    const hookRes = await HookVariable(props.templateId, {
      var_key: varKey,
      var_type: config.type || 'input',
      meta,
      value: currentValue ?? config.default ?? '',
      description: config.name || config.tag_code || '',
      promote_type: 'input',
    })
    console.log('[Promote] HookVariable success:', varKey, hookRes)

    // 自动填充 ${var_key} 引用到字段值
    const refExpr = '${' + varKey + '}'
    renderFormRef.value?.setField(config.tag_code, refExpr)
    if (form.value.plugin_params) {
      form.value.plugin_params[config.tag_code] = refExpr
    }
    formRevision.value++
    ElMessage.success(`Global variable "${varKey}" created — field now references ${refExpr}`)
  } catch (e: any) {
    if (e?.toString()?.includes('cancel') || e?.toString()?.includes('close')) {
      // user closed the prompt dialog, ignore
      return
    }
    console.error('[Promote] HookVariable failed:', varKey, e)
    ElMessage.error(`Promote failed: ${e?.msg || e?.message || 'Unknown error'}`)
  }
}

/** 打开条件编辑器弹窗，同时刷新可用变量列表 */
function openConditionDialog() {
  // 实时从画布获取节点列表
  const graphData = typeof props.getGraphData === 'function' ? props.getGraphData() : null
  const nodes = graphData?.nodes || []
  availableVars.value = getAvailableVars(nodes, opsflowStore, {
    currentNodeId: props.edgeData?.from,
    edges: graphData?.edges || [],
  }) || []
  conditionDialogVisible.value = true
}

/** 条件编辑器保存回调 */
function onConditionSave(struct: ConditionStruct) {
  conditionStruct.value = struct
  edgeForm.value.condition = struct.rules && struct.rules.length > 0
    ? generateConditionExpr(struct.rules, struct.logic)
    : ''
  emitEdgeUpdate()
}

function onEdgeLabelChange(label: string) {
  edgeForm.value.label = label || ''
  if (!label || label === 'success' || label === 'failure') {
    edgeForm.value.condition = ''
    conditionStruct.value = null
  }
  emitEdgeUpdate()
}

function emitEdgeUpdate() {
  emit('update', {
    label: edgeForm.value.label || '',
    condition: edgeForm.value.condition || '',
    conditionStruct: conditionStruct.value || undefined,
  })
}

async function loadTemplates() {
  templatesLoading.value = true
  try {
    const res = await GetTemplates({ is_draft: false, limit: 100 })
    const items = res.data?.results || res.data || res.results || []
    publishedTemplates.value = items
  } catch {
    publishedTemplates.value = []
  }
  templatesLoading.value = false
}

// 初始加载
loadPlugins()
loadTemplates()
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.property-panel {
  width: 375px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 201;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  flex-shrink: 0;
}
.panel-section {
  padding: 12px 14px;
  border-bottom: 1px solid #f0f0f0;
}
.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}
.prop-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}
.prop-row:last-child {
  margin-bottom: 0;
}
.prop-row-vertical {
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
}
.prop-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 50px;
}
.prop-value {
  font-size: 12px;
  color: #333;
}
.prop-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #909399;
  font-size: 11px;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.prop-input {
  flex: 1;
}
.risk-tag {
  font-weight: 600;
}
.gateway-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gateway-desc {
  margin: 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
/* Condition preview (new structural editor) */
.condition-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 6px 10px;
  cursor: pointer;
  transition: border-color 0.2s;
  min-height: 32px;
}
.condition-preview:hover {
  border-color: #409EFF;
  background: #ecf5ff;
}
.condition-code {
  font-size: 12px;
  font-family: monospace;
  color: #303133;
  word-break: break-all;
  line-height: 1.5;
  flex: 1;
}
.condition-placeholder {
  font-size: 12px;
  color: #c0c4cc;
  flex: 1;
}
.cond-refs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.cond-ref-tag {
  font-family: monospace;
  font-size: 11px;
}
.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #c0c4cc;
  font-size: 13px;
  padding: 40px 0;
}
.panel-empty p {
  margin: 0;
}

/* Variable References */
.var-ref-list { display: flex; flex-wrap: wrap; gap: 4px; }
.var-ref-tag { font-family: monospace; }

</style>
