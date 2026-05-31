<template>
  <el-select v-model="selected" :placeholder="placeholder" :disabled="disabled"
    :multiple="multiple" filterable allow-create default-first-option size="small" style="width:100%">
    <el-option v-for="h in hosts" :key="h" :label="h" :value="h" />
  </el-select>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  multiple?: boolean
}>(), { modelValue: '', placeholder: '选择或输入主机地址' })

const emit = defineEmits(['update:modelValue'])

const hosts = ref<string[]>([])

// 生产环境从 API 加载主机列表
// onMounted(async () => { hosts.value = await getHostList() })

const selected = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
