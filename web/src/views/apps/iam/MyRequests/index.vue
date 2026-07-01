<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <span class="iam-section-title">
        <el-icon size="16"><Tickets /></el-icon>
        {{ $t('message.iam.myRequests') }}
      </span>
      <el-button type="primary" size="small" :icon="Plus" @click="showCreateDialog">
        {{ $t('message.iam.newRequest') }}
      </el-button>
    </div>

    <el-table :data="requests" v-loading="loading" size="small" class="iam-table">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column :label="$t('message.iam.type')" width="90">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ isEn ? row.request_type_label_en : row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.target')" min-width="140">
        <template #default="{ row }">
          {{ row.request_type === 'project_role' ? (row.target_project_name || '') + ' — ' + (row.target_project_role || '') : (row.target_role_name || row.target_iam_role_name || (isEn ? row.target_permission_label_en : row.target_permission_label) || row.target_permission || row.target_menu_name || '-') }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.status')" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small" effect="dark">{{ isEn ? row.status_label_en : row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" :label="$t('message.iam.reason')" min-width="160" show-overflow-tooltip />
      <el-table-column :label="$t('message.iam.reviewer')" width="100">
        <template #default="{ row }">{{ row.reviewer_name || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.reviewComment')" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.review_comment || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.createdAt')" width="150">
        <template #default="{ row }">{{ row.create_datetime }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && requests.length === 0" :image-size="60" :description="$t('message.iam.noRequests')" />

    <div class="iam-pagination" v-if="total > 0">
      <el-pagination v-model:currentPage="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next, total" @update:currentPage="fetchRequests" background size="small" />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="createVisible" :title="$t('message.iam.newRequest')" width="960px"
      class="opsflow-dialog" destroy-on-close top="6vh" append-to-body>
      <el-form label-width="100px" size="small">
        <el-form-item label="Request Type">
          <el-radio-group v-model="form.request_type">
            <el-radio-button value="role">{{ $t('message.iam.requestRole') }}</el-radio-button>
            <el-radio-button value="permission">{{ $t('message.iam.requestPermission') }}</el-radio-button>
            <el-radio-button value="project_role">{{ $t('message.iam.requestProjectRole') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('message.iam.selectRole')" v-if="form.request_type === 'role'">
          <el-select v-model="form.target_iam_role" placeholder="Select role"
            filterable style="width:100%">
            <el-option v-for="r in availableRoles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <template v-if="form.request_type === 'permission'">
          <el-form-item :label="$t('message.iam.selectApp')">
            <el-radio-group v-model="selectedApp" @change="onAppChange">
              <el-radio-button v-for="app in catalog" :key="app.app" :value="app.app">{{ appLabel(app.app) }}</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="$t('message.iam.selectPermissions')">
            <div class="perm-list-wrap">
              <!-- Header row -->
              <div class="perm-list-header">
                <span class="perm-list-h-module">{{ $t('message.iam.module') }}</span>
                <span class="perm-list-h-action">{{ $t('message.iam.subPerms') }}</span>
              </div>
              <!-- Rows -->
              <div v-for="tab in currentTabs" :key="tab.key" class="perm-list-row">
                <!-- Left: module name + key badge -->
                <div class="perm-list-module">
                  <el-icon v-if="iconMap[tab.icon]" size="15"><component :is="iconMap[tab.icon]" /></el-icon>
                  <span class="perm-list-module-name">{{ isEn ? tab.label_en : tab.label_zh }}</span>
                  <span v-if="tab.required_perm_tab" class="perm-list-key">{{ tab.required_perm_tab.split(':').slice(1).join(':') }}</span>
                </div>
                <!-- Right: action area -->
                <div class="perm-list-action">
                  <template v-if="tab.buttons.length || tab.required_perm_tab">
                    <el-checkbox-group v-model="form.target_permissions" class="perm-list-sub-grid">
                      <el-checkbox v-for="btn in tab.buttons" :key="btn.key"
                        :value="btn.required_perm" size="small" class="perm-list-sub-cb">
                        {{ isEn ? btn.label_en : btn.label_zh }}
                      </el-checkbox>
                      <el-checkbox v-if="tab.required_perm_tab && !tab.buttons.length"
                        :value="tab.required_perm_tab" size="small">
                        {{ $t('message.iam.grantAccess') }}
                      </el-checkbox>
                    </el-checkbox-group>
                    <div v-if="tab.required_perm_tab && tab.buttons.length" class="perm-list-auto-hint">
                      + {{ $t('message.iam.autoInclude') }} <code>{{ tab.required_perm_tab.split(':').slice(1).join(':') }}</code>
                    </div>
                  </template>
                  <span v-else class="perm-list-open">{{ $t('message.iam.defaultOpen') }}</span>
                </div>
              </div>
            </div>
            <div v-if="form.target_permissions.length" class="perm-selected-count">
              {{ $t('message.iam.selectedCount', { n: form.target_permissions.length }) }}
              <el-button size="small" text type="primary" @click="form.target_permissions = []" style="margin-left:8px">
                {{ $t('message.iam.clearAll') }}
              </el-button>
            </div>
          </el-form-item>
        </template>
        <el-form-item label="Target Project" v-if="form.request_type === 'project_role'">
          <el-select v-model="form.target_project" placeholder="Select project" filterable style="width:100%">
            <el-option v-for="p in myProjects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Project Role" v-if="form.request_type === 'project_role'">
          <el-select v-model="form.target_project_role" placeholder="Select role" style="width:100%">
            <el-option label="Admin" value="admin" />
            <el-option label="Editor" value="editor" />
            <el-option label="Viewer" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="Reason" required>
          <el-input v-model="form.reason" type="textarea" :rows="3" placeholder="Describe why you need this permission" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="createVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="submitting" @click="onCreate">
          {{ $t('message.iam.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Plus, Tickets, DataAnalysis, Document, VideoPlay, Clock,
  Collection, List, Link, Setting, WarningFilled, Edit, User,
  Refresh, Bell,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { i18n } from '/@/i18n/index'
import { useProjectStore } from '/@/stores/project'
import { GetRequests, CreateRequest } from '/@/api/iam/requests'
import { GetAvailableRoles } from '/@/api/iam/permissions'
import { request } from '/@/utils/service'

const t = i18n.global.t
const projectStore = useProjectStore()
const myProjects = ref<any[]>([])

const requests = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const createVisible = ref(false)
const submitting = ref(false)
const availableRoles = ref<any[]>([])
const catalog = ref<any[]>([])
const selectedApp = ref('opsflow')
const isEn = computed(() => String(i18n.global.locale.value).startsWith('en'))

const iconMap: Record<string, any> = {
  DataAnalysis, Document, VideoPlay, Clock,
  Collection, List, Link, Setting, WarningFilled, Edit, User,
  Refresh, Bell,
}

const currentTabs = computed(() => catalog.value.find((a: any) => a.app === selectedApp.value)?.tabs || [])

function appLabel(app: string) {
  const map: Record<string, string> = { opsflow: 'OPSflow', itsm: 'ITSM', cmdb: 'CMDB' }
  return map[app] || app
}

function onAppChange(app: string) {
  selectedApp.value = app
}

const form = ref<any>({ request_type: 'role', target_iam_role: null, target_permissions: [], target_project: null, target_project_role: null, reason: '' })

function requestTypeTag(type: string) {
  const map: Record<string, string> = { role: 'success', menu: 'primary', menu_button: 'warning', project_role: 'danger' }
  return map[type] || 'info'
}
function statusTag(status: string) {
  const map: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

async function fetchRequests() {
  loading.value = true
  try {
    const res = await GetRequests({ page: page.value, limit: pageSize.value })
    requests.value = res.data || []
    total.value = res.total || 0
  } catch { /* ignore */ }
  loading.value = false
}

async function showCreateDialog() {
  myProjects.value = projectStore.myProjects
  form.value = { request_type: 'role', target_iam_role: null, target_permissions: [], target_project: projectStore.currentProjectId, target_project_role: null, reason: '' }
    createVisible.value = true
  try {
    const [r, c] = await Promise.all([
      GetAvailableRoles(),
      request({ url: '/api/iam/permission-catalog/', method: 'get' }),
    ])
    availableRoles.value = r.data?.data || r.data || []
    catalog.value = c.data || []
    selectedApp.value = catalog.value[0]?.app || 'opsflow'
  } catch { /* ignore */ }
}

async function onCreate() {
  if (!form.value.reason) { ElMessage.warning(t('message.iam.errors.reasonRequired')); return }
  if (form.value.request_type === 'role' && !form.value.target_iam_role) { ElMessage.warning(t('message.iam.errors.roleRequired')); return }
  if (form.value.request_type === 'permission' && !form.value.target_permissions.length) { ElMessage.warning(t('message.iam.errors.permissionRequired')); return }
  if (form.value.request_type === 'project_role' && !form.value.target_project) { ElMessage.warning(t('message.iam.errors.roleRequired')); return }
  if (form.value.request_type === 'project_role' && !form.value.target_project_role) { ElMessage.warning(t('message.iam.errors.roleRequired')); return }
  submitting.value = true
  try {
    if (form.value.request_type === 'permission') {
      // Auto-include parent tab permissions when sub-button permissions are selected
      const selected = new Set(form.value.target_permissions)
      const catalogData = catalog.value
      const selApp = selectedApp.value
      const appData = catalogData.find((a: any) => a.app === selApp)
      if (appData) {
        for (const tab of appData.tabs) {
          if (tab.required_perm_tab && tab.buttons?.length) {
            // If any button of this tab is selected, ensure tab perm is also included
            const hasBtnSelected = tab.buttons.some((btn: any) => selected.has(btn.required_perm))
            if (hasBtnSelected) {
              selected.add(tab.required_perm_tab)
            }
          }
        }
      }
      await Promise.all(Array.from(selected).map((codename: string) =>
        request({ url: '/api/iam/requests/', method: 'post', data: {
          request_type: 'permission',
          target_permission: codename,
          reason: form.value.reason,
        }})
      ))
    } else {
      await CreateRequest(form.value)
    }
    createVisible.value = false
    ElMessage.success(t('message.iam.submitted'))
    await fetchRequests()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || t('message.iam.errors.submitFailed')) }
  submitting.value = false
}

onMounted(() => fetchRequests())
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

// ===== Section =====
.iam-section {
  background: $g-bg-card;
  border: 1px solid $g-border-card;
  border-radius: $g-radius-card;
  padding: $g-padding-card;
}
.iam-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.iam-section-title {
  font-size: 15px;
  font-weight: 600;
  color: $g-text-primary;
  display: flex;
  align-items: center;
  gap: 8px;
  .el-icon { color: $g-color-primary; }
}
.iam-table { width: 100%; }
.iam-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

// ===== Permission List (clean two-column layout) =====
.perm-list-wrap {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 10px;
}

.perm-list-header {
  display: flex;
  align-items: center;
  padding: 8px 14px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 1;
}
.perm-list-h-module {
  flex: 0 0 220px;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}
.perm-list-h-action {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.perm-list-row {
  display: flex;
  align-items: flex-start;
  padding: 10px 14px;
  transition: background 0.12s;
  & + & { border-top: 1px solid #f0f0f0; }
  &:hover { background: #fafbfc; }
}

.perm-list-module {
  flex: 0 0 220px;
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  .el-icon { color: #909399; flex-shrink: 0; }
}
.perm-list-module-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.perm-list-key {
  font-size: 11px;
  font-family: 'SF Mono', 'Cascadia Code', Menlo, monospace;
  color: #999;
  background: #f0f0f0;
  padding: 1px 7px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

.perm-list-action {
  flex: 1;
  min-width: 0;
}
.perm-list-sub-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.perm-list-sub-cb {
  margin-right: 0 !important;
  :deep(.el-checkbox__label) {
    font-size: 12px;
    color: #606266;
  }
}
.perm-list-open {
  font-size: 12px;
  color: #c0c4cc;
  line-height: 28px;
}
.perm-list-auto-hint {
  font-size: 11px;
  color: #bbb;
  margin-top: 4px;
  code {
    font-family: 'SF Mono', 'Cascadia Code', Menlo, monospace;
    font-size: 10px;
    background: #f5f5f5;
    padding: 1px 5px;
    border-radius: 3px;
    color: #999;
  }
}

.perm-selected-count {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

// ===== Dialog overrides =====
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
