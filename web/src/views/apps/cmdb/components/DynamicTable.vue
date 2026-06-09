<template>
  <div class="cmdb-dynamic-table">
    <div class="cmdb-table-card">
      <div class="cmdb-table-header">
        <div class="cmdb-table-header-left">
          <span class="cmdb-table-title">{{ modelDef?.name || '' }} 实例</span>
          <span class="cmdb-table-subtitle">({{ modelDef?.code }})</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-button size="small" @click="showExportDialog" :disabled="!modelDef">
            <el-icon><Download /></el-icon> 导出
          </el-button>
          <el-button size="small" @click="showImportDialog" :disabled="!modelDef">
            <el-icon><Upload /></el-icon> 导入
          </el-button>
          <el-input v-model="searchText" placeholder="搜索..." size="small" style="width:180px;" clearable
            @keyup.enter="loadData" @clear="loadData" />
          <el-button type="primary" size="small" @click="showCreateDialog">
            <el-icon><Plus /></el-icon> 新增
          </el-button>
        </div>
      </div>

      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? '加载中...' : '暂无数据'">
        <el-table-column v-for="col in visibleColumns" :key="col.name" :prop="col.name" :label="col.label"
          :width="colWidth(col)" :min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="col.name === 'status'" class="cmdb-status-badge" :class="'cmdb-status-' + (row[col.name] || 'unknown')">
              <span class="cmdb-status-dot" />{{ statusLabel(row[col.name]) }}
            </span>
            <el-tag v-else-if="col.field_type === 'enum'" size="small">{{ row[col.name] }}</el-tag>
            <el-tag v-else-if="col.field_type === 'boolean'" :type="row[col.name] ? 'success' : 'info'" size="small">
              {{ row[col.name] ? '是' : '否' }}
            </el-tag>
            <span v-else>{{ row[col.name] }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button size="small" text type="primary" @click="showChangeHistory(row)" v-if="showDetailBtn">
              <el-icon><Timer /></el-icon>
            </el-button>
            <el-button size="small" text type="primary" @click="showDetail(row)" v-if="showDetailBtn">
              <el-icon><View /></el-icon>
            </el-button>
            <el-popconfirm title="确认删除?" @confirm="deleteRow(row)">
              <template #reference>
                <el-button size="small" text type="danger">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="cmdb-table-footer" v-if="total > pageSize">
        <el-pagination small background layout="total, prev, pager, next"
          :total="total" :page-size="pageSize" v-model:current-page="currentPage"
          @current-change="loadData" />
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editMode === 'create' ? '新增' : '编辑'" width="600px"
      :close-on-click-modal="false" destroy-on-close>
      <el-form :model="form" :label-width="100" size="small" v-loading="saving">
        <el-form-item v-for="f in editFields" :key="f.name" :label="f.label" :required="f.required">
          <el-input v-if="['string', 'ip'].includes(f.field_type)" v-model="form[f.name]" :placeholder="f.placeholder" />
          <el-input-number v-else-if="f.field_type === 'integer'" v-model="form[f.name]" :min="0" style="width:100%;" />
          <el-input-number v-else-if="f.field_type === 'float'" v-model="form[f.name]" :min="0" :precision="2" style="width:100%;" />
          <el-switch v-else-if="f.field_type === 'boolean'" v-model="form[f.name]" />
          <el-select v-else-if="f.field_type === 'enum'" v-model="form[f.name]" placeholder="请选择" style="width:100%;">
            <el-option v-for="opt in (f.options || [])" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-date-picker v-else-if="f.field_type === 'date'" v-model="form[f.name]" type="date" style="width:100%;" />
          <el-date-picker v-else-if="f.field_type === 'datetime'" v-model="form[f.name]" type="datetime" style="width:100%;" />
          <el-input v-else-if="f.field_type === 'json'" v-model="form[f.name]" type="textarea" :rows="3" />
          <el-input v-else v-model="form[f.name]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- Export Dialog -->
    <el-dialog v-model="exportDialogVisible" title="导出 Excel" width="400px" destroy-on-close>
      <p style="margin-bottom:16px;color:#606266;">将当前模型的所有实例导出为 Excel (.xlsx) 文件。</p>
      <el-button type="primary" :loading="exporting" @click="doExport">确认导出</el-button>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入 Excel" width="500px" destroy-on-close>
      <el-upload drag accept=".xlsx,.xls" :auto-upload="false" :on-change="onImportFileChange" :limit="1"
        style="margin-bottom:16px;">
        <el-icon :size="40" color="#409EFF"><Upload /></el-icon>
        <div style="margin-top:8px;">拖拽或点击上传 .xlsx 文件</div>
      </el-upload>
      <el-button type="primary" :loading="importing" :disabled="!importFile" @click="doImport">开始导入</el-button>
    </el-dialog>

    <!-- Change History Dialog -->
    <el-dialog v-model="historyDialogVisible" title="变更历史" width="700px" destroy-on-close>
      <div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
        <el-select v-model="historyFilter.action" placeholder="操作类型" size="small" clearable style="width:120px;">
          <el-option label="创建" value="create" />
          <el-option label="更新" value="update" />
          <el-option label="删除" value="delete" />
        </el-select>
        <el-input v-model="historyFilter.operator" placeholder="操作人" size="small" style="width:140px;" clearable />
        <el-date-picker v-model="historyFilter.dateRange" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" size="small" style="width:260px;" />
        <el-button size="small" type="primary" @click="loadChangeHistory">查询</el-button>
      </div>

      <div v-if="historyLoading" style="text-align:center;padding:30px;">
        <el-icon :size="24" color="#409EFF" class="is-loading"><Loading /></el-icon>
      </div>

      <el-timeline v-else-if="historyItems.length > 0">
        <el-timeline-item v-for="item in historyItems" :key="item.id" :timestamp="item.create_datetime"
          placement="top">
          <div class="history-item">
            <span :class="'history-tag history-tag-' + item.action">
              {{ actionLabel(item.action) }}
            </span>
            <span class="history-operator">{{ item.operator || 'system' }}</span>
            <div v-if="item.changes" class="history-changes">
              <div v-if="item.action === 'update' && item.changes.fields" v-for="ch in item.changes.fields" :key="ch.field" class="history-change-row">
                <span class="history-field">{{ ch.field }}</span>
                <span class="history-arrow">:</span>
                <span class="history-old">{{ formatValue(ch.old_value) }}</span>
                <span class="history-arrow">→</span>
                <span class="history-new">{{ formatValue(ch.new_value) }}</span>
              </div>
              <div v-else-if="item.action === 'create' && item.changes.new_value" class="history-simple">
                创建实例
              </div>
              <div v-else-if="item.action === 'delete' && item.changes.old_value" class="history-simple">
                删除实例
              </div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无变更记录" />

      <div class="cmdb-table-footer" v-if="historyTotal > historyPageSize">
        <el-pagination small background layout="total, prev, pager, next"
          :total="historyTotal" :page-size="historyPageSize" v-model:current-page="historyPage"
          @current-change="loadChangeHistory" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, reactive } from 'vue'
