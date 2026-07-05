<template>
  <div class="service-admin">
    <!-- Toolbar -->
    <div class="sa-toolbar">
      <div class="sa-toolbar-left">
        <el-button type="primary" size="small" @click="onCreate">
          <el-icon><Plus /></el-icon> 新建服务项
        </el-button>
        <el-button size="small" @click="onManageCategories">
          <el-icon><FolderOpened /></el-icon> 管理分类
        </el-button>
      </div>
      <div class="sa-toolbar-right">
        <el-input v-model="searchQuery" placeholder="搜索服务..." clearable size="small" style="width:200px" @input="loadItems" />
      </div>
    </div>

    <!-- Table -->
    <div class="sa-table-card">
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small">
        <el-table-column label="服务名称" min-width="180">
          <template #default="{ row }">
            <span style="margin-right:6px;">{{ row.icon || '📋' }}</span>
            <span style="font-weight:500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="分类" width="120" />
        <el-table-column label="绑定流程" width="160">
          <template #default="{ row }">
            <span v-if="row.workflow_name" style="color:#409EFF;">{{ row.workflow_name }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="模式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.mode === 'flow' ? 'primary' : 'success'" size="small">
              {{ row.mode === 'flow' ? '流程驱动' : '快捷服务' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可见范围" width="100">
          <template #default="{ row }">
            <span style="color:#909399;">{{ row.visible_to === 'all' ? '全员' : row.visible_to }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" width="60" prop="sort_order" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="onEdit(row)">编辑</el-button>
            <el-button size="small" text @click="onPreview(row)">预览</el-button>
            <el-button size="small" text type="danger" @click="onToggleActive(row)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="showDialog" :title="editingId ? '编辑服务项' : '新建服务项'" width="600px" top="5vh" destroy-on-close append-to-body>
      <el-form label-position="top" size="small" v-loading="saving">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="服务名称" required>
              <el-input v-model="form.name" placeholder="如: 申请服务器" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="服务分类">
              <el-select v-model="form.category" clearable filterable style="width:100%" placeholder="选择分类">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="服务描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="描述这个服务做什么" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="图标">
              <el-input v-model="form.icon" placeholder="🖥️" maxlength="8" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="服务模式">
              <el-select v-model="form.mode" style="width:100%">
                <el-option label="流程驱动" value="flow" />
                <el-option label="快捷服务" value="lightweight" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预计时长">
              <el-input v-model="form.expected_duration" placeholder="3-5 工作日" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.mode === 'flow'" label="绑定流程">
          <el-select v-model="form.workflow" clearable filterable style="width:100%" placeholder="选择审批流程">
            <el-option v-for="wf in workflows" :key="wf.id" :label="wf.name" :value="wf.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="可见范围">
          <el-radio-group v-model="form.visible_to">
            <el-radio value="all">全员可见</el-radio>
            <el-radio value="role">指定角色</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog v-model="showPreview" title="服务预览" width="520px" top="8vh" destroy-on-close append-to-body>
      <div v-if="previewItem" class="sa-preview">
        <div class="sa-preview-header">
          <span class="sa-preview-icon">{{ previewItem.icon || '📋' }}</span>
          <div class="sa-preview-info">
            <div class="sa-preview-name">{{ previewItem.name }}</div>
            <div class="sa-preview-meta">
              <span v-if="previewItem.category_name" class="sa-preview-tag">{{ previewItem.category_name }}</span>
              <el-tag :type="previewItem.mode === 'flow' ? 'primary' : 'success'" size="small">
                {{ previewItem.mode === 'flow' ? '流程驱动' : '快捷服务' }}
              </el-tag>
              <span v-if="previewItem.expected_duration" class="sa-preview-duration">⏱ {{ previewItem.expected_duration }}</span>
            </div>
          </div>
        </div>
        <div v-if="previewItem.description" class="sa-preview-desc">{{ previewItem.description }}</div>
        <div v-if="previewItem.form_fields?.length" class="sa-preview-fields">
          <div class="sa-preview-section-title">申请表单预览</div>
          <div v-for="(f, idx) in previewItem.form_fields" :key="idx" class="sa-preview-field">
            <div class="sa-preview-field-label">{{ f.name }}<span v-if="f.required" style="color:#F56C6C;"> *</span></div>
            <div class="sa-preview-field-value">
              <template v-if="f.type === 'TEXT'">
                <div class="sa-preview-input sa-preview-textarea">{{ f.placeholder || '' }}</div>
              </template>
              <template v-else-if="f.type === 'SELECT'">
                <div class="sa-preview-input">请选择{{ f.name }}</div>
              </template>
              <template v-else-if="f.type === 'RADIO'">
                <div class="sa-preview-input">
                  <span v-for="(c, ci) in (f.choice || [])" :key="ci" style="margin-right:16px;">○ {{ c.label }}</span>
                </div>
              </template>
              <template v-else-if="f.type === 'CHECKBOX'">
                <div class="sa-preview-input">
                  <span v-for="(c, ci) in (f.choice || [])" :key="ci" style="margin-right:16px;">□ {{ c.label }}</span>
                </div>
              </template>
              <template v-else>
                <div class="sa-preview-input">{{ f.placeholder || '' }}</div>
              </template>
            </div>
          </div>
        </div>
        <div class="sa-preview-footer">
          <el-tag v-if="previewItem.workflow_name" type="info" size="small">
            绑定流程: {{ previewItem.workflow_name }}
          </el-tag>
          <span v-if="previewItem.visible_to !== 'all'" style="font-size:11px;color:#909399;">
            可见范围: {{ previewItem.visible_to }}
          </span>
          <span style="margin-left:auto;font-size:11px;color:#c0c4cc;">排序: {{ previewItem.sort_order }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, FolderOpened } from '@element-plus/icons-vue'
import { serviceItemApi, workflowApi, serviceCategoryApi } from '/@/api/itsm/index'

const loading = ref(false)
const items = ref<any[]>([])
const categories = ref<any[]>([])
const workflows = ref<any[]>([])
const searchQuery = ref('')
const showDialog = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const showPreview = ref(false)
const previewItem = ref<any>(null)
const form = ref<any>({
  name: '', description: '', icon: '📋', mode: 'flow',
  category: null, workflow: null, visible_to: 'all',
  is_active: true, expected_duration: '', sort_order: 0,
})

async function loadItems() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (searchQuery.value) params.search = searchQuery.value
    const res = await serviceItemApi.list(params)
    items.value = (res as any).results || (res as any).data || []
  } catch { items.value = [] }
  finally { loading.value = false }
}

async function loadCategories() {
  try {
    const res = await serviceCategoryApi.list({ page_size: 1000 })
    categories.value = (res as any).results || (res as any).data || []
  } catch { categories.value = [] }
}

async function loadWorkflows() {
  try {
    const res = await workflowApi.list({ page_size: 1000 })
    workflows.value = (res as any).results || (res as any).data || []
  } catch { workflows.value = [] }
}

function onCreate() {
  editingId.value = null
  form.value = { name: '', description: '', icon: '📋', mode: 'flow', category: null, workflow: null, visible_to: 'all', is_active: true, expected_duration: '', sort_order: 0 }
  showDialog.value = true
}

function onEdit(row: any) {
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

async function onSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入服务名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await serviceItemApi.update(String(editingId.value), form.value)
      ElMessage.success('已更新')
    } else {
      await serviceItemApi.create(form.value)
      ElMessage.success('已创建')
    }
    showDialog.value = false
    await loadItems()
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败')
  }
  saving.value = false
}

