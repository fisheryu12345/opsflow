<template>
  <div class="trading-page">
    <!-- Header -->
    <div class="page-header">
      <div class="page-title">🔧 OpsAgent 运维控制台</div>
      <div class="page-desc">通过自然语言执行运维操作</div>
    </div>

    <!-- Input Area -->
    <div class="section-card input-area">
      <div class="input-row">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="输入运维指令，例如：检查所有服务器的磁盘使用情况"
          :disabled="running"
          @keydown.enter.prevent="execute"
        />
        <el-button type="primary" :loading="running" :disabled="!input.trim() || running" @click="execute" class="execute-btn">
          {{ running ? '执行中...' : '执行' }}
        </el-button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="running" class="section-card running-state">
      <div class="running-indicator">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>🤖 正在执行，请稍候...</span>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error && !running" class="section-card">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>

    <!-- Result Display -->
    <div v-if="result && !running" class="section-card result-area">
      <div class="result-header">
        <span class="result-title">📋 执行结果</span>
        <span class="result-session-id">会话: {{ result.session_id }}</span>
      </div>

      <!-- Tool Calls -->
      <div v-if="result.tool_calls && result.tool_calls.length > 0" class="tool-calls-section">
        <div class="section-subtitle">工具调用 ({{ result.tool_calls.length }})</div>
        <ToolCallCard v-for="(tc, i) in result.tool_calls" :key="i" :tool="tc" />
      </div>

      <!-- Final Output -->
      <div v-if="result.output" class="final-output">
        <div class="section-subtitle">最终输出</div>
        <div class="output-content">{{ result.output }}</div>
      </div>
    </div>

    <!-- History -->
    <div v-if="history.length > 1" class="section-card history-area">
      <div class="section-subtitle">执行历史</div>
      <div class="history-list">
        <div
          v-for="(item, i) in history.slice(1)"
          :key="i"
          class="history-item"
          @click="loadHistory(item)"
        >
          <span class="history-icon">{{ item.result ? '✅' : '❌' }}</span>
          <span class="history-text">{{ item.input }}</span>
          <span class="history-time">{{ item.result?.session_id || '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
import ToolCallCard from './components/ToolCallCard.vue'
import { useConsole } from './useConsole'

const { input, running, result, error, history, execute, loadHistory } = useConsole()
</script>

<style scoped>
.page-header {
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}
.page-desc {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.input-area {
  padding: 16px;
}
.input-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.input-row .el-input {
  flex: 1;
}
.execute-btn {
  min-width: 100px;
  height: 40px;
}

.running-state {
  padding: 24px;
  text-align: center;
}
.running-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 15px;
  color: #606266;
}

.result-area {
  padding: 16px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}
.result-title { font-size: 16px; font-weight: 600; }
.result-session-id { font-size: 12px; color: #909399; }

.tool-calls-section {
  margin-bottom: 16px;
}
.section-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.final-output {
  margin-top: 12px;
}
.output-content {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.history-area {
  padding: 16px;
  margin-top: 16px;
}
.history-list {
  max-height: 200px;
  overflow-y: auto;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
}
.history-item:hover { background: #f5f7fa; }
.history-icon { font-size: 14px; }
.history-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-time { font-size: 12px; color: #909399; }
</style>
