<template>
  <div class="variable-input">
    <div class="var-input-row">
      <el-autocomplete
        ref="inputRef"
        v-model="val"
        :fetch-suggestions="queryVariableSuggestions"
        :placeholder="placeholder"
        :disabled="disabled"
        size="small"
        style="flex:1;min-width:0"
        :trigger-on-focus="hasSuggestions"
        @select="onSuggestionSelect"
        :clearable="clearable"
      >
        <template #default="{ item }">
          <div class="var-suggestion-item">
            <span class="var-suggestion-source" :class="item._sourceType">{{ sourceLabel(item._sourceType) }}</span>
            <span class="var-suggestion-key">{{ item._field }}</span>
            <span v-if="item._nodeLabel" class="var-suggestion-node">{{ item._nodeLabel }}</span>
          </div>
        </template>
      </el-autocomplete>
      <el-button size="small" :icon="BrowseIcon" @click="showBrowser = true" title="Browse variables" :disabled="!templateId" class="browse-btn" />
    </div>
    <div class="var-actions">
      <div class="var-hint" v-if="val && val.includes('${')">
        <el-tag size="small" type="warning" effect="light" round>
          <el-icon style="margin-right:2px"><WarningFilled /></el-icon>Variable reference
        </el-tag>
      </div>
    </div>
    <VariableBrowser
      v-if="templateId"
      v-model="showBrowser"
      :template-id="templateId"
      :graph-nodes="graphNodes"
      :all-graph-nodes="allGraphNodes"
      @insert="onVarInsert"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { WarningFilled, FolderOpened } from '@element-plus/icons-vue'
import VariableBrowser from '/@/views/apps/opsflow/components/panels/VariableBrowser.vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  templateId?: number | null
  nodeId?: string
  tagCode?: string
  availableVars?: any[]
  graphNodes?: any[]
  allGraphNodes?: any[]
}>(), { modelValue: '', availableVars: () => [], graphNodes: () => [], allGraphNodes: () => [] })
const emit = defineEmits(['update:modelValue'])

const BrowseIcon = FolderOpened

const val = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const inputRef = ref<any>(null)
const showBrowser = ref(false)
const hasSuggestions = computed(() => props.availableVars && props.availableVars.length > 0)

function sourceLabel(sourceType: string): string {
  const map: Record<string, string> = {
    node: 'N', global: 'G', project: 'P', system: 'S',
  }
  return map[sourceType] || '?'
}

/** 将 availableVars 转换为 el-autocomplete 建议格式 */
function queryVariableSuggestions(queryString: string, cb: (list: any[]) => void) {
  if (!props.availableVars?.length) {
    cb([])
    return
  }
  const q = queryString.toLowerCase().trim()
  // 在 `${}` 内部搜索：提取已键入的变量名部分
  const innerMatch = queryString.match(/\$\{([^}]*)$/)
  const searchTerm = innerMatch ? innerMatch[1].toLowerCase() : q

  const suggestions = props.availableVars
    .filter(v => {
      const refStr = `${v.source}.${v.field}`.toLowerCase()
      const fieldStr = v.field.toLowerCase()
      return refStr.includes(searchTerm) || fieldStr.includes(searchTerm)
    })
    .slice(0, 20)
    .map(v => ({
      value: `\${${v.source}.${v.field}}`,
      _field: `${v.source}.${v.field}`,
      _sourceType: v.sourceType,
      _nodeLabel: v.sourceType === 'node' ? v.sourceLabel : '',
    }))

  cb(suggestions)
}

function onSuggestionSelect(item: any) {
  const refStr = item.value
  // Try to replace `${partial` at cursor if present, otherwise append
  const inputEl = inputRef.value?.$el?.querySelector('input') || inputRef.value?.$el?.querySelector('textarea')
  if (inputEl) {
    const start = inputEl.selectionStart ?? val.value.length
    const end = inputEl.selectionEnd ?? val.value.length
    const before = val.value.substring(0, start)
    // If cursor is inside ${...}, replace from last `${` to cursor
    const lastDollarBrace = before.lastIndexOf('${')
    if (lastDollarBrace >= 0) {
      const afterCursor = val.value.substring(end)
      const newVal = before.substring(0, lastDollarBrace) + refStr + afterCursor
      emit('update:modelValue', newVal)
      return
    }
    // Otherwise insert at cursor
    const newVal = val.value.substring(0, start) + refStr + val.value.substring(end)
    emit('update:modelValue', newVal)
  } else {
    emit('update:modelValue', (val.value || '') + refStr)
  }
}

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

</script>

<style scoped>
.variable-input { display: flex; flex-direction: column; gap: 2px; }
.var-input-row { display: flex; gap: 4px; align-items: center; }
.var-input-row .el-input { flex: 1; min-width: 0; }
.browse-btn { flex-shrink: 0; color: #909399; transition: color 0.2s; }
.browse-btn:hover { color: #409EFF; }
.var-hint { display: flex; }
.var-suggestion-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.var-suggestion-source {
  font-size: 10px;
  padding: 0 5px;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.var-suggestion-source.node { background: #ecf5ff; color: #409EFF; }
.var-suggestion-source.global { background: #f0f9eb; color: #67C23A; }
.var-suggestion-source.project { background: #fdf6ec; color: #E6A23C; }
.var-suggestion-source.system { background: #f4f4f5; color: #909399; }
.var-suggestion-key {
  font-family: monospace;
  color: #303133;
}
.var-suggestion-node {
  font-size: 10px;
  color: #909399;
  margin-left: auto;
}
</style>
