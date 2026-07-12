<template>
  <div class="ifr-renderer">
    <form-create
      v-if="mode !== 'design'"
      v-model:api="fApi"
      v-model="formData"
      :rule="sortedRules"
      :option="formOption"
    />
    <!-- Design mode: delegate to fc-designer internally (handled upstream) -->
    <div v-else class="ifr-design-placeholder">
      <span style="color:#C0C4CC">Design mode is handled by fc-designer</span>
    </div>
    <div v-if="mode === 'fill' && showSubmit" class="ifr-submit">
      <el-button v-if="cancelText" @click="$emit('cancel')">{{ cancelText }}</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        <el-icon><Select /></el-icon> {{ submitText }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Select } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  fields?: any[]
  data?: Record<string, any>
  mode?: string
  showSubmit?: boolean
  submitText?: string
  cancelText?: string
  submitting?: boolean
  selectedKey?: string
}>(), {
  fields: () => [],
  data: () => ({}),
  mode: 'fill',
  showSubmit: true,
  submitText: '',
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

const fApi = ref()

// form-create v-model: sync external data in, and emit fieldChange out
const formData = computed({
  get: () => ({ ...props.data }),
  set: (val) => {
    // Emit fieldChange for each key (backward compat).
    // Use JSON.stringify for array/object fields where reference equality fails.
    for (const key of Object.keys(val)) {
      const a = val[key]; const b = props.data[key]
      if (a !== b && JSON.stringify(a) !== JSON.stringify(b)) {
        emit('fieldChange', key, a)
      }
    }
  },
})

// Sort rules by itsmSortOrder
const sortedRules = computed(() => {
  return [...props.fields].sort(
    (a, b) => (a.itsmSortOrder ?? 0) - (b.itsmSortOrder ?? 0)
  )
})

// form-create form options
const formOption = computed(() => ({
  form: { size: 'default' as const },
  submitBtn: { show: false },
  resetBtn: { show: false },
  // Read-only for preview mode
  preview: props.mode !== 'fill',
}))

function handleSubmit() {
  if (!fApi.value) return  // form not ready, do nothing
  fApi.value.validate().then((valid: boolean) => {
    if (valid) {
      emit('submit', { ...props.data })
    }
  }).catch(() => {})
}

// Expose fApi for parent access
defineExpose({ fApi })
</script>

<style scoped>
.ifr-renderer {
  width: 100%;
}
.ifr-design-placeholder {
  padding: 40px;
  text-align: center;
}
.ifr-submit {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
