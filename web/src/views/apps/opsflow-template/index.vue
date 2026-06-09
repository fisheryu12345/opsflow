<template>
  <div class="tpl-page">
    <!-- Hero Section -->
    <div class="tpl-hero">
      <div class="tpl-hero-bg" />
      <div class="tpl-hero-inner">
        <div class="tpl-hero-left">
          <h1 class="tpl-hero-title">Templates</h1>
          <p class="tpl-hero-subtitle">Pipeline template library</p>
        </div>
        <ProjectSwitcher :dark="true" />
        <div class="tpl-hero-center">
          <el-input v-model="filterName" placeholder="Search templates..." clearable size="default"
            class="tpl-search-input" @keyup.enter="onFilter" @clear="onFilter">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="tpl-hero-stats">
          <div class="tpl-stat-item"><span class="tpl-stat-value">{{ total }}</span><span class="tpl-stat-label">Total</span></div>
          <div class="tpl-stat-divider" />
          <div class="tpl-stat-item"><span class="tpl-stat-value">{{ pubCount }}</span><span class="tpl-stat-label">Published</span></div>
          <div class="tpl-stat-divider" />
          <div class="tpl-stat-item"><span class="tpl-stat-value">{{ draftCount }}</span><span class="tpl-stat-label">Draft</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="tpl-body">
      <!-- Scope Tabs: Project vs Public -->
      <div class="tpl-scope-tabs">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <el-tab-pane :label="'📁 ' + t('message.template.projectTemplates')" name="project" />
          <el-tab-pane :label="'🌐 ' + t('message.template.publicTemplates')" name="public" />
        </el-tabs>
      </div>
      <!-- Filter bar -->
      <div class="tpl-filter-bar">
        <div class="tpl-filter-tabs">
          <div class="tpl-tab" :class="{ active: filterStatus === '' }" @click="filterStatus = ''; onFilter()">
            <span class="tpl-tab-dot" style="background:#409EFF" />All
          </div>
          <div class="tpl-tab" :class="{ active: filterStatus === 'published' }" @click="filterStatus = 'published'; onFilter()">
            <span class="tpl-tab-dot" style="background:#67C23A" />Published
          </div>
          <div class="tpl-tab" :class="{ active: filterStatus === 'draft' }" @click="filterStatus = 'draft'; onFilter()">
            <span class="tpl-tab-dot" style="background:#E6A23C" />Draft
          </div>
        </div>
        <div class="tpl-filter-actions">
          <el-select v-model="filterCategory" placeholder="Category" clearable filterable size="small" style="width:140px" @change="onFilter">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">{{ $t('message.common.refresh') }}</el-button>
          <div class="tpl-view-toggle" :class="viewMode" @click="viewMode = viewMode === 'table' ? 'cards' : 'table'">
            <div class="tpl-toggle-btn"><el-icon :size="13"><component :is="viewMode === 'table' ? 'Grid' : 'List'" /></el-icon></div>
          </div>
          <el-tooltip content="Import" placement="top">
            <div class="tpl-view-toggle" @click="openImport">
              <div class="tpl-toggle-btn"><el-icon :size="13"><UploadFilled /></el-icon></div>
            </div>
          </el-tooltip>
        </div>
      </div>

      <!-- Table view -->
      <template v-if="viewMode === 'table'">
        <div class="tpl-table-card">
          <el-table :data="displayList" v-loading="loading" stripe highlight-current-row
            style="width:100%" :empty-text="emptyText" @row-click="openView" size="small">
            <el-table-column prop="name" :label="$t('message.common.name')" width="160" show-overflow-tooltip />
            <el-table-column :label="$t('message.execution.status')" width="120" align="center">
              <template #default="{ row }">
                <span class="tpl-status-badge" :class="row.is_draft ? 'st-draft' : 'st-published'">{{ row.is_draft ? 'Draft' : 'Published' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="Scope" width="110" align="center" v-if="activeTab === 'public'">
              <template #default="{ row }">
                <el-tooltip :content="formatScope(row.project_scope)" placement="top">
                  <span class="tpl-scope-badge">{{ formatScopeShort(row.project_scope) }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column label="Pipeline" min-width="160" class-name="pipeline-col">
              <template #default="{ row }">
                <div class="tpl-mini-flow" v-if="row.pipeline_tree?.nodes?.length">
                  <template v-for="(node, ni) in row.pipeline_tree.nodes.slice(0, 6)" :key="node.id">
                    <div class="tpl-mini-node" :style="{ background: nodeColor(node) }" :title="`${node.label || node.id}`">
                      <span class="tpl-mini-icon">{{ nodeIcon(node) }}</span>
                    </div>
                    <div v-if="ni < Math.min(row.pipeline_tree.nodes.length, 6) - 1" class="tpl-mini-arrow">→</div>
                  </template>
                  <span v-if="row.pipeline_tree.nodes.length > 6" class="tpl-mini-more">+{{ row.pipeline_tree.nodes.length - 6 }}</span>
                </div>
                <span v-else class="tpl-no-pl">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="Category" width="120" show-overflow-tooltip />
            <el-table-column prop="created_by_name" label="Creator" width="120" show-overflow-tooltip />
            <el-table-column label="Version" width="120" align="center">
              <template #default="{ row }">
                <span v-if="!row.is_draft" class="tpl-version">V{{ row.version || 1 }}</span>
                <span v-else class="tpl-no-pl">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="Created" width="140" />
            <el-table-column label="Actions" width="280" fixed="right">
              <template #default="{ row }">
                <div class="tpl-actions">
                  <el-tooltip content="Edit in Designer" placement="top">
                    <el-button size="small" text type="primary" @click.stop="goEditTemplate(row)"><el-icon><Edit /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip v-if="!row.is_public || isSuperuser" content="Modify Info" placement="top">
                    <el-button size="small" text type="primary" @click.stop="openEdit(row)"><el-icon><Setting /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip v-if="!row.is_public || isSuperuser" :content="row.is_draft ? 'Publish' : 'New Version'" placement="top">
                    <el-button size="small" text type="success" :loading="publishingId === row.id" @click.stop="handlePublish(row)"><el-icon><Upload /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip v-if="!row.is_draft && (!row.is_public || isSuperuser)" content="Schedule" placement="top">
                    <el-button size="small" text type="warning" @click.stop="openSchedule(row)"><el-icon><Timer /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip content="Versions" placement="top">
                    <el-button size="small" text type="info" @click.stop="openVersions(row)"><el-icon><Clock /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip content="Export" placement="top">
                    <el-button size="small" text @click.stop="handleExport(row)"><el-icon><Download /></el-icon></el-button>
                  </el-tooltip>
                  <el-popconfirm v-if="!row.is_public || isSuperuser" title="Delete this template?" @confirm.stop="handleDelete(row)">
                    <template #reference>
                      <el-tooltip :content="$t('message.common.delete')" placement="top">
                        <el-button size="small" text type="danger" @click.stop><el-icon><Delete /></el-icon></el-button>
                      </el-tooltip>
                    </template>
                  </el-popconfirm>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div class="tpl-pagination" v-if="total > 0">
            <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
              layout="prev, pager, next, total" @current-change="onPageChange" small />
          </div>
        </div>
      </template>

      <!-- Card view -->
      <template v-if="viewMode === 'cards'">
        <div class="tpl-grid" v-loading="loading">
          <el-empty v-if="!loading && displayList.length === 0" :description="emptyText" :image-size="80" />
          <div v-for="item in displayList" :key="item.id" class="tpl-card" @click="openView(item)">
            <div class="tpl-card-top">
              <div class="tpl-card-header">
                <span class="tpl-card-badge" :class="item.is_draft ? 'st-draft' : 'st-published'">{{ item.is_draft ? 'Draft' : 'Published' }}</span>
                <span v-if="item.category" class="tpl-card-cat">{{ item.category }}</span>
              </div>
              <div class="tpl-card-name">{{ item.name }}</div>
              <div class="tpl-card-desc" v-if="item.description">{{ item.description }}</div>
            </div>
            <div class="tpl-card-bottom">
              <div class="tpl-card-stats">
                <span class="tpl-stat-chip"><b>{{ item.pipeline_tree?.nodes?.length || 0 }}</b> nodes</span>
                <span class="tpl-stat-chip"><b>{{ item.pipeline_tree?.edges?.length || 0 }}</b> edges</span>
                <span v-if="!item.is_draft" class="tpl-stat-chip">V{{ item.version || 1 }}</span>
              </div>
              <div class="tpl-card-actions" @click.stop>
                <el-button size="small" text type="primary" @click.stop="goEditTemplate(item)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button v-if="!item.is_public || isSuperuser" size="small" text type="primary" @click.stop="openEdit(item)">
                  <el-icon><Setting /></el-icon>
                </el-button>
                <el-button v-if="(!item.is_public || isSuperuser) && item.is_draft" size="small" text type="success" :loading="publishingId === item.id" @click.stop="handlePublish(item)">
                  <el-icon><Upload /></el-icon>
                </el-button>
                <el-button v-if="(!item.is_public || isSuperuser) && !item.is_draft" size="small" text type="success" :loading="publishingId === item.id" @click.stop="handlePublish(item)">
                  <el-icon><Upload /></el-icon>
                </el-button>
                <el-button v-if="!item.is_draft && (!item.is_public || isSuperuser)" size="small" text type="warning" @click.stop="openSchedule(item)">
                  <el-icon><Timer /></el-icon>
                </el-button>
                <el-button size="small" text type="info" @click.stop="openVersions(item)">
                  <el-icon><Clock /></el-icon>
                </el-button>
                <el-button size="small" text @click.stop="handleExport(item)">
                  <el-icon><Download /></el-icon>
                </el-button>
                <el-popconfirm v-if="!item.is_public || isSuperuser" title="Delete?" @confirm.stop="handleDelete(item)">
                  <template #reference><el-button size="small" text type="danger"><el-icon><Delete /></el-icon></el-button></template>
                </el-popconfirm>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Edit dialog -->
    <el-dialog v-model="formVisible" title="Edit Template" width="480px" top="15vh" destroy-on-close>
      <el-form label-width="90px" size="small">
        <el-form-item :label="$t('message.common.name')" required>
          <el-input v-model="form.name" placeholder="Template name" maxlength="200" />
        </el-form-item>
        <el-form-item label="Category">
          <el-input v-model="form.category" placeholder="e.g. Inspection, Backup, Deploy" maxlength="64" />
        </el-form-item>
        <el-form-item label="Desc">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="Optional description" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false" size="small">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" size="small">Update</el-button>
      </template>
    </el-dialog>

    <!-- View dialog -->
    <el-dialog v-model="viewVisible" title="Template Detail" width="760px" top="5vh" destroy-on-close class="tpl-view-dialog">
      <template v-if="viewRow">
        <div class="tpl-view-meta">
          <span class="tpl-status-badge" :class="viewRow.is_draft ? 'st-draft' : 'st-published'">{{ viewRow.is_draft ? 'Draft' : 'Published' }}</span>
          <span v-if="viewRow.category" class="tpl-view-cat">{{ viewRow.category }}</span>
          <span class="tpl-view-info">By {{ viewRow.created_by_name || '-' }}</span>
          <span class="tpl-view-info">{{ viewRow.created_at }}</span>
        </div>
        <div class="tpl-view-section" v-if="viewRow.pipeline_tree?.nodes?.length">
          <div class="tpl-view-section-title">Pipeline Flow</div>
          <div class="tpl-view-pipeline">
            <div v-for="(node, ni) in viewRow.pipeline_tree.nodes" :key="node.id" class="tpl-vp-node-wrapper">
              <div class="tpl-vp-node" :style="{ background: nodeColor(node, true), borderColor: nodeColor(node) }">
                <div class="tpl-vp-node-header">
                  <span class="tpl-vp-node-icon">{{ nodeIcon(node) }}</span>
                  <span class="tpl-vp-node-name">{{ node.label || node.id }}</span>
                </div>
                <div class="tpl-vp-node-body">
                  <span class="tpl-vp-node-type">{{ node.node_type || 'atom' }}</span>
                  <span v-if="node.atom_type" class="tpl-vp-node-atom">{{ node.atom_type }}</span>
                </div>
              </div>
              <div v-if="ni < viewRow.pipeline_tree.nodes.length - 1" class="tpl-vp-connector">
                <div class="tpl-vp-arrow">↓</div>
                <div class="tpl-vp-line" />
              </div>
            </div>
          </div>
        </div>
        <div class="tpl-view-actions">
          <el-button size="small" :icon="Edit" @click="goEditTemplate(viewRow); viewVisible = false">{{ $t('message.common.edit') }}</el-button>
          <el-button size="small" :icon="Upload" @click="handlePublish(viewRow)">Publish</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Schedule dialog -->
    <ScheduleManager v-model="scheduleVisible" :template-id="scheduleTemplateId" :template-name="scheduleTemplateName" />

    <!-- Version dialog -->
    <VersionDialog v-model:visible="versionVisible" :template-id="versionTemplateId"
      :template-name="versionTemplateName" :current-version="versionCurrentVer" @rolled-back="fetchData" />

    <!-- Import dialog -->
    <el-dialog v-model="importVisible" title="Import Template" width="480px" top="15vh" destroy-on-close>
      <el-upload drag accept=".json" :auto-upload="false" :limit="1" :on-change="onImportFileChange" :file-list="importFiles">
        <el-icon :size="32" color="#C0C4CC"><UploadFilled /></el-icon>
        <div class="el-upload__text">Drop JSON here or <em>click to browse</em></div>
        <template #tip><div class="el-upload__tip">Exported template JSON (.json)</div></template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false" size="small">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importData" @click="handleImport" size="small">{{ $t('message.common.import') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Refresh, Upload, Edit, Delete, Search, List, Grid, Connection, Share, Timer, Setting, Clock, Download, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetTemplates, UpdateTemplate, DeleteTemplate, ConfirmDraft, GetTemplateDetail, PublishTemplate, ExportTemplate, ImportTemplate, GetTemplateCategories } from '../opsflow/api/templates'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'
import { useUserInfo } from '/@/stores/userInfo'
import ScheduleManager from './components/ScheduleManager.vue'
import VersionDialog from './components/VersionDialog.vue'

import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'
const router = useRouter()
const opsflowStore = useOpsflowStore()
const { t } = useI18n()
const userInfo = useUserInfo()

const isSuperuser = computed(() => userInfo.userInfos?.roles?.includes('admin') || false)
const activeTab = ref<'project' | 'public'>('project')

const loading = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterName = ref('')
const filterStatus = ref('')
const filterCategory = ref('')
const categories = ref<string[]>([])
const viewMode = ref<'table' | 'cards'>('table')

const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', category: '', description: '' })

function formatScope(scope: string[] | undefined): string {
  if (!scope || scope.length === 0) return 'No projects'
  if (scope.includes('*')) return 'Visible to all projects'
  return `Visible to projects: ${scope.join(', ')}`
}
function formatScopeShort(scope: string[] | undefined): string {
  if (!scope || scope.length === 0) return '-'
  if (scope.includes('*')) return '🌐 All'
  return `${scope.length} project${scope.length > 1 ? 's' : ''}`
}

function onTabChange() {
  page.value = 1
  filterName.value = ''
  filterCategory.value = ''
  filterStatus.value = ''
  fetchData()
}

const viewVisible = ref(false)
const viewRow = ref<any>(null)
const publishingId = ref<number | null>(null)

const scheduleVisible = ref(false)
const scheduleTemplateId = ref(0)
const scheduleTemplateName = ref('')

const versionVisible = ref(false)
const versionTemplateId = ref<number | null>(null)
const versionTemplateName = ref('')
const versionCurrentVer = ref(1)

const importVisible = ref(false)
const importFiles = ref<any[]>([])
const importData = ref<any>(null)
const importing = ref(false)

const pubCount = computed(() => displayList.value.filter(t => !t.is_draft).length)
const draftCount = computed(() => displayList.value.filter(t => t.is_draft).length)
const emptyText = computed(() => loading.value ? 'Loading...' : 'No templates yet')

const displayList = computed(() => {
  let items = list.value
  if (filterStatus.value === 'published') items = items.filter(t => !t.is_draft)
  else if (filterStatus.value === 'draft') items = items.filter(t => t.is_draft)
  return items
})

function nodeColor(node: any, bg = false): string {
  const nt = node.node_type || ''
  if (nt === 'start_event') return bg ? '#67C23A22' : '#67C23A'
  if (nt === 'end_event') return bg ? '#F56C6C22' : '#F56C6C'
  if (nt.includes('gateway')) return bg ? '#E6A23C22' : '#E6A23C'

  const at = node.atom_type || ''
  const prefixColor: Record<string, string> = {
    esxi_: '#20B2AA', netapp_: '#409EFF', pmax_: '#9B59B6',
    servicenow_: '#909399', redfish_: '#E67E22', http_: '#E6A23C',
    backup_: '#27AE60', docker_: '#0DB7ED', nginx_: '#2ECC71', java_: '#C0392B',
  }
  for (const [prefix, c] of Object.entries(prefixColor)) {
    if (at.startsWith(prefix)) return bg ? c + '22' : c
  }
  const ansible = ['shell', 'file_copy', 'script_exec', 'upload_file', 'service_control', 'send_alert', 'test_print_time']
  if (ansible.includes(at)) return bg ? '#67C23A22' : '#67C23A'
  const monitor = ['disk_check', 'ping_test', 'health_check']
  if (monitor.includes(at)) return bg ? '#1ABC9C22' : '#1ABC9C'
  return bg ? '#90939922' : '#909399'
}
function nodeIcon(node: any): string {
  const nt = node.node_type || ''
  if (nt === 'start_event') return '▶'
  if (nt === 'end_event') return '⏹'
  if (nt === 'exclusive_gateway') return '◇'
  if (nt === 'parallel_gateway') return '⨁'
  if (nt === 'converge_gateway') return '⨂'
  if (nt === 'conditional_parallel_gateway') return '◇?'
  const sym: Record<string, string> = {
    shell: '⚙', file_copy: '📋', script_exec: '📜', upload_file: '📤',
    backup_file: '💾', nginx_reload: '🔄', service_control: '⏯',
    java_deploy: '☕', docker_deploy: '🐳', send_alert: '🔔',
    disk_check: '💿', ping_test: '📡', health_check: '❤',
    test_print_time: '🕐', api_call: '↗',
    esxi_create_vm: '🖥', esxi_destroy_vm: '🗑', esxi_get_state: '🔍',
    esxi_power_on: '🔛', esxi_power_off: '🔴',
    netapp_create_volume: '➕', netapp_delete_volume: '➖',
    netapp_get_volume: '🔎', netapp_modify_volume: '✏', netapp_create_snapshot: '📸',
    redfish_power_on: '🔛', redfish_power_off: '🔴', redfish_power_cycle: '🔄',
    redfish_get_system_info: 'ℹ', redfish_firmware_inventory: '📦',
    redfish_list_storage: '💾', redfish_set_boot_device: '💿',
    servicenow_create_incident: '🚨', servicenow_get_incident: '🔍',
    servicenow_update_incident: '✏', servicenow_create_change_request: '📋',
    servicenow_get_cmdb_ci: '🔎',
    pmax_performance: '📊', pmax_create_snapshot: '📸',
    pmax_storage_group: '💾',
  }
  return sym[node.atom_type] || '⬤'
}

async function loadCategories() {
  try { const r = await GetTemplateCategories(); categories.value = r.data?.data || r.data || [] } catch { categories.value = [] }
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, limit: pageSize.value }
    if (filterName.value) params.search = filterName.value
    if (filterCategory.value) params.category = filterCategory.value
    if (activeTab.value === 'public') params.is_public = true
    const res = await GetTemplates(params)
    const items = res.data?.results || res.data || res.results || []
    list.value = items; total.value = res.total || res.data?.count || res.count || items.length || 0
    await loadCategories()
  } catch { list.value = []; total.value = 0 }
  loading.value = false
}

function onFilter() { page.value = 1; fetchData() }
function onPageChange() { fetchData() }

function openEdit(row: any) {
  isEditing.value = true; editingId.value = row.id
  form.name = row.name; form.category = row.category || ''; form.description = row.description || ''
  formVisible.value = true
}

async function goEditTemplate(row: any) {
  try { const r = await GetTemplateDetail(row.id); opsflowStore.setCurrentTemplate(r.data?.data || r.data || row) } catch { opsflowStore.setCurrentTemplate(row) }
  router.push('/opsflow')
}

async function handleSave() {
  if (!form.name.trim()) { ElMessage.warning('Name is required'); return }
  if (!editingId.value) return
  try {
    const data = { name: form.name, category: form.category || '', description: form.description || '' }
    await UpdateTemplate(editingId.value, data)
    ElMessage.success('Updated')
    formVisible.value = false; await fetchData()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed') }
}

async function handlePublish(row: any) {
  publishingId.value = row.id
  try {
    if (row.is_draft) { await ConfirmDraft(row.id); ElMessage.success('Published as V1') }
    else { await PublishTemplate(row.id); ElMessage.success('New version published') }
    await fetchData()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Publish failed') }
  publishingId.value = null
}

function openImport() { importVisible.value = true; importFiles.value = []; importData.value = null }
function onImportFileChange(uploadFile: any) {
  const file = uploadFile.raw; if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => { try { importData.value = JSON.parse(e.target?.result as string); ElMessage.success('Parsed') } catch { ElMessage.error('Invalid JSON'); importData.value = null } }
  reader.readAsText(file)
}
async function handleImport() {
  if (!importData.value) return; importing.value = true
  try { await ImportTemplate({ data: importData.value }); ElMessage.success('Imported'); importVisible.value = false; await fetchData() } catch { ElMessage.error('Import failed') }
  importing.value = false
}
async function handleExport(row: any) {
  try { const r = await ExportTemplate(row.id); const blob = new Blob([JSON.stringify(r.data?.data || r.data, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${row.name.replace(/\s+/g, '_')}.json`; a.click(); URL.revokeObjectURL(url); ElMessage.success('Exported') } catch { ElMessage.error('Export failed') }
}
async function handleDelete(row: any) {
  try { await ElMessageBox.confirm('Delete this template?', 'Confirm', { type: 'warning' }); await DeleteTemplate(row.id); ElMessage.success('Deleted'); await fetchData() } catch { /* cancelled */ }
}

function openView(row: any) { viewRow.value = row; viewVisible.value = true }
function openSchedule(row: any) { scheduleTemplateId.value = row.id; scheduleTemplateName.value = row.name; scheduleVisible.value = true }
function openVersions(row: any) { versionTemplateId.value = row.id; versionTemplateName.value = row.name; versionCurrentVer.value = row.version || 1; versionVisible.value = true }

// Re-fetch templates when project switches via ProjectSwitcher
function onProjectChanged() {
  fetchData()
}

onMounted(async () => {
  if (!opsflowStore.myProjects.length) await opsflowStore.fetchMyProjects();
  await fetchData();
  window.addEventListener('project-changed', onProjectChanged)

  const key = 'opsflow_tour_template'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: t('message.template.tourMsg'), duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
})
</script>

<style scoped>
.tpl-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.tpl-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.tpl-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.tpl-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.tpl-hero-left { flex: 0 0 auto; }
.tpl-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.tpl-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.tpl-hero-center { flex: 1 1 auto; min-width: 0; }
.tpl-search-input { width: 100%; max-width: 320px; }
.tpl-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.tpl-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.tpl-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.tpl-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.tpl-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.tpl-stat-item { text-align: center; padding: 0 14px; }
.tpl-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.tpl-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.tpl-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.tpl-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.tpl-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.tpl-filter-tabs { display: flex; gap: 4px; }
.tpl-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.tpl-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.tpl-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.tpl-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.tpl-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.tpl-view-toggle { width: 36px; height: 30px; border-radius: 8px; background: #e0e3e8; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background .25s; flex-shrink: 0; }
.tpl-view-toggle.cards { background: #409EFF; }
.tpl-view-toggle.cards .tpl-toggle-btn { color: #fff; }

/* ===== Table card ===== */
.tpl-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.tpl-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.tpl-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.tpl-status-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; text-transform: uppercase; }
.st-published { background: #f0f9eb; color: #67C23A; }
.st-draft { background: #fdf6ec; color: #E6A23C; }
.tpl-version { font-size: 11px; color: #409EFF; font-weight: 600; }
.tpl-mini-flow { display: flex; align-items: center; gap: 2px; flex-wrap: nowrap; max-width: 100px; }
.tpl-mini-node { width: 20px; height: 20px; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.tpl-mini-icon { font-size: 10px; color: #fff; line-height: 1; }
.tpl-mini-arrow { font-size: 10px; color: #C0C4CC; flex-shrink: 0; }
.tpl-mini-more { font-size: 10px; color: #909399; }
.tpl-no-pl { color: #C0C4CC; }
.tpl-actions { display: flex; flex-wrap: nowrap; gap: 2px; }
.tpl-actions .el-button { padding: 4px 8px; border-radius: 6px; font-size: 12px; }
.tpl-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }

/* ===== Scope tabs ===== */
.tpl-scope-tabs { padding: 8px 0 0 0; }
.tpl-scope-tabs :deep(.el-tabs__item) { font-size: 14px; font-weight: 600; padding: 0 16px; }
.tpl-scope-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.tpl-scope-badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 8px; background: #ecf5ff; color: #409EFF; }

/* ===== Card view ===== */
.tpl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; padding-bottom: 24px; }
.tpl-card { display: flex; flex-direction: column; justify-content: space-between; background: #fff; border-radius: 14px; padding: 20px; cursor: pointer; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); border: 1px solid #f0f0f0; position: relative; overflow: hidden; }
.tpl-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1); border-color: transparent; }
.tpl-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; opacity: 0; transition: opacity 0.25s; }
.tpl-card:hover::before { opacity: 1; }
.tpl-card:nth-child(4n+1)::before { background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.tpl-card:nth-child(4n+2)::before { background: linear-gradient(90deg, #67C23A, #95de64); }
.tpl-card:nth-child(4n+3)::before { background: linear-gradient(90deg, #E6A23C, #f5d76e); }
.tpl-card:nth-child(4n+4)::before { background: linear-gradient(90deg, #9B59B6, #c39bd3); }
.tpl-card-top { flex: 1; }
.tpl-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.tpl-card-badge { display: inline-flex; align-items: center; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
.tpl-card-cat { font-size: 11px; color: #909399; background: #f5f5f5; padding: 2px 8px; border-radius: 6px; }
.tpl-card-name { font-size: 16px; font-weight: 700; color: #1a1a2e; line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tpl-card-desc { font-size: 13px; color: #909399; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 19px; }
.tpl-card-bottom { margin-top: 14px; padding-top: 14px; border-top: 1px solid #f5f5f5; }
.tpl-card-stats { display: flex; gap: 12px; margin-bottom: 10px; }
.tpl-stat-chip { font-size: 11px; color: #a0a4ab; }
.tpl-stat-chip b { color: #4e5969; }
.tpl-card-actions { display: flex; flex-wrap: wrap; gap: 2px; }
.tpl-card-actions .el-button { padding: 4px 6px; border-radius: 6px; }

/* ===== View dialog ===== */
.tpl-view-dialog :deep(.el-dialog__header) { padding-bottom: 8px; }
.tpl-view-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.tpl-view-cat { font-size: 11px; color: #909399; background: #f5f5f5; padding: 2px 8px; border-radius: 6px; }
.tpl-view-info { font-size: 12px; color: #909399; }
.tpl-view-section { margin-bottom: 20px; }
.tpl-view-section-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
.tpl-view-pipeline { display: flex; flex-direction: column; align-items: center; gap: 0; }
.tpl-vp-node-wrapper { display: flex; flex-direction: column; align-items: center; }
.tpl-vp-node { border: 2px solid; border-radius: 10px; padding: 10px 20px; min-width: 180px; text-align: center; }
.tpl-vp-node-header { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 4px; }
.tpl-vp-node-icon { font-size: 16px; }
.tpl-vp-node-name { font-size: 14px; font-weight: 600; color: #303133; }
.tpl-vp-node-body { display: flex; gap: 8px; justify-content: center; }
.tpl-vp-node-type, .tpl-vp-node-atom { font-size: 11px; color: #909399; }
.tpl-vp-connector { display: flex; flex-direction: column; align-items: center; height: 36px; }
.tpl-vp-arrow { font-size: 14px; color: #C0C4CC; line-height: 1; }
.tpl-vp-line { width: 1px; flex: 1; background: #dcdfe6; }
.tpl-view-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>
