<template>
  <template v-if="triggerEventTypes.length > 0">
    <el-divider content-position="left">触发器</el-divider>
    <div v-for="et in triggerEventTypes" :key="et" class="trigger-section">
      <div class="trigger-event-label">{{ eventLabel(et) }}</div>
      <div v-if="!triggersByEvent[et]" style="font-size:12px;color:#909399;margin-bottom:4px">暂无配置</div>
      <div v-for="t in (triggersByEvent[et] || [])" :key="t.id" class="trigger-item">
        <div class="trigger-item-header">
          <span>{{ t.name || '(未命名)' }}</span>
          <div>
            <el-switch :model-value="t.is_active" size="small" @change="(v:boolean)=>onToggle(t,v)" />
            <el-button link size="small" type="danger" @click="onDelete(t)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
        <div class="trigger-item-actions">
          <el-tag v-for="a in (t.actions||[])" :key="a.id" size="small"
            :type="a.action_type==='NOTIFY'?'success':a.action_type==='WEBHOOK'?'warning':a.action_type==='OPSFLOW'?'primary':'info'">
            {{ a.action_type === 'NOTIFY' ? '通知' : a.action_type === 'WEBHOOK' ? 'Webhook' : a.action_type === 'OPSFLOW' ? 'OpsFlow' : '改字段' }}
          </el-tag>
        </div>
      </div>
      <el-button size="small" plain @click="onAdd(et)"><el-icon><Plus /></el-icon> 添加</el-button>
    </div>

    <!-- Trigger edit dialog -->
    <el-dialog v-model="editVisible" :title="form.id ? '编辑触发器' : '新建触发器'"
      width="780px" top="3vh" destroy-on-close append-to-body>
      <el-form :model="form" label-width="0" size="small">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item><el-input v-model="form.name" placeholder="触发器名称" clearable /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item><el-switch v-model="form.is_active" active-text="启用" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">动作列表</el-divider>

        <div v-for="(a,i) in form.actions" :key="i" class="trigger-action-card">
          <div class="action-card-head">
            <el-tag size="small" :type="a.action_type==='NOTIFY'?'success':a.action_type==='WEBHOOK'?'warning':a.action_type==='OPSFLOW'?'primary':'info'">{{ i+1 }}</el-tag>
            <el-select v-model="a.action_type" size="small" style="width:130px">
              <el-option v-for="at in actionTypeOptions" :key="at.value" :label="at.label" :value="at.value" />
            </el-select>
            <div style="flex:1" />
            <el-button link size="small" type="danger" @click="form.actions.splice(i,1)">✕</el-button>
          </div>

          <div v-if="a.action_type==='NOTIFY'" class="action-card-body">
            <el-select v-model="a._templateId" size="small" placeholder="选择通知模板" style="width:100%;margin-bottom:6px" clearable
              @change="(v:string)=>onTemplateSelect(i, v, a)">
              <el-option v-for="t in notifTemplateOptions" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
            <el-input v-model="a.config.title_tpl" size="small" placeholder="标题模板" style="margin-bottom:4px" />
          </div>

          <div v-if="a.action_type==='WEBHOOK'" class="action-card-body">
            <div style="display:flex;gap:6px;margin-bottom:4px">
              <el-select v-model="a.config.method" size="small" style="width:90px">
                <el-option v-for="m in ['POST','PUT','GET','DELETE','PATCH']" :key="m" :value="m" :label="m" />
              </el-select>
              <el-input v-model="a.config.url" size="small" placeholder="https://..." style="flex:1" />
            </div>
            <el-input v-model="a.config.body_tpl" size="small" type="textarea" :rows="3" placeholder="请求体模板" style="margin-bottom:4px" />
            <div style="display:flex;gap:6px;align-items:center">
              <span class="cc-label">Content-Type</span>
              <el-input v-model="a.config.content_type" size="small" placeholder="application/json" style="width:150px" />
              <span class="cc-label">超时</span>
              <el-input-number v-model="a.config.timeout" size="small" :min="1" :max="300" style="width:85px" />
              <span style="font-size:12px;color:#909399">s</span>
              <el-checkbox v-model="a.config.ssl_verify" size="small" style="font-size:11px">SSL</el-checkbox>
            </div>
          </div>

          <div v-if="a.action_type==='OPSFLOW'" class="action-card-body">
            <el-input v-model="a.config.flow_id" size="small" placeholder="OpsFlow 流程 ID" />
          </div>

          <div v-if="a.action_type==='MODIFY_FIELD'" class="action-card-body">
            <div style="display:flex;gap:6px">
              <el-input v-model="a.config.field_name" size="small" placeholder="字段名" style="width:140px" />
              <el-input v-model="a.config.field_value" size="small" placeholder="字段值" style="flex:1" />
            </div>
          </div>

          <div class="action-card-foot">
            <el-icon style="font-size:13px"><RefreshRight /></el-icon>
            <span>重试次数</span>
            <el-input-number v-model="a.config.retry_max" size="small" :min="0" :max="10" style="width:70px" />
            <span>次</span>
            <el-input-number v-model="a.config.retry_interval" size="small" :min="5" :max="3600" :step="10" style="width:80px" />
            <span>秒</span>
          </div>
        </div>

        <el-button size="small" type="primary" plain style="width:100%" @click="addAction()">
          <el-icon><Plus /></el-icon> 添加动作
        </el-button>
        <div class="template-hint-trigger">可用变量：${ticket_id}、${ticket_title}、${priority}、${starter_name}、${processor_name}、${field.字段名}</div>
      </el-form>
      <template #footer>
        <el-button @click="editVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </template>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Delete, Plus, RefreshRight } from '@element-plus/icons-vue'
