<template>
  <div class="variable-input">
    <div class="var-input-row">
      <el-input ref="inputRef" v-model="val" :placeholder="placeholder" :disabled="disabled" size="small" />
      <el-button size="small" :icon="BrowseIcon" @click="showBrowser = true" title="Browse variables" :disabled="!templateId" class="browse-btn" />
    </div>
    <div class="var-actions">
      <div class="var-hint" v-if="val && val.includes('${')">
        <el-tag size="small" type="warning" effect="light" round>
          <el-icon style="margin-right:2px"><WarningFilled /></el-icon>Variable reference
        </el-tag>
      </div>
      <el-button v-if="nodeId && tagCode && templateId && !hooked" size="small" text type="primary" class="promote-text-btn" @click="onHook">
        <el-icon><PromoteIcon /></el-icon> Promote
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
import { WarningFilled, FolderOpened, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { HookVariable } from '/@/views/apps/opsflow/api/templates'
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

const BrowseIcon = FolderOpened
const PromoteIcon = Upload

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
.var-input-row .el-input { flex: 1; min-width: 0; }
.browse-btn { flex-shrink: 0; color: #909399; transition: color 0.2s; }
.browse-btn:hover { color: #409EFF; }
.var-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.promote-text-btn { margin-left: auto; flex-shrink: 0; }
.var-hint { display: flex; }
</style>
