<template>
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
        preset-type="user_list" input-mode="select" :node="node"
        v-model:person-users="personUsers" :user-options="userOptions"
        :users-loading="usersLoading" :preset-options="presetOptions"
        :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
        @load-users="loadUsers" @person-change="onPersonChange()" @change="onChange()"
      />
      <PresetProcessorInput
        v-if="node.processors_type === 'ORGANIZATION'"
        preset-type="dept_list" input-mode="text" :node="node"
        :person-users="[]" :user-options="[]" :users-loading="false"
        :preset-options="presetOptions"
        :manual-placeholder="$t('message.preset.deptPlaceholder')"
        @change="onChange()"
      />
      <PresetProcessorInput
        v-if="node.processors_type === 'ROLE'"
        preset-type="role_list" input-mode="text" :node="node"
        :person-users="[]" :user-options="[]" :users-loading="false"
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
        preset-type="user_list" input-mode="select" :node="node"
        v-model:person-users="personUsers" :user-options="userOptions"
        :users-loading="usersLoading" :preset-options="presetOptions"
        :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
        @load-users="loadUsers" @person-change="onPersonChange()" @change="onChange()"
      />
      <PresetProcessorInput
        v-if="node.processors_type === 'ORGANIZATION'"
        preset-type="dept_list" input-mode="text" :node="node"
        :person-users="[]" :user-options="[]" :users-loading="false"
        :preset-options="presetOptions"
        :manual-placeholder="$t('message.preset.deptPlaceholder')"
        @change="onChange()"
      />
      <PresetProcessorInput
        v-if="node.processors_type === 'ROLE'"
        preset-type="role_list" input-mode="text" :node="node"
        :person-users="[]" :user-options="[]" :users-loading="false"
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

    <!-- TASK -->
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
        preset-type="user_list" input-mode="select" :node="node"
        v-model:person-users="personUsers" :user-options="userOptions"
        :users-loading="usersLoading" :preset-options="presetOptions"
        :manual-placeholder="$t('message.designer.searchUserPlaceholder')"
        @load-users="loadUsers" @person-change="onPersonChange()" @change="onChange()"
      />
      <PresetProcessorInput
        v-if="node.processors_type === 'ROLE'"
        preset-type="role_list" input-mode="text" :node="node"
        :person-users="[]" :user-options="[]" :users-loading="false"
        :preset-options="presetOptions"
        :manual-placeholder="$t('message.designer.rolePlaceholder')"
        @change="onChange()"
      />
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

      <!-- OpsFlow config -->
      <el-divider>OpsFlow</el-divider>
      <el-form-item :label="$t('message.designer.opsflowTemplate')">
        <el-select v-model="nodeExtras.opsflow_template_id"
                   :placeholder="$t('message.designer.opsflowTemplateSelect')" clearable style="width:100%"
                   @change="onOpsflowTemplateSelect">
          <el-option v-for="t in opsflowTemplates" :key="t.id"
                     :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="nodeExtras.opsflow_template_id" :label="$t('message.designer.opsflowGlobalVars')">
        <div v-for="k in templateVarKeys" :key="k" class="var-mapping-row">
          <el-tag size="small" type="info">{{ k }}</el-tag>
          <span style="font-size:11px;color:#909399">{{ $t('message.designer.opsflowVarRuntime') }}</span>
        </div>
        <div v-if="!templateVarKeys.length" style="color:#909399;font-size:12px">{{ $t('message.designer.opsflowNoVars') }}</div>
      </el-form-item>
    </template>

    <!-- Fields button (all except gateways) -->
    <template v-if="!['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(node.type)">
      <el-form-item :label="$t('message.designer.formDesign')">
        <template v-if="node.type === 'NORMAL'">
          <div style="display:flex;align-items:center;gap:6px;width:100%">
            <el-button size="small" type="primary" plain @click="$emit('openFieldEditor')">
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
            <el-tag v-for="r in (node.fields || []).slice(0, 6)" :key="r.field" size="small"
              :type="(r.validate?.[0]?.required) ? 'danger' : 'info'">{{ r.title }}</el-tag>
            <el-tag v-if="(node.fields || []).length > 6" size="small">+{{ (node.fields || []).length - 6 }}</el-tag>
          </div>
          <el-button size="small" @click="$emit('openFieldEditor')">
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

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { Edit, Plus } from '@element-plus/icons-vue'
import { getNodeConfig } from '../shapes'
import { request } from '/@/utils/service'
import { presetApi } from '/@/api/itsm/index'
import PresetProcessorInput from './PresetProcessorInput.vue'

