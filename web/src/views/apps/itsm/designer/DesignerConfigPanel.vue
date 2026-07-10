<template>
  <div class="des-config" v-if="configVisible">
    <div class="des-config-header">
      <span>{{ configTitle }}</span>
      <el-button text size="small" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>
    <div class="des-config-body">
      <!-- Node config -->
      <template v-if="node">
        <el-form label-position="top" size="small">
          <el-form-item :label="$t('message.designer.nodeName')">
            <el-input v-model="node.name" @input="onChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.nodeId')">
            <el-input :model-value="node.node_key || node._x6Id" disabled />
          </el-form-item>
          <el-form-item :label="$t('message.designer.nodeType')">
            <el-tag size="small">{{ typeLabel }}</el-tag>
          </el-form-item>

          <!-- APPROVAL -->
          <template v-if="node.type === 'APPROVAL'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starterLeader')" value="STARTER_LEADER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
                <el-option :label="$t('message.designer.organization')" value="ORGANIZATION" />
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
              </el-select>
            </el-form-item>
            <PresetProcessorInput
              v-if="node.processors_type === 'PERSON'"
              preset-type="user_list"
              input-mode="select"
              :node="node"
              v-model:person-users="personUsers"
              :user-options="userOptions"
              :users-loading="usersLoading"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
              @load-users="loadUsers"
              @person-change="onPersonChange()"
              @change="onChange()"
            />
            <PresetProcessorInput
              v-if="node.processors_type === 'ORGANIZATION'"
              preset-type="dept_list"
              input-mode="text"
              :node="node"
              :person-users="[]"
              :user-options="[]"
              :users-loading="false"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.preset.deptPlaceholder')"
              @change="onChange()"
            />
            <PresetProcessorInput
              v-if="node.processors_type === 'ROLE'"
              preset-type="role_list"
              input-mode="text"
              :node="node"
              :person-users="[]"
              :user-options="[]"
              :users-loading="false"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.rolePlaceholder')"
              @change="onChange()"
            />
            <el-form-item :label="$t('message.designer.approvalMethod')">
              <el-radio-group v-model="node.is_multi" @change="onChange">
                <el-radio :value="false">{{ $t('message.designer.singleSign') }}</el-radio>
                <el-radio :value="true">{{ $t('message.designer.multiSign') }}</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="$t('message.designer.allowSkip')">
              <el-switch v-model="node.is_allow_skip" @change="onChange" />
            </el-form-item>
          </template>

          <!-- SIGN -->
          <template v-if="node.type === 'SIGN'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starterLeader')" value="STARTER_LEADER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
                <el-option :label="$t('message.designer.organization')" value="ORGANIZATION" />
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
              </el-select>
            </el-form-item>
            <PresetProcessorInput
              v-if="node.processors_type === 'PERSON'"
              preset-type="user_list"
              input-mode="select"
              :node="node"
              v-model:person-users="personUsers"
              :user-options="userOptions"
              :users-loading="usersLoading"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
              @load-users="loadUsers"
              @person-change="onPersonChange()"
              @change="onChange()"
            />
            <PresetProcessorInput
              v-if="node.processors_type === 'ORGANIZATION'"
              preset-type="dept_list"
              input-mode="text"
              :node="node"
              :person-users="[]"
              :user-options="[]"
              :users-loading="false"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.preset.deptPlaceholder')"
              @change="onChange()"
            />
            <PresetProcessorInput
              v-if="node.processors_type === 'ROLE'"
              preset-type="role_list"
              input-mode="text"
              :node="node"
              :person-users="[]"
              :user-options="[]"
              :users-loading="false"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.rolePlaceholder')"
              @change="onChange()"
            />
            <el-form-item :label="$t('message.designer.signMethod')">
              <el-radio-group v-model="node.is_sequential" @change="onChange">
                <el-radio :value="false">{{ $t('message.designer.parallelSign') }}</el-radio>
                <el-radio :value="true">{{ $t('message.designer.sequentialSign') }}</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <!-- NORMAL (填单) — 提单人自己填写，不需要处理人配置 -->
          <template v-if="node.type === 'NORMAL'">
          </template>

          <!-- TASK -- with WEBHOOK -->
          <template v-if="node.type === 'TASK'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
              </el-select>
            </el-form-item>
            <PresetProcessorInput
              v-if="node.processors_type === 'PERSON'"
              preset-type="user_list"
              input-mode="select"
              :node="node"
              v-model:person-users="personUsers"
              :user-options="userOptions"
              :users-loading="usersLoading"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
              @load-users="loadUsers"
              @person-change="onPersonChange()"
              @change="onChange()"
            />
            <PresetProcessorInput
              v-if="node.processors_type === 'ROLE'"
              preset-type="role_list"
              input-mode="text"
              :node="node"
              :person-users="[]"
              :user-options="[]"
              :users-loading="false"
              :preset-options="presetOptions"
              :manual-placeholder="$t('message.designer.rolePlaceholder')"
              @change="onChange()"
            />
            <!-- TASK only: execute type -->
            <template v-if="node.type === 'TASK'">
              <el-form-item :label="$t('message.designer.executeType')">
                <el-radio-group v-model="node.execute_type" @change="onChange">
                  <el-radio value="internal">{{ $t('message.designer.internalExec') }}</el-radio>
                  <el-radio value="webhook">{{ $t('message.designer.webhookExec') }}</el-radio>
                </el-radio-group>
              </el-form-item>
              <template v-if="node.execute_type === 'webhook'">
                <el-form-item :label="$t('message.designer.requestUrl')">
                  <el-input v-model="node.api_url" @input="onChange" placeholder="https://..." />
                </el-form-item>
                <el-form-item :label="$t('message.designer.requestMethod')">
                  <el-select v-model="node.api_method" @change="onChange" style="width:100%">
                    <el-option label="POST" value="POST" />
                    <el-option label="GET" value="GET" />
                    <el-option label="PUT" value="PUT" />
                  </el-select>
                </el-form-item>
              </template>
            </template>
          </template>

          <!-- Fields button (all except gateways) -->
          <template v-if="!['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(node.type)">
            <el-form-item :label="$t('message.designer.formDesign')">
              <template v-if="node.type === 'NORMAL'">
                <div style="display:flex;align-items:center;gap:6px;width:100%">
                  <el-button size="small" type="primary" plain @click="onOpenFieldEditor">
                    <el-icon><Plus /></el-icon> {{ $t('message.designer.addField') }}
                  </el-button>
                  <span v-if="(node.fields || []).length" style="font-size:12px;color:#909399">
                    {{ $t('message.designer.configStatus', { n: (node.fields || []).length }) }}
                  </span>
                </div>
                <div v-if="!(node.fields || []).length" style="font-size:12px;color:#C0C4CC;margin-top:2px">
                  {{ $t('message.designer.emptyTip') }}
                </div>
              </template>
              <template v-else>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">
                  <el-tag
                    v-for="f in (node.fields || []).slice(0, 6)"
                    :key="f.key"
                    size="small"
                    :type="f.required ? 'danger' : 'info'"
                  >{{ f.name }}</el-tag>
                  <el-tag v-if="(node.fields || []).length > 6" size="small">
                    +{{ (node.fields || []).length - 6 }}
                  </el-tag>
                </div>
                <el-button size="small" @click="onOpenFieldEditor">
                  <el-icon><Edit /></el-icon> {{ $t('message.designer.editField') }}
                </el-button>
              </template>
            </el-form-item>
          </template>

          <!-- Gateway hint -->
          <template v-if="['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(node.type)">
            <el-alert type="info" :closable="false" show-icon :title="gatewayHint(node.type)" />
          </template>

          <!-- Trigger config (non-gateway nodes only) -->
          <template v-if="triggerEventTypes.length > 0">
            <el-divider content-position="left">触发器</el-divider>
            <div v-for="et in triggerEventTypes" :key="et" class="trigger-section">
              <div class="trigger-event-label">{{ et === 'FLOW_START' ? '流程开始' : et === 'FLOW_END' ? '流程结束' : et === 'ENTER_STATE' ? '接入节点' : '离开节点' }}</div>
              <div v-if="!triggersByEvent[et]" style="font-size:12px;color:#909399;margin-bottom:4px">暂无配置</div>
              <div v-for="t in (triggersByEvent[et] || [])" :key="t.id" class="trigger-item">
                <div class="trigger-item-header">
                  <span>{{ t.name || '(未命名)' }}</span>
                  <div>
                    <el-switch :model-value="t.is_active" size="small" @change="(v:boolean)=>onTriggerToggle(t,v)" />
                    <el-button link size="small" type="danger" @click="onTriggerDelete(t)"><el-icon><Delete /></el-icon></el-button>
                  </div>
                </div>
                <div class="trigger-item-actions">
                  <el-tag v-for="a in (t.actions||[])" :key="a.id" size="small" :type="a.action_type==='NOTIFY'?'success':a.action_type==='WEBHOOK'?'warning':a.action_type==='OPSFLOW'?'primary':'info'">
                    {{ a.action_type === 'NOTIFY' ? '通知' : a.action_type === 'WEBHOOK' ? 'Webhook' : a.action_type === 'OPSFLOW' ? 'OpsFlow' : '改字段' }}
                  </el-tag>
                </div>
              </div>
              <el-button size="small" plain @click="onTriggerAdd(et)"><el-icon><Plus /></el-icon> 添加</el-button>
            </div>

            <!-- Quick trigger edit dialog -->
            <el-dialog v-model="triggerEditVisible" :title="triggerForm.id ? '编辑触发器' : '新建触发器'" width="600px" top="10vh" destroy-on-close append-to-body>
              <el-form :model="triggerForm" label-width="100px" size="small">
                <el-form-item label="名称">
                  <el-input v-model="triggerForm.name" placeholder="触发器名称" />
                </el-form-item>
                <el-form-item label="启用">
                  <el-switch v-model="triggerForm.is_active" />
                </el-form-item>
                <el-form-item label="动作列表">
                  <div v-for="(a,i) in triggerForm.actions" :key="i" style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
                    <el-select v-model="a.action_type" style="width:120px" size="small">
                      <el-option value="NOTIFY" label="发送通知" />
                      <el-option value="WEBHOOK" label="HTTP回调" />
                      <el-option value="OPSFLOW" label="触发OpsFlow" />
                      <el-option value="MODIFY_FIELD" label="修改字段" />
                    </el-select>
                    <template v-if="a.action_type==='NOTIFY'">
                      <el-select v-model="a._templateId" size="small" placeholder="选择模板" style="width:140px" clearable @change="(v:string)=>onNotifyTemplateSelect(i, v, a)">
                        <el-option v-for="t in notifTemplateOptions" :key="t.id" :label="t.name" :value="t.id" />
                      </el-select>
                      <el-input v-model="a.config.title_tpl" size="small" placeholder="标题" style="flex:1" />
                    </template>
                    <el-input v-if="a.action_type==='WEBHOOK'" v-model="a.config.url" size="small" placeholder="URL" style="flex:1" />
                    <el-input v-if="a.action_type==='MODIFY_FIELD'" v-model="a.config.field_name" size="small" placeholder="字段名" style="width:100px" />
                    <el-button link size="small" type="danger" @click="triggerForm.actions.splice(i,1)"><el-icon><Delete /></el-icon></el-button>
                  </div>
                  <el-button size="small" plain @click="triggerForm.actions.push({action_type:'NOTIFY',config:{}})"><el-icon><Plus /></el-icon> 添加动作</el-button>
                </el-form-item>
              </el-form>
              <template #footer>
                <el-button @click="triggerEditVisible=false">取消</el-button>
                <el-button type="primary" :loading="triggerSaving" @click="onTriggerSave">保存</el-button>
              </template>
            </el-dialog>
          </template>
        </el-form>
      </template>

      <!-- Edge config -->
      <template v-else-if="edge && isGatewayEdge">
        <el-form label-position="top" size="small">
          <el-form-item :label="$t('message.designer.edgeLabel')">
            <el-input v-model="edge.label" :placeholder="$t('message.designer.edgeLabel')" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.conditionExpr')">
            <!-- Structured preview (opsflow-style) -->
            <div v-if="edge.condition" class="itsm-cond-preview">
              <template v-if="parsedRules.length">
                <div v-for="(r, i) in parsedRules" :key="i" class="cond-rule-line">
                  <span v-if="r.logic" class="cond-logic-tag">{{ r.logic }}</span>
                  <span class="cond-rule-ref">{{ r.source }}.{{ r.field }}</span>
                  <span class="cond-rule-op">{{ r.op }}</span>
                  <span class="cond-rule-val">{{ r.value }}</span>
                </div>
              </template>
              <code v-else class="cond-rule-raw">{{ edge.condition }}</code>
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-top:4px">
              <el-button v-if="edge.condition" link size="small" type="danger" @click="edge.condition = ''; onEdgeChange()">清除</el-button>
              <el-button link size="small" type="primary" @click="openConditionDialog">
                <el-icon><Plus /></el-icon> 添加条件
              </el-button>
              <el-button link size="small" @click="showAdvanced = !showAdvanced">{{ showAdvanced ? '收起' : '手动' }}</el-button>
            </div>
            <el-input v-if="showAdvanced" v-model="edge.condition" type="textarea" :rows="3" placeholder="手动输入，如 ${node_2.field} > 5 AND ${node_3.field} == 'x'" @input="onEdgeChange" style="margin-top:4px" />
          </el-form-item>
        </el-form>
      </template>
    </div>
    <button class="des-config-collapse" @click="$emit('close')">◀</button>

    <ConditionDialog
      :visible="conditionDialogVisible"
      :initial-struct="conditionStruct"
      :available-vars="availableVars"
      @update:visible="conditionDialogVisible = $event"
      @save="onConditionSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Close, Edit, Plus } from '@element-plus/icons-vue'
