<template>
  <div class="property-panel">
    <div class="panel-header">
      <el-icon size="16"><Setting /></el-icon>
      <span>Node Properties</span>
    </div>

    <template v-if="form.id">
      <div class="panel-section">
        <div class="section-title">Basic Info</div>
        <div class="prop-row">
          <span class="prop-label">ID</span>
          <span class="prop-value prop-id">{{ form.id }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">Label</span>
          <el-input v-model="form.label" size="small" @change="emitUpdate" class="prop-input" />
        </div>
      </div>

      <template v-if="isAtom">
        <div class="panel-section">
          <div class="section-title">Action Config</div>
          <div class="prop-row">
            <span class="prop-label">Plugin</span>
            <el-select v-model="form.plugin_code" size="small" style="width:100%"
              filterable @change="onPluginChange" :loading="pluginsLoading">
              <el-option-group v-for="(items, group) in pluginGroups" :key="group" :label="group">
                <el-option v-for="p in items" :key="p.code" :label="p.name + ' (' + p.versions?.join(', ') + ')'" :value="p.code" />
              </el-option-group>
            </el-select>
          </div>
          <!-- 版本选择器 -->
          <div class="prop-row" v-if="isAtom && pluginVersions.length > 1">
            <span class="prop-label">Version</span>
            <el-select v-model="form._plugin_version" size="small" style="width:120px" @change="emitUpdate">
              <el-option v-for="v in pluginVersions" :key="v" :label="v" :value="v" />
            </el-select>
          </div>
          <!-- 动态表单渲染（传递 templateId + nodeId 供 TagVariableInput 使用） -->
          <div class="prop-row-vertical">
            <RenderForm
              ref="renderFormRef"
              :schema="pluginFormSchema"
              :initial-data="form.plugin_params"
              :context="{ templateId, nodeId: form.id, tagCode: '' }"
              @change="onFormChange"
            />
          </div>
        </div>

        <!-- Output Parameters -->
        <div class="panel-section" v-if="isAtom && outputSchema.length">
          <div class="section-title">Output Parameters</div>
          <div class="output-list">
            <div v-for="out in outputSchema" :key="out.name || out.key" class="output-row">
              <div class="output-top">
                <code class="output-key">{{ out.name || out.key }}</code>
                <el-tag size="mini" :type="outputTypeTag(out.type)" effect="plain">{{ out.type }}</el-tag>
                <el-button size="small" text type="primary" @click="copyRef(form.id + '.' + (out.name || out.key))">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </div>
              <span class="output-desc" v-if="out.description">{{ out.description }}</span>
              <div class="output-ref-hint">
                Reference: <code>$\{{ form.id }}.{{ out.name || out.key }}</code>
              </div>
            </div>
          </div>
        </div>

        <!-- Variable References in this node -->
        <div class="panel-section" v-if="varReferences.length">
          <div class="section-title">Variable References</div>
          <div class="var-ref-list">
            <el-tag v-for="ref in varReferences" :key="ref" size="small" type="warning" effect="light" class="var-ref-tag">
              {{ ref }}
            </el-tag>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-title">Execution Control</div>
          <div class="prop-row">
            <span class="prop-label">Max Retries</span>
            <el-input-number v-model="form.max_retries" :min="0" :max="10" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">Retry Delay (s)</span>
            <el-input-number v-model="form.retry_delay" :min="0" :max="300" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">Timeout (s)</span>
            <el-input-number v-model="form.timeout_seconds" :min="5" :max="600" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
          </div>
          <div class="prop-row">
            <span class="prop-label">Risk Level</span>
            <el-tag :type="riskTagType" size="small" effect="dark" class="risk-tag">
              {{ riskLevelText }}
            </el-tag>
          </div>
          <div class="prop-row">
            <span class="prop-label">Optional</span>
            <el-switch v-model="form.optional" @change="emitUpdate" size="small" />
          </div>
        </div>
      </template>

      <!-- SubProcess 配置 -->
      <template v-else-if="isSubprocess">
        <div class="panel-section">
          <div class="section-title">SubProcess Config</div>
          <div class="prop-row-vertical">
            <span class="prop-label">Target Template</span>
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
            <span class="prop-label">Mode</span>
            <el-switch
              v-model="form.independent"
              active-text="Independent"
              inactive-text="Embedded"
              @change="emitUpdate"
              size="small"
            />
          </div>
          <div class="prop-row-vertical" style="margin-top:8px">
            <span class="prop-label">Variable Mapping (parent → child)</span>
            <TagVariableMapping v-model="form.variable_mapping" />
          </div>
          <div class="prop-row-vertical" style="margin-top:8px">
            <span class="prop-label">Output Mapping (child → parent)</span>
            <TagVariableMapping v-model="form.output_mapping" />
          </div>
        </div>
      </template>

      <!-- Approval 配置 -->
      <template v-else-if="isApproval">
        <div class="panel-section">
          <div class="section-title">Approval Config</div>
          <div class="prop-row-vertical">
            <span class="prop-label">Approver(s)</span>
            <el-select v-model="form.approvers" multiple filterable size="small" style="width:100%"
              placeholder="Select approvers" @change="emitUpdate">
              <el-option v-for="u in userList" :key="u" :label="u" :value="u" />
            </el-select>
          </div>
          <div class="prop-row">
            <span class="prop-label">Timeout</span>
            <el-input-number v-model="form.approval_timeout" :min="300" :max="604800" :step="3600" size="small" controls-position="right" style="width:140px" @change="emitUpdate" />
            <span style="font-size:11px;color:#909399">sec</span>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="panel-section">
          <div class="section-title">Node Type</div>
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
        <div class="section-title">Edge Condition</div>
        <div class="prop-row">
          <span class="prop-label">From</span>
          <span class="prop-value prop-id">{{ edgeData.from }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">To</span>
          <span class="prop-value prop-id">{{ edgeData.to }}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">Label</span>
          <el-select v-model="edgeForm.label" size="small" style="width:100%" @change="onEdgeLabelChange">
            <el-option label="success（成功路径）" value="success" />
            <el-option label="failure（失败路径）" value="failure" />
            <el-option label="custom（自定义条件）" value="custom" />
          </el-select>
        </div>
        <!-- 自定义条件输入（选择 custom 时显示） -->
        <div class="prop-row-vertical" v-if="edgeForm.label === 'custom'">
          <span class="prop-label">Condition</span>
          <el-input
            v-model="edgeForm.condition"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="${node_1.output_key > 0}"
            @change="emitEdgeUpdate"
          />
          <div class="condition-hint">
            <p>使用 <code>${node_id.key}</code> 引用节点输出。示例：</p>
            <ul class="hint-list">
              <li><code>${node_1._result}</code> 引用执行结果</li>
              <li><code>${node_1.code} == 200</code> 状态码判断</li>
              <li><code>${node_1.cpu} > 80</code> 数值比较</li>
              <li><code>${node_1.status} == 'ok'</code> 字符串比较</li>
            </ul>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="panel-empty">
      <el-icon size="28" color="#c0c4cc"><Pointer /></el-icon>
      <p>Click a node or edge to view properties</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import { Setting, Pointer, WarnTriangleFilled, CircleCheckFilled, InfoFilled, Aim, Connection, Switch } from '@element-plus/icons-vue'
import RenderForm from '/@/components/RenderForm/RenderForm.vue'
import TagVariableMapping from '/@/components/RenderForm/tags/TagVariableMapping.vue'
import { GetPluginGroups, GetPluginDetail } from '/@/api/opsflow/plugins'
import { GetTemplates } from '/@/api/opsflow/templates'

const props = defineProps<{
  nodeData?: any
  edgeData?: any
  templateId?: number | null
  subprocessVersion?: any | null
}>()

const emit = defineEmits<{
  update: [data: any]
}>()

/* ── Form state (MUST be before any computed/watcher that references them) ── */
const form = ref<any>({})
const edgeForm = ref<any>({ condition: '' })

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
const pluginGroups = ref<Record<string, { code: string; name: string }[]>>({})
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
    pluginFormSchema.value = res.data?.form_schema || []
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

function outputTypeTag(type: string): string {
  const map: Record<string, string> = { string: 'info', int: '', bool: 'success', object: 'warning' }
  return map[type] || 'info'
}

function copyRef(ref: string) {
  navigator.clipboard.writeText('${' + ref + '}')
  ElMessage.success('Copied')
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
  const map: Record<string, string> = { high: 'High', medium: 'Medium', low: 'Low' }
  return map[risk] || risk || 'Unknown'
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
  } else {
    edgeForm.value = { condition: '' }
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
  }
  emitUpdate()
}

function onFormChange(data: Record<string, any>) {
  form.value.plugin_params = data
  emitUpdate()
}

function emitUpdate() {
  const updated = { ...form.value }
  updated.params = form.value.plugin_params || {}
  // 同步 plugin_code → atom_type（bamboo_builder 用 atom_type 路由执行）
  if (updated.plugin_code) {
    updated.atom_type = updated.plugin_code
  }
  emit('update', updated)
}

function onEdgeLabelChange(label: string) {
  edgeForm.value.label = label
  if (label === 'success') edgeForm.value.condition = ''
  else if (label === 'failure') edgeForm.value.condition = ''
  emitEdgeUpdate()
}

function emitEdgeUpdate() {
  emit('update', {
    label: edgeForm.value.label || '',
    condition: edgeForm.value.condition || '',
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
@import '../styles/opsflow-global';

.property-panel {
  width: 280px;
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
.condition-hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: #909399;
  line-height: 1.5;
}
.condition-hint code {
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
  color: #409EFF;
}
/* Output Parameters */
.output-list { display: flex; flex-direction: column; gap: 6px; }
.output-row {
  background: #f8f9fb; border-radius: 6px; padding: 10px 12px;
  display: flex; flex-direction: column; gap: 4px;
}
.output-top { display: flex; align-items: center; gap: 6px; }
.output-key { font-size: 13px; font-weight: 600; color: #409EFF; font-family: monospace; }
.output-desc { font-size: 11px; color: #909399; }
.output-ref-hint { font-size: 11px; color: #909399; }
.output-ref-hint code { color: #67C23A; background: #f0f9eb; padding: 1px 4px; border-radius: 3px; }
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
