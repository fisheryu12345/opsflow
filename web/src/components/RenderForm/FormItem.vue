<template>
  <div class="form-item" v-show="!isHidden" :style="{ gridColumn: `span ${col}` }">
    <div class="form-label-row">
      <label v-if="config.name" class="form-label" :class="{ required: isRequired }">
        {{ config.name }}
      </label>
    </div>
    <div class="form-control">
      <div class="form-control-inner">
        <component
          :is="tagComponent"
          v-bind="tagProps"
          :model-value="value"
          :form-data="formData"
          @update:model-value="onChange"
        />
        <el-button v-if="props.context?.onPromote" text type="primary" size="small" class="promote-btn" @click.stop="props.context.onPromote(config, value)">
          <el-icon><Upload /></el-icon>
        </el-button>
      </div>
      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import {
  TagInput, TagSelect, TagTextarea, TagCheckbox,
  TagRadio, TagInt, TagCodeEditor, TagDatetime,
  TagHostSelector, TagAsyncSelect, TagIpSelector, TagDataTable,
  TagVariableInput, TagMetaConfig, TagVariableMapping,
  TagResourceSelector, TagCascader, TagSlider, TagSwitch,
} from './tags'

const TAG_MAP: Record<string, any> = {
  input: TagInput,
  select: TagSelect,
  textarea: TagTextarea,
  checkbox: TagCheckbox,
  radio: TagRadio,
  int: TagInt,
  code_editor: TagCodeEditor,
  datetime: TagDatetime,
  host_selector: TagHostSelector,
  async_select: TagAsyncSelect,
  ip_selector: TagIpSelector,
  datatable: TagDataTable,
  switch: TagSwitch,
  resource_selector: TagResourceSelector,
  cascader: TagCascader,
  slider: TagSlider,
  variable_input: TagVariableInput,
  meta_config: TagMetaConfig,
  variable_mapping: TagVariableMapping,
}

const props = withDefaults(defineProps<{
  config: any
  value?: any
  formData?: any
  context?: Record<string, any>
  tagCode?: string
}>(), { context: () => ({}) })

const emit = defineEmits<{ update: [value: any] }>()
const errorMsg = ref('')

const tagComponent = computed(() => TAG_MAP[props.config.type] || TagInput)
const isRequired = computed(() =>
  props.config.validation?.some((v: any) => v.type === 'required')
)
const isHidden = computed(() => props.config.hidden || false)
const col = computed(() => Math.min(props.config.col || 12, 12))

const tagProps = computed(() => ({
  ...props.config.attrs,
  // Pass render context to tag components (templateId, nodeId, etc.)
  ...(props.context?.templateId ? { templateId: props.context.templateId } : {}),
  ...(props.context?.nodeId ? { nodeId: props.context.nodeId } : {}),
  ...(props.context?.availableVars ? { availableVars: props.context.availableVars } : {}),
  ...(props.context?.graphNodes ? { graphNodes: props.context.graphNodes } : {}),
  ...(props.context?.allGraphNodes ? { allGraphNodes: props.context.allGraphNodes } : {}),
  tagCode: props.tagCode || props.config.tag_code || '',
}))

function onChange(val: any) {
  errorMsg.value = ''
  // validation
  for (const rule of props.config.validation || []) {
    if (rule.type === 'required' && (val === '' || val === null || val === undefined)) {
      errorMsg.value = rule.error_message || 'Required'
      break
    }
  }
  emit('update', val)
}
</script>

<style scoped>
.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-label-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 18px;
}
.form-label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}
.form-label.required::after {
  content: ' *';
  color: #F56C6C;
}
.promote-btn {
  flex-shrink: 0;
  margin-left: 2px;
}
.form-control { width: 100%; }
.form-control-inner {
  display: flex;
  align-items: center;
  gap: 4px;
}
.form-control-inner > :first-child {
  flex: 1;
  min-width: 0;
}
.error-msg {
  font-size: 11px;
  color: #F56C6C;
  line-height: 1;
}
</style>
