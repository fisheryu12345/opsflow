<template>
  <el-select
    v-model="selectedKey"
    filterable
    size="small"
    style="width:100%"
    placeholder="Select variable"
    @change="onSelect"
    :clearable="clearable"
  >
    <el-option-group
      v-for="group in groupedOptions"
      :key="group.label"
      :label="group.label"
    >
      <el-option
        v-for="opt in group.options"
        :key="opt.value"
        :label="opt.label"
        :value="opt.value"
      >
        <div class="variable-option">
          <span class="var-source-tag" :class="opt.sourceType">{{ sourceTypeLabel(opt.sourceType) }}</span>
          <span class="var-field-label">{{ opt.fieldLabel }}</span>
        </div>
      </el-option>
    </el-option-group>
  </el-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { VariableOption } from '../utils/shapes'

const props = withDefaults(defineProps<{
  options: VariableOption[]
  modelValue?: string
  clearable?: boolean
}>(), {
  modelValue: '',
  clearable: true,
})

const emit = defineEmits<{
  select: [option: VariableOption]
  'update:modelValue': [value: string]
}>()

const selectedKey = computed({
  get: () => props.modelValue,
  set: (val: string) => emit('update:modelValue', val),
})

interface GroupedOpt {
  label: string
  options: { value: string; label: string; sourceType: string; fieldLabel: string }[]
}

const groupedOptions = computed<GroupedOpt[]>(() => {
  const groups: Record<string, GroupedOpt> = {}
  for (const opt of props.options) {
    const key = opt.sourceType
    if (!groups[key]) {
      groups[key] = {
        label: sourceTypeLabel(key),
        options: [],
      }
    }
    groups[key].options.push({
      value: `${opt.source}.${opt.field}`,
      label: `${opt.source}.${opt.field} (${opt.fieldType})`,
      sourceType: opt.sourceType,
      fieldLabel: opt.fieldLabel,
    })
  }
  // 确定排序：node → global → project → system
  const order = ['node', 'global', 'project', 'system']
  return order
    .filter(k => groups[k])
    .map(k => groups[k])
})

function sourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    node: 'Node',
    global: 'Global',
    project: 'Project',
    system: 'System',
  }
  return labels[type] || type
}

function onSelect(value: string) {
  if (!value) return
  const found = props.options.find(
    o => `${o.source}.${o.field}` === value,
  )
  if (found) emit('select', found)
}
</script>

<style scoped>
.variable-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
.var-source-tag {
  font-size: 10px;
  padding: 0 6px;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.var-source-tag.node { background: #ecf5ff; color: #409EFF; }
.var-source-tag.global { background: #f0f9eb; color: #67C23A; }
.var-source-tag.project { background: #fdf6ec; color: #E6A23C; }
.var-source-tag.system { background: #f4f4f5; color: #909399; }
.var-field-label {
  font-size: 12px;
  color: #303133;
  font-family: monospace;
}
</style>
