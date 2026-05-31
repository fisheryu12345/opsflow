<template>
  <div class="kb-page">
    <!-- Hero Section -->
    <div class="kb-hero">
      <div class="kb-hero-bg" />
      <div class="kb-hero-inner">
        <div class="kb-hero-left">
          <h1 class="kb-hero-title">Knowledge Base</h1>
          <p class="kb-hero-subtitle">Runbooks, incidents &amp; engineering docs</p>
        </div>
        <div class="kb-hero-center">
          <el-input
            v-model="searchQuery"
            placeholder="Search..."
            clearable
            size="default"
            class="kb-search-input"
            @keyup.enter="onSearch"
            @clear="onSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <div class="kb-hero-stats">
          <div class="kb-stat-item">
            <span class="kb-stat-value">{{ total }}</span>
            <span class="kb-stat-label">Total</span>
          </div>
          <div class="kb-stat-divider" />
          <div class="kb-stat-item">
            <span class="kb-stat-value">{{ runbookCount }}</span>
            <span class="kb-stat-label">RB</span>
          </div>
          <div class="kb-stat-divider" />
          <div class="kb-stat-item">
            <span class="kb-stat-value">{{ incidentCount }}</span>
            <span class="kb-stat-label">IC</span>
          </div>
          <div class="kb-stat-divider" />
          <div class="kb-stat-item">
            <span class="kb-stat-value">{{ docCount }}</span>
            <span class="kb-stat-label">Doc</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="kb-body">
      <!-- Filter bar -->
      <div class="kb-filter-bar">
        <div class="kb-source-tabs">
          <div class="kb-tab" :class="{ active: filterSource === '' }" @click="filterSource = ''; onSearch()">
            <span class="tab-dot" style="background:#409EFF" />
            All
          </div>
          <div class="kb-tab" :class="{ active: filterSource === 'runbook' }" @click="filterSource = 'runbook'; onSearch()">
            <span class="tab-dot" style="background:#67C23A" />
            Runbooks
          </div>
          <div class="kb-tab" :class="{ active: filterSource === 'incident' }" @click="filterSource = 'incident'; onSearch()">
            <span class="tab-dot" style="background:#F56C6C" />
            Incidents
          </div>
          <div class="kb-tab" :class="{ active: filterSource === 'doc' }" @click="filterSource = 'doc'; onSearch()">
            <span class="tab-dot" style="background:#409EFF" />
            Docs
          </div>
        </div>
        <div class="kb-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">Refresh</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate" size="small">New Entry</el-button>
        </div>
      </div>

      <!-- Grid -->
      <div class="kb-grid" v-loading="loading">
        <el-empty v-if="!loading && list.length === 0" :description="emptyText" :image-size="80" />
        <div
          v-for="item in list" :key="item.id"
          class="kb-card"
          @click="openView(item)"
        >
          <div class="kb-card-top">
            <div class="kb-card-badge" :class="'badge-' + item.source">
              <el-icon size="11" style="margin-right:3px">
                <component :is="sourceIcon(item.source)" />
              </el-icon>
              {{ sourceLabel(item.source) }}
            </div>
            <div class="kb-card-title">{{ item.title }}</div>
            <div class="kb-card-desc">{{ previewText(item.content) }}</div>
          </div>
          <div class="kb-card-bottom">
            <div class="kb-card-tags">
              <span v-for="t in (item.tags || []).slice(0, 4)" :key="t" class="kb-tag">{{ t }}</span>
              <span v-if="(item.tags || []).length > 4" class="kb-tag-more">+{{ item.tags.length - 4 }}</span>
            </div>
            <div class="kb-card-meta">
              <span class="kb-card-time">{{ item.created_at?.substring(0, 10) }}</span>
              <span class="kb-card-words">{{ readingTime(item.content) }} min read</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit -->
    <el-dialog v-model="formVisible" :title="isEditing ? 'Edit Entry' : 'New Entry'" width="640px" top="5vh" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="Title" required>
          <el-input v-model="form.title" placeholder="Entry title" />
        </el-form-item>
        <el-form-item label="Content" required>
          <el-input v-model="form.content" type="textarea" :rows="10" placeholder="Write your knowledge content..." />
        </el-form-item>
        <el-form-item label="Tags">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option
                     placeholder="Add tags..." style="width: 100%">
            <el-option v-for="t in ['ansible', 'network', 'security', 'backup', 'deploy', 'monitor', 'docker', 'k8s', 'linux', 'database', 'nginx']"
                       :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="Source">
          <el-select v-model="form.source" placeholder="Source">
            <el-option label="Runbook" value="runbook" />
            <el-option label="Incident" value="incident" />
            <el-option label="Documentation" value="doc" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Detail -->
    <el-dialog v-model="viewVisible" :title="viewRow?.title || ''" width="760px" top="5vh" destroy-on-close class="kb-detail-dialog">
      <template v-if="viewRow">
        <div class="kb-detail-meta">
          <span class="kb-detail-badge" :class="'badge-' + viewRow.source">
            <el-icon size="12"><component :is="sourceIcon(viewRow.source)" /></el-icon>
            {{ sourceLabel(viewRow.source) }}
          </span>
          <span class="kb-detail-date">{{ viewRow.created_at?.substring(0, 10) }}</span>
          <span class="kb-detail-words">{{ readingTime(viewRow.content) }} min read</span>
        </div>
        <div class="kb-detail-tags" v-if="viewRow.tags?.length">
          <span v-for="t in viewRow.tags" :key="t" class="kb-tag">{{ t }}</span>
        </div>
        <div class="kb-detail-content">{{ viewRow.content }}</div>
        <div class="kb-detail-actions">
          <el-button size="small" :icon="Edit" @click="openEdit(viewRow); viewVisible = false">Edit</el-button>
          <el-button size="small" type="danger" :icon="Delete" @click="handleDelete(viewRow); viewVisible = false">Delete</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Refresh, Plus, Search, Edit, Delete, Clock, Notification, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetKnowledgeList, CreateKnowledge, UpdateKnowledge, DeleteKnowledge } from '/@/api/opsflow/knowledge'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const searchQuery = ref('')
