<template>
  <div class="pj-page">
    <!-- Hero Section -->
    <div class="pj-hero">
      <div class="pj-hero-bg" />
      <div class="pj-hero-inner">
        <div class="pj-hero-left">
          <h1 class="pj-hero-title">Projects</h1>
          <p class="pj-hero-subtitle">Multi-tenant isolation for OpsFlow workspaces</p>
        </div>
        <div class="pj-hero-center">
          <el-input
            v-model="searchQuery"
            placeholder="Search projects..."
            clearable
            size="default"
            class="pj-search-input"
            @keyup.enter="onSearch"
            @clear="onSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="pj-hero-stats">
          <div class="pj-stat-item"><span class="pj-stat-value">{{ total }}</span><span class="pj-stat-label">Total</span></div>
          <div class="pj-stat-divider" />
          <div class="pj-stat-item"><span class="pj-stat-value">{{ activeCount }}</span><span class="pj-stat-label">Active</span></div>
          <div class="pj-stat-divider" />
          <div class="pj-stat-item"><span class="pj-stat-value">{{ templateTotal }}</span><span class="pj-stat-label">Templates</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="pj-body">
      <!-- Filter bar -->
      <div class="pj-filter-bar">
        <div class="pj-filter-tabs">
          <div class="pj-tab" :class="{ active: filterStatus === '' }" @click="filterStatus = ''; onSearch()">
            <span class="pj-tab-dot" style="background:#409EFF" />All
          </div>
          <div class="pj-tab" :class="{ active: filterStatus === 'active' }" @click="filterStatus = 'active'; onSearch()">
            <span class="pj-tab-dot" style="background:#67C23A" />Active
          </div>
          <div class="pj-tab" :class="{ active: filterStatus === 'inactive' }" @click="filterStatus = 'inactive'; onSearch()">
            <span class="pj-tab-dot" style="background:#909399" />Inactive
          </div>
        </div>
        <div class="pj-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">Refresh</el-button>
          <el-button type="primary" :icon="Plus" @click="showForm(null)" size="small">New Project</el-button>
        </div>
      </div>

      <!-- Grid -->
      <div class="pj-grid" v-loading="loading">
        <el-empty v-if="!loading && projects.length === 0" :description="emptyText" :image-size="80" />
        <div
          v-for="p in projects" :key="p.id"
          class="pj-card"
          @click="showDetail(p)"
        >
          <div class="pj-card-top">
            <div class="pj-card-badge-row">
              <span class="pj-card-badge" :class="p.is_active ? 'badge-active' : 'badge-inactive'">
                {{ p.is_active ? 'Active' : 'Inactive' }}
              </span>
              <span class="pj-card-owner" v-if="p.owner_name">👤 {{ p.owner_name }}</span>
            </div>
            <div class="pj-card-name">{{ p.name }}</div>
            <div class="pj-card-desc">{{ p.description || 'No description' }}</div>
          </div>
          <div class="pj-card-bottom">
            <div class="pj-card-stats">
              <span class="pj-stat-chip"><b>{{ p.template_count ?? 0 }}</b> templates</span>
              <span class="pj-stat-chip"><b>{{ p.execution_count ?? 0 }}</b> executions</span>
            </div>
            <div class="pj-card-time">{{ p.created_at?.substring(0, 10) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit dialog -->
    <el-dialog v-model="formVisible" :title="formId ? 'Edit Project' : 'New Project'" width="480px" top="5vh" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="Name" required>
          <el-input v-model="form.name" placeholder="Project name (unique)" maxlength="128" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="Optional description..." maxlength="255" />
        </el-form-item>
        <el-form-item v-if="formId" label="Active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="Max Schedules">
          <el-input-number v-model="form.max_schedule_plans" :min="0" :max="1000" />
          <div class="form-tip" style="margin-left:8px">0 = unlimited</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false" size="small">Cancel</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" size="small">{{ formId ? 'Update' : 'Create' }}</el-button>
      </template>
    </el-dialog>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" :title="detail?.name || ''" width="640px" top="5vh" destroy-on-close class="opsflow-dialog pj-detail-dialog">
      <template v-if="detail">
        <!-- Meta badge -->
        <div class="pj-detail-hero">
          <span class="pj-badge" :class="detail.is_active ? 'badge-active' : 'badge-inactive'">
            {{ detail.is_active ? 'Active' : 'Inactive' }}
          </span>
          <span class="pj-hero-owner" v-if="detail.owner_name">👤 {{ detail.owner_name }}</span>
          <span class="pj-hero-date">{{ detail.created_at?.substring(0, 10) }}</span>
        </div>

        <!-- Info cards row -->
        <div class="pj-detail-grid">
          <div class="pj-info-card"><span class="pj-info-label">Description</span><span class="pj-info-value">{{ detail.description || '—' }}</span></div>
          <div class="pj-info-card"><span class="pj-info-label">Templates</span><span class="pj-info-value">{{ detail.template_count ?? 0 }}</span></div>
          <div class="pj-info-card"><span class="pj-info-label">Executions</span><span class="pj-info-value">{{ detail.execution_count ?? 0 }}</span></div>
          <div class="pj-info-card"><span class="pj-info-label">Schedule Limit</span><span class="pj-info-value">{{ detail.max_schedule_plans ?? 20 }}</span></div>
        </div>

        <!-- Members Section -->
        <div class="pj-section-card">
          <div class="pj-section-header">
            <div class="pj-section-header-left">
              <span class="pj-section-dot" />
              <span>Members</span>
            </div>
            <el-tag size="small" effect="plain" type="primary">{{ members.length }}</el-tag>
          </div>

          <el-table :data="members" v-loading="membersLoading" size="small" empty-text="No members" style="width:100%">
            <el-table-column prop="username" label="User" min-width="120" />
            <el-table-column label="Role" width="110">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'editor' ? 'primary' : 'info'" size="small" effect="plain">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label width="60" align="center">
              <template #default="{ row }">
                <el-button v-if="row.user_id !== currentUserId" size="small" text type="danger" @click="removeMember(row)">✕</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pj-add-row">
            <el-select v-model="newMemberIds" filterable multiple collapse-tags collapse-tags-tooltip
              :loading="usersLoading" placeholder="Select users..." style="width:240px" size="small" clearable>
              <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
            </el-select>
            <el-select v-model="newMemberRole" size="small" style="width:110px">
              <el-option label="Editor" value="editor" />
              <el-option label="Viewer" value="viewer" />
            </el-select>
            <el-button size="small" type="primary" @click="addMember" :disabled="!newMemberIds.length">Add</el-button>
          </div>
        </div>

        <!-- Plugin Visibility Section -->
        <div class="pj-section-card">
          <div class="pj-section-header">
            <div class="pj-section-header-left">
              <span class="pj-section-dot" style="background: linear-gradient(135deg, #E6A23C, #f5d76e);" />
              <span>Plugins</span>
            </div>
            <el-tag size="small" effect="plain" type="warning">Visibility</el-tag>
          </div>
          <div class="pj-plugins-summary">
            <p>Control which plugins are visible to this project. Restricted plugins are only shown to
            projects explicitly assigned to them.</p>
            <el-button size="small" :icon="Setting" @click="showPluginVisibility = true">
              Manage Plugin Visibility
            </el-button>
          </div>
        </div>

        <!-- Environment Variables Section -->
        <div class="pj-section-card">
          <div class="pj-section-header">
            <div class="pj-section-header-left">
              <span class="pj-section-dot" style="background: linear-gradient(135deg, #67C23A, #95de64);" />
              <span>Environment Variables</span>
            </div>
            <el-tag size="small" effect="plain" type="success">Project</el-tag>
          </div>
          <ProjectEnvVarPanel :project-id="detail.id" />
        </div>
      </template>

      <template #footer>
        <el-button size="small" @click="showForm(detail); detailVisible = false" :icon="Edit">Edit</el-button>
        <el-popconfirm title="Delete this project?" @confirm="handleDelete(detail)">
          <template #reference>
            <el-button size="small" type="danger" :icon="Delete">Delete</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-dialog>

    <!-- Plugin Visibility Dialog -->
    <PluginVisibilityDialog v-model:visible="showPluginVisibility" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Setting } from '@element-plus/icons-vue'
import { request } from '/@/utils/service'
import { GetProjects, CreateProject, UpdateProject, DeleteProject, GetProjectDetail,
         GetProjectMembers, AddProjectMember, RemoveProjectMember } from '/@/api/opsflow/projects'
import PluginVisibilityDialog from '/@/views/apps/opsflow/components/PluginVisibilityDialog.vue'
import ProjectEnvVarPanel from '/@/views/apps/opsflow/components/ProjectEnvVarPanel.vue'

const loading = ref(false)
const saving = ref(false)
const projects = ref<any[]>([])
const searchQuery = ref('')
const filterStatus = ref('')

const total = computed(() => projects.value.length)
const activeCount = computed(() => projects.value.filter(p => p.is_active).length)
const templateTotal = computed(() => projects.value.reduce((s, p) => s + (p.template_count || 0), 0))
const emptyText = computed(() => 'No projects yet. Create one to get started.')

// Form
const formVisible = ref(false)
const formId = ref<number | null>(null)
const form = ref({ name: '', description: '', is_active: true, max_schedule_plans: 20 })

// Detail
const detailVisible = ref(false)
const detail = ref<any>(null)

// Members
const members = ref<any[]>([])
const membersLoading = ref(false)
const newMemberIds = ref<number[]>([])
const newMemberRole = ref('editor')
const userOptions = ref<any[]>([])
const usersLoading = ref(false)
const currentUserId = ref<number | null>(null)

// Plugin visibility
const showPluginVisibility = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const res = await GetProjects()
    let items = (res as any).data || []
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      items = items.filter(p => p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q))
    }
    if (filterStatus.value === 'active') items = items.filter(p => p.is_active)
    if (filterStatus.value === 'inactive') items = items.filter(p => !p.is_active)
    projects.value = items
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Failed to load projects')
  } finally {
    loading.value = false
  }
}

