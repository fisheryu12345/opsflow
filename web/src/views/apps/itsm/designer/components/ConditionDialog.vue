<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="680px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
    @closed="onClosed"
    destroy-on-close
  >
    <div class="condition-dialog-body">
      <!-- Condition rule list -->
      <div class="rules-list" v-if="rules.length > 0">
        <template v-for="(rule, idx) in rules" :key="idx">
          <ConditionRow
            :rule="rule"
            :index="idx"
            :available-vars="availableVars"
            :has-error="!!errors[idx]"
            @change="onRuleChange(idx, $event)"
            @remove="removeRule(idx)"
          />
          <!-- AND/OR connector between rows -->
          <div v-if="idx < rules.length - 1" class="logic-connector">
            <el-dropdown @command="setLogic">
              <div class="logic-btn" :class="logic.toLowerCase()">
                {{ logic }}
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="AND">AND</el-dropdown-item>
                  <el-dropdown-item command="OR">OR</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <div class="connector-line" />
          </div>
        </template>
      </div>

      <!-- Empty state + quick presets -->
      <div v-else class="rules-empty">
        <el-icon size="24" color="#c0c4cc"><Plus /></el-icon>
        <p>{{ $t("message.condition.hint") }}</p>
        <div class="quick-presets">
          <el-button size="small" @click="addPreset('_result', '==', 'True')" title="${_result} == True">
            <el-icon><CircleCheck /></el-icon> {{ $t("message.execution.statCompleted") }}
          </el-button>
          <el-button size="small" @click="addPreset('_result', '==', 'False')" title="${_result} == False">
            <el-icon><CloseBold /></el-icon> {{ $t("message.execution.statFailed") }}
          </el-button>
          <el-button size="small" @click="addRule">
            <el-icon><Plus /></el-icon> {{ $t("message.condition.custom") }}
          </el-button>
        </div>
      </div>

      <!-- Add condition -->
      <div class="add-rule-row" v-if="rules.length > 0">
        <el-button size="small" type="primary" plain @click="addRule">
          <el-icon><Plus /></el-icon>
          {{ $t("message.condition.addCondition") }}
        </el-button>
      </div>

      <!-- Preview + validation -->
      <div class="preview-bar" v-if="rules.length > 0">
        <div class="preview-row">
          <span class="preview-label">{{ $t("message.condition.expression") }}:</span>
          <code class="preview-expr">{{ conditionExpr }}</code>
        </div>
        <div class="validation-row" :class="validationStatus">
          <el-icon v-if="validationStatus === 'valid'"><CircleCheck /></el-icon>
          <el-icon v-else-if="validationStatus === 'error'"><WarningFilled /></el-icon>
          <span>{{ validationMessage }}</span>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">{{ $t("message.common.cancel") }}</el-button>
      <el-button type="primary" @click="onSave" :disabled="!isValid">
        {{ $t("message.condition.save") }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, ArrowDown, CircleCheck, CloseBold, WarningFilled } from '@element-plus/icons-vue'
import ConditionRow from './ConditionRow.vue'
import { generateConditionExpr } from '../conditionUtils'
import type { VariableOption, ConditionRule, ConditionStruct } from '../conditionUtils'

const { t } = useI18n()