import { getNodeConfig } from './shapes'
import { request } from '/@/utils/service'
import { presetApi, triggerApi, notificationTemplateApi } from '/@/api/itsm/index'
import PresetProcessorInput from './components/PresetProcessorInput.vue'
import ConditionDialog from './components/ConditionDialog.vue'
import { generateConditionExpr } from './conditionUtils'

const { t } = useI18n()

const props = defineProps<{
  node: any
  edge: any
  allNodes?: any[]  // for edge config: compute upstream field references
  workflowId?: number
}>()

const emit = defineEmits<{
  close: []
  change: []
  openFieldEditor: []
}>()

const configVisible = computed(() => props.node || (props.edge && isGatewayEdge.value))
// Only show edge config for gateway edges (EXCLUSIVE or CONDITIONAL_PARALLEL)
const isGatewayEdge = computed(() => {
  const t = props.edge?._from_state_type || ''
  return t === 'EXCLUSIVE' || t === 'CONDITIONAL_PARALLEL'
})
const configTitle = computed(() => props.node ? t('message.designer.nodeConfig') : t('message.designer.edgeConfig'))
const typeLabel = computed(() => {
  if (!props.node?.type) return ''
  return getNodeConfig(props.node.type).label
})

// ── Edge condition: field reference helpers ──
const fieldRefOptions = computed(() => {
  if (!props.edge || !props.allNodes?.length) return []
  const refs: { label: string; value: string }[] = []
  for (const n of props.allNodes) {
    const nk = n.node_key || n.id || ''
    if (!nk) continue
    for (const f of (n.fields || [])) {
      if (f.key) {
        refs.push({ label: `${n.name || nk}.${f.name || f.key}`, value: `\${${nk}.field_${f.key}}` })
      }
    }
  }
  return refs
})
const parsedRules = computed(() => {
  const c = (props.edge?.condition || '')
  if (!c || typeof c !== 'string' || !c.trim()) return []
  // Opsflow's exact regex: requires ${node.field} prefix
  const logics = []
  const logicRe = /\s+(AND|OR)\s+/gi
  let m2
  while ((m2 = logicRe.exec(c)) !== null) logics.push(m2[1].toUpperCase())
  const parts = c.split(/\s+AND\s+|\s+OR\s+/i).filter(Boolean)
  const RULE_PAT = /^\$\{([^.]+)\.([^}]+)\}\s*(>=|<=|!=|==|>|<|in|notin)\s*(.+)$/
  const rules = parts.map((p, i) => {
    const pm = p.trim().match(RULE_PAT)
    if (!pm) return null
    let v = pm[4]
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
    return { source: pm[1], field: pm[2], op: pm[3], value: v, logic: i > 0 ? (logics[i - 1] || 'AND') : '' }
  }).filter(Boolean)
  return rules
})


