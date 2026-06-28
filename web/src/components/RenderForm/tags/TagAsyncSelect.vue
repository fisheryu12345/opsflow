<template>
  <div>
    <template v-if="ready">
      <el-select
        v-model="localVal"
        :placeholder="placeholder || '请选择'"
        :disabled="disabled"
        :clearable="clearable"
        :multiple="multiple"
        filterable
        size="small"
        style="width:100%"
      >
        <el-option
          v-for="opt in options"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </template>
    <template v-else>
      <div style="display:flex;align-items:center;gap:4px;height:28px;padding:0 8px;background:#f5f7fa;border-radius:4px;font-size:12px;color:#999;">
        {{ loading ? '加载中...' : '请选择' }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { request } from '/@/utils/service'

const props = withDefaults(defineProps<{
  modelValue?: any
  formData?: any
  api_endpoint?: string
  depends_on?: string
  value_key?: string
  label_key?: string
  searchable?: boolean
  multiple?: boolean
  clearable?: boolean
  placeholder?: string
  disabled?: boolean
}>(), {
  modelValue: '',
  formData: () => ({}),
  api_endpoint: '',
  depends_on: '',
  value_key: 'value',
  label_key: 'label',
  searchable: false,
  multiple: false,
  clearable: true,
  placeholder: '请选择',
  disabled: false,
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const options = ref<any[]>([])
const localVal = ref(props.modelValue)
const ready = ref(false)

watch(() => props.modelValue, (v) => { localVal.value = v ?? '' })
watch(localVal, (v) => { emit('update:modelValue', v) })

async function fetchOptions() {
  if (!props.api_endpoint) return
  loading.value = true
  ready.value = false
  try {
    const params: any = {}
    if (props.depends_on) {
      for (const dep of props.depends_on.split(',').map(s => s.trim())) {
        const depVal = props.formData[dep]
        if (depVal !== undefined && depVal !== null && depVal !== '') {
          params[dep] = depVal
        }
      }
    }
    const res = await request({ url: props.api_endpoint, method: 'get', params })
    const data = res?.data?.data || res?.data || res || []
    options.value = Array.isArray(data) ? data : []
  } catch {
    options.value = []
  } finally {
    loading.value = false
    ready.value = true
  }
}

if (props.depends_on) {
  watch(
    () => props.depends_on.split(',').map(d => props.formData[d.trim()]).join('|'),
    () => fetchOptions(),
  )
}

onMounted(() => {
  if (props.api_endpoint) fetchOptions()
  else ready.value = true
})
</script>
