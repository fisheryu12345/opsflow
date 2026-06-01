<template>
  <el-select
    v-model="val" :placeholder="placeholder" :disabled="disabled"
    :multiple="multiple" :clearable="clearable" :loading="loading"
    :filterable="isSearchable"
    :default-first-option="true" size="small" style="width:100%"
    :popper-append-to-body="false"
    @visible-change="onVisibleChange"
  >
    <el-option
      v-for="opt in filteredOptions" :key="opt[valueKey]"
      :label="opt[labelKey]"
      :value="opt[valueKey]"
    />
  </el-select>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
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
  clearable: false,
  placeholder: '请选择',
  disabled: false,
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const allOptions = ref<any[]>([])

const isSearchable = computed(() => props.searchable && props.api_endpoint.length > 0)

/* Pass through all options; el-select's built-in filterable handles client-side search */
const filteredOptions = computed(() => allOptions.value)

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

async function fetchOptions(query?: string) {
  if (!props.api_endpoint) return
  loading.value = true
  try {
    const params: any = {}
    if (query) params.q = query
    // Parse depends_on: watch other form fields for re-fetching
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
    allOptions.value = Array.isArray(data) ? data : []
  } catch {
    allOptions.value = []
  } finally {
    loading.value = false
  }
}

function onVisibleChange(visible: boolean) {
  if (visible && allOptions.value.length === 0) {
    fetchOptions()
  }
}

/* Re-fetch when depends_on fields change */
if (props.depends_on) {
  watch(
    () => {
      const deps = props.depends_on.split(',').map(s => s.trim())
      return deps.map(d => props.formData[d]).join('|')
    },
    () => { fetchOptions() },
  )
}

/* Preload data on mount so dropdown shows options immediately */
onMounted(() => {
  if (props.api_endpoint) {
    fetchOptions()
  }
})
</script>