const filterSource = ref('')
const useMock = ref(false)

const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', content: '', tags: [] as string[], source: 'doc' })

const viewVisible = ref(false)
const viewRow = ref<any>(null)

const emptyText = computed(() => useMock.value ? 'No data' : 'No entries yet. Create one to get started.')

const runbookCount = computed(() => list.value.filter(i => i.source === 'runbook').length)
const incidentCount = computed(() => list.value.filter(i => i.source === 'incident').length)
const docCount = computed(() => list.value.filter(i => i.source === 'doc').length)

function sourceIcon(src: string) {
  const map: Record<string, any> = { runbook: Notification, incident: Clock, doc: Document }
  return map[src] || Document
}

function sourceLabel(src: string) {
  const map: Record<string, string> = { runbook: 'Runbook', incident: 'Incident', doc: 'Doc' }
  return map[src] || src
}

function previewText(content: string) {
  return content ? content.replace(/\n/g, ' ').substring(0, 160) + (content.length > 160 ? '...' : '') : ''
}

function readingTime(content: string) {
  if (!content) return 0
  return Math.max(1, Math.round(content.length / 500))
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = {}
    if (searchQuery.value) params.search = searchQuery.value
    if (filterSource.value) params.source = filterSource.value
    const res = await GetKnowledgeList(params)
    const items = res.data?.data || res.data?.results || res.data || []
    if (items.length > 0) {
      list.value = items
      total.value = res.data?.total || res.data?.count || items.length
      useMock.value = false
    } else {
      fallbackMock()
    }
  } catch {
    fallbackMock()
  }
  loading.value = false
}

function fallbackMock() {
  let items = [...mockData.value]
  if (filterSource.value) items = items.filter(i => i.source === filterSource.value)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(i => i.title.toLowerCase().includes(q) || i.content.toLowerCase().includes(q))
  }
  list.value = items
  total.value = items.length
  useMock.value = true
}

