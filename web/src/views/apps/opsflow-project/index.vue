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
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false" size="small">Cancel</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" size="small">{{ formId ? 'Update' : 'Create' }}</el-button>
      </template>
    </el-dialog>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" :title="detail?.name || ''" width="560px" top="5vh" destroy-on-close class="pj-detail-dialog">
      <template v-if="detail">
        <div class="pj-detail-meta">
          <span class="pj-card-badge" :class="detail.is_active ? 'badge-active' : 'badge-inactive'">
            {{ detail.is_active ? 'Active' : 'Inactive' }}
          </span>
          <span class="pj-detail-owner" v-if="detail.owner_name">👤 {{ detail.owner_name }}</span>
        </div>
        <el-descriptions :column="1" border size="small" class="pj-detail-descs">
          <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="Name">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="Description">{{ detail.description || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Owner">{{ detail.owner_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Templates">{{ detail.template_count ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="Executions">{{ detail.execution_count ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="Created">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
        <div class="pj-detail-actions">
          <el-button size="small" :icon="Edit" @click="showForm(detail); detailVisible = false">Edit</el-button>
          <el-popconfirm title="Delete this project?" @confirm="handleDelete(detail)">
            <template #reference>
              <el-button size="small" type="danger" :icon="Delete">Delete</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { GetProjects, CreateProject, UpdateProject, DeleteProject, GetProjectDetail } from '/@/api/opsflow/projects'

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
const form = ref({ name: '', description: '', is_active: true })

// Detail
const detailVisible = ref(false)
const detail = ref<any>(null)

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
    form.value = { name: row.name, description: row.description || '', is_active: row.is_active ?? true }
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

onMounted(fetchData)
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

/* ===== Detail dialog ===== */
.pj-detail-dialog :deep(.el-dialog__header) { padding-bottom: 8px; }
.pj-detail-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.pj-detail-owner { font-size: 13px; color: #606266; margin-left: auto; }
.pj-detail-descs { margin-bottom: 12px; }
.pj-detail-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>
