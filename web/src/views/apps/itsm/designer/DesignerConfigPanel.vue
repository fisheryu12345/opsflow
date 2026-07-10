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
        </el-form>
      </template>

      <!-- Edge config -->
      <template v-else-if="edge">
        <el-form label-position="top" size="small">
          <el-form-item :label="$t('message.designer.edgeLabel')">
            <el-input v-model="edge.label" :placeholder="$t('message.designer.edgeLabel')" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.conditionExpr')">
            <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
              <el-select size="small" style="flex:1;min-width:120px" placeholder="字段" @change="onCondFieldSelect" clearable filterable>
                <el-option v-for="r in fieldRefOptions" :key="r.value" :label="r.label" :value="r.value" />
              </el-select>
              <el-select size="small" style="width:70px" placeholder="操作" @change="onCondOpSelect" clearable>
                <el-option v-for="op in condOperators" :key="op" :label="op" :value="op" />
              </el-select>
              <el-input v-model="condState.value" size="small" style="flex:1;min-width:80px" placeholder="值" @change="buildCondExpr" clearable />
            </div>
            <div v-if="edge.condition" style="margin-top:4px;font-size:11px;color:#409EFF;background:#ecf5ff;padding:4px 8px;border-radius:4px;word-break:break-all">
              {{ edge.condition }}
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-top:4px">
              <el-button v-if="edge.condition" link size="small" type="danger" @click="edge.condition = ''; onEdgeChange()">清除（默认分支）</el-button>
              <el-button link size="small" type="primary" @click="openConditionDialog">
                <el-icon><Plus /></el-icon> 添加条件
              </el-button>
              <el-button link size="small" @click="showAdvanced = !showAdvanced">{{ showAdvanced ? '收起' : '手动' }}</el-button>
            </div>
            <el-input v-if="showAdvanced" v-model="edge.condition" type="textarea" :rows="2" placeholder="手动输入" @input="onEdgeChange" style="margin-top:4px" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.rejectEdge')">
            <el-switch v-model="edge.isReject" @change="onEdgeChange" />
            <span style="font-size:11px;color:#909399;margin-left:8px;">{{ $t('message.designer.rejectTip') }}</span>
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
import { presetApi } from '/@/api/itsm/index'
import PresetProcessorInput from './components/PresetProcessorInput.vue'
import ConditionDialog from '/@/views/apps/opsflow/components/gates/ConditionDialog.vue'
import { generateConditionExpr } from '/@/views/apps/opsflow/composables/useGraphCanvas'

const { t } = useI18n()

const props = defineProps<{
  node: any
  edge: any
  allNodes?: any[]  // for edge config: compute upstream field references
}>()

const emit = defineEmits<{
  close: []
  change: []
  openFieldEditor: []
}>()

const configVisible = computed(() => props.node || props.edge)
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

// Parse conditionStruct from edge.condition (string)
function openConditionDialog() {
  const raw = props.edge?.condition || ''
  if (typeof raw === 'string' && raw.trim()) {
    // Try to parse existing expression back into struct (basic: single rule)
    conditionStruct.value = { logic: 'AND', rules: [{ source: '', field: '', op: '==', value: raw }] }
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

const condOperators = ['==', '!=', '>', '<', '>=', '<=']
const condState = reactive({ field: '', op: '', value: '' })

function onCondFieldSelect(v: string) { condState.field = v || ''; buildCondExpr() }
function onCondOpSelect(v: string) { condState.op = v || ''; buildCondExpr() }

function buildCondExpr() {
  if (!props.edge) return
  const { field, op, value } = condState
  if (!field) return
  const valPart = isNaN(Number(value)) && value !== 'true' && value !== 'false'
    ? `'${value}'` : value
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
  props.edge.label = props.edge.isReject ? '驳回' : (props.edge.label || '')
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
</style>