function showForm(row: any | null) {
  if (row) {
    formId.value = row.id
    form.value = { name: row.name, description: row.description || '', is_active: row.is_active ?? true, max_schedule_plans: row.max_schedule_plans ?? 20 }
  } else {
    formId.value = null
    form.value = { name: '', description: '', is_active: true }
  }
  formVisible.value = true
}

async function showDetail(row: any) {
  try {
    const res = await GetProjectDetail(row.id)
    detail.value = (res as any).data || row
  } catch {
    detail.value = row
  }
  detailVisible.value = true
  // Load members
  await Promise.all([
    loadMembers(row.id),
    loadAllUsers(),
  ])
  // Get current user id
  try {
    const userRes = await request({ url: '/api/system/user/user_info/', method: 'get' })
    currentUserId.value = (userRes as any).data?.id || null
  } catch { /* ignore */ }
}

async function loadMembers(projectId: number) {
  membersLoading.value = true
  try {
    const res = await GetProjectMembers(projectId)
    members.value = (res as any).data || []
  } catch { members.value = [] }
  membersLoading.value = false
}

async function loadAllUsers() {
  usersLoading.value = true
  try {
    const res = await request({ url: '/api/system/user/', method: 'get', params: { page_size: 200 } })
    userOptions.value = (res as any).data?.results || (res as any).data || []
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

async function addMember() {
  if (!newMemberIds.value.length || !detail.value) return
  try {
    for (const uid of newMemberIds.value) {
      await AddProjectMember(detail.value.id, uid, newMemberRole.value)
    }
    ElMessage.success(`Added ${newMemberIds.value.length} member(s)`)
    newMemberIds.value = []
    await loadMembers(detail.value.id)
  } catch (e: any) { ElMessage.error(e?.msg || 'Failed to add member') }
}

async function removeMember(row: any) {
  if (!detail.value) return
  try {
    await RemoveProjectMember(detail.value.id, row.id)
    ElMessage.success('Member removed')
    await loadMembers(detail.value.id)
  } catch (e: any) { ElMessage.error(e?.msg || 'Failed to remove member') }
}

async function handleSave() {
  if (!form.value.name) { ElMessage.warning('Project name is required'); return }
  saving.value = true
  try {
    if (formId.value) {
      await UpdateProject(formId.value, form.value)
      ElMessage.success('Project updated')
    } else {
      await CreateProject({ name: form.value.name, description: form.value.description })
      ElMessage.success('Project created')
    }
    formVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Save failed')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await DeleteProject(row.id)
    ElMessage.success('Project deleted')
    detailVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Delete failed')
  }
}

function onSearch() { fetchData() }

onMounted(async () => {
  const { useOpsflowStore } = await import('/@/views/apps/opsflow/stores/opsflowStore')
  const store = useOpsflowStore()
  if (!store.myProjects.length) await store.fetchMyProjects()
  fetchData()
})
</script>

<style scoped>
/* ===== Layout ===== */
.pj-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.pj-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.pj-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.pj-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.pj-hero-left { flex: 0 0 auto; }
.pj-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.pj-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.pj-hero-center { flex: 1 1 auto; min-width: 0; }
.pj-search-input { width: 100%; max-width: 320px; }
.pj-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.pj-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.pj-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.pj-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.pj-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.pj-stat-item { text-align: center; padding: 0 14px; }
.pj-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.pj-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.pj-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.pj-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.pj-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.pj-filter-tabs { display: flex; gap: 4px; }
.pj-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.pj-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.pj-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.pj-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.pj-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Grid ===== */
.pj-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; padding-bottom: 24px; min-height: 200px; }

/* ===== Card ===== */
.pj-card { display: flex; flex-direction: column; justify-content: space-between; background: #fff; border-radius: 14px; padding: 20px; cursor: pointer; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); border: 1px solid #f0f0f0; position: relative; overflow: hidden; }
.pj-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1); border-color: transparent; }
.pj-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; opacity: 0; transition: opacity 0.25s; }
.pj-card:hover::before { opacity: 1; }
.pj-card:nth-child(4n+1)::before { background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.pj-card:nth-child(4n+2)::before { background: linear-gradient(90deg, #67C23A, #95de64); }
.pj-card:nth-child(4n+3)::before { background: linear-gradient(90deg, #E6A23C, #f5d76e); }
.pj-card:nth-child(4n+4)::before { background: linear-gradient(90deg, #9B59B6, #c39bd3); }

.pj-card-top { flex: 1; }
.pj-card-badge-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.pj-card-badge { display: inline-flex; align-items: center; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
.badge-active { background: #f0f9eb; color: #67C23A; }
.badge-inactive { background: #f5f5f5; color: #909399; }
.pj-card-owner { font-size: 11px; color: #909399; margin-left: auto; }

.pj-card-name { font-size: 17px; font-weight: 700; color: #1a1a2e; line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.pj-card-desc { font-size: 13px; color: #909399; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 20px; }

.pj-card-bottom { margin-top: 14px; padding-top: 14px; border-top: 1px solid #f5f5f5; display: flex; justify-content: space-between; align-items: center; }
.pj-card-stats { display: flex; gap: 12px; }
.pj-stat-chip { font-size: 11px; color: #a0a4ab; }
.pj-stat-chip b { color: #4e5969; }
.pj-card-time { font-size: 11px; color: #C0C4CC; }

/* ===== Detail dialog (opsflow style) ===== */
.pj-detail-dialog { }
.pj-detail-dialog :deep(.el-dialog__header) {
  padding: 16px 20px; margin: 0; border-bottom: 1px solid #e4e7ed; font-weight: 600;
}
.pj-detail-dialog :deep(.el-dialog__body) { padding: 20px; }
.pj-detail-dialog :deep(.el-dialog__footer) {
  padding: 12px 20px; border-top: 1px solid #e4e7ed;
}

/* Hero badge row */
.pj-detail-hero {
  display: flex; align-items: center; gap: 10px; margin-bottom: 18px;
}
.pj-badge {
  display: inline-flex; align-items: center; font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.3px;
}
.pj-hero-owner { font-size: 13px; color: #606266; margin-left: auto; }
.pj-hero-date { font-size: 12px; color: #909399; }

/* Info grid */
.pj-detail-grid {
  display: flex; gap: 12px; margin-bottom: 20px;
}
.pj-info-card {
  flex: 1; background: #f8f9fb; border-radius: 10px; padding: 14px 16px;
  border: 1px solid #f0f0f0; display: flex; flex-direction: column; gap: 6px;
}
.pj-info-label { font-size: 11px; color: #909399; text-transform: uppercase; letter-spacing: 0.3px; }
.pj-info-value { font-size: 14px; font-weight: 600; color: #303133; }

/* Section card (members) */
.pj-section-card {
  background: #f8f9fb; border-radius: 10px; padding: 16px 18px;
  border: 1px solid #f0f0f0; margin-bottom: 8px;
}
.pj-section-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
  font-size: 14px; font-weight: 600; color: #333;
}
.pj-section-header-left { display: flex; align-items: center; gap: 8px; flex: 1; }
.pj-section-dot {
  width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #409EFF, #337ecc);
  flex-shrink: 0;
}
.pj-add-row { display: flex; gap: 8px; margin-top: 12px; align-items: center; }

/* ===== Plugin Visibility ===== */
.pj-plugins-summary { display: flex; flex-direction: column; gap: 10px; }
.pj-plugins-summary p { margin: 0; font-size: 13px; color: #909399; line-height: 1.6; }
</style>
