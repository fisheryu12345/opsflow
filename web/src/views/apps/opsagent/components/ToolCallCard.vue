<template>
  <div class="tool-call-card" :class="{ 'tool-success': isSuccess, 'tool-error': !isSuccess }">
    <div class="tool-call-header" @click="expanded = !expanded">
      <span class="tool-icon">{{ isSuccess ? '✅' : '❌' }}</span>
      <span class="tool-name">{{ tool.tool_name }}</span>
      <span class="tool-status" :class="isSuccess ? 'text-success' : 'text-danger'">
        {{ isSuccess ? `exit: ${tool.result || 0}` : 'failed' }}
      </span>
      <span class="tool-expand-btn">{{ expanded ? '收起 ▲' : '展开 ▼' }}</span>
    </div>
    <div v-if="expanded" class="tool-call-body">
      <div v-if="hasArgs" class="tool-section">
        <div class="section-label">参数</div>
        <div class="section-content">
          <div v-for="(val, key) in tool.arguments" :key="key" class="arg-row">
            <span class="arg-key">{{ key }}:</span>
            <span class="arg-val">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
          </div>
        </div>
      </div>
      <div v-if="tool.result" class="tool-section">
        <div class="section-label">输出</div>
        <pre class="section-content output-text">{{ tool.result }}</pre>
      </div>
      <div v-if="tool.error" class="tool-section">
        <div class="section-label text-danger">错误</div>
        <pre class="section-content error-text">{{ tool.error }}</pre>
      </div>
      <div v-if="tool.assessment" class="tool-section">
        <div class="section-label">安全评估</div>
        <div class="section-content">
          <span>风险分: {{ tool.assessment.score }} / 决策: {{ tool.assessment.decision }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCallLog } from './useConsole'

const props = defineProps<{ tool: ToolCallLog }>()
const expanded = ref(false)

const isSuccess = computed(() => props.tool.status !== 'error' && !props.tool.error)
const hasArgs = computed(() => {
  return props.tool.arguments && Object.keys(props.tool.arguments).length > 0
})
</script>

<style scoped>
.tool-call-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
  background: #fff;
}
.tool-call-card.tool-success { border-left: 3px solid #67c23a; }
.tool-call-card.tool-error { border-left: 3px solid #f56c6c; }

.tool-call-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  background: #f5f7fa;
  font-size: 13px;
}
.tool-call-header:hover { background: #ecf5ff; }

.tool-icon { font-size: 14px; }
.tool-name { font-weight: 600; color: #303133; flex: 1; }
.tool-status { font-size: 12px; }
.tool-expand-btn { font-size: 12px; color: #909399; }

.tool-call-body { padding: 8px 12px; }
.tool-section { margin-bottom: 8px; }
.tool-section:last-child { margin-bottom: 0; }
.section-label { font-size: 12px; color: #909399; margin-bottom: 4px; font-weight: 600; }
.section-content { font-size: 13px; color: #303133; }
.output-text {
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Courier New', monospace;
}
.error-text {
  background: #fef0f0;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
  font-size: 12px;
  color: #f56c6c;
  white-space: pre-wrap;
}
.arg-row {
  display: flex;
  gap: 8px;
  padding: 2px 0;
  font-size: 12px;
}
.arg-key { color: #409eff; font-weight: 600; min-width: 80px; }
.arg-val { color: #303133; word-break: break-all; }
.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
</style>