const props = defineProps<{ node: any }>()
const emit = defineEmits<{ change: []; openFieldEditor: [] }>()

const typeLabel = computed(() => props.node?.type ? getNodeConfig(props.node.type).label : '')

// Ensure extras is always a valid object for v-model bindings
const nodeExtras = computed(() => {
  if (!props.node) return {}
  if (!props.node.extras) props.node.extras = {}
  return props.node.extras
})

const personUsers = ref<(string | number)[]>([])
const usersLoading = ref(false)
const userOptions = ref<any[]>([])
const presetOptions = ref<any[]>([])

function onChange() { emit('change') }

function onPersonChange() {
  if (props.node) props.node.processorsRaw = JSON.stringify(personUsers.value || [])
  onChange()
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

async function loadPresets() {
  try {
    const res = await presetApi.list({ page_size: 200 })
    presetOptions.value = (res as any).data || []
  } catch { presetOptions.value = [] }
}

function gatewayHint(type: string) {
  const hints: Record<string, string> = {
    COVERAGE: '汇聚网关 — 等待所有并行分支完成后继续',
    EXCLUSIVE: '排他网关 — 首个匹配条件的分支执行，其他跳过；需至少有一条无条件边',
    CONDITIONAL_PARALLEL: '条件并行网关 — 所有匹配条件的分支同时执行，需配合汇聚网关使用',
    PARALLEL: '并行网关 — 所有分支同时执行，需配合汇聚网关使用',
  }
  return hints[type] || ''
}


watch(() => props.node, async (newNode) => {
  if (newNode?.processors_type === 'PERSON' && newNode?.processorsRaw) {
    const raw = newNode.processorsRaw
    let ids: (string | number)[] = []
    try {
      const parsed = JSON.parse(raw)
      ids = Array.isArray(parsed) ? parsed : (typeof parsed === 'number' ? [parsed] : [])
    } catch {
      ids = raw.split(',').filter(Boolean).map((v: string) => v.trim())
    }
    personUsers.value = ids.map((v: any) => {
      const n = typeof v === 'number' ? v : parseInt(String(v).trim(), 10)
      return isNaN(n) ? String(v).trim() : n
    }) as any
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

// ── OpsFlow integration ──
const opsflowTemplates = ref<any[]>([])

async function loadOpsflowTemplates() {
  try {
    const res = await request({ url: '/api/opsflow/templates/', method: 'get', params: { page_size: 500 } })
    opsflowTemplates.value = (res as any).data || (res as any).results || []
  } catch { opsflowTemplates.value = [] }
}

const templateVarKeys = ref<string[]>([])

async function onOpsflowTemplateSelect(tid: number | null) {
  if (!tid) { templateVarKeys.value = []; onChange(); return }
  onChange()
  try {
    const res = await request({ url: `/api/opsflow/templates/${tid}/global-variables/`, method: 'get' })
    templateVarKeys.value = Object.keys((res as any).data || {})
  } catch { templateVarKeys.value = [] }
}

onMounted(() => { loadPresets(); loadOpsflowTemplates() })
</script>

<style scoped>
.var-mapping-row {
  display: flex; gap: 4px; align-items: center; margin-bottom: 4px;
}
</style>
