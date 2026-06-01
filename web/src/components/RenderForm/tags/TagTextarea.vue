<template>
  <div class="tag-textarea-wrapper">
    <div class="var-input-row">
      <el-input ref="inputRef" v-model="val" type="textarea" :placeholder="placeholder" :disabled="disabled"
        :rows="rows" size="small" style="width:100%" />
      <el-button v-if="templateId" size="small" :icon="Coin" @click="showBrowser = true" title="Browse variables" style="align-self:flex-start;margin-top:2px" />
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
import VariableBrowser from '/@/views/apps/opsflow/components/VariableBrowser.vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  rows?: number
  templateId?: number | null
  nodeId?: string
  tagCode?: string
}>(), { modelValue: '', rows: 3 })
const emit = defineEmits(['update:modelValue'])

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const inputRef = ref<any>(null)
const showBrowser = ref(false)

function onVarInsert(key: string) {
  const refStr = `\${${key}}`
  const inputEl = inputRef.value?.$el?.querySelector('textarea')
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
.tag-textarea-wrapper { width: 100%; }
.var-input-row { display: flex; gap: 4px; align-items: stretch; }
</style>
