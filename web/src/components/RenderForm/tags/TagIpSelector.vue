<template>
  <div class="ip-selector">
    <div class="ip-tags" v-if="selectedIps.length">
      <el-tag v-for="ip in selectedIps" :key="ip" closable size="small" @close="removeIp(ip)" type="info">
        {{ ip }}
      </el-tag>
    </div>
    <div class="ip-input-row">
      <el-input v-model="inputVal" :placeholder="placeholder" :disabled="disabled"
        size="small" clearable style="width:160px" @keyup.enter="addIp" />
      <el-button size="small" type="primary" @click="addIp" :disabled="disabled">添加</el-button>
      <el-button v-if="presetIps.length" size="small" @click="selectPreset">预设</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  multiple?: boolean
  attrs?: { presets?: string[] }
}>(), { modelValue: '', placeholder: '输入 IP 地址' })

const emit = defineEmits(['update:modelValue'])

const inputVal = ref('')
const presetIps = computed(() => props.attrs?.presets || [])

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
  const next = [...selectedIps.value, ip]
  selectedIps.value = next
  inputVal.value = ''
}

function removeIp(ip: string) {
  selectedIps.value = selectedIps.value.filter((i: string) => i !== ip)
}

function selectPreset() {
  // 将预设列表中不在当前列表中的IP添加进去
  const current = new Set(selectedIps.value)
  const toAdd = presetIps.value.filter((ip: string) => !current.has(ip))
  if (toAdd.length) {
    selectedIps.value = [...selectedIps.value, ...toAdd]
  }
}
</script>

<style scoped>
.ip-selector { display: flex; flex-direction: column; gap: 6px; }
.ip-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.ip-input-row { display: flex; gap: 4px; align-items: center; }
</style>
