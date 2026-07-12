<template>
  <div>
    <!-- Filter bar -->
    <div class="itsm-filter-bar">
      <div class="itsm-filter-tabs">
        <div class="itsm-tab" :class="{ active: wfFilter === '' }" @click="wfFilter = ''; loadWorkflows()">
          <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterAll') }}
        </div>
        <div class="itsm-tab" :class="{ active: wfFilter === 'change' }" @click="wfFilter = 'change'; loadWorkflows()">
          <span class="itsm-tab-dot" style="background:#E6A23C" />{{ $t('message.itsmPage.changes') }}
        </div>
        <div class="itsm-tab" :class="{ active: wfFilter === 'incident' }" @click="wfFilter = 'incident'; loadWorkflows()">
          <span class="itsm-tab-dot" style="background:#F56C6C" />{{ $t('message.itsmPage.incidents') }}
        </div>
      </div>
      <div class="itsm-filter-actions">
        <el-button v-can="'itsm:workflow:create'" size="small" type="primary" @click="showAICreate = true">
          <el-icon><MagicStick /></el-icon> {{ $t('message.itsmPage.aiCreate') }}
        </el-button>
        <el-button :icon="Refresh" size="small" text @click="loadWorkflows" :loading="loading">{{ $t('message.itsmPage.refresh') }}</el-button>
      </div>
    </div>

    <div class="itsm-wf-grid">
      <div v-for="wf in workflows" :key="wf.id" class="itsm-wf-card">
        <div class="itsm-wf-card-inner">
          <div class="itsm-wf-card-header">
            <span class="itsm-wf-type-tag" :class="'wf-type-' + wf.itsm_type">{{ wf.itsm_type }}</span>
            <el-tag v-if="wf.is_draft" size="small" type="warning">{{ $t('message.itsmPage.filterDraft') }}</el-tag>
            <el-tag v-else size="small" type="success">{{ $t('message.itsmPage.published') }}</el-tag>
          </div>
          <div class="itsm-wf-name">{{ wf.name }}</div>
          <div class="itsm-wf-desc" v-if="wf.description">{{ wf.description }}</div>
          <div class="itsm-wf-meta">
            <span>{{ wf.created_by || '-' }}</span>
            <span>{{ wf.create_datetime || '' }}</span>
          </div>
          <div class="itsm-wf-actions">
            <el-button v-if="wf.is_draft" v-can="'itsm:workflow:deploy'" size="small" text type="success" @click="onDeployWorkflow(wf)">
              <el-icon><Upload /></el-icon> {{ $t('message.itsmPage.deploy') }}
            </el-button>
            <el-button v-can="'itsm:workflow:design'" size="small" text @click="emit('openDesigner', wf.id)">
              <el-icon><Setting /></el-icon> {{ $t('message.itsmPage.design') }}
            </el-button>
            <el-button size="small" text @click="onOpenVersions(wf)">
              <el-icon><Clock /></el-icon> {{ $t('message.itsmPage.version') }}
            </el-button>
            <el-button v-can.admin="'itsm:workflow:delete'" size="small" text type="danger" @click="onDeleteWorkflow(wf)">
              <el-icon><Delete /></el-icon> {{ $t('message.itsmPage.delete') }}
            </el-button>
          </div>
        </div>
      </div>
      <div v-if="!workflows.length && !loading" class="itsm-wf-empty">
        <el-empty :description="$t('message.itsmPage.noWorkflows')" :image-size="50" />
      </div>
    </div>

    <!-- AI Create dialog -->
    <el-dialog v-model="showAICreate" :title="$t('message.aiCreate.title')" width="620px" top="5vh" class="itsm-dialog">
      <el-form label-position="top">
        <el-form-item :label="$t('message.aiCreate.descLabel')">
          <el-input v-model="aiDescription" type="textarea" :rows="4"
            :placeholder="$t('message.aiCreate.descPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.ticketCreate.itsmType')">
          <el-select v-model="aiType" style="width:100%">
            <el-option :label="$t('message.ticketCreate.changeRequest')" value="change" />
            <el-option :label="$t('message.ticketCreate.eventTicket')" value="incident" />
            <el-option :label="$t('message.ticketCreate.serviceRequest')" value="request" />
            <el-option :label="$t('message.ticketCreate.problem')" value="problem" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="aiResult" class="itsm-ai-preview g-fade-in-up">
        <div class="itsm-ai-preview-header">{{ $t('message.aiCreate.generatePreview') }}</div>
        <div class="itsm-ai-flow">
          <span v-for="(s, idx) in aiResult.states?.filter((s: any) => s.type !== 'START' && s.type !== 'END') || []" :key="idx" class="itsm-ai-node">
            <span class="itsm-ai-node-badge" :class="'node-' + (s.type || '').toLowerCase()">{{ s.type }}</span>
            {{ s.name }}
            <el-icon v-if="Number(idx) < arrowCount(aiResult)"><ArrowRight /></el-icon>
          </span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAICreate = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button v-if="!aiResult" type="primary" :loading="aiLoading" @click="onAIGenerate">
          <el-icon><MagicStick /></el-icon> {{ $t('message.aiCreate.oneClick') }}
        </el-button>
        <el-button v-else type="success" :loading="savingWf" @click="onSaveAIWorkflow">
          <el-icon><Check /></el-icon> {{ $t('message.aiCreate.saveTemplate') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Version history dialog -->
    <el-dialog v-model="showVersionDialog" :title="$t('message.itsmPage.versionHistory', { name: versionDialogWf?.name || '' })" width="520px" top="10vh" destroy-on-close @closed="onVersionDialogClosed">
      <div v-loading="versionLoading" style="min-height: 80px;">
        <div v-if="!versionLoading && !versionList.length" style="text-align:center;padding:24px;color:#909399;">{{ $t('message.itsmPage.noVersions') }}</div>
        <div v-for="ver in versionList" :key="ver.id" style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0;">
          <div>
            <el-tag size="small" type="info" style="margin-right:8px;">v{{ ver.version }}</el-tag>
            <span style="font-size:12px;color:#909399;">{{ ver.create_datetime }}</span>
          </div>
          <div>
            <el-button size="small" text type="warning" @click="onRollbackClick(ver)">{{ $t('message.itsmPage.rollback') }}</el-button>
            <el-button size="small" text type="danger" @click="onDeleteVersion(ver)">{{ $t('message.itsmPage.delete') }}</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showVersionDialog = false">{{ $t('message.itsmPage.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- Rollback dialog -->
    <el-dialog v-model="showRollbackDialog" :title="$t('message.itsmPage.rollbackConfirm')" width="440px" top="25vh" destroy-on-close>
      <div style="padding: 8px 0; font-size: 14px;">
        <p style="margin-bottom: 12px;">{{ $t('message.itsmPage.rollbackToVersion', { version: rollbackTarget?.version }) }}</p>
        <p style="color: #909399; font-size: 12px; margin-bottom: 0;">{{ $t('message.itsmPage.rollbackHint') }}</p>
      </div>
      <template #footer>
        <el-button @click="showRollbackDialog = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="warning" :loading="rollbackLoading" @click="confirmRollback">{{ $t('message.itsmPage.confirmRollback') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, MagicStick, Upload, Setting, Clock, Delete, ArrowRight, Check } from '@element-plus/icons-vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { workflowApi, workflowVersionApi, stateApi, transitionApi, DeployWorkflow, AIGenerateWorkflow, RollbackVersion } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const emit = defineEmits<{ openDesigner: [wfId: number] }>()
const { t } = useI18n()
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const workflows = ref<any[]>([])
const wfFilter = ref('')

// AI create
const showAICreate = ref(false)
const aiDescription = ref('')
const aiType = ref('change')
const aiLoading = ref(false)
const aiResult = ref<any>(null)
const savingWf = ref(false)

// Version dialog
const showVersionDialog = ref(false)
const versionDialogWf = ref<any>(null)
const versionList = ref<any[]>([])
const versionLoading = ref(false)

// Rollback dialog
const showRollbackDialog = ref(false)
const rollbackTarget = ref<any>(null)
const rollbackLoading = ref(false)

function arrowCount(result: any): number {
  return ((result.states?.filter((s: any) => s.type !== 'START' && s.type !== 'END') || []).length || 1) - 1
}

async function loadWorkflows() {
  loading.value = true
  try {
    const params: any = {}
    if (wfFilter.value) params.itsm_type = wfFilter.value
    const res = await workflowApi.list(params)
    workflows.value = res?.results || res?.data || res || []
    reportStats()
  } finally { loading.value = false }
}

function reportStats() {
  updateHeroStats([
    { value: workflows.value.length, label: '模板总数' },
    { value: workflows.value.filter((w: any) => !w.is_draft).length, label: '已发布' },
    { value: workflows.value.filter((w: any) => w.is_draft).length, label: '草稿' },
  ])
}

async function onDeployWorkflow(wf: any) {
  const msg = await ElMessageBox.prompt('版本说明（可选）', '部署流程').catch(() => null)
  if (msg === null) return
  try {
    await DeployWorkflow(wf.id, msg?.value || '')
    ElMessage.success('部署成功')
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '部署失败')
  }
}

async function onOpenVersions(wf: any) {
  versionDialogWf.value = wf
  versionList.value = []
  versionLoading.value = true
  showVersionDialog.value = true
  try {
    const res = await workflowVersionApi.list({ workflow: wf.id })
    versionList.value = res?.results || res?.data || []
  } catch { versionList.value = [] }
  finally { versionLoading.value = false }
}

function onVersionDialogClosed() {
  versionDialogWf.value = null
  versionList.value = []
}

function onRollbackClick(ver: any) {
  rollbackTarget.value = ver
  showRollbackDialog.value = true
}

async function confirmRollback() {
  if (!rollbackTarget.value) return
  rollbackLoading.value = true
  try {
    await RollbackVersion(rollbackTarget.value.id)
    ElMessage.success('已回滚并创建新版本')
    showRollbackDialog.value = false
    if (versionDialogWf.value) {
      versionLoading.value = true
      const res = await workflowVersionApi.list({ workflow: versionDialogWf.value.id })
      versionList.value = res?.results || res?.data || []
      versionLoading.value = false
    }
  } catch { ElMessage.error('回滚失败') }
  finally { rollbackLoading.value = false }
}

async function onDeleteVersion(ver: any) {
  try {
    await workflowVersionApi.delete(ver.id)
    ElMessage.success("版本已删除")
    if (versionDialogWf.value) {
      versionLoading.value = true
      const res = await workflowVersionApi.list({ workflow: versionDialogWf.value.id })
      versionList.value = res?.results || res?.data || []
      versionLoading.value = false
    }
  } catch { ElMessage.error("删除失败") }
}

async function onDeleteWorkflow(wf: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除流程模板「${wf.name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await workflowApi.delete(wf.id)
    ElMessage.success('流程模板已删除')
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '删除失败')
  }
}