import { triggerApi, notificationTemplateApi } from '/@/api/itsm/index'

const props = defineProps<{
  node: any
  workflowId?: number
}>()

const triggers = ref<any[]>([])
const editVisible = ref(false)
const saving = ref(false)
const form = ref<any>({ id: null, name: '', is_active: true, event_type: '', actions: [] })
const currentEventType = ref('')
const notifTemplateOptions = ref<any[]>([])

const actionTypeOptions = [
  { value: 'NOTIFY', label: '发送通知' },
  { value: 'WEBHOOK', label: 'HTTP 回调' },
  { value: 'OPSFLOW', label: '触发运维流程' },
  { value: 'MODIFY_FIELD', label: '修改工单字段' },
]

const triggerEventTypes = computed(() => {
  if (!props.node?.type) return [] as string[]
  const t = props.node.type
  if (t === 'START') return ['FLOW_START']
  if (t === 'END') return ['FLOW_END']
  if (['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(t)) return []
  return ['ENTER_STATE', 'LEAVE_STATE']
})

const triggersByEvent = computed(() => {
  const map: Record<string, any[]> = {}
  for (const et of triggerEventTypes.value) map[et] = []
  for (const t of triggers.value) { if (map[t.event_type]) map[t.event_type].push(t) }
  return map
})

function eventLabel(et: string) {
  const m: Record<string, string> = { FLOW_START: '流程开始', FLOW_END: '流程结束', ENTER_STATE: '接入节点', LEAVE_STATE: '离开节点' }
  return m[et] || et
}

function addAction() {
  form.value.actions.push({ action_type: 'NOTIFY', config: { channels: ['site'], title_tpl: '', body_tpl: '', receivers: ['processor'], retry_max: 0, retry_interval: 60 } })
}

function onAdd(eventType: string) {
  currentEventType.value = eventType
  form.value = { id: null, name: '', is_active: true, event_type: eventType, actions: [{ action_type: 'NOTIFY', config: { channels: ['site'], title_tpl: '', body_tpl: '', receivers: ['processor'], retry_max: 0, retry_interval: 60 } }] }
  editVisible.value = true
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name || `触发_${form.value.event_type}`,
      name_en: '', is_active: form.value.is_active, event_type: form.value.event_type,
      workflow: props.workflowId, state_ids: [props.node.id], priority: '', condition: {},
      actions: form.value.actions.map((a: any, i: number) => {
        const cfg = { ...(a.config || {}) }
        cfg.retry = { max: Number(cfg.retry_max || 0), interval: Number(cfg.retry_interval || 60) }
        delete cfg.retry_max; delete cfg.retry_interval
        return { order: i, action_type: a.action_type, config: cfg }
      }),
    }
    if (form.value.id) { await triggerApi.update(form.value.id, payload) }
    else { await triggerApi.create(payload) }
    editVisible.value = false
    await loadTriggers()
  } catch { /* silently fail in designer context */ }
  finally { saving.value = false }
}

async function onDelete(t: any) {
  try { await triggerApi.delete(t.id); await loadTriggers() } catch { /* ignore */ }
}

async function onToggle(t: any, v: boolean) {
  try { await triggerApi.update(t.id, { is_active: v }); t.is_active = v } catch { /* ignore */ }
}

function onTemplateSelect(idx: number, templateId: string, action: any) {
  if (!templateId) return
  const tpl = notifTemplateOptions.value.find((t: any) => String(t.id) === String(templateId))
  if (!tpl) return
  action._templateId = templateId
  action.config.title_tpl = tpl.title_tpl || ''
  action.config.body_tpl = tpl.body_tpl || ''
  action.config.channels = tpl.channels || ['site']
  action.config.receivers = tpl.receivers || ['processor']
}

async function loadTriggers() {
  if (!props.workflowId || !props.node?.id) { triggers.value = []; return }
  try {
    const res = await triggerApi.list({ workflow: props.workflowId, states: props.node.id }) as any
    triggers.value = res?.results || res?.data || res || []
  } catch { triggers.value = [] }
}

async function loadTemplates() {
  try {
    const res = await notificationTemplateApi.list({ is_active: true }) as any
    notifTemplateOptions.value = res?.results || res?.data || res || []
  } catch { notifTemplateOptions.value = [] }
}

loadTemplates()
watch(() => [props.node, props.workflowId], () => {
  if (props.node?.id && props.workflowId) loadTriggers()
})
</script>

<style scoped>
.trigger-section { margin-bottom: 10px; }
.trigger-event-label { font-size: 13px; font-weight: 500; color: #303133; margin-bottom: 6px; }
.trigger-item { border: 1px solid #e4e7ed; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; }
.trigger-item-header { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.trigger-item-actions { display: flex; gap: 4px; margin-top: 4px; }
.trigger-action-card { border: 1px solid #e4e7ed; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
.action-card-head { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: #fafafa; border-bottom: 1px solid #ebeef5; }
.action-card-body { padding: 8px 10px; }
.action-card-foot { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: #fafafa; border-top: 1px solid #ebeef5; font-size: 12px; color: #909399; }
.template-hint-trigger { font-size: 12px; color: #909399; margin-top: 8px; line-height: 1.8; }
.template-hint-trigger code { background: #f0f2f5; padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.cc-label { font-size: 12px; color: #909399; white-space: nowrap; }
</style>
