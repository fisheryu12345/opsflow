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
            <span class="prop-label">Atom Type</span>
            <el-select v-model="form.atom_type" size="small" style="width:100%" @change="emitUpdate">
              <el-option v-for="atom in atomOptions" :key="atom.value" :label="atom.label" :value="atom.value" />
            </el-select>
          </div>
          <div class="prop-row prop-row-vertical">
            <span class="prop-label">Params</span>
            <el-input
              v-model="paramsText"
              type="textarea"
              :rows="3"
              placeholder='{"key": "value"}'
              size="small"
              @change="onParamsChange"
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
import { ref, watch, computed } from 'vue'
import { Setting, Pointer, WarnTriangleFilled, CircleCheckFilled, InfoFilled, Aim, Connection, Switch } from '@element-plus/icons-vue'

const props = defineProps<{
  nodeData: any
}>()

const emit = defineEmits<{
  update: [data: any]
}>()

const atomOptions = [
  { label: 'Shell', value: 'shell' },
  { label: 'Disk Check', value: 'disk_check' },
  { label: 'Ping Test', value: 'ping_test' },
  { label: 'Health Check', value: 'health_check' },
  { label: 'Service Control', value: 'service_control' },
  { label: 'Upload File', value: 'upload_file' },
  { label: 'Copy File', value: 'file_copy' },
  { label: 'Run Script', value: 'script_exec' },
  { label: 'Backup File', value: 'backup_file' },
  { label: 'Deploy App', value: 'java_deploy' },
  { label: 'Docker Deploy', value: 'docker_deploy' },
  { label: 'Nginx Reload', value: 'nginx_reload' },
  { label: 'Send Alert', value: 'send_alert' },
]

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
const paramsText = ref('')

const isAtom = computed(() => !form.value.node_type || form.value.node_type === 'atom')
const nodeTypeLabel = computed(() => typeLabels[form.value.node_type] || form.value.node_type || 'Atom')
const gatewayDescription = computed(() => gatewayDescriptions[form.value.node_type] || '')
const gatewayIcon = computed(() => gatewayIcons[form.value.node_type] || InfoFilled)

const riskLevelText = computed(() => {
  const map: Record<string, string> = { high: 'High', medium: 'Medium', low: 'Low' }
  return map[form.value.risk_level] || form.value.risk_level || 'Unknown'
})

const riskTagType = computed(() => {
  switch (form.value.risk_level) {
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
    form.value = { ...val }
    paramsText.value = JSON.stringify(val.params || {}, null, 2)
  } else {
    form.value = {}
    paramsText.value = ''
  }
}, { immediate: true, deep: true })

function emitUpdate() {
  const updated = { ...form.value }
  try {
    updated.params = JSON.parse(paramsText.value)
  } catch {
    updated.params = form.value.params || {}
  }
  emit('update', updated)
}

function onParamsChange() {
  emitUpdate()
}
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
