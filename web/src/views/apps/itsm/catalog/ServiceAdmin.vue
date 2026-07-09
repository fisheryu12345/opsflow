<template>
  <div class="service-admin">
    <!-- Toolbar -->
    <div class="sa-toolbar">
      <div class="sa-toolbar-left">
        <el-button type="primary" size="small" @click="onCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.serviceAdmin.newService') }}
        </el-button>
        <el-button size="small" @click="onManageCategories">
          <el-icon><FolderOpened /></el-icon> {{ $t('message.serviceAdmin.manageCategories') }}
        </el-button>
      </div>
      <div class="sa-toolbar-right">
        <Teleport v-if="active && searchEl" :to="searchEl">
          <el-input v-model="searchQuery" :placeholder="$t('message.serviceAdmin.searchPlaceholder')" clearable size="default" class="sa-search-input" @input="loadItems" />
        </Teleport>
      </div>
    </div>

    <!-- Table -->
    <div class="sa-table-card">
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small">
        <el-table-column :label="$t('message.serviceAdmin.colServiceName')" min-width="180">
          <template #default="{ row }">
            <span style="margin-right:6px;">{{ row.icon || '📋' }}</span>
            <span style="font-weight:500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" :label="$t('message.serviceAdmin.colCategory')" width="120" />
        <el-table-column :label="$t('message.serviceAdmin.colWorkflow')" width="160">
          <template #default="{ row }">
            <span v-if="row.workflow_name" style="color:#409EFF;">{{ row.workflow_name }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.serviceAdmin.colMode')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.mode === 'flow' ? 'primary' : 'success'" size="small">
              {{ row.mode === 'flow' ? $t('message.serviceAdmin.flowMode') : $t('message.serviceAdmin.lightweightMode') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.serviceAdmin.colVisibleTo')" width="100">
          <template #default="{ row }">
            <span style="color:#909399;">{{ row.visible_to === 'all' ? $t('message.serviceAdmin.visibleAll') : row.visible_to }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colStatus')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? $t('message.serviceAdmin.enabled') : $t('message.serviceAdmin.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.serviceAdmin.colSortOrder')" width="60" prop="sort_order" />
        <el-table-column :label="$t('message.itsmPage.colActions')" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="onEdit(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button size="small" text @click="onPreview(row)">{{ $t('message.serviceAdmin.preview') }}</el-button>
            <el-button size="small" text type="danger" @click="onToggleActive(row)">
              {{ row.is_active ? $t('message.serviceAdmin.disabled') : $t('message.serviceAdmin.enabled') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Category Management Dialog -->
    <el-dialog v-model="showCatDialog" :title="$t('message.serviceAdmin.manageCategories')" width="540px" top="5vh" destroy-on-close append-to-body @closed="loadCategories">
      <div v-loading="catSaving" class="sa-cat-body">
        <div class="sa-cat-form-card">
          <div class="sa-cat-form-title">{{ catEditingId ? $t('message.serviceAdmin.catEditTitle') : $t('message.serviceAdmin.catNewTitle') }}</div>
          <div class="sa-cat-form-row">
            <el-input v-model="catForm.code" :placeholder="$t('message.serviceAdmin.catCode')" size="small" style="width:130px" />
            <el-input v-model="catForm.name" :placeholder="$t('message.serviceAdmin.catName')" size="small" style="width:160px" />
            <el-select v-model="catParent" clearable size="small" style="width:130px" :placeholder="$t('message.serviceAdmin.catParent')">
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-button v-if="catEditingId" size="small" @click="catEditingId = null; catForm = {name:'', code:''}; catParent = null">{{ $t('message.serviceAdmin.catCancel') }}</el-button>
            <el-button type="primary" size="small" @click="onSaveCat">{{ catEditingId ? $t('message.serviceAdmin.catSave') : $t('message.serviceAdmin.catAdd') }}</el-button>
          </div>
        </div>
        <div class="sa-cat-list-card">
          <div class="sa-cat-list-title">{{ $t('message.serviceAdmin.catList') }}</div>
          <div v-for="root in catTree" :key="root.id" class="sa-cat-group">
            <div class="sa-cat-row sa-cat-root">
              <el-icon :size="16" color="#E6A23C"><FolderOpened /></el-icon>
              <span class="sa-cat-name">{{ root.name }}</span>
              <el-tag size="small" type="info" style="margin-left:4px;">{{ root.code }}</el-tag>
              <div class="sa-cat-actions">
                <el-button size="small" text :icon="Edit" @click="onEditCat(root)" />
                <el-button size="small" text type="danger" :icon="Delete" @click="onDeleteCat(root)" />
              </div>
            </div>
            <div v-for="child in root.children" :key="child.id" class="sa-cat-child-row">
              <div class="sa-cat-row">
                <span class="sa-cat-indent">└─</span>
                <el-icon :size="14" color="#409EFF"><FolderOpened /></el-icon>
                <span class="sa-cat-name">{{ child.name }}</span>
                <el-tag size="small" type="info" style="margin-left:4px;">{{ child.code }}</el-tag>
                <div class="sa-cat-actions">
                  <el-button size="small" text :icon="Edit" @click="onEditCat(child)" />
                  <el-button size="small" text type="danger" :icon="Delete" @click="onDeleteCat(child)" />
                </div>
              </div>
            </div>
          </div>
          <div v-if="!catTree.length" class="sa-cat-empty">{{ $t('message.common.empty') }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- Edit Dialog -->
    <el-dialog v-model="showDialog" :title="editingId ? $t('message.serviceAdmin.editService') : $t('message.serviceAdmin.newService')" width="600px" top="5vh" destroy-on-close append-to-body>
      <el-form label-position="top" size="small" v-loading="saving">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('message.serviceAdmin.formName')" required>
              <el-input v-model="form.name" :placeholder="$t('message.serviceAdmin.formNamePlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('message.serviceAdmin.formCategory')">
              <el-select v-model="form.category" clearable filterable style="width:100%" :placeholder="$t('message.serviceAdmin.formCategoryPlaceholder')">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="$t('message.serviceAdmin.formDescription')">
          <el-input v-model="form.description" type="textarea" :rows="2" :placeholder="$t('message.serviceAdmin.formDescriptionPlaceholder')" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item :label="$t('message.serviceAdmin.formIcon')">
              <div class="sa-icon-input-row">
                <span class="sa-icon-preview">{{ form.icon || '📋' }}</span>
                <el-popover placement="bottom-start" :width="360" trigger="click">
                  <template #reference>
                    <el-button size="small">{{ $t('message.serviceAdmin.chooseIcon') }}</el-button>
                  </template>
                  <div class="sa-emoji-picker">
                    <span v-for="emoji in emojiList" :key="emoji" class="sa-emoji-opt"
                      :class="{ active: form.icon === emoji }" @click="form.icon = emoji">{{ emoji }}</span>
                  </div>
                </el-popover>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('message.serviceAdmin.formMode')">
              <el-select v-model="form.mode" style="width:100%">
                <el-option :label="$t('message.serviceAdmin.flowMode')" value="flow" />
                <el-option :label="$t('message.serviceAdmin.lightweightMode')" value="lightweight" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('message.serviceAdmin.formDuration')">
              <el-input v-model="form.expected_duration" :placeholder="$t('message.serviceAdmin.formDurationPlaceholder')" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.mode === 'flow'" :label="$t('message.serviceAdmin.formWorkflow')">
          <el-select v-model="form.workflow" clearable filterable style="width:100%" :placeholder="$t('message.serviceAdmin.formWorkflowPlaceholder')">
            <el-option v-for="wf in workflows" :key="wf.id" :label="wf.name" :value="wf.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.serviceAdmin.formVisibleTo')">
          <el-radio-group v-model="form.visible_to">
            <el-radio value="all">{{ $t('message.serviceAdmin.visibleAllLabel') }}</el-radio>
            <el-radio value="role">{{ $t('message.serviceAdmin.visibleRoleLabel') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('message.serviceAdmin.formActiveStatus')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ $t('message.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog v-model="showPreview" :title="$t('message.serviceAdmin.previewTitle')" width="520px" top="8vh" destroy-on-close append-to-body>
      <div v-if="previewItem" class="sa-preview">
        <div class="sa-preview-header">
          <span class="sa-preview-icon">{{ previewItem.icon || '📋' }}</span>
          <div class="sa-preview-info">
            <div class="sa-preview-name">{{ previewItem.name }}</div>
            <div class="sa-preview-meta">
              <span v-if="previewItem.category_name" class="sa-preview-tag">{{ previewItem.category_name }}</span>
              <el-tag :type="previewItem.mode === 'flow' ? 'primary' : 'success'" size="small">
                {{ previewItem.mode === 'flow' ? $t('message.serviceAdmin.flowMode') : $t('message.serviceAdmin.lightweightMode') }}
              </el-tag>
              <span v-if="previewItem.expected_duration" class="sa-preview-duration">⏱ {{ previewItem.expected_duration }}</span>
            </div>
          </div>
        </div>
        <div v-if="previewItem.description" class="sa-preview-desc">{{ previewItem.description }}</div>
        <div v-if="previewItem.form_fields?.length" class="sa-preview-fields">
          <div class="sa-preview-section-title">{{ $t('message.serviceAdmin.previewForm') }}</div>
          <ItsmFormRenderer
            mode="preview"
            :fields="previewItem.form_fields"
            :show-submit="false"
          />
        </div>
        <div class="sa-preview-footer">
          <el-tag v-if="previewItem.workflow_name" type="info" size="small">
            {{ $t('message.serviceAdmin.previewBoundWorkflow', { name: previewItem.workflow_name }) }}
          </el-tag>
          <span v-if="previewItem.visible_to !== 'all'" style="font-size:11px;color:#909399;">
            {{ $t('message.serviceAdmin.previewVisibleTo', { scope: previewItem.visible_to }) }}
          </span>
          <span style="margin-left:auto;font-size:11px;color:#c0c4cc;">{{ $t('message.serviceAdmin.previewSortOrder', { order: previewItem.sort_order }) }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, FolderOpened, Edit, Delete } from '@element-plus/icons-vue'
import ItsmFormRenderer from '/@/components/ItsmFormRenderer/index.vue'
import { serviceItemApi, workflowApi, serviceCategoryApi } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { t } = useI18n()
const emojiList = ['📋','🖥️','🔧','🛡️','📡','💾','🗄️','🔑','📧','🌐','⚙️','📊','🔔','📁','🔄','💡','🗂️','📌','🏷️','📎','🔒','🔓','📞','📟','📠','📱','📲','💻','🖨️','🖱️','🖲️','💿','📀','🗜️','⚡','🔥','⭐','✅','❌','⚠️','ℹ️']

const { searchEl, reportStats: updateHeroStats } = useHeroConsumer()

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

// ===== Category Management =====
const showCatDialog = ref(false)
const catForm = ref({ name: '', code: '' })
const catEditingId = ref<number | null>(null)
const catParent = ref<any>(null)
const catSaving = ref(false)

const catTree = computed(() => {
  const roots = categories.value.filter((c: any) => !c.parent)
  return roots.map((r: any) => ({
    ...r,
    children: categories.value.filter((c: any) => c.parent === r.id),
  }))
})

function onManageCategories() {
  catForm.value = { name: '', code: '' }
  catEditingId.value = null
  catParent.value = null
  showCatDialog.value = true
}

async function onSaveCat() {
  if (!catForm.value.name.trim() || !catForm.value.code.trim()) {
    ElMessage.warning('请填写名称和编码')
    return
  }
  catSaving.value = true
  try {
    const payload: any = { name: catForm.value.name, code: catForm.value.code, parent: catParent.value || null }
    if (catEditingId.value) {
      await serviceCategoryApi.update(String(catEditingId.value), payload)
    } else {
      await serviceCategoryApi.create(payload)
    }
    ElMessage.success('保存成功')
    catForm.value = { name: '', code: '' }
    catEditingId.value = null
    catParent.value = null
    await loadCategories()
  } catch (e: any) { ElMessage.error(e?.msg || '保存失败') }
  catSaving.value = false
}

function onEditCat(cat: any) {
  catForm.value = { name: cat.name, code: cat.code }
  catEditingId.value = cat.id
  catParent.value = cat.parent || null
}

async function onDeleteCat(cat: any) {
  try { await ElMessageBox.confirm(`确定删除分类「${cat.name}」吗？`, '删除确认', { type: 'warning' }) }
  catch { return }
  try {
    await serviceCategoryApi.delete(String(cat.id))
    ElMessage.success('已删除')
    await loadCategories()
  } catch { ElMessage.error('删除失败') }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '服务总数' },
    { value: items.value.filter((it: any) => it.is_active).length, label: '已启用' },
    { value: items.value.filter((it: any) => !it.is_active).length, label: '已禁用' },
  ])
}

onMounted(async () => {
  await Promise.all([loadItems(), loadCategories(), loadWorkflows()])
  if (props.active) reportStats()
})

// Re-report stats when this tab becomes active
watch(() => props.active, (isActive) => {
  if (isActive && items.value.length > 0) reportStats()
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
.sa-icon-input-row { display: flex; align-items: center; gap: 10px; }
.sa-icon-input-row .sa-icon-preview { font-size: 24px; min-width: 36px; text-align: center; }
.sa-emoji-picker { display: flex; flex-wrap: wrap; gap: 6px; max-height: 300px; overflow-y: auto; }
.sa-emoji-opt { font-size: 22px; cursor: pointer; padding: 6px 8px; border-radius: 6px; border: 1px solid transparent; transition: all 0.15s; }
.sa-emoji-opt:hover { background: #ecf5ff; border-color: #409EFF; }
.sa-emoji-opt.active { background: #409EFF; }
.sa-preview-name { font-size: 16px; font-weight: 600; color: #303133; }
.sa-preview-meta { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.sa-preview-tag { font-size: 11px; color: #909399; }
.sa-preview-duration { font-size: 11px; color: #c0c4cc; }
.sa-preview-desc { font-size: 13px; color: #606266; line-height: 1.6; padding: 10px 0; border-top: 1px solid #f5f6fa; margin-bottom: 10px; }
.sa-preview-section-title { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.sa-preview-fields { border-top: 1px solid #f0f0f0; padding-top: 12px; }
.sa-preview-field { margin-bottom: 10px; }
.sa-preview-field-label { font-size: 12px; color: #606266; margin-bottom: 4px; }
.sa-preview-input {
  padding: 6px 10px; border: 1px solid #e8e8e8; border-radius: 6px;
  font-size: 12px; color: #c0c4cc; background: #fafafa; min-height: 28px;
}
.sa-preview-textarea { min-height: 50px; }
.sa-preview-footer {
  display: flex; align-items: center; gap: 8px; margin-top: 16px;
  padding-top: 10px; border-top: 1px solid #f0f0f0;
}

/* ===== Category Management ===== */
.sa-cat-body { min-height: 260px; }
.sa-cat-form-card {
  background: #f7f8fa;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 14px;
}
.sa-cat-form-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}
.sa-cat-form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sa-cat-list-card {
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  overflow: hidden;
}
.sa-cat-list-title {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  padding: 8px 14px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}
.sa-cat-group {
  padding: 0;
  &:not(:last-child) { border-bottom: 1px solid #f5f6fa; }
}
.sa-cat-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  transition: background 0.1s;
  &:hover { background: #f0f5ff; }
}
.sa-cat-root {
  background: #fafbfc;
  font-weight: 500;
}
.sa-cat-child-row {
  padding-left: 24px;
  .sa-cat-row:hover { background: #f5f7fa; }
}
.sa-cat-name { color: #303133; }
.sa-cat-indent { color: #c0c4cc; font-size: 12px; width: 20px; flex-shrink: 0; }
.sa-cat-actions { margin-left: auto; flex-shrink: 0; display: flex; gap: 2px; }
.sa-cat-empty { text-align: center; padding: 24px; color: #C0C4CC; font-size: 13px; }
</style>