const showAdvanced = ref(false)
const conditionDialogVisible = ref(false)
const conditionLogic = ref<'AND' | 'OR'>('AND')
const conditionStruct = ref<any>(null)

// Build available variables from ALL graph nodes' fields
const availableVars = computed(() => {
  const vars: any[] = []
  if (!props.allNodes?.length) return vars
  for (const n of props.allNodes) {
    const nk = n.node_key || n.id || ''
    if (!nk) continue
    const nodeName = n.name || nk
    for (const f of (n.fields || [])) {
      if (f.key) {
        vars.push({
          source: nk,
          sourceLabel: nodeName,
          field: f.key,
          fieldLabel: f.name || f.key,
          fieldType: f.type === 'NUMBER' || f.type === 'INT' ? 'number' : f.type === 'SELECT' || f.type === 'RADIO' ? 'string' : 'string',
          sourceType: 'node' as const,
          label: `${nodeName}.${f.name || f.key}`,
          group: nodeName,
        })
      }
    }
  }
  return vars
})

// Parse existing condition expression back into structured rules for editing
function openConditionDialog() {
  const raw = props.edge?.condition || ''
  if (typeof raw === 'string' && raw.trim()) {
    const parts = raw.split(/\s+AND\s+|\s+OR\s+/i).filter(Boolean)
    const logic = raw.match(/\s+OR\s+/i) ? 'OR' : 'AND'
    const rules: any[] = []
    for (const p of parts) {
      const m = p.trim().match(/^\$\{([^.]+)\.([^}]+)\}\s*(>=|<=|!=|==|>|<|in|notin)\s*(.+)$/)
      if (m) {
        let v = m[4]
        if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
        rules.push({ source: m[1], field: m[2], op: m[3], value: v, fieldType: 'string' })
      }
    }
    conditionStruct.value = rules.length ? { logic, rules } : null
  } else {
    conditionStruct.value = null
  }
  conditionDialogVisible.value = true
}

