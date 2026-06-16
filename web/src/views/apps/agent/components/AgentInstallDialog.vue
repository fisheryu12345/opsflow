<template>
  <el-dialog v-model="visible" :title="$t('message.agentPage.installTitle')" width="680px" class="opsflow-dialog">
    <!-- Mode selector -->
    <el-radio-group v-model="mode" style="margin-bottom:20px;width:100%">
      <el-radio-button value="auto" style="width:50%">
        <el-icon style="vertical-align:-2px;margin-right:4px"><UploadFilled /></el-icon>
        {{ $t('message.agentPage.installModeAuto') }}
        <div style="font-size:11px;opacity:0.6;font-weight:normal">{{ $t('message.agentPage.installModeAutoDesc') }}</div>
      </el-radio-button>
      <el-radio-button value="manual" style="width:50%">
        <el-icon style="vertical-align:-2px;margin-right:4px"><Document /></el-icon>
        {{ $t('message.agentPage.installModeManual') }}
        <div style="font-size:11px;opacity:0.6;font-weight:normal">{{ $t('message.agentPage.installModeManualDesc') }}</div>
      </el-radio-button>
    </el-radio-group>

    <el-steps :active="step" finish-status="success" simple>
      <el-step :title="$t('message.agentPage.installStepHosts')" />
      <el-step :title="$t('message.agentPage.installStepConfig')" />
      <el-step v-if="mode === 'auto'" :title="$t('message.agentPage.installProgress')" />
    </el-steps>

    <!-- Step 0: Select hosts -->
    <div v-if="step === 0" style="margin-top:20px">
      <el-input v-model="hosts" type="textarea" :rows="4" :placeholder="$t('message.agentPage.installHostsPlaceholder')" />
    </div>

    <!-- Step 1: Configure -->
    <div v-if="step === 1" style="margin-top:20px">
      <el-form :label-width="110" v-if="mode === 'auto'">
        <el-form-item :label="$t('message.agentPage.installSshAccount')">
          <el-input v-model="account" :placeholder="$t('message.agentPage.installSshAccountPlaceholder')" style="width:200px" />
        </el-form-item>
        <el-form-item :label="$t('message.agentPage.installSshPassword')">
          <el-input v-model="password" type="password" show-password :placeholder="$t('message.agentPage.installSshPasswordPlaceholder')" style="width:300px" />
        </el-form-item>
        <el-form-item :label="$t('message.agentPage.installSshKey')">
          <el-input v-model="sshKey" type="textarea" :rows="3" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;..." style="width:400px" />
        </el-form-item>
        <el-form-item :label="$t('message.agentPage.installAgentVersion')">
          <el-select v-model="agentVersion">
            <el-option :label="$t('message.agentPage.latestVersion')" value="1.0.0" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="mode === 'manual'">
        <el-alert :title="$t('message.agentPage.installCmdTitle')" type="info" :closable="false" />
        <div class="ag-cmd-block">
          curl -fsSL https://agent.example.com/install.sh | bash -s -- --token=AUTO_{{ token }}
        </div>
      </div>
    </div>

    <!-- Step 2 (auto only): Progress -->
    <div v-if="step === 2 && mode === 'auto'" style="margin-top:20px">
      <div v-for="(r, hi) in results" :key="hi" style="margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:8px">
          <el-icon v-if="r.status === 'success'" color="#67C23A"><SuccessFilled /></el-icon>
          <el-icon v-else-if="r.status === 'failed'" color="#F56C6C"><RemoveFilled /></el-icon>
          <el-icon v-else class="is-loading" color="#409EFF"><Loading /></el-icon>
          <strong>{{ r.host }}</strong>
          <el-tag v-if="r.status === 'success'" type="success" size="small">OK</el-tag>
          <el-tag v-else-if="r.status === 'failed'" type="danger" size="small">FAIL</el-tag>
          <el-tag v-else type="info" size="small">{{ $t('message.agentPage.installProgressing') }}</el-tag>
        </div>
        <div v-if="r.status === 'failed'" style="font-size:12px;color:#F56C6C;margin-left:28px">{{ r.error || $t('message.agentPage.installUnknownError') }}</div>
      </div>
      <div v-if="running" style="text-align:center;margin-top:16px">
        <el-icon class="is-loading"><Loading /></el-icon> {{ $t('message.agentPage.installProgressing') }}
      </div>
    </div>

    <template #footer>
      <el-button v-if="step > 0 && !running" @click="step--">{{ $t('message.agentPage.prevStep') }}</el-button>
      <el-button v-if="step < 1" type="primary" @click="step++">{{ $t('message.agentPage.nextStep') }}</el-button>
      <el-button v-if="step === 1 && mode === 'auto'" type="primary" :loading="running" @click="doInstall">
        {{ $t('message.agentPage.batchInstall') }}
      </el-button>
      <el-button v-if="step === 1 && mode === 'manual'" type="primary" @click="reset()">
        {{ $t('message.agentPage.finish') }}
      </el-button>
      <el-button v-if="step === 2 && mode === 'auto'" type="primary" @click="reset()">
        {{ $t('message.agentPage.finish') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, SuccessFilled, RemoveFilled, Loading } from '@element-plus/icons-vue'
import * as agentApi from '/@/api/agent'

const { t } = useI18n()

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; installed: [] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const mode = ref<'auto' | 'manual'>('auto')
const step = ref(0)
const hosts = ref('')
const account = ref('root')
const password = ref('')
const sshKey = ref('')
const agentVersion = ref('1.0.0')
const token = ref('')
const running = ref(false)
type InstallResult = { host: string; status: 'pending' | 'success' | 'failed'; error?: string }
const results = ref<InstallResult[]>([])

function reset() {
  visible.value = false
  step.value = 0
  results.value = []
  running.value = false
}

function doInstall() {
  const hostList = hosts.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (!hostList.length) {
    ElMessage.warning(t('message.agentPage.installNeedHosts'))
    return
  }
  running.value = true
  results.value = hostList.map(h => ({ host: h, status: 'pending' as const, error: t('message.agentPage.installPending') }))
  step.value = 2

  agentApi.pushInstall({
    hosts: hostList,
    username: account.value || 'root',
    password: password.value,
    ssh_key: sshKey.value,
    agent_version: agentVersion.value,
    server_host: window.location.hostname,
  }).then((res: any) => {
    const data = res.data || res
    const respResults = data.results || {}
    results.value = hostList.map(h => {
      const r = respResults[h]
      if (!r) return { host: h, status: 'failed' as const, error: t('message.agentPage.installNoResult') }
      const errMsg = r.stderr || r.error || r.message || r.stdout || ''
      return {
        host: h,
        status: r.success ? ('success' as const) : ('failed' as const),
        error: errMsg.trim(),
      }
    })
    const okCount = results.value.filter(r => r.status === 'success').length
    const failCount = results.value.length - okCount
    if (failCount === 0) {
      ElMessage.success(t('message.agentPage.installAllSuccess', { okCount, total: hostList.length }))
    } else {
      ElMessage.warning(t('message.agentPage.installPartial', { okCount, failCount }))
    }
    emit('installed')
  }).catch((err: any) => {
    results.value = hostList.map(h => ({ host: h, status: 'failed' as const, error: err.message || t('message.agentPage.installReqFailed') }))
  }).finally(() => {
    running.value = false
  })
}
</script>
