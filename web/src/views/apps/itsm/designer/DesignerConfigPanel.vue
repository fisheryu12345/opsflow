<template>
  <div class="des-config" v-if="configVisible">
    <div class="des-config-header">
      <span>{{ configTitle }}</span>
      <el-button text size="small" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>
    <div class="des-config-body">
      <!-- Node config -->
      <template v-if="node">
        <NodeConfigPanel :node="node" @change="$emit('change')" @openFieldEditor="$emit('openFieldEditor')" />
        <TriggerConfigSection :node="node" :workflow-id="workflowId" />
      </template>

      <!-- Edge config -->
      <template v-else-if="edge && isGatewayEdge">
        <EdgeConfigPanel
          :edge="edge"
          :all-nodes="allNodes"
          @change="$emit('change')"
          @openConditionDialog="openConditionDialog"
        />
      </template>
    </div>
    <button class="des-config-collapse" @click="$emit('close')">&#9664;</button>

    <ConditionDialog
      :visible="conditionDialogVisible"
      :initial-struct="conditionStruct"
      :available-vars="availableVars"
      @update:visible="conditionDialogVisible = $event"
      @save="onConditionSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Close } from '@element-plus/icons-vue'
import { getNodeConfig } from './shapes'
import NodeConfigPanel from './components/NodeConfigPanel.vue'
import TriggerConfigSection from './components/TriggerConfigSection.vue'
import EdgeConfigPanel from './components/EdgeConfigPanel.vue'
import ConditionDialog from './components/ConditionDialog.vue'
import { generateConditionExpr } from './conditionUtils'

const { t } = useI18n()

const props = defineProps<{
  node: any
  edge: any
  allNodes?: any[]
  workflowId?: number
}>()

const emit = defineEmits<{
  close: []
  change: []
  openFieldEditor: []
}>()

const configVisible = computed(() => props.node || (props.edge && isGatewayEdge.value))
const isGatewayEdge = computed(() => {
  const t = props.edge?._from_state_type || ''
  return t === 'EXCLUSIVE' || t === 'CONDITIONAL_PARALLEL'
})
const configTitle = computed(() => props.node ? t('message.designer.nodeConfig') : t('message.designer.edgeConfig'))

// ── Edge condition: dialog state ──
const conditionDialogVisible = ref(false)
const conditionStruct = ref<any>(null)

const availableVars = computed(() => {
  const vars: any[] = []
  if (!props.allNodes?.length) return vars
  for (const n of props.allNodes) {
    const nk = n.node_key || n.id || ''
    if (!nk) continue
    const nodeName = n.name || nk
    for (const f of (n.fields || [])) {
      if (f.field) {
        const isNumber = f.type === 'number' || f.type === 'ItsmInt'
        const isString = f.type === 'select' || f.type === 'radio' || f.type === 'ItsmMembers' || f.type === 'ItsmCascader'
        vars.push({
          source: nk, sourceLabel: nodeName, field: f.field, fieldLabel: f.title || f.field,
          fieldType: isNumber ? 'number' : isString ? 'string' : 'string',
          sourceType: 'node' as const,
          label: `${nodeName}.${f.title || f.field}`, group: nodeName,
        })
      }
    }
  }
  return vars
})

function openConditionDialog() {
  const raw = props.edge?.condition || ''
  if (typeof raw === 'string' && raw.trim()) {
    const parts = raw.split(/\s+AND\s+|\s+OR\s+/i).filter(Boolean)
    const logic = raw.match(/\s+OR\s+/i) ? 'OR' : 'AND'
    const rules: any[] = []
    for (const p of parts) {
      const m = p.trim().match(/^\$\{([^.]+)\.([^}]+)\}\s*(>=|<=|!=|==|>|<|in|notin)\s*(.+)$/)
      if (m) {
        let v = m[4]
        if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
        rules.push({ source: m[1], field: m[2], op: m[3], value: v, fieldType: 'string' })
      }
    }
    conditionStruct.value = rules.length ? { logic, rules } : null
  } else {
    conditionStruct.value = null
  }
  conditionDialogVisible.value = true
}

function onConditionSave(struct: any) {
  if (!props.edge) return
  props.edge.condition = generateConditionExpr(struct.rules, struct.logic)
  conditionDialogVisible.value = false
  emit('change')
}
</script>

<style scoped>
.des-config {
  width: 320px; border-left: 1px solid #e4e7ed;
  background: #fff; overflow-y: auto; flex-shrink: 0;
  display: flex; flex-direction: column; position: relative;
}
.des-config-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f5f7fa; border-bottom: 1px solid #e4e7ed;
  font-size: 13px; font-weight: 600; color: #303133; flex-shrink: 0;
}
.des-config-body { flex: 1; padding: 12px; overflow-y: auto; }
.des-config-collapse {
  position: absolute; left: -16px; top: 50%; transform: translateY(-50%);
  width: 16px; height: 48px; border: 1px solid #e4e7ed; border-right: none;
  background: #f5f7fa; cursor: pointer; border-radius: 4px 0 0 4px;
  color: #909399; font-size: 10px; display: flex; align-items: center;
  justify-content: center;
}
.des-config-collapse:hover { color: #409EFF; background: #e8f0fe; }
</style>
