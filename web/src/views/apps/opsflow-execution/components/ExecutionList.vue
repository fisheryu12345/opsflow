<template>
  <div class="execution-list">
    <!-- Filter bar -->
    <div class="filter-bar">
      <el-select v-model="filterTemplate" placeholder="All templates" clearable filterable style="width: 200px"
                 @change="fetchExecutions">
        <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="All statuses" clearable multiple style="width: 200px"
                 @change="fetchExecutions">
        <el-option label="Pending" value="pending" />
        <el-option label="Running" value="running" />
        <el-option label="Paused" value="paused" />
        <el-option label="Completed" value="completed" />
        <el-option label="Failed" value="failed" />
        <el-option label="Cancelled" value="cancelled" />
      </el-select>
      <el-button :icon="Refresh" @click="fetchExecutions" :loading="loading">
        Refresh
      </el-button>
      <div class="filter-spacer" />
      <el-button type="primary" :icon="Plus" @click="showCreateDialog" :disabled="templates.length === 0">
        New Execution
      </el-button>
    </div>

    <!-- Table -->
    <el-table :data="executions" v-loading="loading" stripe highlight-current-row
              @row-click="onRowClick" style="width: 100%" :empty-text="emptyText">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="Status" width="120">
        <template #default="{ row }">
          <div class="status-cell">
            <span class="status-dot" :style="{ background: statusColor(row.status) }" />
            <el-tag :type="statusTagType(row.status)" size="small" effect="dark">
              {{ statusLabel(row.status) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="template_name" label="Template" min-width="180" show-overflow-tooltip />
      <el-table-column label="Started" width="170">
        <template #default="{ row }">{{ row.started_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="Duration" width="110">
        <template #default="{ row }">
          {{ row.started_at && row.ended_at ? formatDuration(row.started_at, row.ended_at) : (row.started_at ? 'Running...' : '-') }}
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click.stop="onViewDetail(row)">Detail</el-button>
          <el-button v-if="row.status === 'pending'" size="small" type="success" link
                     :loading="startingId === row.id" @click.stop="onStart(row)">Start</el-button>
          <el-button v-if="row.status === 'running'" size="small" type="warning" link
                     :loading="pausingId === row.id" @click.stop="onPause(row)">Pause</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                     layout="prev, pager, next, total" @current-change="onPageChange" />
    </div>

    <!-- Create dialog -->
    <el-dialog v-model="createVisible" title="New Execution" width="480px">
      <el-form label-width="80px">
        <el-form-item label="Template">
          <el-select v-model="createTemplateId" placeholder="Select template" filterable style="width: 100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id">
              <div class="template-option">
                <span>{{ t.name }}</span>
                <el-tag v-if="t.is_draft" size="small" type="info" effect="plain">draft</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <div v-if="selectedTemplate" class="template-info">
          <div class="template-info-row">
            <span class="info-label">Created:</span>
            <span>{{ selectedTemplate.created_at }}</span>
          </div>
          <div class="template-info-row" v-if="selectedTemplate.pipeline_tree">
            <span class="info-label">Nodes:</span>
            <span>{{ selectedTemplate.pipeline_tree.nodes?.length || 0 }}</span>
          </div>
        </div>

        <!-- Optional node selection (execution scheme) -->
        <div v-if="optionalNodes.length > 0" class="optional-nodes-section">
          <div class="section-label">Optional Nodes (deselect to skip)</div>
          <el-checkbox-group v-model="selectedNodeIds" class="node-checkbox-group">
            <el-checkbox v-for="node in optionalNodes" :key="node.id" :label="node.id" class="node-checkbox">
              {{ node.label || node.id }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="onCreate">Create</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetTemplates } from '/@/api/opsflow/templates'
import { GetExecutions, CreateExecution, StartExecution as StartExec, PauseExecution } from '/@/api/opsflow/executions'

const emit = defineEmits<{ viewDetail: [execution: any] }>()

const templates = ref<any[]>([])
const executions = ref<any[]>([])
const loading = ref(false)
const filterTemplate = ref<number | null>(null)
const filterStatus = ref<string[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const startingId = ref<number | null>(null)
const pausingId = ref<number | null>(null)
const createVisible = ref(false)
const createTemplateId = ref<number | null>(null)
const creating = ref(false)

const emptyText = computed(() => loading.value ? 'Loading...' : 'No executions yet. Create one to get started.')
const selectedTemplate = computed(() => templates.value.find(t => t.id === createTemplateId.value))
const selectedNodeIds = ref<string[]>([])
const optionalNodes = computed(() => {
  const tree = selectedTemplate.value?.pipeline_tree || {}
  const nodes = tree.nodes || []
  return nodes.filter((n: any) =>
    n.node_type === 'atom' && n.optional !== false
  )
})
watch(createTemplateId, () => {
  selectedNodeIds.value = optionalNodes.value.map((n: any) => n.id)
})

function statusColor(status: string) {
  const map: Record<string, string> = { pending: '#909399', running: '#E6A23C', paused: '#909399', completed: '#67C23A', failed: '#F56C6C', cancelled: '#909399' }
  return map[status] || '#909399'
}
function statusTagType(status: string) {
  const map: Record<string, string> = { pending: 'info', running: 'warning', paused: 'info', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[status] || 'info'
}
function statusLabel(status: string) {
  const map: Record<string, string> = { pending: 'Pending', running: 'Running', paused: 'Paused', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled' }
  return map[status] || status
}
function formatDuration(start: string, end: string) {
  const diff = new Date(end).getTime() - new Date(start).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
}

async function fetchTemplates() {
  try {
    const res = await GetTemplates()
    templates.value = res.data || res.results || []
  } catch { /* ignore */ }
}
async function fetchExecutions() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterTemplate.value) params.template = filterTemplate.value
    if (filterStatus.value.length) params.status = filterStatus.value.join(',')
    const res = await GetExecutions(params)
    executions.value = res.data?.results || res.data || res.results || []
    total.value = res.data?.count || res.count || 0
  } catch { /* ignore */ }
  loading.value = false
}

function showCreateDialog() { createTemplateId.value = null; createVisible.value = true }
function onPageChange() { fetchExecutions() }

async function onCreate() {
  if (!createTemplateId.value) { ElMessage.warning('Please select a template'); return }
  creating.value = true
  try {
    // Compute excluded nodes = all optional nodes minus selected ones
    const allOptional = optionalNodes.value.map((n: any) => n.id)
    const excluded = allOptional.filter((id: string) => !selectedNodeIds.value.includes(id))
    const data: any = { template: createTemplateId.value }
    if (excluded.length > 0) {
      data.excluded_nodes = excluded
    }
    const res = await CreateExecution(data)
    const exec = res.data?.data || res.data
    if (exec?.id) {
      createVisible.value = false
      ElMessage.success('Execution created')
      await fetchExecutions()
      emit('viewDetail', exec)
    }
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed to create execution') }
  creating.value = false
}
function onRowClick(row: any) { emit('viewDetail', row) }
function onViewDetail(row: any) { emit('viewDetail', row) }
async function onStart(row: any) {
  startingId.value = row.id
  try { await StartExec(row.id); await fetchExecutions() } catch { /* ignore */ }
  startingId.value = null
}
async function onPause(row: any) {
  pausingId.value = row.id
  try { await PauseExecution(row.id); await fetchExecutions() } catch { /* ignore */ }
  pausingId.value = null
}

onMounted(() => { fetchTemplates(); fetchExecutions() })
</script>

<style scoped>
.execution-list { display: flex; flex-direction: column; height: 100%; }
.filter-bar {
  display: flex; gap: 12px; align-items: center; padding: 12px 16px;
  background: #fff; border-bottom: 1px solid #ebeef5; flex-shrink: 0;
}
.filter-spacer { flex: 1; }
.status-cell { display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.pagination-wrap { display: flex; justify-content: flex-end; padding: 12px 16px; flex-shrink: 0; }
.template-option { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.template-info { margin-top: 8px; padding: 10px 12px; background: #f5f7fa; border-radius: 6px; font-size: 12px; }
.template-info-row { display: flex; justify-content: space-between; padding: 2px 0; }
.template-info-row .info-label { color: #909399; }
.optional-nodes-section { margin-top: 12px; }
.optional-nodes-section .section-label { font-size: 12px; color: #606266; font-weight: 500; margin-bottom: 8px; }
.node-checkbox-group { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; padding: 8px 12px; background: #fafafa; border-radius: 6px; }
.node-checkbox { margin: 0; font-size: 12px; }
</style>