async function onAIGenerate() {
  if (!aiDescription.value) {
    ElMessage.warning('请输入审批需求描述')
    return
  }
  aiLoading.value = true
  aiResult.value = null
  try {
    const res = await AIGenerateWorkflow(aiDescription.value, aiType.value)
    aiResult.value = res.data || res
  } catch (e: any) {
    ElMessage.error(e?.msg || '生成失败')
  } finally { aiLoading.value = false }
}

async function onSaveAIWorkflow() {
  if (!aiResult.value) return
  savingWf.value = true
  try {
    const wfData = aiResult.value.workflow || {}
    const res = await workflowApi.create({
      name: wfData.name || `AI-${aiType.value}-${Date.now()}`,
      itsm_type: aiType.value,
      description: wfData.description || aiDescription.value,
    })
    const wf = res.data?.data || res.data || res
    for (const state of aiResult.value.states || []) {
      await stateApi.create({ ...state, workflow: wf.id })
    }
    for (const trans of aiResult.value.transitions || []) {
      await transitionApi.create({ ...trans, workflow: wf.id })
    }
    ElMessage.success('流程模板已创建，可在「流程模板」中查看并部署')
    showAICreate.value = false
    aiResult.value = null
    aiDescription.value = ''
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败')
  } finally { savingWf.value = false }
}

onMounted(() => {
  if (props.active) loadWorkflows()
})

watch(() => props.active, (isActive) => {
  if (isActive) {
    if (workflows.value.length === 0) loadWorkflows()
    else reportStats()
  }
})
</script>
