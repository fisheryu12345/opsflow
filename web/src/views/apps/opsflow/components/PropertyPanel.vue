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
                <el-option v-for="p in items" :key="p.code" :label="p.name" :value="p.code" />
              </el-option-group>
            </el-select>
          </div>
          <!-- 动态表单渲染 -->
          <div class="prop-row-vertical">
            <RenderForm
              ref="renderFormRef"
              :schema="pluginFormSchema"
              :initial-data="form.plugin_params"
              @change="onFormChange"
            />
          </div>
        </div>

        <div class="panel-section">
          <div class="section-title">Execution Control</div>
          <div class="prop-row">
            <span class="prop-label">Max Retries</span>
            <el-input-number v-model="form.max_retries" :min="0" :max="10" size="small" controls-position="right" style="width:120px" @change="emitUpdate" />
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
        </div>
      </template>

      <template v-else>
        <div class="panel-section">
          <div class="section-title">Node Type</div>
          <div class="gateway-info">
            <el-tag :type="gatewayTagType" size="default" effect="plain">
              <el-icon size="14" style="margin-right:4px">{{ gatewayIcon }}</el-icon>
              {{ nodeTypeLabel }}
            </el-tag>
            <p class="gateway-desc">{{ gatewayDescription }}</p>
          </div>
        </div>
      </template>
    </template>

    <div v-else class="panel-empty">
      <el-icon size="28" color="#c0c4cc"><Pointer /></el-icon>
      <p>Click a node to view properties</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import { Setting, Pointer, WarnTriangleFilled, CircleCheckFilled, InfoFilled, Aim, Connection, Switch } from '@element-plus/icons-vue'
import RenderForm from '/@/components/RenderForm/RenderForm.vue'
import { GetPluginGroups, GetPluginDetail } from '/@/api/opsflow/plugins'

const props = defineProps<{
  nodeData: any
}>()

const emit = defineEmits<{
  update: [data: any]
}>()

/* ---------- Plugin loading ---------- */
const pluginsLoading = ref(false)
const pluginGroups = ref<Record<string, { code: string; name: string }[]>>({})
const pluginFormSchema = ref<any[]>([])
const pluginRiskMap = ref<Record<string, string>>({})
const renderFormRef = ref<InstanceType<typeof RenderForm> | null>(null)

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
    if (res.data?.risk_level) {
      pluginRiskMap.value[code] = res.data.risk_level
    }
  } catch {
    pluginFormSchema.value = []
  }
}

/* ---------- Form state ---------- */
const typeLabels: Record<string, string> = {
  start_event: 'Start Event',
  end_event: 'End Event',
  exclusive_gateway: 'Exclusive Gateway',
  parallel_gateway: 'Parallel Gateway',
  conditional_parallel_gateway: 'Conditional Parallel Gateway',
  converge_gateway: 'Converge Gateway',
}

const gatewayDescriptions: Record<string, string> = {
  start_event: 'Start of the pipeline. Only one per pipeline.',
  end_event: 'End of the pipeline. All paths converge here.',
  exclusive_gateway: 'Select one path based on condition.',
  parallel_gateway: 'Execute all branches in parallel.',
  conditional_parallel_gateway: 'Execute matching branches in parallel.',
  converge_gateway: 'Merge parallel branches into one path.',
}

const gatewayIcons: Record<string, any> = {
  start_event: Aim,
  end_event: CircleCheckFilled,
  exclusive_gateway: WarnTriangleFilled,
  parallel_gateway: Connection,
  conditional_parallel_gateway: Switch,
  converge_gateway: InfoFilled,
}

const form = ref<any>({})

const isAtom = computed(() => !form.value.node_type || form.value.node_type === 'atom')
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

async function onPluginChange(code: string) {
  form.value.plugin_code = code
  pluginFormSchema.value = []
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

// 初始加载插件列表
loadPlugins()
</script>

<style scoped>
.property-panel {
  width: 280px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
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
</style>
