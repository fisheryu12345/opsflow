<template>
  <div class="opsflow-template-page">
    <div class="template-page-body">
      <!-- Filter bar -->
      <div class="filter-bar">
        <el-input v-model="filterName" placeholder="Search name..." clearable style="width: 220px"
                  @keyup.enter="onFilter" @clear="onFilter">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterDraft" placeholder="Status" clearable filterable style="width: 140px"
                   @change="onFilter">
          <el-option label="Draft" :value="true" />
          <el-option label="Published" :value="false" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchData" :loading="loading">Refresh</el-button>
        <div class="filter-spacer" />
        <div class="view-toggle">
          <el-button :type="viewMode === 'table' ? 'primary' : 'default'" size="small" @click="viewMode = 'table'">
            <el-icon><List /></el-icon>
          </el-button>
          <el-button :type="viewMode === 'cards' ? 'primary' : 'default'" size="small" @click="viewMode = 'cards'">
            <el-icon><Grid /></el-icon>
          </el-button>
        </div>
        <el-button type="primary" :icon="Plus" @click="openCreate">New Template</el-button>
        <span v-if="useMock" class="mock-badge">Mock Data</span>
      </div>

      <!-- Table view -->
      <template v-if="viewMode === 'table'">
        <el-table :data="list" v-loading="loading" stripe highlight-current-row style="width: 100%"
                  :empty-text="emptyText" @row-click="openView" class="template-table">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="Name" min-width="40" show-overflow-tooltip />
          <el-table-column label="Status" width="120" align="center">
            <template #default="{ row }">
              <div class="status-cell">
                <span class="status-dot" :style="{ background: row.is_draft ? '#909399' : '#67C23A' }" />
                <el-tag :type="row.is_draft ? 'info' : 'success'" size="small" effect="dark">
                  {{ row.is_draft ? 'Draft' : 'Published' }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Pipeline" min-width="60" class-name="pipeline-col">
            <template #default="{ row }">
              <div class="mini-flow" v-if="row.pipeline_tree?.nodes?.length">
                <template v-for="(node, ni) in row.pipeline_tree.nodes" :key="node.id">
                  <div class="mini-node" :style="{ background: nodeColor(node) }"
                       :title="`${node.label || node.id} (${node.type}${node.atom_type ? ': ' + node.atom_type : ''})`">
                    <span class="mini-node-icon">{{ nodeIcon(node) }}</span>
                  </div>
                  <div v-if="ni < row.pipeline_tree.nodes.length - 1" class="mini-arrow">→</div>
                </template>
              </div>
              <span v-else class="no-pipeline">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_by_name" label="Created By" width="120" show-overflow-tooltip />
          <el-table-column label="V" width="50" align="center">
            <template #default="{ row }">
              <el-tag v-if="!row.is_draft" size="small" type="primary" effect="plain">V{{ row.version || 1 }}</el-tag>
              <span v-else class="no-version">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="Created" width="130" />
          <el-table-column label="Actions" width="300" fixed="right" class-name="actions-col">
            <template #default="{ row }">
              <div class="action-icons">
                <el-tooltip content="Edit" placement="top">
                  <el-button size="small" type="primary" link @click.stop="goEditTemplate(row)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Modify" placement="top">
                  <el-button size="small" type="primary" link @click.stop="openEdit(row)">
                    <el-icon><Setting /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="row.is_draft" content="Publish" placement="top">
                  <el-button size="small" type="success" link
                             :loading="publishingId === row.id" @click.stop="handlePublish(row)">
                    <el-icon><Upload /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="!row.is_draft" content="New Version" placement="top">
                  <el-button size="small" type="success" link
                             :loading="publishingId === row.id" @click.stop="handlePublish(row)">
                    <el-icon><Upload /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="!row.is_draft" content="Schedule" placement="top">
                  <el-button size="small" type="warning" link @click.stop="openSchedule(row)">
                    <el-icon><Timer /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Versions" placement="top">
                  <el-button size="small" type="info" link @click.stop="openVersions(row)">
                    <el-icon><Clock /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Delete" placement="top">
                  <el-button size="small" type="danger" link @click.stop="handleDelete(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- Card view -->
      <template v-if="viewMode === 'cards'">
        <div class="card-list" v-loading="loading">
          <el-empty v-if="!loading && list.length === 0" :description="emptyText" />
          <el-card v-for="item in list" :key="item.id" class="template-card" shadow="hover"
                   @click="openView(item)">
            <div class="tcard-header">
              <div class="tcard-title-row">
                <el-tooltip :content="item.name" placement="top">
                  <span class="tcard-title">{{ item.name }}</span>
                </el-tooltip>
                <el-tag :type="item.is_draft ? 'info' : 'success'" size="small" effect="dark">
                  {{ item.is_draft ? 'Draft' : 'Published' }}
                </el-tag>
              </div>
              <div class="tcard-meta">
                <span>by {{ item.created_by_name || '-' }}</span>
                <span>{{ item.created_at }}</span>
              </div>
            </div>
            <div class="tcard-pipeline" v-if="item.pipeline_tree?.nodes?.length">
              <div class="tcard-flow">
                <template v-for="(node, ni) in item.pipeline_tree.nodes" :key="node.id">
                  <div class="flow-node" :style="{ background: nodeColor(node) + '18', borderColor: nodeColor(node) }">
                    <span class="flow-node-icon">{{ nodeIcon(node) }}</span>
                    <span class="flow-node-label">{{ node.label || node.id }}</span>
                  </div>
                  <div v-if="ni < item.pipeline_tree.nodes.length - 1" class="flow-arrow">→</div>
                </template>
              </div>
            </div>
            <div class="tcard-footer">
              <div class="tcard-footer-top">
                <div class="tcard-stats">
                  <span class="tcard-stat">
                    <el-icon style="margin-right: 3px"><Connection /></el-icon>
                    {{ item.pipeline_tree?.nodes?.length || 0 }} nodes
                  </span>
                  <span class="tcard-stat">
                    <el-icon style="margin-right: 3px"><Share /></el-icon>
                    {{ item.pipeline_tree?.edges?.length || 0 }} edges
                  </span>
                </div>
              </div>
              <div class="tcard-actions" @click.stop>
                <el-tooltip content="Edit" placement="top">
                  <el-button size="small" type="primary" link @click.stop="goEditTemplate(item)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Modify" placement="top">
                  <el-button size="small" type="primary" link @click="openEdit(item)">
                    <el-icon><Setting /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="item.is_draft" content="Publish" placement="top">
                  <el-button size="small" type="success" link
                             :loading="publishingId === item.id" @click.stop="handlePublish(item)">
                    <el-icon><Upload /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="!item.is_draft" content="New Version" placement="top">
                  <el-button size="small" type="success" link
                             :loading="publishingId === item.id" @click.stop="handlePublish(item)">
                    <el-icon><Upload /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="!item.is_draft" content="Schedule" placement="top">
                  <el-button size="small" type="warning" link @click.stop="openSchedule(item)">
                    <el-icon><Timer /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Versions" placement="top">
                  <el-button size="small" type="info" link @click.stop="openVersions(item)">
                    <el-icon><Clock /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="Delete" placement="top">
                  <el-button size="small" type="danger" link @click.stop="handleDelete(item)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </el-card>
        </div>
      </template>

      <!-- Pagination -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                       layout="prev, pager, next, total" @current-change="onPageChange" />
      </div>
    </div>

    <!-- Create / Edit dialog -->
    <el-dialog v-model="formVisible" :title="isEditing ? 'Edit Template' : 'New Template'" width="520px">
      <el-form label-width="100px">
        <el-form-item label="Name" required>
          <el-input v-model="form.name" placeholder="Template name" />
        </el-form-item>
        <el-form-item label="Status">
          <el-switch v-model="form.is_draft" active-text="Draft" inactive-text="Published"
                     :active-value="true" :inactive-value="false" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- View dialog: pipeline visualization -->
    <el-dialog v-model="viewVisible" title="Template Detail" width="820px" top="5vh" class="view-dialog">
      <template v-if="viewRow">
        <!-- Info bar -->
        <div class="v-info-bar">
          <div class="v-info-item">
            <span class="v-info-label">Name</span>
            <el-tooltip :content="viewRow.name" placement="top">
              <span class="v-info-value name-ellipsis">{{ viewRow.name }}</span>
            </el-tooltip>
          </div>
          <div class="v-info-item">
            <span class="v-info-label">Status</span>
            <el-tag :type="viewRow.is_draft ? 'info' : 'success'" size="small">
              {{ viewRow.is_draft ? 'Draft' : 'Published' }}
            </el-tag>
          </div>
          <div class="v-info-item">
            <span class="v-info-label">Created By</span>
            <span class="v-info-value">{{ viewRow.created_by_name || '-' }}</span>
          </div>
          <div class="v-info-item">
            <span class="v-info-label">Created</span>
            <span class="v-info-value">{{ viewRow.created_at }}</span>
          </div>
          <div class="v-info-item">
            <span class="v-info-label">Updated</span>
            <span class="v-info-value">{{ viewRow.updated_at }}</span>
          </div>
        </div>

        <!-- Pipeline visualization -->
        <div class="v-section" v-if="viewRow.pipeline_tree">
          <div class="v-section-title">
            <el-icon style="margin-right: 6px"><Connection /></el-icon>
            Pipeline Flow
          </div>
          <div class="v-pipeline-stats">
            <span>Nodes: {{ viewRow.pipeline_tree.nodes?.length || 0 }}</span>
            <span>Edges: {{ viewRow.pipeline_tree.edges?.length || 0 }}</span>
          </div>
          <div class="v-flow" v-if="viewRow.pipeline_tree.nodes?.length">
            <div v-for="(node, ni) in viewRow.pipeline_tree.nodes" :key="node.id" class="v-flow-node-wrapper">
              <div class="v-flow-node" :style="{ background: nodeColor(node, true), borderColor: nodeColor(node) }">
                <div class="v-flow-node-header">
                  <span class="v-flow-node-icon">{{ nodeIcon(node) }}</span>
                  <span class="v-flow-node-title">{{ node.label || node.id }}</span>
                </div>
                <div class="v-flow-node-body">
                  <span class="v-flow-node-type">{{ node.type }}</span>
                  <span v-if="node.atom_type" class="v-flow-node-atom">{{ node.atom_type }}</span>
                </div>
              </div>
              <div v-if="ni < viewRow.pipeline_tree.nodes.length - 1" class="v-flow-connector">
                <div class="v-flow-arrow">↓</div>
                <div class="v-flow-line" />
              </div>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="v-legend">
          <span class="v-legend-title">Legend:</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#409EFF" /> Task</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#67C23A" /> Start</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#F56C6C" /> End</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#E6A23C" /> Gateway</span>
          <span class="v-legend-divider" />
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#909399" /> ServiceNow</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#67C23A" /> Ansible</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#E6A23C" /> HTTP</span>
          <span class="v-legend-item"><span class="v-legend-dot" style="background:#20B2AA" /> ESXi</span>
        </div>
      </template>
    </el-dialog>

    <!-- Schedule manager dialog -->
    <ScheduleManager
      v-model="scheduleVisible"
      :template-id="scheduleTemplateId"
      :template-name="scheduleTemplateName"
    />

    <!-- Version history dialog -->
    <VersionDialog
      v-model:visible="versionVisible"
      :template-id="versionTemplateId"
      :template-name="versionTemplateName"
      :current-version="versionCurrentVer"
      @rolled-back="fetchData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Plus, View, Edit, Upload, Delete, Search, List, Grid, Connection, Share, Timer, Setting, Clock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetTemplates, CreateTemplate, UpdateTemplate, DeleteTemplate, ConfirmDraft, GetTemplateDetail, PublishTemplate } from '/@/api/opsflow/templates'
import { useOpsflowStore } from '/@/views/apps/opsflow/stores/opsflowStore'
import ScheduleManager from './components/ScheduleManager.vue'
import VersionDialog from './components/VersionDialog.vue'

const router = useRouter()
const opsflowStore = useOpsflowStore()

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterName = ref('')
const filterDraft = ref<boolean | ''>('')
const useMock = ref(false)
const viewMode = ref<'table' | 'cards'>('table')

const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', is_draft: true })

const viewVisible = ref(false)
const viewRow = ref<any>(null)

const publishingId = ref<number | null>(null)
const scheduleVisible = ref(false)
const scheduleTemplateId = ref(0)
const scheduleTemplateName = ref('')

// 版本管理
const versionVisible = ref(false)
const versionTemplateId = ref<number | null>(null)
const versionTemplateName = ref('')
const versionCurrentVer = ref(1)

function openVersions(row: any) {
  versionTemplateId.value = row.id
  versionTemplateName.value = row.name
  versionCurrentVer.value = row.version || 1
  versionVisible.value = true
}

const emptyText = computed(() => loading.value ? 'Loading...' : useMock.value ? 'No data' : 'No templates yet')

/** Map node type to color (matching MonitorCanvas legend) */
function nodeColor(node: any, bg = false): string {
  const map: Record<string, string> = {
    start_event: '#67C23A',
    end_event: '#F56C6C',
    task: '#409EFF',
    gateway: '#E6A23C',
  }
  const typeColor = map[node.type] || '#909399'
  if (bg && node.atom_type) {
    const atomMap: Record<string, string> = {
      servicenow: '#909399',
      ansible: '#67C23A',
      http: '#E6A23C',
      esxi: '#20B2AA',
    }
    return atomMap[node.atom_type] || typeColor
  }
  if (bg) return typeColor
  return typeColor
}

/** Emoji/symbol for node type */
function nodeIcon(node: any): string {
  if (node.atom_type) {
    const iconMap: Record<string, string> = {
      ansible: '⚙',
      http: '↗',
      servicenow: '◆',
      esxi: '🖥',
    }
    return iconMap[node.atom_type] || '◉'
  }
  const iconMap: Record<string, string> = {
    start_event: '▶',
    end_event: '■',
    task: '◉',
    gateway: '◇',
  }
  return iconMap[node.type] || '○'
}

const mockData = computed<any[]>(() => [
  { id: 1, name: '日常巡检流程', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '检查磁盘', type: 'task', atom_type: 'ansible' }, { id: 'n3', label: '检查内存', type: 'task', atom_type: 'ansible' }, { id: 'n4', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }] }, is_draft: false, created_by_name: 'admin', created_at: '2026-05-20 09:00:00', updated_at: '2026-05-20 09:30:00' },
  { id: 2, name: '故障自愈 - Web 服务', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '健康检查', type: 'task', atom_type: 'http' }, { id: 'n3', label: '重启服务', type: 'task', atom_type: 'ansible' }, { id: 'n4', label: '二次检查', type: 'task', atom_type: 'http' }, { id: 'n5', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }] }, is_draft: false, created_by_name: 'admin', created_at: '2026-05-18 14:00:00', updated_at: '2026-05-19 10:00:00' },
  { id: 3, name: '数据库备份验证', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '执行备份', type: 'task', atom_type: 'ansible' }, { id: 'n3', label: '校验备份', type: 'task', atom_type: 'http' }, { id: 'n4', label: '通知结果', type: 'task', atom_type: 'http' }, { id: 'n5', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }] }, is_draft: true, created_by_name: 'admin', created_at: '2026-05-25 16:00:00', updated_at: '2026-05-25 16:00:00' },
  { id: 4, name: 'ESXi 虚拟机部署', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '创建 VM', type: 'task', atom_type: 'esxi' }, { id: 'n3', label: '配置网络', type: 'task', atom_type: 'ansible' }, { id: 'n4', label: '部署应用', type: 'task', atom_type: 'ansible' }, { id: 'n5', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }] }, is_draft: true, created_by_name: 'admin', created_at: '2026-05-30 11:00:00', updated_at: '2026-05-30 11:30:00' },
  { id: 5, name: '网络设备配置备份', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: 'SSH 备份配置', type: 'task', atom_type: 'ansible' }, { id: 'n3', label: '上传备份服务器', type: 'task', atom_type: 'http' }, { id: 'n4', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }] }, is_draft: false, created_by_name: 'admin', created_at: '2026-05-10 08:00:00', updated_at: '2026-05-12 09:00:00' },
  { id: 6, name: '安全漏洞扫描流程', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '执行扫描', type: 'task', atom_type: 'ansible' }, { id: 'n3', label: '生成报告', type: 'task', atom_type: 'http' }, { id: 'n4', label: '发送邮件通知', type: 'task', atom_type: 'http' }, { id: 'n5', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }] }, is_draft: true, created_by_name: 'admin', created_at: '2026-05-28 13:00:00', updated_at: '2026-05-28 13:00:00' },
  { id: 7, name: '应用发布 - 金丝雀部署', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '金丝雀发布', type: 'task', atom_type: 'ansible' }, { id: 'n3', label: '健康检查', type: 'task', atom_type: 'http' }, { id: 'n4', label: '全量发布', type: 'task', atom_type: 'ansible' }, { id: 'n5', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }] }, is_draft: false, created_by_name: 'admin', created_at: '2026-05-15 10:30:00', updated_at: '2026-05-16 14:20:00' },
  { id: 8, name: 'ServiceNow 变更审批', pipeline_tree: { nodes: [{ id: 'n1', label: 'Start', type: 'start_event' }, { id: 'n2', label: '创建变更单', type: 'task', atom_type: 'servicenow' }, { id: 'n3', label: '等待审批', type: 'task', atom_type: 'servicenow' }, { id: 'n4', label: '执行变更', type: 'task', atom_type: 'ansible' }, { id: 'n5', label: '关闭变更单', type: 'task', atom_type: 'servicenow' }, { id: 'n6', label: 'End', type: 'end_event' }], edges: [{ from: 'n1', to: 'n2' }, { from: 'n2', to: 'n3' }, { from: 'n3', to: 'n4' }, { from: 'n4', to: 'n5' }, { from: 'n5', to: 'n6' }] }, is_draft: true, created_by_name: 'admin', created_at: '2026-05-29 09:00:00', updated_at: '2026-05-29 09:00:00' },
])

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, limit: pageSize.value }
    if (filterName.value) params.search = filterName.value
    if (filterDraft.value !== '') params.is_draft = filterDraft.value
    const res = await GetTemplates(params)
    const items = res.data?.results || res.data || res.results || []
    if (items.length > 0) {
      list.value = items
      total.value = res.total || res.data?.count || res.count || items.length
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
  if (filterName.value) {
    const q = filterName.value.toLowerCase()
    items = items.filter(i => i.name.toLowerCase().includes(q))
  }
  if (filterDraft.value !== '') items = items.filter(i => i.is_draft === filterDraft.value)
  list.value = items
  total.value = items.length
  useMock.value = true
}

