<template>
  <div class="cmdb-dynamic-table">
    <div class="cmdb-table-card">
      <div class="cmdb-table-header">
        <div class="cmdb-table-header-left">
          <span class="cmdb-table-title">{{ modelDef?.name || '' }} 实例</span>
          <span class="cmdb-table-subtitle">({{ modelDef?.code }})</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-input v-model="searchText" placeholder="搜索..." size="small" style="width:200px;" clearable
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
            <!-- Status badge for enum fields named status -->
            <span v-if="col.name === 'status'" class="cmdb-status-badge" :class="'cmdb-status-' + (row[col.name] || 'unknown')">
              <span class="cmdb-status-dot" />{{ statusLabel(row[col.name]) }}
            </span>
            <!-- Enum field -->
            <el-tag v-else-if="col.field_type === 'enum'" size="small">{{ row[col.name] }}</el-tag>
            <!-- Boolean -->
            <el-tag v-else-if="col.field_type === 'boolean'" :type="row[col.name] ? 'success' : 'info'" size="small">
              {{ row[col.name] ? '是' : '否' }}
            </el-tag>
            <!-- Default -->
            <span v-else>{{ row[col.name] }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon>
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
          <!-- String / IP -->
          <el-input v-if="['string', 'ip'].includes(f.field_type)" v-model="form[f.name]" :placeholder="f.placeholder" />
          <!-- Integer -->
          <el-input-number v-else-if="f.field_type === 'integer'" v-model="form[f.name]" :min="0" style="width:100%;" />
          <!-- Float -->
          <el-input-number v-else-if="f.field_type === 'float'" v-model="form[f.name]" :min="0" :precision="2" style="width:100%;" />
          <!-- Boolean -->
          <el-switch v-else-if="f.field_type === 'boolean'" v-model="form[f.name]" />
          <!-- Enum -->
          <el-select v-else-if="f.field_type === 'enum'" v-model="form[f.name]" placeholder="请选择" style="width:100%;">
            <el-option v-for="opt in (f.options || [])" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <!-- Date -->
          <el-date-picker v-else-if="f.field_type === 'date'" v-model="form[f.name]" type="date" style="width:100%;" />
          <!-- Datetime -->
          <el-date-picker v-else-if="f.field_type === 'datetime'" v-model="form[f.name]" type="datetime" style="width:100%;" />
          <!-- JSON -->
          <el-input v-else-if="f.field_type === 'json'" v-model="form[f.name]" type="textarea" :rows="3" />
          <!-- Default -->
          <el-input v-else v-model="form[f.name]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Plus, Edit, Delete, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getInstances, createInstance, updateInstance, deleteInstance } from '/@/api/cmdb/index'

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

watch(() => props.modelDef, () => {
  currentPage.value = 1
  loadData()
})

onMounted(() => {
  if (props.modelDef) loadData()
})
</script>

<style scoped>
@use '../../opsflow/styles/opsflow-global' as *;

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
</style>
