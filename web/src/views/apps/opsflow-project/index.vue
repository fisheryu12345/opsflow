<template>
  <div class="pj-page">
    <!-- Hero Section -->
    <div class="pj-hero">
      <div class="pj-hero-bg" />
      <div class="pj-hero-inner">
        <div class="pj-hero-left">
          <h1 class="pj-hero-title">{{ $t("message.project.title") }}</h1>
          <p class="pj-hero-subtitle">{{ $t("message.opsflowPage.projectsSubtitle") }}</p>
        </div>
        <div class="pj-hero-center">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('message.opsflowPage.projectsSearch')"
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
          <div class="pj-stat-item"><span class="pj-stat-value">{{ total }}</span><span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatTotal") }}</span></div>
          <div class="pj-stat-divider" />
          <div class="pj-stat-item"><span class="pj-stat-value">{{ activeCount }}</span><span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatActive") }}</span></div>
          <div class="pj-stat-divider" />
          <div class="pj-stat-item"><span class="pj-stat-value">{{ templateTotal }}</span><span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatTemplates") }}</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="pj-body">
      <!-- Filter bar -->
      <div class="pj-filter-bar">
        <div class="pj-filter-tabs">
          <div class="pj-tab" :class="{ active: filterStatus === '' }" @click="filterStatus = ''; onSearch()">
            <span class="pj-tab-dot" style="background:#409EFF" />{{ $t("message.opsflowPage.projectsFilterAll") }}
          </div>
          <div class="pj-tab" :class="{ active: filterStatus === 'active' }" @click="filterStatus = 'active'; onSearch()">
            <span class="pj-tab-dot" style="background:#67C23A" />{{ $t("message.opsflowPage.projectsFilterActive") }}
          </div>
          <div class="pj-tab" :class="{ active: filterStatus === 'inactive' }" @click="filterStatus = 'inactive'; onSearch()">
            <span class="pj-tab-dot" style="background:#909399" />{{ $t("message.opsflowPage.projectsFilterInactive") }}
          </div>
        </div>
        <div class="pj-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">{{ $t("message.common.refresh") }}</el-button>
          <el-button type="primary" :icon="Plus" @click="showForm(null)" size="small">{{ $t("message.opsflowPage.projectsNew") }}</el-button>
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
                {{ p.is_active ? $t('message.opsflowPage.projectsActive') : $t('message.opsflowPage.projectsInactive') }}
              </span>
              <span class="pj-card-owner" v-if="p.owner_name">👤 {{ p.owner_name }}</span>
            </div>
            <div class="pj-card-name">{{ p.name }}</div>
            <div class="pj-card-desc">{{ p.description || t('message.opsflowPage.projectsNoDesc') }}</div>
          </div>
          <div class="pj-card-bottom">
            <div class="pj-card-stats">
              <span class="pj-stat-chip"><b>{{ p.template_count ?? 0 }}</b> {{ $t("message.opsflowPage.projectsTemplates") }}</span>
              <span class="pj-stat-chip"><b>{{ p.execution_count ?? 0 }}</b> {{ $t("message.opsflowPage.projectsExecutions") }}</span>
            </div>
            <div class="pj-card-time">{{ p.created_at?.substring(0, 10) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit dialog -->
    <el-dialog v-model="formVisible" :title="formId ? $t('message.opsflowPage.projectsEdit') : $t('message.opsflowPage.projectsNew')" width="480px" top="5vh" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item :label="$t('message.common.name')" required>
          <el-input v-model="form.name" :placeholder="$t('message.opsflowPage.projectsNamePlaceholder')" maxlength="128" />
        </el-form-item>
        <el-form-item :label="$t('message.template.descLabel')">
          <el-input v-model="form.description" type="textarea" :rows="3" :placeholder="$t('message.opsflowPage.projectsDescPlaceholder')" maxlength="255" />
        </el-form-item>
        <el-form-item v-if="formId" :label="$t('message.opsflowPage.projectsActive')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.projectsMaxSchedules')">
          <el-input-number v-model="form.max_schedule_plans" :min="0" :max="1000" />
          <div class="form-tip" style="margin-left:8px">{{ $t("message.opsflowPage.projectsUnlimitedHint") }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false" >{{ $t("message.common.cancel") }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" >{{ formId ? $t('message.opsflowPage.projectsUpdate') : $t('message.opsflowPage.projectsCreate') }}</el-button>
      </template>
    </el-dialog>

    <!-- Detail dialog with tabs -->
    <el-dialog v-model="detailVisible" :title="detail?.name || ''" width="740px" top="5vh" destroy-on-close class="opsflow-dialog pj-detail-dialog">
      <template v-if="detail">
        <el-tabs v-model="detailTab" class="pj-detail-tabs">
          <!-- ═══ Tab: Overview ═══ -->
          <el-tab-pane :label="$t('message.opsflowPage.projectsOverview')" name="overview">
            <div class="pj-hero-row">
              <span class="pj-badge" :class="detail.is_active ? 'badge-active' : 'badge-inactive'">
                {{ detail.is_active ? $t('message.opsflowPage.projectsActive') : $t('message.opsflowPage.projectsInactive') }}
              </span>
              <span class="pj-hero-label" v-if="detail.owner_name">{{ $t("message.opsflowPage.projectsOwner") }}: {{ detail.owner_name }}</span>
              <span class="pj-hero-date">{{ $t("message.opsflowPage.projectsCreated") }} {{ detail.created_at?.substring(0, 10) }}</span>
            </div>

            <div class="pj-info-grid">
              <div class="pj-info-card"><span class="pj-info-label">{{ $t("message.opsflowPage.projectsDescLabel") }}</span><span class="pj-info-value">{{ detail.description || '—' }}</span></div>
              <div class="pj-info-card"><span class="pj-info-label">{{ $t("message.opsflowPage.projectsTemplates") }}</span><span class="pj-info-value">{{ detail.template_count ?? 0 }}</span></div>
              <div class="pj-info-card"><span class="pj-info-label">{{ $t("message.opsflowPage.projectsExecutions") }}</span><span class="pj-info-value">{{ detail.execution_count ?? 0 }}</span></div>
              <div class="pj-info-card"><span class="pj-info-label">{{ $t("message.opsflowPage.projectsScheduleLimit") }}</span><span class="pj-info-value">{{ detail.max_schedule_plans ?? $t('message.opsflowPage.projectsUnlimited') }}</span></div>
            </div>

            <div class="pj-overview-actions">
              <el-button size="small" :icon="Edit" @click="showForm(detail); detailVisible = false">{{ $t("message.common.edit") }}</el-button>
              <el-popconfirm title="Delete this project?" @confirm="handleDelete(detail)">
                <template #reference>
                  <el-button size="small" type="danger" :icon="Delete">{{ $t("message.common.delete") }}</el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-tab-pane>

          <!-- ═══ Tab: Members ═══ -->
          <el-tab-pane :label="$t('message.opsflowPage.projectsMembers')" name="members">
            <div class="pj-tab-header">
              <span class="pj-tab-title">{{ members.length }} member{{ members.length !== 1 ? 's' : '' }}</span>
            </div>
            <el-table :data="members" v-loading="membersLoading" size="small" empty-text="No members" style="width:100%">
              <el-table-column prop="username" :label="$t('message.opsflowPage.projectsUser')" min-width="140" />
              <el-table-column :label="$t('message.opsflowPage.projectsRole')" width="120">
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
                :loading="usersLoading" :placeholder="$t('message.opsflowPage.projectsSelectUsers')" style="width:260px" size="small" clearable>
                <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
              </el-select>
              <el-select v-model="newMemberRole" size="small" style="width:110px">
                <el-option label="Editor" value="editor" />
                <el-option label="Viewer" value="viewer" />
              </el-select>
              <el-button size="small" type="primary" @click="addMember" :disabled="!newMemberIds.length">{{ $t("message.opsflowPage.projectsAdd") }}</el-button>
            </div>
          </el-tab-pane>

          <!-- ═══ Tab: Plugins ═══ -->
          <el-tab-pane :label="$t('message.opsflowPage.projectsPlugins')" name="plugins">
            <div class="pj-tab-header">
              <span class="pj-tab-title">{{ $t("message.opsflowPage.projectsPluginsFor") }}</span>
            </div>
            <p class="pj-tab-desc">{{ $t("message.opsflowPage.projectsPluginsDesc") }}</p>
            <el-button size="small" :icon="Setting" @click="showPluginVisibility = true" type="primary">
              {{ $t("message.opsflowPage.projectsManagePlugins") }}
            </el-button>
          </el-tab-pane>

          <!-- ═══ Tab: Environment ═══ -->
          <el-tab-pane :label="$t('message.opsflowPage.projectsEnvironment')" name="env">
            <ProjectEnvVarPanel :project-id="detail.id" />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>

    <!-- Plugin Visibility Dialog -->
    <PluginVisibilityDialog v-model:visible="showPluginVisibility" :project-id="detail?.id" :project-name="detail?.name" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Setting } from '@element-plus/icons-vue'
import { request } from '/@/utils/service'
import { GetProjects, CreateProject, UpdateProject, DeleteProject, GetProjectDetail,
         GetProjectMembers, AddProjectMember, RemoveProjectMember } from '../opsflow/api/projects'
import PluginVisibilityDialog from '/@/views/apps/opsflow/components/pickers/PluginVisibilityDialog.vue'
import ProjectEnvVarPanel from '/@/views/apps/opsflow/components/common/ProjectEnvVarPanel.vue'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)
const projects = ref<any[]>([])
const searchQuery = ref('')
const filterStatus = ref('')

const total = computed(() => projects.value.length)
const activeCount = computed(() => projects.value.filter(p => p.is_active).length)
const templateTotal = computed(() => projects.value.reduce((s, p) => s + (p.template_count || 0), 0))
const emptyText = computed(() => t('message.opsflowPage.projectsNoProjects'))

// Form
const formVisible = ref(false)
const formId = ref<number | null>(null)
const form = ref({ name: '', description: '', is_active: true, max_schedule_plans: 20 })

// Detail
const detailVisible = ref(false)
const detail = ref<any>(null)
const detailTab = ref('overview')

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
    ElMessage.error(e?.msg || e?.message || t('message.opsflowPage.projectsLoadFailed'))
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
    form.value = { name: '', description: '', is_active: true, max_schedule_plans: 20 }
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
  // Load members, users, and current user id in parallel
  await Promise.all([
    loadMembers(row.id),
    loadAllUsers(),
    (async () => {
      try {
        const userRes = await request({ url: '/api/system/user/user_info/', method: 'get' })
        currentUserId.value = (userRes as any).data?.id || null
      } catch { /* ignore */ }
    })(),
  ])
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
    const res = await request({ url: '/api/system/user/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = (res as any).data?.results || (res as any).data || []
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

async function addMember() {
  if (!newMemberIds.value.length || !detail.value) return
  try {
    const results = await Promise.allSettled(
      newMemberIds.value.map(uid =>
        AddProjectMember(detail.value.id, uid, newMemberRole.value)
      )
    )
    const succeeded = results.filter(r => r.status === 'fulfilled').length
    const failed = results.filter(r => r.status === 'rejected').length
    if (failed > 0) {
      ElMessage.warning(`${succeeded} member(s) added, ${failed} failed`)
    } else {
      ElMessage.success(`Added ${succeeded} member(s)`)
    }
    newMemberIds.value = []
    await loadMembers(detail.value.id)
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Failed to add member')
  }
}

async function removeMember(row: any) {
  if (!detail.value) return
  try {
    await RemoveProjectMember(detail.value.id, row.id)
    ElMessage.success(t('message.opsflowPage.projectsMemberRemoved'))
    await loadMembers(detail.value.id)
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed to remove member') }
}

async function handleSave() {
  if (!form.value.name) { ElMessage.warning('Project name is required'); return }
  saving.value = true
  try {
    if (formId.value) {
      await UpdateProject(formId.value, form.value)
      ElMessage.success(t('message.opsflowPage.projectsUpdated'))
    } else {
      await CreateProject({ name: form.value.name, description: form.value.description })
      ElMessage.success(t('message.opsflowPage.projectsCreated'))
    }
    formVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Save failed')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await DeleteProject(row.id)
    ElMessage.success(t('message.opsflowPage.projectsDeleted'))
    detailVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Delete failed')
  }
}

function onSearch() { fetchData() }

// When detail dialog closes, reset tab and close plugin visibility dialog
watch(detailVisible, (v) => {
  if (!v) {
    detailTab.value = 'overview'
    showPluginVisibility.value = false
  }
})

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

/* ===== Detail dialog (tabs style, OpsFlow consistent) ===== */
.pj-detail-dialog { }
.pj-detail-dialog :deep(.el-dialog__header) {
  padding: 16px 24px; margin: 0; border-bottom: 1px solid #e4e7ed; font-weight: 600;
}
.pj-detail-dialog :deep(.el-dialog__body) { padding: 0; }
.pj-detail-dialog :deep(.el-dialog__footer) { display: none; }

/* ── Tabs ── */
.pj-detail-tabs { }
.pj-detail-tabs :deep(.el-tabs__header) {
  margin: 0; padding: 0 24px; background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}
.pj-detail-tabs :deep(.el-tabs__nav-wrap) { padding: 0; }
.pj-detail-tabs :deep(.el-tabs__item) {
  font-size: 13px; font-weight: 500; color: #606266;
  padding: 14px 20px; height: auto; line-height: 1;
}
.pj-detail-tabs :deep(.el-tabs__item.is-active) { color: #409EFF; font-weight: 600; }
.pj-detail-tabs :deep(.el-tabs__active-bar) { background: #409EFF; height: 2px; }
.pj-detail-tabs :deep(.el-tabs__content) { padding: 20px 24px; }

/* ── Hero row (Overview tab) ── */
.pj-hero-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 18px;
}
.pj-badge {
  display: inline-flex; align-items: center; font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.3px;
}
.badge-active { background: #f0f9eb; color: #67C23A; }
.badge-inactive { background: #f5f5f5; color: #909399; }
.pj-hero-label { font-size: 13px; color: #606266; }
.pj-hero-date { font-size: 12px; color: #909399; margin-left: auto; }

/* ── Info grid (Overview tab) ── */
.pj-info-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}
.pj-info-card {
  background: #f8f9fb; border-radius: 10px; padding: 14px 16px;
  border: 1px solid #f0f0f0; display: flex; flex-direction: column; gap: 6px;
}
.pj-info-label { font-size: 11px; color: #909399; text-transform: uppercase; letter-spacing: 0.3px; }
.pj-info-value { font-size: 14px; font-weight: 600; color: #303133; }

/* ── Overview actions ── */
.pj-overview-actions { display: flex; gap: 8px; padding-top: 16px; border-top: 1px solid #f0f0f0; }

/* ── Tab header / desc ── */
.pj-tab-header { margin-bottom: 14px; }
.pj-tab-title { font-size: 14px; font-weight: 600; color: #303133; }
.pj-tab-desc { margin: 0 0 14px; font-size: 13px; color: #909399; line-height: 1.6; }

/* ── Member add row ── */
.pj-add-row { display: flex; gap: 8px; margin-top: 14px; align-items: center; }
</style>
