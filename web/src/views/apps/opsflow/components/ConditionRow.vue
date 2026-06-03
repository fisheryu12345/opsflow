<template>
  <div class="condition-row" :class="{ 'has-error': hasError }">
    <div class="row-header">
      <span class="row-index" :style="{ background: indexColor }">{{ index + 1 }}</span>
      <span class="row-label">When</span>
      <el-button size="small" text type="danger" :icon="Delete" @click="$emit('remove')" />
    </div>
    <div class="row-fields">
      <VariablePicker
        :options="availableVars"
        :model-value="variableKey"
        class="field-cell"
        @select="onVariableSelect"
        @update:model-value="onVariableKeyChange"
        :clearable="false"
      />
      <el-select
        v-model="localRule.op"
        size="small"
        class="field-cell op-cell"
        @change="emitChange"
      >
        <el-option
          v-for="op in filteredOps"
          :key="op"
          :label="op"
          :value="op"
        />
      </el-select>
      <el-input
        v-model="localRule.value"
        size="small"
        class="field-cell"
        :placeholder="valuePlaceholder"
        :type="valueInputType"
        @change="emitChange"
      />
      <span class="field-type-badge">{{ fieldTypeLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import VariablePicker from './VariablePicker.vue'
import { opsForType } from '../composables/useGraphCanvas'
import type { VariableOption, ConditionRule } from '../utils/shapes'

const props = withDefaults(defineProps<{
  rule: ConditionRule
  index: number
  availableVars: VariableOption[]
  hasError?: boolean
}>(), {
  hasError: false,
})

const emit = defineEmits<{
  change: [rule: ConditionRule]
  remove: []
}>()

const localRule = ref<ConditionRule>({ ...props.rule })
const variableKey = ref('')

watch(() => props.rule, (r) => {
  localRule.value = { ...r }
  variableKey.value = r.source && r.field ? `${r.source}.${r.field}` : ''
}, { immediate: true, deep: true })

const fieldType = computed(() => localRule.value.fieldType || 'string')
const filteredOps = computed(() => opsForType(fieldType.value))
const fieldTypeLabel = computed(() => {
  const labels: Record<string, string> = { string: 'string', number: 'number', boolean: 'bool' }
  return labels[fieldType.value] || 'string'
})
const valueInputType = computed(() => fieldType.value === 'number' ? 'number' : 'text')
const valuePlaceholder = computed(() => {
  if (fieldType.value === 'number') return 'e.g. 80'
  if (fieldType.value === 'boolean') return 'true / false'
  return 'e.g. ok'
})
const indexColor = computed(() => {
  const colors = ['#67C23A', '#E6A23C', '#409EFF', '#9B59B6', '#00BCD4']
  return colors[props.index % colors.length]
})

function onVariableSelect(opt: VariableOption) {
  localRule.value.source = opt.source
  localRule.value.field = opt.field
  localRule.value.fieldLabel = opt.fieldLabel
  localRule.value.fieldType = opt.fieldType
  variableKey.value = `${opt.source}.${opt.field}`
  // 字段类型变化时调整运算符
  const availableOps = opsForType(opt.fieldType)
  if (!availableOps.includes(localRule.value.op)) {
    localRule.value.op = availableOps[0]
  }
  emitChange()
}

function onVariableKeyChange(val: string) {
  variableKey.value = val
  if (!val) {
    localRule.value.source = ''
    localRule.value.field = ''
    emitChange()
  }
}

function emitChange() {
  emit('change', { ...localRule.value })
}
</script>

<style scoped>
.condition-row {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid transparent;
  transition: border-color 0.2s;
}
.condition-row.has-error {
  border-color: #F56C6C;
}
.row-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.row-index {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.row-label {
  font-size: 12px;
  color: #909399;
  flex: 1;
}
.row-fields {
  display: flex;
  align-items: center;
  gap: 8px;
}
.field-cell {
  flex: 1;
}
.op-cell {
  flex: 0 0 90px;
}
.field-type-badge {
  font-size: 10px;
  color: #909399;
  background: #e9e9eb;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
}
</style>