async function onToggleActive(row: any) {
  try {
    await serviceItemApi.update(String(row.id), { is_active: !row.is_active })
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '已启用' : '已停用')
  } catch { ElMessage.error('操作失败') }
}

function onPreview(row: any) {
  previewItem.value = row
  showPreview.value = true
}

function onManageCategories() {
  ElMessage.info('分类管理功能即将上线')
}

onMounted(async () => {
  await Promise.all([loadItems(), loadCategories(), loadWorkflows()])
})
</script>

<style lang="scss" scoped>
.service-admin { padding: 0; }

.sa-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  gap: 12px;
}
.sa-toolbar-left, .sa-toolbar-right { display: flex; align-items: center; gap: 8px; }

.sa-table-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  overflow: hidden;
}
.sa-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.sa-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }

/* ===== Preview ===== */
.sa-preview { font-size: 13px; }
.sa-preview-header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.sa-preview-icon { font-size: 32px; }
.sa-preview-name { font-size: 16px; font-weight: 600; color: #303133; }
.sa-preview-meta { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.sa-preview-tag { font-size: 11px; color: #909399; }
.sa-preview-duration { font-size: 11px; color: #c0c4cc; }
.sa-preview-desc { font-size: 13px; color: #606266; line-height: 1.6; padding: 10px 0; border-top: 1px solid #f5f6fa; margin-bottom: 10px; }
.sa-preview-section-title { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.sa-preview-fields { border-top: 1px solid #f0f0f0; padding-top: 12px; }
.sa-preview-field { margin-bottom: 10px; }
.sa-preview-field-label { font-size: 12px; color: #606266; margin-bottom: 4px; }
.sa-preview-field-value { }
.sa-preview-input {
  padding: 6px 10px; border: 1px solid #e8e8e8; border-radius: 6px;
  font-size: 12px; color: #c0c4cc; background: #fafafa; min-height: 28px;
}
.sa-preview-textarea { min-height: 50px; }
.sa-preview-footer {
  display: flex; align-items: center; gap: 8px; margin-top: 16px;
  padding-top: 10px; border-top: 1px solid #f0f0f0;
}
</style>