function onConditionSave(struct: any) {
  if (!props.edge) return
  props.edge.condition = generateConditionExpr(struct.rules, struct.logic)
  conditionDialogVisible.value = false
  emit('change')
}

const condOperators = ['==', '!=', '>', '<', '>=', '<=', 'in', 'notin']
const condState = reactive({ field: '', op: '', value: '' })

function onCondFieldSelect(v: string) { condState.field = v || ''; buildCondExpr() }
function onCondOpSelect(v: string) { condState.op = v || ''; buildCondExpr() }

function buildCondExpr() {
  if (!props.edge) return
  const { field, op, value } = condState
  if (!field) return
  const valPart = isNaN(Number(value)) && value !== 'true' && value !== 'false'
    ? `"${value}"` : value
  const expr = op ? `${field} ${op} ${valPart}` : field
  props.edge.condition = expr
  updateEdgeLabel()
  onEdgeChange()
}

function onEdgeChange() {
  updateEdgeLabel()
  emit('change')
}

function updateEdgeLabel() {
  if (!props.edge) return
  // Only set label from user input; don't auto-generate from condition text
  props.edge.label = props.edge.label || ''
}

function onChange() { emit('change') }
function onOpenFieldEditor() { emit('openFieldEditor') }
function gatewayHint(type: string) {
  const hints: Record<string, string> = {
    COVERAGE: '汇聚网关 — 等待所有并行分支完成后继续',
    EXCLUSIVE: '排他网关 — 首个匹配条件的分支执行，其他跳过；需至少有一条无条件边',
    CONDITIONAL_PARALLEL: '条件并行网关 — 所有匹配条件的分支同时执行，需配合汇聚网关使用',
    PARALLEL: '并行网关 — 所有分支同时执行，需配合汇聚网关使用',
  }
  return hints[type] || ''
}

