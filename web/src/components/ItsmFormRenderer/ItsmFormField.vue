<template>
  <div
    class="ifr-field"
    :class="{ 'ifr-field-selected': selected, 'ifr-field-sec': field.type === 'SECTION' }"
    :style="{ width: field.type === 'SECTION' ? '100%' : layoutWidth }"
    v-show="visible"
    @click.stop="$emit('select')"
  >
    <!-- SECTION divider -->
    <template v-if="field.type === 'SECTION'">
      <SectionDivider :label="field.name || '分组'" />
    </template>

    <!-- Regular field -->
    <template v-else>
      <div class="ifr-field-label">
        {{ field.name || field.key }}
        <span v-if="field.required" class="ifr-req">*</span>
        <span v-if="showTypeTag" class="ifr-type-tag">{{ typeLabel }}</span>
      </div>
      <component
        :is="tagComponent"
        :model-value="safeModelValue"
        :placeholder="field.placeholder"
        :disabled="isDisabled"
        v-bind="tagExtraProps"
        @update:model-value="(v: any) => $emit('update:modelValue', v)"
      />
      <!-- Design mode actions -->
      <div v-if="showActions" class="ifr-actions" @click.stop>
        <el-button size="small" text @click="$emit('copy')">
          <el-icon><CopyDocument /></el-icon>
        </el-button>
        <el-button size="small" text type="danger" @click="$emit('delete')">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Delete, CopyDocument } from '@element-plus/icons-vue'
import {
  TagInput, TagSelect, TagTextarea, TagCheckbox,
  TagRadio, TagInt, TagDatetime, TagCascader,
} from '/@/components/RenderForm/tags'
import MembersField from './fields/MembersField.vue'
import FileField from './fields/FileField.vue'
import RichtextField from './fields/RichtextField.vue'
import TableField from './fields/TableField.vue'
import DateField from './fields/DateField.vue'
import SectionDivider from './fields/SectionDivider.vue'
import { LAYOUT_COL_MAP } from './types'
import type { ItsmField, ItsmFieldType, RendererMode } from './types'

const props = withDefaults(defineProps<{
  field: ItsmField
  modelValue?: any
  mode?: RendererMode
  selected?: boolean
  showTypeTag?: boolean
  showActions?: boolean
}>(), {
  mode: 'fill',
  modelValue: '',
})

// Coerce empty string to null for numeric types (ElInputNumber rejects "")
const numericTypes = ['INT', 'NUMBER', 'FLOAT']
const safeModelValue = computed(() => {
  const v = props.modelValue
  if (v === '' && numericTypes.includes(props.field.type || '')) return null
  return v
})

defineEmits<{
  'update:modelValue': [value: any]
  select: []
  copy: []
  delete: []
}>()

const isDisabled = computed(() => props.mode !== 'fill')

const visible = computed(() => {
  // Visibility is handled by parent (useFieldVisibility) via v-show on the wrapper.
  // This computed is a fallback — if show_conditions exist, parent controls v-show.
  return true
})

const layoutWidth = computed(() => {
  return LAYOUT_COL_MAP[props.field.layout || 'COL_12'] || '100%'
})

const TYPE_LABELS: Record<string, string> = {
  STRING: '文本', TEXT: '多行', INT: '数字', DATE: '日期', DATETIME: '时间',
  SELECT: '下拉', RADIO: '单选', CHECKBOX: '复选', MULTISELECT: '多选',
  MEMBERS: '人员', TABLE: '表格', FILE: '附件', RICHTEXT: '富文', CASCADE: '级联',
}
const typeLabel = computed(() => TYPE_LABELS[props.field.type] || props.field.type)

// Map ITSM field type → Tag component
const TAG_COMPONENT_MAP: Record<string, any> = {
  STRING: TagInput,
  TEXT: TagTextarea,
  INT: TagInt,
  DATE: DateField,
  DATETIME: TagDatetime,
  SELECT: TagSelect,
  RADIO: TagRadio,
  CHECKBOX: TagCheckbox,
  MULTISELECT: TagSelect,
  CASCADE: TagCascader,
  MEMBERS: MembersField,
  FILE: FileField,
  RICHTEXT: RichtextField,
  TABLE: TableField,
}

const tagComponent = computed(() => {
  if (props.field.type === 'SECTION') return null
  return TAG_COMPONENT_MAP[props.field.type] || TagInput
})

const tagExtraProps = computed(() => {
  const t = props.field.type
  const extras: Record<string, any> = {}

  // Options for select/radio/checkbox/multiselect/cascade
  if (['SELECT', 'RADIO', 'CHECKBOX', 'MULTISELECT'].includes(t)) {
    extras.options = props.field.choice || []
  }
  if (t === 'MULTISELECT') {
    extras.multiple = true
  }

  // Textarea rows
  if (t === 'TEXT') {
    extras.rows = 3
  }

  return extras
})
</script>

<style scoped>
.ifr-field {
  position: relative;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 8px;
  transition: border-color 0.2s;
  background: #fff;
  box-sizing: border-box;
}
.ifr-field:hover {
  border-color: #d9ecff;
}
.ifr-field-selected {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.15);
}
.ifr-field-sec {
  border: none;
  padding: 4px 0;
  cursor: default;
}
.ifr-field-label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ifr-req {
  color: #F56C6C;
}
.ifr-type-tag {
  font-size: 10px;
  color: #909399;
  background: #f5f7fa;
  padding: 0 6px;
  border-radius: 3px;
  line-height: 16px;
}
.ifr-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  display: none;
  gap: 2px;
}
.ifr-field:hover .ifr-actions {
  display: flex;
}
.ifr-actions :deep(.el-button) {
  padding: 2px 4px;
  min-height: 0;
}
</style>
