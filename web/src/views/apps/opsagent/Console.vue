<template>
  <div class="console-page">
    <!-- Hero Section -->
    <div v-if="!embedded" class="console-hero">
      <div class="console-hero-bg" />
      <div class="console-hero-inner">
        <div class="console-hero-left">
          <h1 class="console-hero-title">OpsAgent Console</h1>
          <p class="console-hero-subtitle">Execute ops tasks via natural language</p>
        </div>
        <div class="console-hero-spacer" />
        <div class="console-hero-stats">
          <div class="console-stat-item"><span class="console-stat-value">{{ history.length }}</span><span class="console-stat-label">History</span></div>
          <div class="console-stat-divider" />
          <div class="console-stat-item"><span class="console-stat-value">{{ toolCount }}</span><span class="console-stat-label">Tools</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="console-body">
      <!-- Input Card -->
      <div class="console-input-card">
        <div class="console-input-row">
          <el-input v-model="input" type="textarea" :rows="2"
            placeholder="Describe your ops task, e.g. 'Check disk usage on all servers'"
            :disabled="running" class="console-input"
            @keydown.enter.prevent="handleExecuteClick" />
          <el-button type="primary" :loading="running" :disabled="running || (!canExecute ? false : !input.trim())"
            class="console-exec-btn" size="large" @click="handleExecuteClick">
            <template v-if="!canExecute && !running">🔒 </template>
            {{ running ? 'Executing...' : canExecute ? 'Execute' : 'No Permission' }}
          </el-button>
        </div>
      </div>

      <!-- Running State -->
      <div v-if="running" class="console-card console-running">
        <div class="console-running-inner">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <span>🤖 Processing your request...</span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error && !running" class="console-card">
        <el-alert :title="error" type="error" show-icon :closable="false" />
      </div>

      <!-- Result -->
      <div v-if="result && !running" class="console-card console-result">
        <div class="console-result-header">
          <span class="console-result-title">📋 Result</span>
          <span class="console-result-sid">Session: {{ result.session_id }}</span>
        </div>
        <div v-if="result.tool_calls && result.tool_calls.length > 0" class="console-tools-section">
          <div class="console-section-title">Tool Calls ({{ result.tool_calls.length }})</div>
          <ToolCallCard v-for="(tc, i) in result.tool_calls" :key="i" :tool="tc" />
        </div>
        <div v-if="result.output" class="console-output">
          <div class="console-section-title">Output</div>
          <div class="console-output-content">{{ result.output }}</div>
        </div>
      </div>

      <!-- History -->
      <div v-if="history.length > 1" class="console-card console-history">
        <div class="console-section-title">Execution History</div>
        <div class="console-history-list">
          <div v-for="(item, i) in history.slice(1)" :key="i" class="console-history-item" @click="loadHistory(item)">
            <span class="console-h-icon">{{ item.result ? '✅' : '❌' }}</span>
            <span class="console-h-text">{{ item.input }}</span>
            <span class="console-h-sid">{{ item.result?.session_id || '' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
import { computed, withDefaults } from 'vue'
import { usePermissionStore } from '/@/stores/permission'

const permissionStore = usePermissionStore()

interface BtnPerms {
  [key: string]: boolean
}
const props = withDefaults(defineProps<{ embedded?: boolean; btnPerms?: BtnPerms }>(), { embedded: false, btnPerms: () => ({}) })
import ToolCallCard from './components/ToolCallCard.vue'
import { useConsole } from './useConsole'

const { input, running, result, error, history, execute, loadHistory } = useConsole()

const canExecute = computed(() => props.btnPerms?.execute !== false)

function handleExecuteClick() {
  if (!canExecute.value) {
    permissionStore.requestPerm('Execute Task', 'opsagent:console:execute')
    return
  }
  if (!input.value.trim() || running.value) return
  execute()
}

const toolCount = computed(() => {
  if (result?.tool_calls) return result.tool_calls.length
  return 0
})
</script>

<style scoped>
.console-page { background: transparent; overflow: visible; }

/* ===== Hero ===== */
.console-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.console-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.console-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.console-hero-left { flex: 0 0 auto; }
.console-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.console-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.console-hero-spacer { flex: 1 1 auto; }
.console-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.console-stat-item { text-align: center; padding: 0 14px; }
.console-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.console-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.console-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.console-body { padding: 0 16px 24px; }

/* ===== Shared card style ===== */
.console-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; margin-bottom: 16px; }

/* ===== Input ===== */
.console-input-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); padding: 20px; margin-top: 16px; margin-bottom: 16px; position: relative; overflow: hidden; }
.console-input-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.console-input-row { display: flex; gap: 12px; align-items: flex-start; }
.console-input { flex: 1; }
.console-input :deep(.el-textarea__inner) { border-radius: 10px; padding: 10px 14px; font-size: 14px; }
.console-exec-btn { min-width: 120px; height: 44px; border-radius: 10px; font-weight: 600; }

/* ===== Running ===== */
.console-running { padding: 32px 20px; text-align: center; }
.console-running-inner { display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 16px; color: #606266; }

/* ===== Result ===== */
.console-result { padding: 20px; }
.console-result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }
.console-result-title { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.console-result-sid { font-size: 12px; color: #909399; font-family: 'Courier New', monospace; }
.console-tools-section { margin-bottom: 16px; }
.console-section-title { font-size: 13px; font-weight: 600; color: #606266; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #f5f5f5; }
.console-output { }
.console-output-content { background: #f5f7fa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 16px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }

/* ===== History ===== */
.console-history { padding: 20px; }
.console-history-list { max-height: 240px; overflow-y: auto; }
.console-history-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; border-radius: 8px; font-size: 13px; transition: background .15s; }
.console-history-item:hover { background: #f5f7fa; }
.console-h-icon { font-size: 14px; }
.console-h-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #303133; }
.console-h-sid { font-size: 11px; color: #c0c4cc; font-family: 'Courier New', monospace; }
</style>
