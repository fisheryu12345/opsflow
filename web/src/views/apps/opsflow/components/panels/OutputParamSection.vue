<template>
  <div class="panel-section" v-if="schema.length">
    <div class="section-title">{{ $t("message.properties.outputParams") }}</div>
    <div class="output-list">
      <div v-for="out in schema" :key="out.name || out.key" class="output-row">
        <div class="output-top">
          <code class="output-key">{{ out.name || out.key }}</code>
          <el-tag size="small" :type="outputTypeTag(out.type)" effect="plain">{{ out.type }}</el-tag>
          <span class="output-actions">
            <el-button size="small" text @click="copyRef(nodeId + '.' + (out.name || out.key))">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
            <el-button size="small" text type="success" @click="promoteOutput(out)">
              <el-icon><Upload /></el-icon> Promote
            </el-button>
          </span>
        </div>
        <span class="output-desc" v-if="out.description">{{ out.description }}</span>
        <div class="output-ref-hint">
          Reference: <code>$\{{ nodeId }}.{{ out.name || out.key }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessageBox, ElMessage } from 'element-plus'
import { CopyDocument, Upload } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { HookVariable } from '../../api/templates'

const { t } = useI18n()

const props = defineProps<{
  schema: any[]
  nodeId: string
  templateId?: number | null
}>()

function outputTypeTag(type: string): string {
  const map: Record<string, string> = { string: 'info', int: '', bool: 'success', object: 'warning' }
  return map[type] || 'info'
}

function copyRef(ref: string) {
  navigator.clipboard.writeText('${' + ref + '}')
  ElMessage.success(t('message.opsflowPage.copied'))
}

/** 将节点输出字段提升为全局变量 */
async function promoteOutput(out: any) {
  const fieldName = (out.name || out.key || '').trim()
  if (!props.nodeId || !fieldName) return
  const defaultVarName = fieldName
  try {
    const { value } = await ElMessageBox.prompt(
      'Enter a name for the global variable:',
      'Promote Node Output to Global',
      {
        inputValue: defaultVarName,
        inputPlaceholder: 'Variable name (used as ${name})',
        confirmButtonText: 'Promote',
        cancelButtonText: 'Cancel',
      },
    )
    if (!value || !value.trim()) return
    const varKey = value.trim()
    await HookVariable(props.templateId, {
      var_key: varKey,
      node_id: props.nodeId,
      tag_code: fieldName,
      var_type: 'output',
      description: out.description || fieldName,
    })
    ElMessage.success(`Global variable "${varKey}" created from ${props.nodeId}.${fieldName}`)
  } catch {
    // user cancelled
  }
}
</script>

<style scoped>
@use '/@/styles/global' as *;

.output-list { display: flex; flex-direction: column; gap: 6px; }
.output-row {
  background: #f8f9fb; border-radius: 6px; padding: 10px 12px;
  display: flex; flex-direction: column; gap: 4px;
}
.output-top { display: flex; align-items: center; gap: 6px; }
.output-actions { margin-left: auto; display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.output-key { font-size: 13px; font-weight: 600; color: #409EFF; font-family: monospace; }
.output-desc { font-size: 11px; color: #909399; }
.output-ref-hint { font-size: 11px; color: #909399; }
.output-ref-hint code { color: #67C23A; background: #f0f9eb; padding: 1px 4px; border-radius: 3px; }
</style>
