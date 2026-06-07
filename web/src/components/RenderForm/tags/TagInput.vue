<template>
  <div class="tag-input-wrapper">
    <div class="var-input-row">
      <el-input ref="inputRef" v-model="val" :placeholder="placeholder" :disabled="disabled" :clearable="clearable" size="small" style="width:100%" />
      <el-button v-if="templateId" size="small" :icon="Coin" @click="showBrowser = true" title="Browse variables" />
    </div>
    <VariableBrowser
      v-if="templateId"
      v-model="showBrowser"
      :template-id="templateId"
      @insert="onVarInsert"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Coin } from '@element-plus/icons-vue'
import VariableBrowser from '/@/views/apps/opsflow/components/panels/VariableBrowser.vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  templateId?: number | null
  nodeId?: string
  tagCode?: string
}>(), { modelValue: '' })
const emit = defineEmits(['update:modelValue'])

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const inputRef = ref<any>(null)
const showBrowser = ref(false)

function onVarInsert(key: string) {
  const refStr = `\${${key}}`
  const inputEl = inputRef.value?.$el?.querySelector('input')
  if (inputEl) {
    const start = inputEl.selectionStart ?? val.value.length
    const end = inputEl.selectionEnd ?? val.value.length
    const newVal = val.value.substring(0, start) + refStr + val.value.substring(end)
    emit('update:modelValue', newVal)
  } else {
    emit('update:modelValue', (val.value || '') + refStr)
  }
}
</script>

<style scoped>
.tag-input-wrapper { width: 100%; }
.var-input-row { display: flex; gap: 4px; align-items: center; }
</style>
