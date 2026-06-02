<template>
  <el-dialog v-model="visible" title="Change Preview" width="85%" top="4vh" class="diff-dialog" destroy-on-close>
    <div v-if="stats" class="diff-stats">
      <span class="diff-stat diff-stat-add">+{{ stats.added }} added</span>
      <span class="diff-stat diff-stat-remove">-{{ stats.removed }} removed</span>
      <span class="diff-stat diff-stat-modify">~{{ stats.modified }} modified</span>
    </div>

    <div class="diff-container">
      <div class="diff-panel">
        <div class="diff-panel-header">
          <el-icon size="14"><ChatDotSquare /></el-icon>
          <span>AI Original</span>
        </div>
        <div class="diff-content-wrapper">
          <div class="diff-line-nums">
            <div v-for="n in aiLines.length" :key="n" class="diff-line-num">{{ n }}</div>
          </div>
          <pre class="diff-content"><code v-for="(line, i) in aiLines" :key="i" :class="lineClass(line)">{{ line.text }}</code></pre>
        </div>
      </div>
      <div class="diff-divider" />
      <div class="diff-panel">
        <div class="diff-panel-header">
          <el-icon size="14"><EditPen /></el-icon>
          <span>Manual Edit</span>
        </div>
        <div class="diff-content-wrapper">
          <div class="diff-line-nums">
            <div v-for="n in curLines.length" :key="n" class="diff-line-num">{{ n }}</div>
          </div>
          <pre class="diff-content"><code v-for="(line, i) in curLines" :key="i" :class="lineClass(line)">{{ line.text }}</code></pre>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">Cancel</el-button>
      <el-button type="primary" :loading="confirming" @click="onConfirm">
        <el-icon><Check /></el-icon>Confirm & Save
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotSquare, EditPen, Check } from '@element-plus/icons-vue'
import { ConfirmDraft } from '/@/api/opsflow/templates'

const props = defineProps<{
  templateId: number
  aiOriginal: any
  current: any
}>()

const emit = defineEmits<{
  confirmed: []
}>()

const visible = ref(false)
const confirming = ref(false)

interface DiffLine {
  text: string
  type: 'same' | 'add' | 'remove'
}

const aiLines = computed<DiffLine[]>(() => computeDiff(props.aiOriginal, props.current, 'remove'))
const curLines = computed<DiffLine[]>(() => computeDiff(props.current, props.aiOriginal, 'add'))

const stats = computed(() => {
  const ai = JSON.stringify(props.aiOriginal, null, 2)
  const cur = JSON.stringify(props.current, null, 2)
  if (ai === cur) return null

  const aiNodes = (props.aiOriginal?.nodes || []).length
  const curNodes = (props.current?.nodes || []).length
  const aiEdges = (props.aiOriginal?.edges || []).length
  const curEdges = (props.current?.edges || []).length

  return {
    added: Math.max(0, (curNodes - aiNodes) + (curEdges - aiEdges)),
    removed: Math.max(0, (aiNodes - curNodes) + (aiEdges - curEdges)),
    modified: ai === cur ? 0 : 1,
  }
})

function computeDiff(base: any, compare: any, matchType: 'add' | 'remove'): DiffLine[] {
  const baseStr = JSON.stringify(base, null, 2) || ''
  const compareStr = JSON.stringify(compare, null, 2) || ''

  const baseLines = baseStr.split('\n')
  const compLines = compareStr.split('\n')

  const compSet = new Set(compLines)
  return baseLines.map(line => ({
    text: line,
    type: compSet.has(line) ? 'same' as const : matchType as DiffLine['type'],
  }))
}

function lineClass(line: DiffLine): string {
  if (line.type === 'remove') return 'diff-line diff-line-remove'
  if (line.type === 'add') return 'diff-line diff-line-add'
  return ''
}

function show() {
  visible.value = true
}

async function onConfirm() {
  confirming.value = true
  try {
    await ConfirmDraft(props.templateId)
    ElMessage.success('Confirmed and saved')
    visible.value = false
    emit('confirmed')
  } catch (e) {
    ElMessage.error('Failed to confirm')
  } finally {
    confirming.value = false
  }
}

defineExpose({ show })
</script>

<style lang="scss" scoped>
@import '../styles/opsflow-global';

.diff-dialog :deep(.el-dialog__header) { @include of-dialog-header; }
.diff-dialog :deep(.el-dialog__body) { padding: 0; }
.diff-dialog :deep(.el-dialog__footer) { @include of-dialog-footer; }
.diff-stats {
  display: flex;
  gap: 16px;
  padding: 12px 20px;
  background: $of-bg-card;
  border-bottom: 1px solid $of-border-default;
}
.diff-stat {
  font-size: 13px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 10px;
}
.diff-stat-add {
  color: #67c23a;
  background: $of-bg-success;
}
.diff-stat-remove {
  color: #f56c6c;
  background: $of-bg-danger;
}
.diff-stat-modify {
  color: #e6a23c;
  background: $of-bg-warning;
}
.diff-container {
  display: flex;
  min-height: 450px;
  max-height: 65vh;
}
.diff-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.diff-panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: $of-bg-header;
  border-bottom: 1px solid $of-border-default;
  font-size: 13px;
  font-weight: 600;
  color: $of-text-secondary;
  flex-shrink: 0;
}
.diff-content-wrapper {
  flex: 1;
  display: flex;
  overflow: auto;
}
.diff-line-nums {
  user-select: none;
  text-align: right;
  padding: 10px 0;
  border-right: 1px solid $of-border-default;
  background: #fafafa;
  flex-shrink: 0;
}
.diff-line-num {
  font-size: 11px;
  line-height: 1.6;
  padding: 0 8px;
  color: $of-text-placeholder;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}
.diff-content {
  margin: 0;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  flex: 1;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}
.diff-line {
  display: block;
  white-space: pre;
}
.diff-line-remove {
  background: $of-bg-danger;
  color: #f56c6c;
}
.diff-line-add {
  background: $of-bg-success;
  color: #67c23a;
}
.diff-divider {
  width: 1px;
  background: $of-border-default;
  flex-shrink: 0;
}
</style>
