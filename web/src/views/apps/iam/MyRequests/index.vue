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
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.target')" min-width="140">
        <template #default="{ row }">
          {{ row.request_type === 'project_role' ? (row.target_project_name || '') + ' — ' + (row.target_project_role || '') : (row.target_role_name || row.target_menu_name || '-') }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.status')" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small" effect="dark">{{ row.status_label }}</el-tag>
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
    <el-dialog v-model="createVisible" title="New Request" width="1080px"
      class="opsflow-dialog" destroy-on-close top="8vh" append-to-body>
      <el-form label-width="100px" size="small">
        <el-form-item label="Request Type">
          <el-radio-group v-model="form.request_type">
            <el-radio-button value="role">申请角色</el-radio-button>
            <el-radio-button value="menu">申请菜单</el-radio-button>
            <el-radio-button value="project_role">申请项目角色</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Target Role" v-if="form.request_type === 'role'">
          <el-select v-model="form.target_role" placeholder="Select role"
            filterable style="width:100%">
            <el-option v-for="r in availableRoles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Target Menu" v-if="form.request_type === 'menu'">
          <el-select v-model="form.target_menu" placeholder="Select menu"
            filterable style="width:100%" @change="onMenuChange">
            <el-option-group v-for="group in menuGroups" :key="group.label" :label="group.label">
              <el-option v-for="m in group.children" :key="m.id" :label="m.name" :value="m.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.request_type === 'menu' && form.target_menu">
          <template #label>
            <span>Buttons <el-tag size="small" type="warning" style="margin-left:4px">{{ form.selected_buttons?.length || 0 }}/{{ menuButtons.length }}</el-tag></span>
          </template>
          <div v-if="menuButtons.length">
            <div style="margin-bottom:6px">
              <el-button size="small" text @click="form.selected_buttons = menuButtons.map(b => b.id)">Select All</el-button>
              <el-button size="small" text @click="form.selected_buttons = []">Deselect All</el-button>
            </div>
            <el-checkbox-group v-model="form.selected_buttons" class="iam-btn-grid">
              <el-checkbox v-for="b in menuButtons" :key="b.id" :label="b.id" border>
                <el-tooltip :content="b.value" placement="top" :show-after="300">
                  <span class="iam-btn-name">{{ b.name }}</span>
                </el-tooltip>
              </el-checkbox>
            </el-checkbox-group>
          </div>
          <span v-else-if="!loadingButtons" style="color:#C0C4CC;font-size:12px">No buttons under this menu</span>
          <span v-if="loadingButtons" style="color:#409EFF;font-size:12px">Loading...</span>
        </el-form-item>
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
import { Plus, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { i18n } from '/@/i18n/index'
import { useProjectStore } from '/@/stores/project'
import { GetRequests, CreateRequest } from '/@/api/iam/requests'
import { GetAvailableRoles, GetAvailableMenus } from '/@/api/iam/permissions'

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
const availableMenus = ref<any[]>([])
const menuGroups = computed(() => {
  const items = availableMenus.value
  // Menus with no parent are top-level
  const top = items.filter((m: any) => !m.parent)
  // Standalone menus (no children) shown directly under "All"
  const withKids = top.filter((m: any) => items.some((c: any) => c.parent === m.id))
  const withoutKids = top.filter((m: any) => !items.some((c: any) => c.parent === m.id))
  const groups = withKids.map((m: any) => ({
    label: m.name,
    children: items.filter((c: any) => c.parent === m.id),
  }))
  if (withoutKids.length) {
    groups.unshift({ label: 'Direct Access', children: withoutKids })
  }
  return groups
})
const form = ref<any>({ request_type: 'role', target_role: null, target_menu: null, target_project: null, target_project_role: null, selected_buttons: [], reason: '' })
const menuButtons = ref<any[]>([])
const loadingButtons = ref(false)

async function onMenuChange(menuId: number | null) {
  form.value.selected_buttons = []
  menuButtons.value = []
  if (!menuId) return
  loadingButtons.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res: any = await request({ url: '/api/iam/menu_button/', params: { menu: menuId } })
    menuButtons.value = (res as any).results || (res as any).data || []
    // Default: select all buttons
    form.value.selected_buttons = menuButtons.value.map((b: any) => b.id)
  } catch { menuButtons.value = [] }
  loadingButtons.value = false
}

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
  form.value = { request_type: 'role', target_role: null, target_menu: null, target_project: projectStore.currentProjectId, target_project_role: null, selected_buttons: [], reason: '' }
  createVisible.value = true
  try {
    const [r, m] = await Promise.all([GetAvailableRoles(), GetAvailableMenus()])
    availableRoles.value = r.data?.data || r.data || []
    availableMenus.value = m.data?.data || m.data || []
  } catch { /* ignore */ }
}

async function onCreate() {
  if (!form.value.reason) { ElMessage.warning(t('message.iam.errors.reasonRequired')); return }
  if (form.value.request_type === 'role' && !form.value.target_role) { ElMessage.warning('请选择角色'); return }
  if (form.value.request_type === 'menu' && !form.value.target_menu) { ElMessage.warning('请选择菜单'); return }
  if (form.value.request_type === 'project_role' && !form.value.target_project) { ElMessage.warning('请选择项目'); return }
  if (form.value.request_type === 'project_role' && !form.value.target_project_role) { ElMessage.warning('请选择项目角色'); return }
  submitting.value = true
  try {
    await CreateRequest(form.value)
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

.iam-btn-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  max-height: 360px;
  overflow-y: auto;
  padding: 10px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.iam-btn-grid :deep(.el-checkbox) {
  margin-right: 0;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fff;
  transition: all 0.15s;
}
.iam-btn-grid :deep(.el-checkbox:hover) {
  border-color: #409EFF;
  background: #f0f5ff;
}
.iam-btn-grid :deep(.el-checkbox.is-checked) {
  background: #ecf5ff;
  border-color: #409EFF;
}
.iam-btn-name {
  font-size: 13px; color: #303133; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

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
.iam-table {
  width: 100%;
}
.iam-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
.iam-form-tip {
  font-size: 11px;
  color: $g-text-muted;
  margin-top: 2px;
}
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