const mockData = computed<any[]>(() => [
  { id: 1, title: 'Nginx Common Issue Troubleshooting', content: 'Common causes of Nginx startup failure:\n1. Port already in use (netstat -tlnp | grep 80)\n2. Config syntax error (nginx -t)\n3. SELinux blocking (setenforce 0 to test)\n\nSteps:\n- Check systemctl status nginx\n- View /var/log/nginx/error.log\n- Verify upstream backend is alive', tags: ['nginx', 'web', 'troubleshooting'], source: 'runbook', created_at: '2026-05-28 14:30:00' },
  { id: 2, title: 'Disk Space Alert Response', content: 'Standard procedure when disk usage exceeds 90%:\n1. Find large files: du -sh /* | sort -rh | head -10\n2. Clean logs: journalctl --vacuum-size=500M\n3. Clean Docker: docker system prune -af\n4. Expand cloud disk if above cannot resolve', tags: ['disk', 'monitor', 'ops'], source: 'runbook', created_at: '2026-05-27 09:15:00' },
  { id: 3, title: 'Database Connection Pool Exhaustion', content: 'Emergency response when MySQL connections hit max_connections:\n1. Check connections: SHOW PROCESSLIST;\n2. Kill idle: SELECT CONCAT(\'KILL \', id, \';\') FROM information_schema.PROCESSLIST WHERE COMMAND=\'Sleep\' AND TIME>300;\n3. Increase pool temporarily: SET GLOBAL max_connections=500;\n4. Investigate application-level connection leak', tags: ['mysql', 'database', 'incident'], source: 'incident', created_at: '2026-05-25 16:42:00' },
  { id: 4, title: 'K8s Node NotReady Troubleshooting', content: 'Steps to diagnose a NotReady Kubernetes node:\nkubectl get nodes\nkubectl describe node <name>\n# Check kubelet status\nssh <node> systemctl status kubelet\n# View kubelet logs\njournalctl -u kubelet -n 100 --no-pager\n# Restart kubelet\nsystemctl restart kubelet', tags: ['k8s', 'container', 'troubleshooting'], source: 'runbook', created_at: '2026-05-24 11:00:00' },
  { id: 5, title: 'Redis Memory Optimization', content: 'Redis memory best practices:\n1. Set maxmemory and eviction policy\n2. Use compressed data structures (ziplist, intset)\n3. Split large keys (max 10MB per key)\n4. Run MEMORY PURGE periodically\n5. Monitor RSS vs used_memory ratio in INFO memory', tags: ['redis', 'cache', 'optimization'], source: 'doc', created_at: '2026-05-22 08:30:00' },
  { id: 6, title: 'SSL Certificate Emergency Replacement', content: 'Steps to replace an expiring SSL certificate:\n1. Generate new cert or download from CA\n2. Upload to /etc/ssl/certs/\n3. Update Nginx/Traefik config\n4. Reload: nginx -s reload\n5. Verify: openssl s_client -connect example.com:443', tags: ['ssl', 'security', 'certificate'], source: 'runbook', created_at: '2026-05-20 15:20:00' },
  { id: 7, title: 'Cross-DC Network Latency Incident', content: 'Latency between DC-A and DC-B spiked from 2ms to 200ms.\nRoot cause: Fiber optic cable damaged by construction.\n\nActions:\n1. Confirm backup link bandwidth sufficient\n2. Notify construction team for repair\n3. Switch back to primary after repair', tags: ['network', 'incident'], source: 'incident', created_at: '2026-05-18 22:10:00' },
  { id: 8, title: 'Ansible Tower Usage Guide', content: 'Ansible Tower daily operations:\n1. Job Template creation and configuration\n2. Credential management (SSH Key / Vault)\n3. Workflow template design\n4. Notification setup (Email / Webhook)\n5. RBAC and audit logging', tags: ['ansible', 'tower', 'automation'], source: 'doc', created_at: '2026-05-15 10:00:00' },
])

async function onSearch() { fetchData() }

function resetForm() {
  form.title = ''; form.content = ''; form.tags = []; form.source = 'doc'
  editingId.value = null; isEditing.value = false
}

function openCreate() { resetForm(); formVisible.value = true }
function openEdit(row: any) {
  isEditing.value = true; editingId.value = row.id
  form.title = row.title; form.content = row.content
  form.tags = [...(row.tags || [])]; form.source = row.source || 'doc'
  formVisible.value = true
}

async function handleSave() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('Title and content are required'); return
  }
  saving.value = true
  try {
    const data = { title: form.title, content: form.content, tags: form.tags, source: form.source }
    if (isEditing.value && editingId.value) {
      await UpdateKnowledge(editingId.value, data)
      ElMessage.success('Updated')
    } else {
      await CreateKnowledge(data)
      ElMessage.success('Created')
    }
    formVisible.value = false; await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Operation failed')
  }
  saving.value = false
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('Delete this entry?', 'Confirm', { type: 'warning' })
    useMock.value ? fallbackMock() : await DeleteKnowledge(row.id)
    ElMessage.success('Deleted'); await fetchData()
  } catch { /* cancelled */ }
}