const props = withDefaults(defineProps<{
  visible: boolean
  initialStruct?: ConditionStruct | null
  availableVars?: VariableOption[]
  sourceNodeLabel?: string
  targetNodeLabel?: string
}>(), {
  visible: false,
  initialStruct: null,
  availableVars: () => [],
  sourceNodeLabel: '',
  targetNodeLabel: '',
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  save: [struct: ConditionStruct]
}>()

const rules = ref<ConditionRule[]>([])
const logic = ref<'AND' | 'OR'>('AND')
const errors = ref<Record<number, string>>({})
const conditionExpr = ref('')

const dialogTitle = computed(() => {
  const base = t('message.condition.title')
  if (props.sourceNodeLabel && props.targetNodeLabel) {
    return `${base}: ${props.sourceNodeLabel} → ${props.targetNodeLabel}`
  }
  return base
})

const isValid = computed(() => {
  return rules.value.length > 0 && Object.keys(errors.value).length === 0
})

const validationStatus = computed(() => {
  if (rules.value.length === 0) return ''
  return Object.keys(errors.value).length > 0 ? 'error' : 'valid'
})

const validationMessage = computed(() => {
  if (rules.value.length === 0) return ''
  const errKeys = Object.keys(errors.value)
  if (errKeys.length > 0) {
    return `${t('message.condition.validationFailed')}: ${errKeys.length} ${t('message.condition.rowsError')}`
  }
  return t('message.condition.validationPassed')
})

// Initialize / backfill
watch(() => props.visible, (show) => {
  if (!show) return
  if (props.initialStruct?.rules && props.initialStruct.rules.length > 0) {
    rules.value = props.initialStruct.rules.map(r => ({ ...r }))
    logic.value = props.initialStruct.logic || 'AND'
  } else {
    // Default: add one empty condition row
    rules.value = [createEmptyRule()]
    logic.value = 'AND'
  }
  rebuildExpr()
})

function createEmptyRule(): ConditionRule {
  return { source: '', field: '', op: '==', value: '', valueType: '' }
}

function onRuleChange(idx: number, rule: ConditionRule) {
  rules.value[idx] = rule
  // Validate
  if (!rule.source || !rule.field) {
    errors.value[idx] = 'Variable not selected'
  } else if (rule.value === '' || rule.value === undefined) {
    errors.value[idx] = 'Comparison value is empty'
  } else {
    delete errors.value[idx]
  }
  rebuildExpr()
}

function removeRule(idx: number) {
  rules.value.splice(idx, 1)
  delete errors.value[idx]
  rebuildExpr()
}

function addRule() {
  rules.value.push(createEmptyRule())
}

/** Quick preset: use first matching available var */
function addPreset(field: string, op: string, value: string) {
  const firstNodeVar = props.availableVars.find(v => v.sourceType === 'node' && v.field === field)
  if (firstNodeVar) {
    rules.value.push({
      source: firstNodeVar.source,
      field: firstNodeVar.field,
      fieldLabel: firstNodeVar.fieldLabel,
      fieldType: firstNodeVar.fieldType,
      op,
      value,
      valueType: '',
    })
    rebuildExpr()
  } else {
    // Fallback: empty rule with preset op/value
    const rule = createEmptyRule()
    rule.op = op
    rule.value = value
    rules.value.push(rule)
  }
}

function setLogic(cmd: string) {
  logic.value = cmd as 'AND' | 'OR'
  rebuildExpr()
}

function rebuildExpr() {
  const validRules = rules.value.filter(r => r.source && r.field && r.value !== '' && r.value !== undefined)
  conditionExpr.value = validRules.length > 0
    ? generateConditionExpr(validRules, logic.value)
    : ''
}

function onSave() {
  if (!isValid.value) return
  const validRules = rules.value.filter(r => r.source && r.field && r.value !== '' && r.value !== undefined)
  emit('save', { logic: logic.value, rules: validRules })
  emit('update:visible', false)
}

function onClosed() {
  rules.value = []
  errors.value = {}
  conditionExpr.value = ''
}
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.condition-dialog-body {
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
}
.rules-list {
  margin-bottom: 8px;
}
.logic-connector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
}
.logic-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}
.logic-btn.and {
  background: $g-bg-warning;
  color: #E6A23C;
  border: 1px solid $g-border-warning;
}
.logic-btn.or {
  background: $g-bg-light-blue;
  color: $g-color-primary;
  border: 1px solid #b3d8ff;
}
.connector-line {
  flex: 1;
  height: 1px;
  background: $g-border-light;
}
.rules-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: $g-text-placeholder;
  gap: 12px;
}
.rules-empty p {
  margin: 0;
  font-size: 13px;
  color: $g-text-muted;
}
.quick-presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}
.add-rule-row {
  margin-bottom: 12px;
}
.preview-bar {
  background: $g-bg-header;
  border-radius: 6px;
  padding: 10px 14px;
}
.preview-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}
.preview-label {
  font-size: 12px;
  color: $g-text-muted;
  white-space: nowrap;
  margin-top: 2px;
}
.preview-expr {
  font-size: 13px;
  font-family: monospace;
  color: $g-text-primary;
  word-break: break-all;
  line-height: 1.5;
}
.validation-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.validation-row.valid { color: #67C23A; }
.validation-row.error { color: #F56C6C; }
</style>
