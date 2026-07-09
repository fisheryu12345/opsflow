<template>
  <div class="ifr-renderer">
    <div class="ifr-grid">
      <ItsmFormField
        v-for="f in sortedFields"
        :key="f.key"
        v-show="isVisible(f)"
        :field="f"
        :model-value="data[f.key]"
        :mode="mode"
        :show-type-tag="mode === 'design'"
        :show-actions="mode === 'design'"
        :selected="mode === 'design' && selectedKey === f.key"
        @update:model-value="(v: any) => $emit('fieldChange', f.key, v)"
        @select="mode === 'design' && $emit('fieldSelect', f.key)"
        @copy="mode === 'design' && $emit('fieldCopy', f.key)"
        @delete="mode === 'design' && $emit('fieldDelete', f.key)"
      />
    </div>
    <div v-if="mode === 'fill' && showSubmit" class="ifr-submit">
      <el-button v-if="cancelText" @click="$emit('cancel')">{{ cancelText }}</el-button>
      <el-button type="primary" :loading="submitting" @click="$emit('submit', data)">
        <el-icon><Select /></el-icon> {{ submitText }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Select } from '@element-plus/icons-vue'
import ItsmFormField from './ItsmFormField.vue'
import type { ItsmField, RendererMode } from './types'

const props = withDefaults(defineProps<{
  fields?: ItsmField[]
  data?: Record<string, any>
  mode?: RendererMode
  showSubmit?: boolean
  submitText?: string
  cancelText?: string
  submitting?: boolean
  /** For design mode: which field is currently selected */
  selectedKey?: string
}>(), {
  fields: () => [],
  data: () => ({}),
  mode: 'fill',
  showSubmit: true,
  submitText: '提交',
  submitting: false,
})

const emit = defineEmits<{
  fieldChange: [key: string, value: any]
  submit: [data: Record<string, any>]
  cancel: []
  fieldSelect: [key: string]
  fieldCopy: [key: string]
  fieldDelete: [key: string]
}>()

// Sort fields by sort_order (if present) to preserve designer order
const sortedFields = computed(() => {
  return [...props.fields].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
})

// Check show_conditions
function isVisible(field: ItsmField): boolean {
  const cond = field.show_conditions
  if (!cond?.field) return true
  const depValue = props.data[cond.field]
  return String(depValue ?? '') === String(cond.value ?? '')
}

// Expose for parent access
defineExpose({})
</script>

<style scoped>
.ifr-renderer {
  width: 100%;
}
.ifr-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}
.ifr-submit {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
