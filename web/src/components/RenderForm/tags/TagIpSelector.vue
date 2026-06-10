<template>
  <div class="ip-selector">
    <!-- 模式 Tab -->
    <div class="mode-tabs" v-if="modes.length > 1">
      <el-tag
        v-for="m in modes" :key="m"
        :type="activeMode === m ? 'primary' : 'info'"
        size="small"
        class="mode-tab"
        @click="activeMode = m"
        effect="plain">
        {{ modeLabels[m] || m }}
      </el-tag>
    </div>

    <!-- 模式: 手动输入 -->
    <template v-if="activeMode === 'manual'">
      <div class="ip-tags" v-if="selectedIps.length">
        <el-tag v-for="ip in selectedIps" :key="ip" closable size="small" @close="removeIp(ip)" type="info">
          {{ ip }}
        </el-tag>
      </div>
      <div class="ip-input-row">
        <el-input v-model="inputVal" :placeholder="placeholder" :disabled="disabled"
          size="small" clearable style="width:160px" @keyup.enter="addIp" />
        <el-button size="small" type="primary" :icon="Plus" @click="addIp" :disabled="disabled">添加</el-button>
        <el-button v-if="presetIps.length" size="small" @click="selectPreset">预设</el-button>
      </div>
    </template>

    <!-- 模式: 静态选择 -->
    <template v-if="activeMode === 'static'">
      <el-select v-model="selectedIps" :placeholder="placeholder" :disabled="disabled"
        multiple filterable collapse-tags size="small" style="width:100%">
        <el-option v-for="opt in options" :key="opt.value" :label="opt.label" :value="opt.value" />
      </el-select>
    </template>

    <!-- 模式: 动态搜索 -->
    <template v-if="activeMode === 'dynamic'">
      <div class="ip-tags" v-if="selectedIps.length">
        <el-tag v-for="ip in selectedIps" :key="ip" closable size="small" @close="removeIp(ip)" type="info">
          {{ ip }}
        </el-tag>
      </div>
      <el-select v-model="searchSelected" :placeholder="'搜索并选择 IP...'" :disabled="disabled"
        multiple filterable remote collapse-tags
        :remote-method="searchIps" :loading="searching"
        size="small" style="width:100%"
        @remove-tag="onRemoteRemoveTag">
        <el-option v-for="item in searchResults" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  attrs?: {
    modes?: string[]
    options?: { label: string; value: string }[]
    api_endpoint?: string
    presets?: string[]
  }
}>(), {
  modelValue: '',
  placeholder: '输入 IP 地址',
  attrs: () => ({}),
})

const emit = defineEmits(['update:modelValue'])

const modeLabels: Record<string, string> = {
  manual: '手动输入',
  static: '静态选择',
  dynamic: '动态搜索',
  search: 'IP 搜索',
}

const modes = computed(() => props.attrs?.modes || ['manual'])
const activeMode = ref(modes.value[0])
const inputVal = ref('')
const presetIps = computed(() => props.attrs?.presets || [])
const options = computed(() => props.attrs?.options || [])
const apiEndpoint = computed(() => props.attrs?.api_endpoint || '')

const selectedIps = computed({
  get: () => {
    const v = props.modelValue
    if (Array.isArray(v)) return v
    if (typeof v === 'string') return v ? v.split(',').map((s: string) => s.trim()) : []
    return []
  },
  set: (v) => emit('update:modelValue', v),
})

const IP_REGEX = /^(\d{1,3}\.){3}\d{1,3}$/

function addIp() {
  const ip = inputVal.value.trim()
  if (!ip) return
  if (!IP_REGEX.test(ip)) {
    ElMessage.warning('请输入有效的 IPv4 地址')
    return
  }
  if (selectedIps.value.includes(ip)) {
    ElMessage.warning('IP 已存在')
    inputVal.value = ''
    return
  }
  selectedIps.value = [...selectedIps.value, ip]
  inputVal.value = ''
}

function removeIp(ip: string) {
  selectedIps.value = selectedIps.value.filter((i: string) => i !== ip)
}

function selectPreset() {
  const current = new Set(selectedIps.value)
  const toAdd = presetIps.value.filter((ip: string) => !current.has(ip))
  if (toAdd.length) {
    selectedIps.value = [...selectedIps.value, ...toAdd]
  }
}

// ── 动态搜索 ──
const searchResults = ref<{ value: string; label: string }[]>([])
const searching = ref(false)
const searchSelected = ref<string[]>([])

// sync selectedIps ↔ searchSelected
watch(selectedIps, (val) => {
  searchSelected.value = [...val]
}, { immediate: true })

watch(searchSelected, (val) => {
  selectedIps.value = [...val]
})

async function searchIps(query: string) {
  if (!apiEndpoint.value) return
  searching.value = true
  try {
    const url = apiEndpoint.value + (query ? `?q=${encodeURIComponent(query)}` : '')
    const res = await fetch(url)
    const json = await res.json()
    searchResults.value = json.data || []
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function onRemoteRemoveTag(tag: string) {
  selectedIps.value = selectedIps.value.filter((i: string) => i !== tag)
}
</script>

<style scoped>
.ip-selector { display: flex; flex-direction: column; gap: 6px; }
.mode-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
.mode-tab { cursor: pointer; user-select: none; }
.ip-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.ip-input-row { display: flex; gap: 4px; align-items: center; }
</style>
