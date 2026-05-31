<template>
  <div class="variable-input">
    <div class="var-input-row">
      <el-input ref="inputRef" v-model="val" :placeholder="placeholder" :disabled="disabled" size="small" style="width:100%" />
      <el-button size="small" :icon="Coin" @click="showBrowser = true" title="Browse variables" :disabled="!templateId" />
    </div>
    <div class="var-actions">
      <div class="var-hint" v-if="val && val.includes('${')">
        <el-tag size="small" type="warning" effect="light" round>
          <el-icon style="margin-right:2px"><WarningFilled /></el-icon>Variable reference
        </el-tag>
      </div>
      <el-button v-if="nodeId && tagCode && templateId && !hooked" size="small" text type="primary" @click="onHook">
        <el-icon><Link /></el-icon> Promote
      </el-button>
      <el-tag v-if="hooked" size="small" type="success" effect="light" round>Global</el-tag>
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
import { WarningFilled, Coin, Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { HookVariable } from '/@/api/opsflow/templates'
import VariableBrowser from '/@/views/apps/opsflow/components/VariableBrowser.vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  templateId?: number | null
  nodeId?: string
  tagCode?: string
  hooked?: boolean
}>(), { modelValue: '' })
const emit = defineEmits(['update:modelValue', 'hook'])

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const inputRef = ref<any>(null)
const showBrowser = ref(false)

function onVarInsert(key: string) {
  const refStr = `\${${key}}`
  // Try to insert at cursor position
  const inputEl = inputRef.value?.$el?.querySelector('input') || inputRef.value?.$el?.querySelector('textarea')
  if (inputEl) {
    const start = inputEl.selectionStart ?? val.value.length
    const end = inputEl.selectionEnd ?? val.value.length
    const newVal = val.value.substring(0, start) + refStr + val.value.substring(end)
    emit('update:modelValue', newVal)
  } else {
    emit('update:modelValue', (val.value || '') + refStr)
  }
}

async function onHook() {
  if (!props.templateId || !props.nodeId || !props.tagCode) return
  const varKey = `\${${props.tagCode}}`
  try {
    await HookVariable(props.templateId, {
      var_key: varKey,
      node_id: props.nodeId,
      tag_code: props.tagCode,
      var_type: 'input',
    })
    ElMessage.success('Variable promoted to global')
    emit('hook', { key: varKey, value: val.value })
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Hook failed')
  }
}
</script>

<style scoped>
.variable-input { display: flex; flex-direction: column; gap: 2px; }
.var-input-row { display: flex; gap: 4px; align-items: center; }
.var-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.var-hint { display: flex; }
</style>
