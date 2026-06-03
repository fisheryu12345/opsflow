<template>
  <el-dialog
    :model-value="visible"
    title="Edit Condition"
    width="680px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
    @closed="onClosed"
    destroy-on-close
  >
    <div class="condition-dialog-body">
      <!-- 条件行列表 -->
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
          <!-- AND/OR 连接器（行间） -->
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

      <!-- 空状态 -->
      <div v-else class="rules-empty">
        <el-icon size="24" color="#c0c4cc"><Plus /></el-icon>
        <p>No conditions yet. Add one below.</p>
      </div>

      <!-- 添加条件 -->
      <div class="add-rule-row">
        <el-button size="small" type="primary" plain @click="addRule">
          <el-icon><Plus /></el-icon>
          Add Condition
        </el-button>
      </div>

      <!-- 预览 + 校验 -->
      <div class="preview-bar" v-if="rules.length > 0">
        <div class="preview-row">
          <span class="preview-label">Expression:</span>
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
      <el-button @click="$emit('update:visible', false)">Cancel</el-button>
      <el-button type="primary" @click="onSave" :disabled="!isValid">
        Confirm
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, ArrowDown, CircleCheck, WarningFilled } from '@element-plus/icons-vue'
import ConditionRow from './ConditionRow.vue'
import { generateConditionExpr } from '../composables/useGraphCanvas'
import type { VariableOption, ConditionRule, ConditionStruct } from '../utils/shapes'

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
    return `Validation failed: ${errKeys.length} row(s) have errors`
  }
  return 'Validation passed'
})

// 初始化/回填
watch(() => props.visible, (show) => {
  if (!show) return
  if (props.initialStruct?.rules && props.initialStruct.rules.length > 0) {
    rules.value = props.initialStruct.rules.map(r => ({ ...r }))
    logic.value = props.initialStruct.logic || 'AND'
  } else {
    // 默认添加一个空条件行
    rules.value = [createEmptyRule()]
    logic.value = 'AND'
  }
  rebuildExpr()
})

function createEmptyRule(): ConditionRule {
  return { source: '', field: '', op: '==', value: '' }
}

function onRuleChange(idx: number, rule: ConditionRule) {
  rules.value[idx] = rule
  // 校验
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

<style scoped>
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
  background: #fdf6ec;
  color: #E6A23C;
  border: 1px solid #f5d6a6;
}
.logic-btn.or {
  background: #ecf5ff;
  color: #409EFF;
  border: 1px solid #b3d8ff;
}
.connector-line {
  flex: 1;
  height: 1px;
  background: #ebeef5;
}
.rules-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #c0c4cc;
  gap: 8px;
}
.rules-empty p {
  margin: 0;
  font-size: 13px;
}
.add-rule-row {
  margin-bottom: 12px;
}
.preview-bar {
  background: #f5f7fa;
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
  color: #909399;
  white-space: nowrap;
  margin-top: 2px;
}
.preview-expr {
  font-size: 13px;
  font-family: monospace;
  color: #303133;
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