function onFilter() { page.value = 1; fetchData() }
function onPageChange() { fetchData() }

function resetForm() {
  form.name = ''
  form.is_draft = true
  editingId.value = null
  isEditing.value = false
}

function openCreate() { resetForm(); formVisible.value = true }
function openEdit(row: any) {
  isEditing.value = true
  editingId.value = row.id
  form.name = row.name
  form.is_draft = row.is_draft
  formVisible.value = true
}

async function goEditTemplate(row: any) {
  try {
    const res = await GetTemplateDetail(row.id)
    const detail = res.data?.data || res.data || row
    opsflowStore.setCurrentTemplate(detail)
    router.push('/opsflow')
  } catch {
    opsflowStore.setCurrentTemplate(row)
    router.push('/opsflow')
  }
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('Name is required')
    return
  }
  saving.value = true
  try {
    const data = { name: form.name, is_draft: form.is_draft }
    if (isEditing.value && editingId.value) {
      if (!useMock.value) await UpdateTemplate(editingId.value, data)
      ElMessage.success('Updated')
    } else {
      if (!useMock.value) await CreateTemplate(data)
      ElMessage.success('Created')
    }
    formVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Operation failed')
  }
  saving.value = false
}

async function handlePublish(row: any) {
  publishingId.value = row.id
  try {
    if (useMock.value) {
      row.is_draft = false
    } else if (row.is_draft) {
      await ConfirmDraft(row.id)
      ElMessage.success('Published as V1')
    } else {
      await PublishTemplate(row.id)
      ElMessage.success('New version published')
    }
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Publish failed')
  }
  publishingId.value = null
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('Delete this template?', 'Confirm', { type: 'warning' })
    if (!useMock.value) await DeleteTemplate(row.id)
    ElMessage.success('Deleted')
    await fetchData()
  } catch { /* cancelled */ }
}

