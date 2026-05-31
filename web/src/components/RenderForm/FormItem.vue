<template>
  <div class="form-item" v-show="!isHidden" :style="{ gridColumn: `span ${col}` }">
    <label v-if="config.name" class="form-label" :class="{ required: isRequired }">
      {{ config.name }}
    </label>
    <div class="form-control">
      <component
        :is="tagComponent"
        v-bind="tagProps"
        :model-value="value"
        @update:model-value="onChange"
      />
      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  TagInput, TagSelect, TagTextarea, TagCheckbox,
  TagRadio, TagInt, TagCodeEditor, TagDatetime, TagHostSelector,
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
}

const props = withDefaults(defineProps<{
  config: any
  value?: any
}>(), {})

const emit = defineEmits<{ update: [value: any] }>()
const errorMsg = ref('')

const tagComponent = computed(() => TAG_MAP[props.config.type] || TagInput)
const isRequired = computed(() =>
  props.config.validation?.some((v: any) => v.type === 'required')
)
const isHidden = computed(() => props.config.hidden || false)
const col = computed(() => Math.min(props.config.col || 12, 12))
const tagProps = computed(() => ({ ...props.config.attrs }))

function onChange(val: any) {
  errorMsg.value = ''
  // 校验
  for (const rule of props.config.validation || []) {
    if (rule.type === 'required' && (val === '' || val === null || val === undefined)) {
      errorMsg.value = rule.error_message || '必填项'
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
.form-label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}
.form-label.required::after {
  content: ' *';
  color: #F56C6C;
}
.form-control { width: 100%; }
.error-msg {
  font-size: 11px;
  color: #F56C6C;
  line-height: 1;
}
</style>