// Watch selected node changes: restore personUsers from processorsRaw for PERSON type
watch(() => props.node, async (newNode) => {
  if (newNode?.processors_type === 'PERSON' && newNode?.processorsRaw) {
    // processorsRaw may be "5" (single), "5,4,1" (comma-separated), or
    // "[5,4,1]" (JSON array from preset expansion). Normalize to number[].
    const raw = newNode.processorsRaw
    let ids: (string | number)[] = []
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        ids = parsed
      } else if (typeof parsed === 'number') {
        ids = [parsed]
      } else {
        throw new Error('not usable')
      }
    } catch {
      ids = raw.split(',').filter(Boolean).map((v: string) => v.trim())
    }
    personUsers.value = ids.map((v: any) => {
      const n = typeof v === 'number' ? v : parseInt(String(v).trim(), 10)
      return isNaN(n) ? String(v).trim() : n
    }) as any
    // Pre-load user options so the multi-select can resolve IDs to names.
    // Ensure selected users exist in userOptions even if API doesn't return them.
    await loadUsers()
    for (const uid of personUsers.value) {
      if (!userOptions.value.some((o: any) => o.value === uid)) {
        userOptions.value.push({ value: uid, label: `用户${uid}` })
      }
    }
  } else {
    personUsers.value = []
  }
})