import { Plus, Edit, Delete, View, Download, Upload, Timer, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getInstances, createInstance, updateInstance, deleteInstance,
  exportInstances, importInstances, getChangeHistory,
} from '/@/api/cmdb/index'

const props = defineProps<{
  modelDef: any
  fields: any[]
  showDetailBtn?: boolean
}>()

const emit = defineEmits<{
  detail: [row: any]
  created: []
  deleted: []
}>()

const items = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchText = ref('')

const dialogVisible = ref(false)
const editMode = ref<'create' | 'edit'>('create')
const editingId = ref<string>('')
const form = ref<Record<string, any>>({})

// Export/Import state
const exportDialogVisible = ref(false)
const exporting = ref(false)
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)

// Change history state
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const historyItems = ref<any[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historyInstanceId = ref('')
const historyFilter = reactive({
  action: '',
  operator: '',
  dateRange: null as [string, string] | null,
})

// System fields to hide
const systemFields = ['instance_id', '__model_code', '__created_at', '__updated_at', 'rel_id']

const visibleColumns = computed(() =>
  props.fields.filter(f => !systemFields.includes(f.name))
)

const editFields = computed(() =>
  props.fields.filter(f => !systemFields.includes(f.name) && !f.is_readonly && !f.is_system)
)

function colWidth(col: any) {
  if (col.field_type === 'enum') return 120
  if (col.field_type === 'integer') return 100
  if (col.field_type === 'ip') return 160
  return undefined
}

function statusLabel(val: string) {
  const map: Record<string, string> = {
    normal: '正常', alarm: '告警', offline: '已下线',
    maintenance: '维护中', unknown: '未知',
    running: '运行中', stopped: '已停止', error: '异常',
    online: '在线', offline: '离线',
  }
  return map[val] || val
}

function actionLabel(val: string) {
  const map: Record<string, string> = { create: '创建', update: '更新', delete: '删除' }
  return map[val] || val
}

function formatValue(val: any) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

async function loadData() {
  if (!props.modelDef) return
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchText.value) params.search = searchText.value
    const res = await getInstances(props.modelDef.code, params)
    const data = res.data || {}
    items.value = data.items || data || []
    total.value = data.total || items.value.length
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e?.msg || e?.message))
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  editMode.value = 'create'
  editingId.value = ''
  const f: Record<string, any> = {}
  for (const field of editFields.value) {
    f[field.name] = field.default_value ?? (field.field_type === 'boolean' ? false : field.field_type === 'integer' ? 0 : null)
  }
  form.value = f
  dialogVisible.value = true
}

