<template>
  <el-dialog v-model="visible" :title="$t('message.agentPage.execTitle')" width="680px" top="5vh"
    :close-on-click-modal="false" class="opsflow-dialog ag-exec-dialog" @closed="onClosed">
    <div class="ag-exec-body">
      <div class="ag-exec-form">
        <div class="ag-exec-field">
          <label class="ag-exec-label">{{ $t('message.agentPage.execTarget') }}</label>
          <el-tag>{{ target?.hostname }} ({{ target?.ip }})</el-tag>
        </div>
        <div class="ag-exec-field">
          <label class="ag-exec-label">{{ $t('message.agentPage.execScriptType') }}</label>
          <el-select v-model="scriptType" style="width:220px">
            <el-option :label="$t('message.agentPage.scriptTypeShell')" value="shell" />
            <el-option :label="$t('message.agentPage.scriptTypePython')" value="python" />
            <el-option :label="$t('message.agentPage.scriptTypeBat')" value="bat" />
            <el-option :label="$t('message.agentPage.scriptTypePowershell')" value="powershell" />
          </el-select>
        </div>
        <div class="ag-exec-field">
          <label class="ag-exec-label">{{ $t('message.agentPage.execContent') }}</label>
          <el-input v-model="content" type="textarea" :rows="4" :placeholder="$t('message.agentPage.execContentPlaceholder')" />
        </div>
        <div class="ag-exec-field">
          <label class="ag-exec-label">{{ $t('message.agentPage.execTimeout') }}</label>
          <el-input-number v-model="timeout" :min="10" :max="86400" />
        </div>
      </div>

      <transition name="ag-panel-fade">
        <div v-if="result" class="ag-exec-output">
          <div class="ag-exec-output-bar">
            <div class="ag-exec-output-status">
              <el-tag v-if="result.status === 'success'" type="success" size="small" effect="dark">✅ {{ $t('message.agentPage.execSuccess') }}</el-tag>
              <el-tag v-else-if="result.status === 'failed'" type="danger" size="small" effect="dark">❌ {{ $t('message.agentPage.execFailed') }}</el-tag>
              <el-tag v-else type="warning" size="small" effect="dark">⏳ {{ $t('message.agentPage.execRunning') }}</el-tag>
              <span v-if="result.exit_code != null" class="ag-exec-exitcode">{{ $t('message.agentPage.execExitCode') }}: {{ result.exit_code }}</span>
            </div>
          </div>
          <div class="ag-exec-output-body">
            <div v-if="result.stdout" class="ag-exec-stdout">{{ result.stdout }}</div>
            <div v-if="result.stderr" class="ag-exec-stderr">{{ result.stderr }}</div>
            <div v-if="running" class="ag-exec-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>{{ $t('message.agentPage.execRunning') }}</span>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <template #footer>
      <div class="ag-exec-footer">
        <el-button plain @click="visible = false">{{ $t('message.agentPage.cancel') }}</el-button>
        <el-button type="primary" :loading="running" @click="doExec">
          <el-icon v-if="!running"><Promotion /></el-icon>
          {{ $t('message.agentPage.execute') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, Promotion } from '@element-plus/icons-vue'
import * as agentApi from '/@/api/agent'
import type { AgentInstance } from '/@/api/agent'

const { t } = useI18n()

const props = defineProps<{
  modelValue: boolean
  target: AgentInstance | null
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const scriptType = ref('shell')
const content = ref('')
const timeout = ref(3600)
const running = ref(false)
const result = ref<{ status: string; exit_code?: number; stdout: string; stderr: string } | null>(null)

watch(() => props.modelValue, (v) => {
  if (v) {
    content.value = ''
    result.value = null
    running.value = false
  }
})

function doExec() {
  if (!props.target) return
  running.value = true
  result.value = { status: 'pending', stdout: '', stderr: '' }

  agentApi.execCommand({
    agent_id: props.target.agent_id,
    script_type: scriptType.value,
    script_content: content.value,
    timeout: timeout.value,
  }).then((res: any) => {
    const execId = res.data?.exec_id || res.exec_id
    const agentResult = res.data?.agent_result || {}
    running.value = false
    if (agentResult.success) {
      result.value = { status: 'running', stdout: `${t('message.agentPage.msgExecSuccess')} (exec_id: ${execId})\n${t('message.agentPage.execPending')}`, stderr: '' }
    } else {
      result.value = { status: 'failed', stdout: '', stderr: agentResult.error || t('message.agentPage.msgExecFailed') }
    }
    let attempts = 0
    const maxAttempts = Math.ceil((timeout.value || 60) / 2) + 10
    const poll = setInterval(() => {
      attempts++
      agentApi.getTaskList({ search: execId }).then((r: any) => {
        const data = r.data || r; const tasks = data.results || data || []
        const task = tasks.find((t: any) => t.exec_id === execId)
        if (!task || attempts >= maxAttempts) { if (attempts >= maxAttempts) clearInterval(poll); return }
        if (task.status === 'success' || task.status === 'failed') {
          clearInterval(poll)
          agentApi.getTaskResults(task.id).then((r2: any) => {
            const chunks = Array.isArray(r2.data) ? r2.data : Array.isArray(r2) ? r2 : []
            result.value = { status: task.status, exit_code: task.exit_code, stdout: chunks.map((c: any) => c.stdout || '').join('') || '(no output)', stderr: chunks.map((c: any) => c.stderr || '').join('') || '' }
          }).catch(() => { result.value = { status: task.status, exit_code: task.exit_code, stdout: '(no result data)', stderr: '' } })
        }
      }).catch(() => {})
    }, 3000)
  }).catch((err: any) => {
    result.value = { status: 'failed', stdout: '', stderr: err.message || t('message.agentPage.msgExecFailed') }
    running.value = false
  })
}
</script>