// ===== PERSON 处理人用户选择 =====
const personUsers = ref<(string | number)[]>([])
const usersLoading = ref(false)
const userOptions = ref<any[]>([])

// ===== 预设加载 =====
const presetOptions = ref<any[]>([])
const presetsLoading = ref(false)

async function loadPresets() {
  presetsLoading.value = true
  try {
    const res = await presetApi.list({ page_size: 200 })
    presetOptions.value = (res as any).data || []
  } catch { presetOptions.value = [] }
  presetsLoading.value = false
}

async function loadUsers() {
  if (userOptions.value.length) return
  usersLoading.value = true
  try {
    const res: any = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 500 } })
    userOptions.value = (res as any).data || []
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

function onPersonChange() {
  if (props.node) props.node.processorsRaw = JSON.stringify(personUsers.value || [])
  onChange()
}

onMounted(() => {
  loadPresets()
})

// ===== Trigger config =====
const triggers = ref<any[]>([])
const triggerEditVisible = ref(false)
const triggerSaving = ref(false)
const triggerForm = ref<any>({ id: null, name: '', is_active: true, event_type: '', actions: [] })
const currentTriggerEventType = ref('')

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
  for (const t of triggers.value) {
    if (map[t.event_type]) map[t.event_type].push(t)
  }
  return map
})

async function loadTriggers() {
  if (!props.workflowId || !props.node?.id) { triggers.value = []; return }
  try {
    const res = await triggerApi.list({ workflow: props.workflowId, states: props.node.id }) as any
    triggers.value = res?.results || res?.data || res || []
  } catch { triggers.value = [] }
}

function onTriggerAdd(eventType: string) {
  currentTriggerEventType.value = eventType
  triggerForm.value = { id: null, name: '', is_active: true, event_type: eventType, actions: [{ action_type: 'NOTIFY', config: { channels: ['site'], title_tpl: '', body_tpl: '', receivers: ['processor'] } }] }
  triggerEditVisible.value = true
}

