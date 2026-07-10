<template>
  <el-form label-position="top" size="small">
    <el-form-item :label="$t('message.designer.edgeLabel')">
      <el-input v-model="edge.label" :placeholder="$t('message.designer.edgeLabel')" @input="onEdgeChange" />
    </el-form-item>
    <el-form-item :label="$t('message.designer.conditionExpr')">
      <div v-if="edge.condition" class="itsm-cond-preview">
        <template v-if="parsedRules.length">
          <div v-for="(r, i) in parsedRules" :key="i" class="cond-rule-line">
            <span v-if="r.logic" class="cond-logic-tag">{{ r.logic }}</span>
            <span class="cond-rule-ref">{{ r.source }}.{{ r.field }}</span>
            <span class="cond-rule-op">{{ r.op }}</span>
            <span class="cond-rule-val">{{ r.value }}</span>
          </div>
        </template>
        <code v-else class="cond-rule-raw">{{ edge.condition }}</code>
      </div>
      <div style="display:flex;gap:8px;align-items:center;margin-top:4px">
        <el-button v-if="edge.condition" link size="small" type="danger" @click="edge.condition = ''; onEdgeChange()">清除</el-button>
        <el-button link size="small" type="primary" @click="openConditionDialog">
          <el-icon><Plus /></el-icon> 添加条件
        </el-button>
        <el-button link size="small" @click="showAdvanced = !showAdvanced">{{ showAdvanced ? '收起' : '手动' }}</el-button>
      </div>
      <el-input v-if="showAdvanced" v-model="edge.condition" type="textarea" :rows="3"
        placeholder="手动输入，如 ${node_2.field} > 5 AND ${node_3.field} == 'x'"
        @input="onEdgeChange" style="margin-top:4px" />
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'

const props = defineProps<{
  edge: any
  allNodes?: any[]
}>()
const emit = defineEmits<{
  change: []
  openConditionDialog: []
}>()

const showAdvanced = ref(false)

const parsedRules = computed(() => {
  const c = (props.edge?.condition || '')
  if (!c || typeof c !== 'string' || !c.trim()) return []
  const logics: string[] = []
  const logicRe = /\s+(AND|OR)\s+/gi
  let m2
  while ((m2 = logicRe.exec(c)) !== null) logics.push(m2[1].toUpperCase())
  const parts = c.split(/\s+AND\s+|\s+OR\s+/i).filter(Boolean)
  const RULE_PAT = /^\$\{([^.]+)\.([^}]+)\}\s*(>=|<=|!=|==|>|<|in|notin)\s*(.+)$/
  return parts.map((p, i) => {
    const pm = p.trim().match(RULE_PAT)
    if (!pm) return null
    let v = pm[4]
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
    return { source: pm[1], field: pm[2], op: pm[3], value: v, logic: i > 0 ? (logics[i - 1] || 'AND') : '' }
  }).filter(Boolean)
})

function onEdgeChange() {
  if (props.edge) props.edge.label = props.edge.label || ''
  emit('change')
}

function openConditionDialog() { emit('openConditionDialog') }
</script>

<style scoped>
.itsm-cond-preview { background: #f5f7fa; border-radius: 6px; padding: 8px 10px; margin-top: 4px; word-break: break-all; }
.cond-rule-line { display: flex; align-items: center; gap: 4px; font-size: 12px; font-family: monospace; padding: 3px 0; white-space: nowrap; }
.cond-rule-line + .cond-rule-line { border-top: 1px dashed #e4e7ed; }
.cond-logic-tag { background: #fdf6ec; color: #E6A23C; font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; margin-right: 4px; }
.cond-rule-ref { color: #909399; }
.cond-rule-op { color: #409EFF; font-weight: 600; }
.cond-rule-val { color: #67C23A; }
.cond-rule-raw { font-size: 12px; color: #606266; }
</style>