function showEditDialog(row: any) {
  editMode.value = 'edit'
  editingId.value = row.instance_id
  const f: Record<string, any> = {}
  for (const field of editFields.value) {
    f[field.name] = row[field.name] ?? null
  }
  form.value = f
  dialogVisible.value = true
}

function showDetail(row: any) {
  emit('detail', row)
}

function showChangeHistory(row: any) {
  historyInstanceId.value = row.instance_id
  historyPage.value = 1
  historyFilter.action = ''
  historyFilter.operator = ''
  historyFilter.dateRange = null
  historyDialogVisible.value = true
  loadChangeHistory()
}

async function loadChangeHistory() {
  if (!props.modelDef || !historyInstanceId.value) return
  historyLoading.value = true
  try {
    const params: any = { page: historyPage.value, page_size: historyPageSize.value }
    if (historyFilter.action) params.action = historyFilter.action
    if (historyFilter.operator) params.operator = historyFilter.operator
    if (historyFilter.dateRange) {
      params.start_date = historyFilter.dateRange[0]
      params.end_date = historyFilter.dateRange[1]
    }
    const res = await getChangeHistory(props.modelDef.code, historyInstanceId.value, params)
    const data = res.data || {}
    historyItems.value = data.items || []
    historyTotal.value = data.total || 0
  } catch (e: any) {
    ElMessage.error('加载变更历史失败: ' + (e?.msg || e?.message))
  } finally {
    historyLoading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    if (editMode.value === 'create') {
      await createInstance(props.modelDef.code, form.value)
      ElMessage.success('创建成功')
    } else {
      await updateInstance(props.modelDef.code, editingId.value, form.value)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    await loadData()
    emit('created')
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteRow(row: any) {
  try {
    await deleteInstance(props.modelDef.code, row.instance_id)
    ElMessage.success('已删除')
    await loadData()
    emit('deleted')
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e?.msg || e?.message))
  }
}

// ─── Export ───
function showExportDialog() {
  exportDialogVisible.value = true
}

async function doExport() {
  if (!props.modelDef) return
  exporting.value = true
  try {
    const res = await exportInstances(props.modelDef.code)
    // response interceptor returns full response for blob type; data is in res.data
    const blobData = res.data || res
    const blob = new Blob([blobData], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.modelDef.code}_export.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
    exportDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error('导出失败: ' + (e?.msg || e?.message))
  } finally {
    exporting.value = false
  }
}

// ─── Import ───
function showImportDialog() {
  importDialogVisible.value = true
  importFile.value = null
}

function onImportFileChange(uploadFile: any) {
  importFile.value = uploadFile.raw || null
  return false // Prevent auto-upload
}

async function doImport() {
  if (!props.modelDef || !importFile.value) return
  importing.value = true
  try {
    const res = await importInstances(props.modelDef.code, importFile.value)
    ElMessage.success('导入完成: ' + (res.data?.total || 0) + ' 条记录')
    importDialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error('导入失败: ' + (e?.msg || e?.message))
  } finally {
    importing.value = false
  }
}

watch(() => props.modelDef, () => {
  currentPage.value = 1
  loadData()
})

onMounted(() => {
  if (props.modelDef) loadData()
})
</script>

<style scoped>
@use '../../../../styles/opsflow-global' as *;

.cmdb-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.cmdb-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.cmdb-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.cmdb-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.cmdb-table-header-left { display: flex; align-items: center; gap: 8px; }
.cmdb-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }
.cmdb-table-subtitle { font-size: 12px; color: #909399; }
.cmdb-table-footer { padding: 12px 20px; display: flex; justify-content: flex-end; }

.cmdb-status-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px; }
.cmdb-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.cmdb-status-normal .cmdb-status-dot { background: #67C23A; }
.cmdb-status-normal { background: #f0f9eb; color: #67C23A; }
.cmdb-status-alarm .cmdb-status-dot { background: #F56C6C; }
.cmdb-status-alarm { background: #fef0f0; color: #F56C6C; }
.cmdb-status-unknown .cmdb-status-dot { background: #c0c4cc; }
.cmdb-status-unknown { background: #f5f7fa; color: #909399; }

/* Change History */
.history-item { line-height: 1.6; }
.history-tag { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 8px; }
.history-tag-create { background: #f0f9eb; color: #67C23A; }
.history-tag-update { background: #e6f7ff; color: #409EFF; }
.history-tag-delete { background: #fef0f0; color: #F56C6C; }
.history-operator { font-size: 12px; color: #909399; }
.history-changes { margin-top: 4px; font-size: 12px; }
.history-change-row { margin: 2px 0; }
.history-field { font-weight: 600; color: #606266; }
.history-arrow { color: #c0c4cc; margin: 0 4px; }
.history-old { color: #F56C6C; text-decoration: line-through; }
.history-new { color: #67C23A; }
.history-simple { color: #909399; font-style: italic; }
</style>
