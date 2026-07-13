<template>
  <div class="gvi-form">
    <div v-for="(cfg, key) in vars" :key="key" class="gvi-item">
      <div class="gvi-label">
        {{ cfg.label || key }}
        <el-tag v-if="cfg.type" size="small" effect="plain">{{ varTypeLabel(cfg.type) }}</el-tag>
      </div>

      <!-- select / async_select -->
      <el-select
        v-if="cfg.type === 'select' || cfg.type === 'async_select'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :placeholder="`请选择${cfg.label || key}`"
        :multiple="cfg.meta?.multiple"
        :loading="asyncLoadingKey === key"
        filterable clearable style="width:100%"
      >
        <el-option v-for="o in (cfg.meta?.options || [])" :key="o.value ?? o"
          :label="o.label ?? o" :value="o.value ?? o" />
      </el-select>

      <!-- host_selector / ip_selector (filterable + allow-create) -->
      <el-select
        v-else-if="cfg.type === 'host_selector' || cfg.type === 'ip_selector'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :placeholder="`请选择${cfg.label || key}`"
        :multiple="cfg.meta?.multiple"
        filterable allow-create default-first-option clearable style="width:100%"
      >
        <el-option v-for="o in (cfg.meta?.options || [])" :key="o.value ?? o"
          :label="o.label ?? o" :value="o.value ?? o" />
      </el-select>

      <!-- int / float -->
      <el-input-number
        v-else-if="cfg.type === 'int' || cfg.type === 'float'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :placeholder="`请输入${cfg.label || key}`"
        :min="cfg.meta?.min ?? -Infinity"
        :max="cfg.meta?.max ?? Infinity"
        :step="cfg.type === 'float' ? 0.1 : 1"
        controls-position="right"
        style="width:100%"
      />

      <!-- textarea -->
      <el-input
        v-else-if="cfg.type === 'textarea'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        type="textarea" :rows="3"
        :placeholder="`请输入${cfg.label || key}`"
      />

      <!-- datetime -->
      <el-date-picker
        v-else-if="cfg.type === 'datetime'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        type="datetime"
        format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss"
        style="width:100%"
      />

      <!-- date -->
      <el-date-picker
        v-else-if="cfg.type === 'date'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        type="date"
        format="YYYY-MM-DD" value-format="YYYY-MM-DD"
        style="width:100%"
      />

      <!-- time -->
      <el-time-picker
        v-else-if="cfg.type === 'time'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        format="HH:mm:ss" value-format="HH:mm:ss"
        style="width:100%"
      />

      <!-- switch -->
      <el-switch
        v-else-if="cfg.type === 'switch'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :active-value="cfg.meta?.activeValue ?? true"
        :inactive-value="cfg.meta?.inactiveValue ?? false"
        active-text="是" inactive-text="否"
      />

      <!-- slider -->
      <el-slider
        v-else-if="cfg.type === 'slider'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :min="cfg.meta?.min ?? 0" :max="cfg.meta?.max ?? 100"
      />

      <!-- checkbox -->
      <el-checkbox-group v-else-if="cfg.type === 'checkbox'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)">
        <el-checkbox v-for="o in (cfg.meta?.options || [])" :key="o.value" :label="o.value">{{ o.label }}</el-checkbox>
      </el-checkbox-group>

      <!-- radio -->
      <el-radio-group v-else-if="cfg.type === 'radio'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)">
        <el-radio v-for="o in (cfg.meta?.options || [])" :key="o.value" :label="o.value">{{ o.label }}</el-radio>
      </el-radio-group>

      <!-- cascader -->
      <el-cascader
        v-else-if="cfg.type === 'cascader'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :options="cfg.meta?.options || []"
        :placeholder="`请选择${cfg.label || key}`"
        clearable style="width:100%"
      />

      <!-- password -->
      <el-input
        v-else-if="cfg.type === 'password'"
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        type="password" show-password
        :placeholder="`请输入${cfg.label || key}`"
      />

      <!-- default: input -->
      <el-input
        v-else
        :model-value="modelValue[key]"
        @update:model-value="setVal(key, $event)"
        :placeholder="`请输入${cfg.label || key}`"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { request } from '/@/utils/service'

const props = defineProps<{
  vars: Record<string, any>
  modelValue: Record<string, any>
  loading?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [val: Record<string, any>] }>()

const asyncLoadingKey = ref<string | null>(null)

function setVal(key: string, val: any) {
  const next = { ...props.modelValue, [key]: val }
  emit('update:modelValue', next)
}

function varTypeLabel(t?: string) {
  const m: Record<string, string> = {
    select: '下拉', async_select: '异步下拉', int: '整数', float: '小数',
    datetime: '日期时间', date: '日期', time: '时间', textarea: '多行',
    password: '密码', switch: '开关', checkbox: '多选', radio: '单选',
    slider: '滑块', cascader: '级联',
  }
  return m[t || ''] || t || '文本'
}

// ── async_select support ──
function getDeps(key: string): string[] {
  return ((props.vars[key]?.meta?.dependsOn || '') as string).split(',').map((s: string) => s.trim()).filter(Boolean)
}

function depsResolved(key: string): boolean {
  return getDeps(key).every(dep => {
    const v = props.modelValue[dep]
    return v !== undefined && v !== null && v !== '' && !/^\$\{/.test(String(v))
  })
}

async function loadAsyncOptions(key: string) {
  const info = props.vars[key]
  if (!info?.meta?.apiEndpoint) return
  asyncLoadingKey.value = key
  try {
    const params: any = {}
    for (const k of Object.keys(props.modelValue)) {
      const v = props.modelValue[k]
      if (v !== undefined && v !== null && v !== '' && !/^\$\{/.test(String(v))) params[k] = v
    }
    const res = await request({ url: info.meta.apiEndpoint, method: 'get', params })
    const arr = Array.isArray(res) ? res : (Array.isArray((res as any)?.data) ? (res as any).data : [])
    if (!props.vars[key].meta) props.vars[key].meta = {}
    props.vars[key].meta.options = arr
  } catch {
    if (!props.vars[key].meta) props.vars[key].meta = {}
    props.vars[key].meta.options = []
  } finally {
    asyncLoadingKey.value = null
  }
}

function loadReadyAsyncOptions() {
  for (const key of Object.keys(props.vars)) {
    if (props.vars[key]?.type === 'async_select' && depsResolved(key)) loadAsyncOptions(key)
  }
}

watch(() => props.vars, () => loadReadyAsyncOptions(), { immediate: true })
watch(() => props.modelValue, () => loadReadyAsyncOptions(), { deep: true })
</script>

<style scoped>
.gvi-form { padding: 4px 0; }
.gvi-item { margin-bottom: 12px; }
.gvi-label { font-size: 13px; color: #606266; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
</style>