async function onTriggerSave() {
  triggerSaving.value = true
  try {
    const payload = {
      name: triggerForm.value.name || `触发_${triggerForm.value.event_type}`,
      name_en: '',
      is_active: triggerForm.value.is_active,
      event_type: triggerForm.value.event_type,
      workflow: props.workflowId,
      state_ids: [props.node.id],
      priority: '',
      condition: {},
      actions: triggerForm.value.actions.map((a: any, i: number) => ({
        order: i,
        action_type: a.action_type,
        config: a.config || {},
      })),
    }
    if (triggerForm.value.id) {
      await triggerApi.update(triggerForm.value.id, payload)
    } else {
      await triggerApi.create(payload)
    }
    triggerEditVisible.value = false
    await loadTriggers()
  } catch (e: any) {
    // silently fail in designer context
  } finally {
    triggerSaving.value = false
  }
}

async function onTriggerDelete(t: any) {
  try {
    await triggerApi.delete(t.id)
    await loadTriggers()
  } catch { /* ignore */ }
}

async function onTriggerToggle(t: any, v: boolean) {
  try {
    await triggerApi.update(t.id, { is_active: v })
    t.is_active = v
  } catch { /* ignore */ }
}

// Notification template options for NOTIFY action
const notifTemplateOptions = ref<any[]>([])

async function loadNotifTemplates() {
  try {
    const res = await notificationTemplateApi.list({ is_active: true }) as any
    notifTemplateOptions.value = res?.results || res?.data || res || []
  } catch { notifTemplateOptions.value = [] }
}

function onNotifyTemplateSelect(actionIndex: number, templateId: string, action: any) {
  if (!templateId) return
  const tpl = notifTemplateOptions.value.find((t: any) => String(t.id) === String(templateId))
  if (!tpl) return
  action._templateId = templateId
  action.config.title_tpl = tpl.title_tpl || ''
  action.config.body_tpl = tpl.body_tpl || ''
  action.config.channels = tpl.channels || ['site']
  action.config.receivers = tpl.receivers || ['processor']
}

loadNotifTemplates()
watch(() => [props.node, props.workflowId], () => {
  if (props.node?.id && props.workflowId) loadTriggers()
})
</script>

<style scoped>
.des-config {
  width: 320px; border-left: 1px solid #e4e7ed;
  background: #fff; overflow-y: auto; flex-shrink: 0;
  display: flex; flex-direction: column;
  position: relative;
}
.des-config-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f5f7fa; border-bottom: 1px solid #e4e7ed;
  font-size: 13px; font-weight: 600; color: #303133; flex-shrink: 0;
}
.des-config-body { flex: 1; padding: 12px; overflow-y: auto; }
.des-config-collapse {
  position: absolute; left: -16px; top: 50%; transform: translateY(-50%);
  width: 16px; height: 48px; border: 1px solid #e4e7ed; border-right: none;
  background: #f5f7fa; cursor: pointer; border-radius: 4px 0 0 4px;
  color: #909399; font-size: 10px; display: flex; align-items: center;
  justify-content: center;
}
.des-config-collapse:hover { color: #409EFF; background: #e8f0fe; }

/* Opsflow-style condition preview */
.itsm-cond-preview {
  background: #f5f7fa; border-radius: 6px; padding: 8px 10px;
  margin-top: 4px; word-break: break-all;
}
.cond-rule-line { display: flex; align-items: center; gap: 4px; font-size: 12px; font-family: monospace; padding: 3px 0; white-space: nowrap; }
.cond-rule-line + .cond-rule-line { border-top: 1px dashed #e4e7ed; }
.cond-logic-tag {
  background: #fdf6ec; color: #E6A23C; font-size: 10px; font-weight: 600;
  padding: 1px 6px; border-radius: 3px; margin-right: 4px;
}
.cond-rule-ref { color: #909399; }
.cond-rule-op { color: #409EFF; font-weight: 600; }
.cond-rule-val { color: #67C23A; }
.cond-rule-raw { font-size: 12px; color: #606266; }

/* Trigger section */
.trigger-section { margin-bottom: 10px; }
.trigger-event-label { font-size: 13px; font-weight: 500; color: #303133; margin-bottom: 6px; }
.trigger-item {
  border: 1px solid #e4e7ed; border-radius: 6px; padding: 8px 10px;
  margin-bottom: 6px;
}
.trigger-item-header { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.trigger-item-actions { display: flex; gap: 4px; margin-top: 4px; }
</style>