function openView(row: any) { viewRow.value = row; viewVisible.value = true }

function openSchedule(row: any) {
  scheduleTemplateId.value = row.id
  scheduleTemplateName.value = row.name
  scheduleVisible.value = true
}

onMounted(fetchData)
</script>

<style scoped>
.opsflow-template-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; background: #f0f2f5; overflow: hidden;
}
.template-page-body {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
  margin: 8px; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.filter-bar {
  display: flex; gap: 12px; align-items: center; padding: 12px 16px;
  background: #fff; border-bottom: 1px solid #ebeef5; flex-shrink: 0;
}
.filter-spacer { flex: 1; }
.view-toggle { display: flex; gap: 2px; }
.view-toggle .el-button { padding: 6px 8px; }

/* ---------- Status ---------- */
.status-cell { display: flex; align-items: center; gap: 6px; justify-content: center; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }

/* ---------- Mock badge ---------- */
.mock-badge {
  font-size: 11px; color: #E6A23C; background: #fdf6ec;
  padding: 2px 8px; border-radius: 4px;
}

/* ---------- Mini pipeline flow (table) ---------- */
.pipeline-col .mini-flow {
  display: flex; align-items: center; gap: 2px; flex-wrap: nowrap;
  max-width: 80px;
}
.mini-node {
  width: 22px; height: 22px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; cursor: default;
}
.mini-node-icon { font-size: 11px; color: #fff; line-height: 1; }
.mini-arrow { font-size: 12px; color: #C0C4CC; flex-shrink: 0; }
.no-pipeline { color: #C0C4CC; }

/* ---------- Card view ---------- */
.card-list {
  flex: 1; overflow-y: auto; padding: 16px;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px;
  align-content: start;
}
.template-card { cursor: pointer; }
.template-card:hover { border-color: #409EFF; }
.tcard-header { margin-bottom: 12px; }
.tcard-title-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.tcard-title { font-size: 15px; font-weight: 600; color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tcard-meta { display: flex; gap: 16px; font-size: 12px; color: #C0C4CC; margin-top: 4px; }
.tcard-pipeline { margin-bottom: 12px; }
.tcard-flow { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.flow-node {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px;
  border: 1px solid; border-radius: 6px; font-size: 12px;
}
.flow-node-icon { font-size: 12px; }
.flow-node-label { color: #303133; font-weight: 500; white-space: nowrap; }
.flow-arrow { font-size: 14px; color: #C0C4CC; }
.tcard-footer { display: flex; flex-direction: column; gap: 8px; padding-top: 8px; border-top: 1px solid #f0f0f0; }
.tcard-footer-top { display: flex; justify-content: space-between; align-items: center; }
.tcard-stats { display: flex; gap: 16px; }
.tcard-stat { font-size: 12px; color: #909399; display: flex; align-items: center; }
.tcard-actions { display: flex; flex-wrap: wrap; gap: 2px; }

/* ---------- Pagination ---------- */
.pagination-wrap {
  display: flex; justify-content: flex-end; padding: 12px 16px;
  background: #fff; flex-shrink: 0; border-top: 1px solid #ebeef5;
}

/* ---------- View dialog ---------- */
.v-info-bar {
  display: flex; flex-wrap: wrap; gap: 20px; padding: 12px 16px;
  background: #f5f7fa; border-radius: 8px; margin-bottom: 20px;
}
.v-info-item { display: flex; flex-direction: column; gap: 2px; }
.v-info-label { font-size: 11px; color: #909399; text-transform: uppercase; }
.v-info-value { font-size: 14px; color: #303133; font-weight: 500; }
.name-ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; display: inline-block; vertical-align: middle; }

.v-section { margin-bottom: 20px; }
.v-section-title {
  font-size: 14px; font-weight: 600; color: #303133;
  display: flex; align-items: center; margin-bottom: 10px;
}
.v-pipeline-stats {
  display: flex; gap: 20px; font-size: 12px; color: #909399; margin-bottom: 12px;
}

/* Vertical flow in dialog */
.v-flow {
  display: flex; flex-direction: column; align-items: center; gap: 0;
}
.v-flow-node-wrapper { display: flex; flex-direction: column; align-items: center; }
.v-flow-node {
  border: 2px solid; border-radius: 10px; padding: 10px 20px; min-width: 180px;
  text-align: center;
}
.v-flow-node-header { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 4px; }
.v-flow-node-icon { font-size: 16px; }
.v-flow-node-title { font-size: 14px; font-weight: 600; color: #303133; }
.v-flow-node-body { display: flex; gap: 8px; justify-content: center; }
.v-flow-node-type { font-size: 11px; color: #909399; }
.v-flow-node-atom { font-size: 11px; color: #909399; font-weight: 600; }
.v-flow-connector { display: flex; flex-direction: column; align-items: center; height: 36px; }
.v-flow-arrow { font-size: 14px; color: #C0C4CC; line-height: 1; }
.v-flow-line { width: 1px; flex: 1; background: #dcdfe6; }

/* Legend */
.v-legend {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; background: #f5f7fa; border-radius: 6px;
  font-size: 12px; color: #606266;
}
.v-legend-title { font-weight: 600; color: #909399; }
.v-legend-item { display: flex; align-items: center; gap: 4px; }
.v-legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.v-legend-divider { width: 1px; height: 14px; background: #dcdfe6; }

.template-table { cursor: pointer; }
.action-icons { display: flex; align-items: center; gap: 4px; }
.action-icons .el-button,
.tcard-actions .el-button { padding: 5px 6px; border-radius: 6px; }
.action-icons .el-button--primary,
.tcard-actions .el-button--primary { background: #ecf5ff; }
.action-icons .el-button--success,
.tcard-actions .el-button--success { background: #f0f9eb; }
.action-icons .el-button--warning,
.tcard-actions .el-button--warning { background: #fdf6ec; }
.action-icons .el-button--danger,
.tcard-actions .el-button--danger { background: #fef0f0; }
.action-icons .el-button .el-icon,
.tcard-actions .el-button .el-icon { font-size: 15px; }
.action-icons .el-button:hover,
.tcard-actions .el-button:hover { opacity: 0.85; filter: brightness(0.95); }
</style>
