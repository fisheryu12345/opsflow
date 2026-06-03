<template>
  <div class="cascader-wrapper">
    <el-cascader
      v-model="cascaderValue"
      :options="cascaderOptions"
      :placeholder="placeholder"
      :disabled="disabled"
      :props="cascaderProps"
      :show-all-levels="true"
      filterable
      clearable
      size="small"
      style="width:100%"
      @change="onChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  attrs?: {
    options?: any[]
    api_endpoint?: string
    props?: Record<string, any>
  }
}>(), {
  modelValue: undefined,
  placeholder: '请选择...',
  attrs: () => ({}),
})

const emit = defineEmits(['update:modelValue'])

const cascaderValue = computed({
  get: () => {
    const v = props.modelValue
    if (v === undefined || v === null || v === '') return []
    if (Array.isArray(v)) return v
    return [v]
  },
  set: (val) => emit('update:modelValue', val),
})

// 静态选项或动态加载后的缓存
const cascaderOptions = ref<any[]>([])

const apiEndpoint = computed(() => props.attrs?.api_endpoint || '')
const staticOptions = computed(() => props.attrs?.options || [])

const cascaderProps = computed(() => ({
  multiple: false,
  checkStrictly: true,
  emitPath: true,
  ...(props.attrs?.props || {}),
}))

function onChange(val: any) {
  emit('update:modelValue', val)
}

async function loadOptions() {
  // 优先使用静态选项
  if (staticOptions.value.length) {
    cascaderOptions.value = staticOptions.value
    return
  }
  // 动态从 API 加载
  if (!apiEndpoint.value) return
  try {
    const res = await fetch(apiEndpoint.value)
    const json = await res.json()
    cascaderOptions.value = json.data || []
  } catch {
    cascaderOptions.value = []
  }
}

onMounted(loadOptions)
</script>

<style scoped>
.cascader-wrapper { width: 100%; }
</style>