function openView(row: any) { viewRow.value = row; viewVisible.value = true }

onMounted(fetchData)
</script>

<style scoped>
/* ---------- Layout ---------- */
.kb-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden;
}

/* ---------- Hero (horizontal row) ---------- */
.kb-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.kb-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px),
    radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.kb-hero-inner {
  position: relative; z-index: 1;
  padding: 12px 20px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.kb-hero-left { flex: 0 0 auto; display: flex; flex-direction: column; gap: 1px; }
.kb-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.kb-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.kb-hero-center { flex: 1 1 auto; min-width: 0; }
.kb-search-input { width: 100%; max-width: 360px; }
.kb-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none; border-radius: 10px; padding: 2px 12px;
}
.kb-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.kb-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.kb-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.kb-hero-stats { flex: 0 0 auto; display: flex; flex-direction: row; align-items: center; gap: 0; }
.kb-stat-item { text-align: center; padding: 0 14px; }
.kb-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.kb-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.kb-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ---------- Body ---------- */
.kb-body {
  flex: 1; overflow-y: auto; padding: 0 16px 24px;
  width: 100%;
}

/* ---------- Filter bar ---------- */
.kb-filter-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10;
  background: #f5f6fa;
}
.kb-source-tabs { display: flex; gap: 4px; }
.kb-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500;
  color: #606266; cursor: pointer; transition: all 0.2s; user-select: none;
}
.kb-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.kb-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.kb-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ---------- Grid ---------- */
.kb-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px; padding-bottom: 24px; min-height: 200px;
}

/* ---------- Card ---------- */
.kb-card {
  display: flex; flex-direction: column; justify-content: space-between;
  background: #fff; border-radius: 14px; padding: 20px;
  cursor: pointer; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #f0f0f0; position: relative; overflow: hidden;
}
.kb-card:hover {
  transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1);
  border-color: transparent;
}
.kb-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  opacity: 0; transition: opacity 0.25s;
}
.kb-card:hover::before { opacity: 1; }
.kb-card:nth-child(4n+1)::before { background: linear-gradient(90deg, #409EFF, #7ec1ff); }
.kb-card:nth-child(4n+2)::before { background: linear-gradient(90deg, #67C23A, #95de64); }
.kb-card:nth-child(4n+3)::before { background: linear-gradient(90deg, #E6A23C, #f5d76e); }
.kb-card:nth-child(4n+4)::before { background: linear-gradient(90deg, #9B59B6, #c39bd3); }

.kb-card-top { flex: 1; }
.kb-card-badge {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;
  text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 10px;
}
.badge-runbook { background: #f0f9eb; color: #67C23A; }
.badge-incident { background: #fef0f0; color: #F56C6C; }
.badge-doc { background: #ecf5ff; color: #409EFF; }

.kb-card-title {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  line-height: 1.4; margin-bottom: 8px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.kb-card-desc {
  font-size: 13px; color: #909399; line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.kb-card-bottom { margin-top: 14px; padding-top: 14px; border-top: 1px solid #f5f5f5; }
.kb-card-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.kb-tag {
  display: inline-block; font-size: 11px; font-weight: 500;
  padding: 2px 8px; border-radius: 6px; color: #606266;
  background: #f5f6fa; transition: background 0.15s;
}
.kb-tag:hover { background: #e8eaed; }
.kb-tag-more { font-size: 11px; color: #C0C4CC; padding: 2px 4px; }
.kb-card-meta { display: flex; justify-content: space-between; align-items: center; }
.kb-card-time { font-size: 12px; color: #C0C4CC; }
.kb-card-words { font-size: 11px; color: #C0C4CC; }

/* ---------- Detail dialog ---------- */
.kb-detail-dialog :deep(.el-dialog__header) { padding-bottom: 8px; }
.kb-detail-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.kb-detail-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;
  text-transform: uppercase;
}
.kb-detail-date, .kb-detail-words { font-size: 12px; color: #C0C4CC; }
.kb-detail-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.kb-detail-content { font-size: 14px; color: #303133; line-height: 1.8; white-space: pre-wrap; background: #fafafa; padding: 16px; border-radius: 10px; border: 1px solid #f0f0f0; }
.kb-detail-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>
