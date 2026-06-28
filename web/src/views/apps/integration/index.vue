<template>
  <!-- 集成中心页面：连接器定义浏览、实例管理（含凭证 CRUD）、AI 对话测试、调用日志查看 -->
  <div class="int-page">
    <!-- ===== Hero Section ===== -->
    <div class="int-hero">
      <div class="int-hero-bg" />
      <div class="int-hero-inner">
        <div class="int-hero-left">
          <h1 class="int-hero-title">{{ $t('message.integration.title') }}</h1>
          <p class="int-hero-subtitle">{{ $t('message.integration.subtitle') }}</p>
        </div>
        <div class="int-hero-center">
          <el-input v-model="searchQuery" :placeholder="$t('message.integration.searchPlaceholder')" clearable size="default"
            class="int-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="int-hero-stats">
          <div class="int-stat-item"><span class="int-stat-value">{{ definitions.length }}</span><span class="int-stat-label">{{ $t('message.integration.heroDefinitions') }}</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ onlineCount }}</span><span class="int-stat-label">{{ $t('message.integration.heroOnline') }}</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ credentials.length }}</span><span class="int-stat-label">{{ $t('message.integration.heroCredentials') }}</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ callLogs.length }}</span><span class="int-stat-label">{{ $t('message.integration.heroRecentCalls') }}</span></div>
        </div>
      </div>
      <!-- Hero bottom tabs -->
      <div class="int-hero-tabs">
        <div class="int-hero-tab" :class="{ active: activeTab === 'instances' }" @click="activeTab = 'instances'">
          <el-icon><Connection /></el-icon> {{ $t('message.integration.tabInstances') }}
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'definitions' }" @click="activeTab = 'definitions'">
          <el-icon><List /></el-icon> {{ $t('message.integration.tabDefinitions') }}
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'credentials' }" @click="activeTab = 'credentials'">
          <el-icon><Key /></el-icon> {{ $t('message.integration.tabCredentials') }}
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
          <el-icon><Document /></el-icon> {{ $t('message.integration.tabLogs') }}
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'cloud-sync' }" @click="activeTab = 'cloud-sync'">
          <el-icon><Cloudy /></el-icon> {{ $t('message.integration.tabCloudSync') }}
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="int-body">

      <!-- ── Tab: 连接器定义 ── -->
      <div v-show="activeTab === 'definitions'" class="int-section g-fade-in-up">
        <div class="int-filter-bar">
          <div class="int-filter-tabs">
            <div class="int-tab" :class="{ active: defCategoryFilter === 'all' }" @click="defCategoryFilter = 'all'">
              <span class="int-tab-dot" style="background:#409EFF" />{{ $t('message.integration.filterAll') }}
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'ai' }" @click="defCategoryFilter = 'ai'">
              <span class="int-tab-dot" style="background:#E6A23C" />{{ $t('message.integration.catAi') }}
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'cloud' }" @click="defCategoryFilter = 'cloud'">
              <span class="int-tab-dot" style="background:#409EFF" />{{ $t('message.integration.catCloud') }}
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'notification' }" @click="defCategoryFilter = 'notification'">
              <span class="int-tab-dot" style="background:#67C23A" />{{ $t('message.integration.catNotification') }}
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'other' }" @click="defCategoryFilter = 'other'">
              <span class="int-tab-dot" style="background:#909399" />{{ $t('message.integration.catOther') }}
            </div>
          </div>
          <div class="int-filter-actions">
            <el-button :icon="Refresh" @click="loadData" :loading="loading" text size="small">{{ $t('message.integration.refresh') }}</el-button>
          </div>
        </div>

        <div class="int-def-grid" v-if="filteredDefinitions.length">
          <div v-for="(def, idx) in filteredDefinitions" :key="def.id"
               class="int-def-card g-stagger-item"
               :style="{ animationDelay: `${idx * 0.04}s` }"
               :class="{ 'int-def-card-ai': def.category === 'ai' }">
            <div class="int-def-card-inner">
              <div class="int-def-card-header">
                <span class="int-def-icon" :class="'int-def-icon-' + (def.category || 'other')">
                  <el-icon><component :is="defIcon(def.category)" /></el-icon>
                </span>
                <el-tag :type="def.category === 'ai' ? 'warning' : 'info'" size="small" effect="dark" class="int-cat-tag">
                  {{ categoryLabel(def.category) }}
                </el-tag>
              </div>
              <div class="int-def-name">{{ def.name }}</div>
              <div class="int-def-code"><code>{{ def.code }}</code></div>
              <div class="int-def-desc" v-if="def.description">{{ def.description }}</div>
              <div class="int-def-footer">
                <el-tag size="small" type="info" effect="plain">{{ $t('message.integration.versionPrefix') }}{{ def.version }}</el-tag>
                <el-button size="small" text @click="createInstance(def)">
                  <el-icon><Plus /></el-icon> {{ $t('message.integration.addInstance') }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else :description="$t('message.integration.noMatch')" :image-size="60" />
      </div>

      <!-- ── Tab: 连接器实例 ── -->
      <div v-show="activeTab === 'instances'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">{{ $t('message.integration.tabInstances') }}</span>
            <el-button type="primary" size="small" @click="showAddInstance = true">
              <el-icon><Plus /></el-icon> {{ $t('message.integration.addInstance') }}
            </el-button>
          </div>
          <el-table :data="instances" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? $t('message.integration.loading') : $t('message.integration.noInstances')">
            <el-table-column prop="name" :label="$t('message.integration.colName')" min-width="120" show-overflow-tooltip />
            <el-table-column :label="$t('message.integration.colType')" min-width="80">
              <template #default="{ row }">
                <span>{{ row.definition_code?.name || '-' }}</span>
                <el-tag v-if="row.definition_code?.category === 'ai'"
                        size="small" type="warning" effect="dark" style="margin-left:6px">AI</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.integration.colCategory')" width="150">
              <template #default="{ row }">
                <el-tag :type="tagType(row.definition_code?.category)" size="small" effect="plain">
                  {{ categoryLabel(row.definition_code?.category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('message.integration.colStatus')" width="165">
              <template #default="{ row }">
                <span class="int-status-badge" :class="'int-status-' + (row.status || 'unknown')">
                  <span class="int-status-dot" />{{ statusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" :label="$t('message.integration.colEnabled')" width="80" align="center">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" @change="toggleInstance(row)" size="small" />
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.integration.colActions')" width="300" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="runHealthCheck(row)">
                  <el-icon><Finished /></el-icon> {{ $t('message.integration.healthCheck') }}
                </el-button>
                <el-button size="small" text @click="editInstance(row)">
                  <el-icon><Edit /></el-icon> {{ $t('message.integration.configure') }}
                </el-button>
                <el-button v-if="row.definition_code?.category === 'ai'"
                           size="small" text type="warning" @click="testAiChat(row)">
                  <el-icon><ChatDotSquare /></el-icon> {{ $t('message.integration.test') }}
                </el-button>
                <el-button size="small" text type="danger" @click="deleteInstance(row)">
                  <el-icon><Delete /></el-icon> {{ $t('message.integration.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Tab: 凭证管理 ── -->
      <div v-show="activeTab === 'credentials'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">{{ $t('message.integration.tabCredentials') }}</span>
          </div>
          <el-table :data="credentials" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? $t('message.integration.loading') : $t('message.integration.noCredentials')">
            <el-table-column prop="name" :label="$t('message.integration.credName')" min-width="160" show-overflow-tooltip />
            <el-table-column prop="instance.name" :label="$t('message.integration.credInstance')" min-width="140" show-overflow-tooltip />
            <el-table-column prop="cred_type" :label="$t('message.integration.colType')" width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.cred_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="expire_at" :label="$t('message.integration.credExpire')" width="180">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.expire_at && isExpiring(row.expire_at) }">
                  {{ row.expire_at || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.integration.colActions')" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="warning" @click="showDecrypt(row)">
                  <el-icon><View /></el-icon> {{ $t('message.integration.view') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Tab: 调用日志 ── -->
      <div v-show="activeTab === 'logs'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">{{ $t('message.integration.tabLogs') }}</span>
            <el-button :icon="Refresh" text size="small" @click="loadData" :loading="loading">{{ $t('message.integration.refresh') }}</el-button>
          </div>
          <el-table :data="callLogs" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? $t('message.integration.loading') : $t('message.integration.noLogs')">
            <el-table-column prop="instance" :label="$t('message.integration.logInstance')" min-width="140" show-overflow-tooltip />
            <el-table-column prop="action" :label="$t('message.integration.logAction')" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status" :label="$t('message.integration.colStatus')" width="100">
              <template #default="{ row }">
                <span class="int-status-badge" :class="'int-status-' + row.status">
                  <span class="int-status-dot" />{{ row.status === 'success' ? $t('message.integration.logSuccess') : $t('message.integration.logFailed') }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="duration_ms" :label="$t('message.integration.logDuration')" width="100">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.duration_ms > 3000 }">{{ row.duration_ms ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="create_datetime" :label="$t('message.integration.logTime')" width="180" />
          </el-table>
        </div>
      </div>

      <!-- ── Tab: 云同步 ── -->
      <div v-show="activeTab === 'cloud-sync'" class="int-section g-fade-in-up">
        <CloudSync />
      </div>
    </div>

    <!-- ===== Edit Instance Dialog ===== -->
    <el-dialog v-model="showEditInstance" :title="$t('message.integration.editTitle')" width="600px" top="6vh"
      destroy-on-close class="int-dialog">
      <el-form label-width="100px" class="int-form">
        <el-form-item :label="$t('message.integration.colName')">
          <el-input v-model="editForm.name" :placeholder="$t('message.integration.colName')" />
        </el-form-item>
        <el-form-item :label="$t('message.integration.colType')">
          <span class="int-edit-def-name">{{ editForm.definitionName }}</span>
          <el-tag size="small" effect="plain" style="margin-left:8px">{{ editForm.definitionCode }}</el-tag>
        </el-form-item>
        <!-- 动态配置字段 (api_base, model 等) -->
        <template v-for="(field, fk) in editConfigFields" :key="fk">
          <el-form-item :label="field.title || fk">
            <el-input v-model="editConfig[fk]" :placeholder="field.placeholder || ''" />
          </el-form-item>
        </template>
        <el-divider content-position="left">{{ $t('message.integration.tabCredentials') }}</el-divider>
        <div class="int-cred-list">
          <div v-for="(cred, idx) in editCredentials" :key="cred.id || idx" class="int-cred-row">
            <el-select v-model="cred.cred_type" size="small" style="width:140px;flex-shrink:0;" :placeholder="$t('message.integration.colType')">
              <el-option v-for="opt in credTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-input v-model="cred.name" size="small" style="width:160px;flex-shrink:0;" :placeholder="$t('message.integration.credName')" />
            <el-input v-model="cred.encrypted_value" size="small" style="flex:1;" :type="cred.showSecret ? 'text' : 'password'"
              :placeholder="cred.id ? $t('message.integration.editCredReplaceHint') : $t('message.integration.editCredValuePlaceholder')" />
            <el-button :icon="View" size="small" text @click="cred.showSecret = !cred.showSecret" />
            <el-button :icon="Delete" size="small" text type="danger"
              :loading="cred._deleting" @click="deleteCredential(cred, idx)" />
          </div>
        </div>
        <el-button size="small" :icon="Plus" @click="addCredentialRow" :disabled="editForm.id === null">
          {{ $t('message.integration.addCredential') }}
        </el-button>
      </el-form>
      <template #footer>
        <el-button @click="showEditInstance = false">{{ $t('message.integration.cancel') }}</el-button>
        <el-button type="primary" @click="onSaveEdit" :loading="editSubmitting">{{ $t('message.integration.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== Add Instance Dialog ===== -->
    <el-dialog v-model="showAddInstance" :title="$t('message.integration.addTitle')" width="600px" top="6vh"
      destroy-on-close class="int-dialog">
      <el-form label-width="110px" class="int-form">
        <el-form-item :label="$t('message.integration.colType')">
          <el-select v-model="newInstance.definition_id" :placeholder="$t('message.integration.addConnectorPlaceholder')" style="width:100%"
            @change="onDefChange">
            <el-option v-for="d in definitions" :key="d.id"
                       :label="`${d.name} (${d.code})`" :value="d.id">
              <span>{{ d.name }}</span>
              <el-tag v-if="d.category === 'ai'" size="small" type="warning" style="margin-left:8px">AI</el-tag>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.integration.colName')">
          <el-input v-model="newInstance.name" :placeholder="$t('message.integration.addNamePlaceholder')" />
        </el-form-item>
        <template v-if="newInstance.definition_id && addConfigFields.length">
          <el-divider content-position="left">{{ $t('message.integration.configTitle') }}</el-divider>
          <el-form-item v-for="field in addConfigFields" :key="field.key" :label="field.title">
            <el-input v-if="field.type === 'string' && field.key !== 'webhook_url' && field.key !== 'bot_token' && field.key !== 'api_url'"
              v-model="addConfigValues[field.key]" :placeholder="field.default || field.title" />
            <el-input v-else-if="field.type === 'string'"
              v-model="addConfigValues[field.key]" :placeholder="field.default || field.title" />
            <el-input-number v-else-if="field.type === 'integer'"
              v-model="addConfigValues[field.key]" :min="0" :max="65535" style="width:100%" />
          </el-form-item>
        </template>
        <template v-if="newInstance.definition_id">
          <el-divider content-position="left">{{ $t('message.integration.tabCredentials') }}</el-divider>
          <div class="int-cred-list">
            <div v-for="(cred, idx) in addCredentials" :key="idx" class="int-cred-row">
              <el-select v-model="cred.cred_type" size="small" style="width:130px;flex-shrink:0;" :placeholder="$t('message.integration.credType')">
                <el-option v-for="opt in credTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
              <el-input v-model="cred.name" size="small" style="width:150px;flex-shrink:0;" :placeholder="$t('message.integration.credName')" />
              <el-input v-model="cred.encrypted_value" size="small" style="flex:1;" type="password" :placeholder="$t('message.integration.credValuePlaceholder')" />
              <el-button :icon="Delete" size="small" text type="danger" @click="removeAddCredential(idx)" />
            </div>
          </div>
          <el-button size="small" :icon="Plus" @click="addAddCredentialRow">
            {{ $t('message.integration.addCredential') }}
          </el-button>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showAddInstance = false">{{ $t('message.integration.cancel') }}</el-button>
        <el-button type="primary" @click="onAddInstance" :loading="submitting">{{ $t('message.integration.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== AI Chat Test Dialog ===== -->
    <el-dialog v-model="showChatTest" :title="$t('message.integration.aiTestTitle')" width="560px" top="8vh"
      destroy-on-close class="int-dialog">
      <div class="int-chat-area">
        <el-input v-model="chatPrompt" type="textarea" :rows="3"
          :placeholder="$t('message.integration.chatPlaceholder')" />
      </div>
      <div v-if="chatResponse" class="int-chat-response g-fade-in-up">
        <div class="int-chat-response-header">{{ $t('message.integration.response') }}</div>
        <pre class="int-chat-response-body">{{ chatResponse }}</pre>
      </div>
      <template #footer>
        <el-button @click="showChatTest = false">{{ $t('message.integration.close') }}</el-button>
        <el-button type="warning" :loading="chatTesting" @click="onTestChat">
          <el-icon><Promotion /></el-icon> {{ $t('message.integration.sendTest') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts" name="IntegrationHub">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import { connectorDefinitionApi, connectorInstanceApi, credentialApi, callLogApi, HealthCheck, ToggleInstance, DecryptCredential } from '/@/api/integration/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request } from '/@/utils/service'
import { Search, Refresh, Plus, Connection, List, Key, Document, Edit, Finished, ChatDotSquare, View, Promotion, Delete, Cloudy } from '@element-plus/icons-vue'
import CloudSync from './cloud-sync.vue'

/* --- TypeScript Interfaces --- */
interface ConnectorDef {
  id: number; code: string; name: string; category: string; version: string;
  description?: string; is_active?: boolean; config_schema?: Record<string, any>; provider_class?: string;
}
interface ConnectorInst {
  id: number; name: string; definition: number; definition_code?: ConnectorDef;
  status: string; is_active: boolean; config?: Record<string, any>; last_health_check?: string;
  last_health_message?: string; create_datetime?: string;
}
interface Credential {
  id?: number; instance?: number; name: string; cred_type: string;
  encrypted_value: string; expire_at?: string; last_used_at?: string;
  remark?: string; create_datetime?: string;
  // local only
  showSecret?: boolean; _deleting?: boolean; _existing?: boolean;
}
interface CallLog {
  id: number; instance: string; action: string; status: string;
  duration_ms?: number; create_datetime: string;
}
/* --- End Interfaces --- */

const { t } = useI18n()

const activeTab = ref('instances')
const defCategoryFilter = ref('all')
const searchQuery = ref('')

const loading = ref(false)
const submitting = ref(false)
const definitions = ref<ConnectorDef[]>([])
const instances = ref<ConnectorInst[]>([])
const credentials = ref<Credential[]>([])
const callLogs = ref<CallLog[]>([])

const showAddInstance = ref(false)
const newInstance = ref<{ definition_id: number | null; name: string }>({ definition_id: null, name: '' })
const addConfigFields = ref<{ key: string; title: string; type: string; default?: string }[]>([])
const addConfigValues = ref<Record<string, any>>({})
const addCredentials = ref<{ name: string; cred_type: string; encrypted_value: string }[]>([])

function onDefChange(defId: number) {
  const def = definitions.value.find(d => d.id === defId)
  addConfigFields.value = []
  addConfigValues.value = {}
  if (def?.config_schema?.properties) {
    const props = def.config_schema.properties
    addConfigFields.value = Object.entries(props).map(([key, val]: [string, any]) => ({
      key,
      title: val.title || key,
      type: val.type || 'string',
      default: val.default || '',
    }))
    // Set defaults
    for (const f of addConfigFields.value) {
      if (f.default) addConfigValues.value[f.key] = f.default
    }
  }
  // Reset credentials
  addCredentials.value = []
}

function addAddCredentialRow() {
  addCredentials.value.push({ name: '', cred_type: 'access_key', encrypted_value: '' })
}

function removeAddCredential(idx: number) {
  addCredentials.value.splice(idx, 1)
}

const showEditInstance = ref(false)
const editSubmitting = ref(false)
const editForm = ref<{ id: number | null; name: string; definitionName: string; definitionCode: string }>({ id: null, name: '', definitionName: '', definitionCode: '' })
const editConfig = ref<Record<string, any>>({})
const editConfigFields = ref<Record<string, any>>({})
const editCredentials = ref<Credential[]>([])

const showChatTest = ref(false)
const chatTesting = ref(false)
const chatPrompt = ref(t('message.integration.defaultPrompt'))
const chatResponse = ref('')
const chatInstanceId = ref<number | null>(null)

const categoryLabels: Record<string, string> = {
  cloud: t('message.integration.catCloud'), notification: t('message.integration.catNotification'), auth: t('message.integration.catAuth'),
  paas: t('message.integration.catPaas'), monitor: t('message.integration.catMonitor'), ai: t('message.integration.catAi'),
  automation: t('message.integration.catAutomation'), log: t('message.integration.catLog'),
  scm: t('message.integration.catScm'), cicd: t('message.integration.catCicd'),
  other: t('message.integration.catOther'),
}
function categoryLabel(cat: string) { return categoryLabels[cat] || cat || t('message.integration.catUnknown') }

function statusLabel(s: string) {
  const map: Record<string, string> = {
    online: t('message.integration.statusOnline'),
    offline: t('message.integration.statusOffline'),
    error: t('message.integration.statusError'),
    unknown: t('message.integration.statusUnknown'),
    connected: t('message.integration.statusConnected'),
    success: t('message.integration.statusSuccess'),
    failed: t('message.integration.statusFailed'),
  }
  return map[s] || s || t('message.integration.unknown')
}

const credTypeOptions = computed(() => [
  { value: 'access_key', label: t('message.integration.credTypeAccessKey') },
  { value: 'password', label: t('message.integration.credTypePassword') },
  { value: 'token', label: t('message.integration.credTypeToken') },
  { value: 'certificate', label: t('message.integration.credTypeCertificate') },
])

function tagType(cat: string) {
  const map: Record<string, string> = { cloud: 'primary', notification: 'success', ai: 'warning', monitor: 'danger', other: 'info' }
  return map[cat] || 'info'
}

const onlineCount = computed(() => instances.value.filter(i => i.status === 'online' || i.status === 'connected').length)

const filteredDefinitions = computed(() => {
  let items = definitions.value
  if (defCategoryFilter.value !== 'all') {
    items = items.filter(d => d.category === defCategoryFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(d => d.name.toLowerCase().includes(q) || d.code?.toLowerCase().includes(q))
  }
  return items
})

function defIcon(cat: string) {
  const map: Record<string, any> = {
    ai: markRaw(ChatDotSquare), cloud: markRaw(Connection),
    notification: markRaw(Promotion), monitor: markRaw(Finished),
    automation: markRaw(Connection), log: markRaw(Document),
    scm: markRaw(Connection), cicd: markRaw(Refresh),
    auth: markRaw(Key), paas: markRaw(List),
    other: markRaw(List),
  }
  return map[cat] || markRaw(List)
}

function isExpiring(dateStr: string) {
  return new Date(dateStr).getTime() < Date.now() + 7 * 24 * 60 * 60 * 1000
}

function onSearch() {
  // Filtering is reactive via filteredDefinitions
}

async function loadData() {
  loading.value = true
  try {
    const [defRes, insRes, credRes, logRes] = await Promise.all([
      connectorDefinitionApi.list({ limit: 1000 }),
      connectorInstanceApi.list({ limit: 1000 }),
      credentialApi.list(),
      callLogApi.list({ limit: 50 }),
    ])
    definitions.value = defRes.data || []
    instances.value = insRes.data || []
    credentials.value = credRes.data || []
    callLogs.value = logRes.data || []
  } finally {
    loading.value = false
  }
}

async function runHealthCheck(row: ConnectorInst) {
  try {
    await HealthCheck(row.id)
    ElMessage.success(t('message.integration.healthCheckDone'))
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.healthCheckFailed'))
  }
}

async function toggleInstance(row: ConnectorInst) {
  try {
    await ToggleInstance(row.id)
    ElMessage.success(t('message.integration.operationSuccess'))
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.operationFailed'))
  }
}

async function showDecrypt(row: Credential) {
  try {
    const res = await DecryptCredential(row.id)
    ElMessage.info(t('message.integration.credValue') + ': ' + res.data.decrypted_value)
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.decryptFailed'))
  }
}

async function editInstance(row: ConnectorInst) {
  editForm.value = {
    id: row.id,
    name: row.name || '',
    definitionName: row.definition_code?.name || '',
    definitionCode: row.definition_code?.code || '',
  }
  editConfig.value = { ...(row.config || {}) }
  editCredentials.value = []
  showEditInstance.value = true
  // 加载连接器定义的 config_schema 以渲染动态表单字段
  const defId = row.definition_code?.id || row.definition
  if (defId) {
    try {
      const defRes = await connectorDefinitionApi.detail(defId)
      const defData = defRes.data || defRes
      const schema = defData.config_schema || {}
      editConfigFields.value = schema.properties || {}
    } catch {
      editConfigFields.value = {}
    }
  } else {
    editConfigFields.value = {}
  }
  await loadEditCredentials(row.id)
}

async function loadEditCredentials(instanceId: number) {
  try {
    const res = await credentialApi.list({ instance: instanceId })
    editCredentials.value = (res.data || []).map((c: Credential) => ({
      ...c,
      encrypted_value: '',
      showSecret: false,
      _deleting: false,
      _existing: true,  // 标记为已有记录
    }))
  } catch { /* ignore */ }
}

function addCredentialRow() {
  editCredentials.value.push({
    id: null,
    name: '',
    cred_type: 'access_key',
    encrypted_value: '',
    showSecret: false,
    _deleting: false,
    _existing: false,
  })
}

async function deleteCredential(cred: Credential, idx: number) {
  if (!cred.id) {
    editCredentials.value.splice(idx, 1)
    return
  }
  cred._deleting = true
  try {
    await credentialApi.delete(cred.id)
    editCredentials.value.splice(idx, 1)
    ElMessage.success(t('message.integration.credDeleted'))
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.deleteFailed'))
  } finally {
    cred._deleting = false
  }
}

async function deleteInstance(row: any) {
  try {
    await ElMessageBox.confirm(
      t('message.integration.deleteConfirm', { name: row.name }),
      t('message.integration.confirmDelete'),
      { type: 'warning', confirmButtonText: t('message.integration.delete'), cancelButtonText: t('message.integration.cancel') },
    )
    await connectorInstanceApi.delete(row.id)
    ElMessage.success(t('message.integration.deleteSuccess'))
    await loadData()
  } catch { /* cancelled */ }
}

async function onSaveEdit() {
  if (!editForm.value.name) {
    ElMessage.warning(t('message.integration.enterName'))
    return
  }
  editSubmitting.value = true
  try {
    // 更新实例名称和配置
    const updateData: Record<string, any> = { name: editForm.value.name }
    if (Object.keys(editConfigFields.value).length > 0) {
      updateData.config = { ...editConfig.value }
    }
    await connectorInstanceApi.update(editForm.value.id, updateData)

    // 处理凭证：新建或更新已有
    for (const cred of editCredentials.value) {
      if (!cred.encrypted_value && cred._existing) continue  // 已有记录且未修改密码
      if (!cred.encrypted_value) continue  // 新建但无值
      if (!cred.name) continue

      if (cred._existing) {
        // 更新已有凭证
        await credentialApi.update(cred.id, {
          name: cred.name,
          cred_type: cred.cred_type,
          encrypted_value: cred.encrypted_value,
        })
      } else {
        // 新建凭证
        await credentialApi.create({
          instance: editForm.value.id,
          name: cred.name,
          cred_type: cred.cred_type,
          encrypted_value: cred.encrypted_value,
        })
      }
    }

    ElMessage.success(t('message.integration.saveSuccess'))
    showEditInstance.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.saveFailed'))
  } finally {
    editSubmitting.value = false
  }
}

function createInstance(def: ConnectorDef) {
  newInstance.value = { definition_id: def.id, name: t('message.integration.instanceSuffix', { name: def.name }) }
  addConfigFields.value = []
  addConfigValues.value = {}
  addCredentials.value = []
  // Trigger config fields load
  onDefChange(def.id)
  showAddInstance.value = true
}

async function onAddInstance() {
  if (!newInstance.value.definition_id || !newInstance.value.name) {
    ElMessage.warning(t('message.integration.fillInfo'))
    return
  }
  submitting.value = true
  try {
    const res = await connectorInstanceApi.create({
      definition: newInstance.value.definition_id,
      name: newInstance.value.name,
      config: addConfigValues.value,
      is_active: true,
    })
    const instanceId = res.data?.id
    // Save credentials
    if (instanceId) {
      for (const cred of addCredentials.value) {
        if (!cred.name || !cred.encrypted_value) continue
        await credentialApi.create({
          instance: instanceId,
          name: cred.name,
          cred_type: cred.cred_type,
          encrypted_value: cred.encrypted_value,
        })
      }
    }
    ElMessage.success(t('message.integration.createSuccess'))
    showAddInstance.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.integration.createFailed'))
  } finally {
    submitting.value = false
  }
}

function testAiChat(row: ConnectorInst) {
  chatInstanceId.value = row.id
  chatPrompt.value = t('message.integration.defaultPrompt')
  chatResponse.value = ''
  showChatTest.value = true
}

async function onTestChat() {
  if (!chatInstanceId.value || !chatPrompt.value) {
    ElMessage.warning(t('message.integration.enterPrompt'))
    return
  }
  chatTesting.value = true
  chatResponse.value = ''
  try {
    const res = await request({
      url: `/api/integration/connector-instances/${chatInstanceId.value}/ai_chat/`,
      method: 'post',
      data: { prompt: chatPrompt.value },
    })
    chatResponse.value = res.data?.content || res.data?.message || JSON.stringify(res.data)
  } catch (e: any) {
    chatResponse.value = `${t('message.integration.chatFailed')}: ${e?.msg || e?.message || t('message.integration.unknown')}`
  } finally {
    chatTesting.value = false
  }
}

onMounted(async () => {
  await loadData()

  // Onboarding tour message
  const key = 'opsflow_tour_integration'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: t('message.integration.onboardingMessage'), duration: 1500 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

// ===== Page Layout =====
.int-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: $g-bg-page;
  overflow: hidden;
}

// ===== Hero =====
.int-hero {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.int-hero-bg {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  background-image:
    radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px),
    radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.int-hero-inner {
  position: relative;
  z-index: 1;
  padding: 14px 24px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
}
.int-hero-left { flex: 0 0 auto; }
.int-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.int-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.int-hero-center { flex: 1 1 auto; min-width: 0; max-width: 360px; }
.int-search-input { width: 100%; }
.int-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none;
  border-radius: 10px;
  padding: 2px 12px;
}
.int-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.int-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.int-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.int-hero-stats { flex: 0 0 auto; display: flex; align-items: center; margin-left: auto; }
.int-stat-item { text-align: center; padding: 0 14px; }
.int-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.int-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.int-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

// ===== Hero Tabs =====
.int-hero-tabs {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 0;
  padding: 0 24px;
  margin-top: -4px;
}
.int-hero-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
  user-select: none;
  .el-icon { font-size: 16px; }
}
.int-hero-tab:hover { color: rgba(255,255,255,0.9); }
.int-hero-tab.active {
  color: #fff;
  border-bottom-color: #409EFF;
}

// ===== Body =====
.int-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 24px;
}
.int-section {
  padding-top: 16px;
}

// ===== Filter bar =====
.int-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 16px;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: $g-bg-page;
}
.int-filter-tabs { display: flex; gap: 4px; }
.int-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: $g-text-secondary;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.int-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.int-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.int-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.int-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

// ===== Definition Grid =====
.int-def-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.int-def-card {
  border-radius: $g-radius-card;
  overflow: hidden;
  @include g-hover-lift;
}
.int-def-card-inner {
  background: #fff;
  border: 1px solid $g-border-default;
  border-radius: $g-radius-card;
  padding: 18px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.int-def-card-ai .int-def-card-inner {
  border-color: #e6a23c;
  background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%);
}
.int-def-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.int-def-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;
}
.int-def-icon-ai { background: linear-gradient(135deg, #e6a23c, #f4c152); }
.int-def-icon-cloud { background: linear-gradient(135deg, #409EFF, #337ecc); }
.int-def-icon-notification { background: linear-gradient(135deg, #67C23A, #85ce61); }
.int-def-icon-monitor { background: linear-gradient(135deg, #F56C6C, #f78989); }
.int-def-icon-automation { background: linear-gradient(135deg, #722ed1, #b37feb); }
.int-def-icon-log { background: linear-gradient(135deg, #13c2c2, #5cdbd3); }
.int-def-icon-scm { background: linear-gradient(135deg, #eb2f96, #ff85c0); }
.int-def-icon-cicd { background: linear-gradient(135deg, #fa8c16, #ffc069); }
.int-def-icon-auth { background: linear-gradient(135deg, #1890ff, #69c0ff); }
.int-def-icon-paas { background: linear-gradient(135deg, #5c6bc0, #9fa8da); }
.int-def-icon-other { background: linear-gradient(135deg, #909399, #a6a9ad); }
.int-cat-tag { font-size: 11px; }
.int-def-name { font-weight: 600; font-size: 15px; color: $g-text-primary; margin-bottom: 4px; }
.int-def-code { margin-bottom: 6px; }
.int-def-code code { font-size: 12px; color: $g-text-muted; }
.int-def-desc { font-size: 12px; color: $g-text-secondary; margin-bottom: 10px; line-height: 1.5; flex: 1; }
.int-def-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid $g-border-light;
}

// ===== Table Card =====
.int-table-card {
  background: #fff;
  border-radius: $g-radius-card;
  box-shadow: $g-shadow-card;
  overflow: hidden;
}
.int-table-card :deep(.el-table th.el-table__cell) {
  background: $g-bg-header;
  color: $g-text-primary;
  font-weight: 600;
  font-size: 12px;
}
.int-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.int-table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px 0;
}
.int-table-title {
  font-size: 15px;
  font-weight: 600;
  color: $g-text-primary;
}

// ===== Status Badges =====
.int-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: $g-radius-sm;
}
.int-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.int-status-online .int-status-dot { background: #67C23A; }
.int-status-online { background: #f0f9eb; color: #67C23A; }
.int-status-connected .int-status-dot { background: #67C23A; }
.int-status-connected { background: #f0f9eb; color: #67C23A; }
.int-status-offline .int-status-dot { background: #c0c4cc; }
.int-status-offline { background: #f5f7fa; color: #909399; }
.int-status-error .int-status-dot { background: #F56C6C; }
.int-status-error { background: #fef0f0; color: #F56C6C; }
.int-status-unknown .int-status-dot { background: #c0c4cc; }
.int-status-unknown { background: #f5f7fa; color: #909399; }
.int-status-success .int-status-dot { background: #67C23A; }
.int-status-success { background: #f0f9eb; color: #67C23A; }
.int-status-failed .int-status-dot { background: #F56C6C; }
.int-status-failed { background: #fef0f0; color: #F56C6C; }

// ===== Dialog =====
.int-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.int-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.int-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
.int-form .el-form-item:last-child { margin-bottom: 0; }
.int-edit-def-name { font-weight: 600; color: $g-text-primary; }
.int-cred-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.int-cred-row { display: flex; align-items: center; gap: 6px; }

// ===== Chat =====
.int-chat-area { margin-bottom: 16px; }
.int-chat-response {
  border: 1px solid $g-border-default;
  border-radius: $g-radius-sm;
  padding: 14px;
  background: #f5f7fa;
}
.int-chat-response-header { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: $g-text-secondary; }
.int-chat-response-body {
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: $g-text-primary;
}

// ===== Utilities =====
.text-danger { color: #F56C6C; font-weight: 500; }
.text-warning { color: #E6A23C; font-weight: 500; }
</style>
