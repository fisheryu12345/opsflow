<template>
  <div class="gv-panel">
    <!-- Header -->
    <div class="gv-header">
      <div class="gv-header-top">
        <div class="gv-header-left">
          <div class="gv-header-icon">
            <el-icon :size="16" color="#fff"><Coin /></el-icon>
          </div>
          <span class="gv-header-title">Variables</span>
        </div>
        <div class="gv-header-actions">
          <el-tag size="small" effect="plain" type="primary" class="gv-count-tag">{{ filteredVars.length }}</el-tag>
          <el-button size="small" circle :icon="Plus" type="primary" @click="openAddDialog" class="gv-add-btn" />
        </div>
      </div>
      <div class="gv-search">
        <el-input v-model="searchQuery" placeholder="Search variables..." size="small" clearable class="gv-search-input">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <!-- List -->
    <div class="gv-list">
      <div v-for="v in filteredVars" :key="v.key" class="gv-item" :class="{ 'gv-item-unused': v.reference_count === 0 }" @click="selectVar(v)">
        <div class="gv-item-top">
          <div class="gv-item-key-row">
            <span class="gv-item-key">{{ v.key }}</span>
            <span class="gv-item-badge" :class="'badge-' + v.source_type">{{ sourceLabel(v.source_type) }}</span>
          </div>
          <div class="gv-item-ref" v-if="v.reference_count > 0">
            <el-icon size="11"><Link /></el-icon>
            <span>{{ v.reference_count }}</span>
          </div>
        </div>
        <div class="gv-item-value">{{ displayValue(v.value) }}</div>
        <div class="gv-item-desc" v-if="v.description">{{ v.description }}</div>
        <div class="gv-item-type-row" v-if="v.show_type !== false">
          <span class="gv-item-type-label">{{ v.type }}</span>
          <span v-if="v.reference_count === 0" class="gv-item-unused-label">unreferenced</span>
        </div>
      </div>
      <el-empty v-if="!filteredVars.length" :description="searchQuery ? 'No matching variables' : 'No variables yet'" :image-size="40" />
    </div>

    <!-- Drawer -->
    <el-drawer v-model="detailVisible" :title="editKey ? editKey : 'Add Variable'" size="420px" class="gv-drawer">
      <template #title>
        <div class="gv-drawer-title">
          <div class="gv-drawer-icon" :class="editKey ? 'icon-edit' : 'icon-add'">
            <el-icon :size="14" color="#fff">
              <Edit v-if="editKey" />
              <Plus v-else />
            </el-icon>
          </div>
          <span>{{ editKey ? editKey : 'New Variable' }}</span>
        </div>
      </template>
      <el-form label-position="top" size="small" class="gv-form">
        <el-form-item label="Key">
          <el-input v-model="editForm.key" placeholder="e.g. target_host" :disabled="!!editKey" />
        </el-form-item>
        <el-form-item label="Type">
          <el-select v-model="editForm.type" style="width:100%">
            <el-option label="Text" value="input" />
            <el-option label="Textarea" value="textarea" />
            <el-option label="Select" value="select" />
            <el-option label="Number" value="int" />
            <el-option label="Float" value="float" />
            <el-option label="Password" value="password" />
          </el-select>
        </el-form-item>
        <el-form-item label="Value">
          <el-input v-if="editForm.type === 'textarea'" v-model="editForm.value" type="textarea" :rows="4" />
          <el-input v-else v-model="editForm.value" />
        </el-form-item>
        <el-form-item label="Desc">
          <el-input v-model="editForm.description" type="textarea" :rows="2" placeholder="Optional description" />
        </el-form-item>
        <el-form-item v-if="editForm.source_info && editForm.source_type === 'node_output'" label="Source">
          <el-tag type="success" size="small" effect="light">
            <el-icon size="11" style="margin-right:3px"><Link /></el-icon>
            {{ editForm.source_info.node_id }}.{{ editForm.source_info.tag_code }}
          </el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="gv-drawer-footer">
          <div class="gv-footer-left">
            <el-button v-if="editKey" @click="onDelete" type="danger" plain size="small">
              <el-icon><Delete /></el-icon> Delete
            </el-button>
          </div>
          <div class="gv-footer-right">
            <el-button v-if="editForm.source_type === 'node_output'" @click="onUnhook" text size="small" class="gv-unhook-btn">
              <el-icon><Link /></el-icon> Unhook
            </el-button>
            <el-button @click="detailVisible = false" size="small">Cancel</el-button>
            <el-button type="primary" @click="onSave" size="small">Save</el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Coin, Delete, Link, Edit } from '@element-plus/icons-vue'
import { GetGlobalVariables, UpdateGlobalVariables, PatchGlobalVariables, UnhookVariable } from '../../api/templates'

const props = defineProps<{ templateId: number | null }>()
const emit = defineEmits<{ update: [] }>()

const searchQuery = ref('')
const variables = ref<Record<string, any>>({})
const detailVisible = ref(false)
const editKey = ref('')
const editForm = ref({ key: '', value: '', type: 'input', description: '', source_type: 'manual', source_info: null as any })

function sourceLabel(st: string) {
  return { manual: 'Manual', node_output: 'Output', hook: 'Hook' }[st] || st
}

const filteredVars = computed(() => {
  const entries = Object.entries(variables.value).map(([key, val]: [string, any]) => ({
    key, value: val?.value ?? '', type: val?.type ?? 'input',
    source_type: val?.source_type ?? 'manual', source_info: val?.source_info ?? null,
    description: val?.description ?? '', reference_count: val?.reference_count ?? 0,
    show_type: val?.show_type ?? true,
  }))
  if (!searchQuery.value) return entries
  const q = searchQuery.value.toLowerCase()
  return entries.filter(v => v.key.toLowerCase().includes(q) || v.description.toLowerCase().includes(q))
})

function displayValue(val: any): string {
  if (val === null || val === undefined) return '-'
  const s = String(val)
  return s.length > 50 ? s.slice(0, 50) + '...' : s
}

function selectVar(v: any) {
  editKey.value = v.key
  editForm.value = {
    key: v.key, value: typeof v.value === 'object' ? JSON.stringify(v.value) : String(v.value ?? ''),
    type: v.type || 'input', description: v.description || '',
    source_type: v.source_type || 'manual', source_info: v.source_info || null,
  }
  detailVisible.value = true
}

function openAddDialog() {
  editKey.value = ''
  editForm.value = { key: '', value: '', type: 'input', description: '', source_type: 'manual', source_info: null }
  detailVisible.value = true
}

async function fetchVars() {
  if (!props.templateId) return
  try {
    const res = await GetGlobalVariables(props.templateId)
    variables.value = res.data?.data || res.data || {}
  } catch { /* silent */ }
}

async function onSave() {
  if (!props.templateId || !editForm.value.key) return
  const key = editForm.value.key
  const entry: any = {
    value: editForm.value.value, type: editForm.value.type,
    description: editForm.value.description, source_type: editForm.value.source_type,
  }
  if (editForm.value.source_info) entry.source_info = editForm.value.source_info
  try {
    await PatchGlobalVariables(props.templateId, { global_vars: { [key]: entry } })
    ElMessage.success('Saved')
    detailVisible.value = false
    emit('update')
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Save failed')
  }
}

async function onDelete() {
  if (!props.templateId || !editKey.value) return
  try {
    await ElMessageBox.confirm('Delete variable ' + editKey.value + '?', 'Confirm', { type: 'warning' })
    const current = { ...variables.value }
    delete current[editKey.value]
    await UpdateGlobalVariables(props.templateId, { global_vars: current })
    ElMessage.success('Deleted')
    detailVisible.value = false
    emit('update')
  } catch { /* cancelled */ }
}

async function onUnhook() {
  if (!props.templateId || !editKey.value) return
  try {
    await UnhookVariable(props.templateId, { var_key: editKey.value })
    ElMessage.success('Unhooked')
    emit('update')
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Unhook failed')
  }
}

watch(() => props.templateId, fetchVars, { immediate: true })
</script>

<style lang="scss" scoped>
@use '../../styles/opsflow-global' as *;
/* ---------- Layout ---------- */
.gv-panel {
  width: 300px; min-width: 300px;
  border-left: 1px solid #e8ecf1;
  background: #fff;
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* ---------- Header ---------- */
.gv-header {
  padding: 12px 14px 10px;
  border-bottom: 1px solid #f0f2f5;
  display: flex; flex-direction: column; gap: 10px;
  flex-shrink: 0;
}
.gv-header-top {
  display: flex; justify-content: space-between; align-items: center;
}
.gv-header-left { display: flex; align-items: center; gap: 8px; }
.gv-header-icon {
  width: 28px; height: 28px; border-radius: 8px;
  background: $of-gradient-accent;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(102,126,234,0.3);
}
.gv-header-title { font-size: 14px; font-weight: 700; color: #1a1a2e; }
.gv-header-actions { display: flex; align-items: center; gap: 6px; }
.gv-count-tag { font-weight: 600; min-width: 22px; text-align: center; }
.gv-add-btn { width: 26px; height: 26px; }

.gv-search-input :deep(.el-input__wrapper) {
  background: #f5f6fa; border-radius: 8px; border: none;
  box-shadow: none; padding: 2px 10px;
}

/* ---------- List ---------- */
.gv-list {
  flex: 1; overflow-y: auto; padding: 4px 0;
}

/* ---------- Item ---------- */
.gv-item {
  padding: 10px 14px; cursor: pointer; transition: all 0.15s;
  border-bottom: 1px solid #f8f9fc;
}
.gv-item:hover { background: #f0f4ff; }
.gv-item:active { background: #e8edf8; }
.gv-item-unused { opacity: 0.55; }

.gv-item-top {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;
}
.gv-item-key-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.gv-item-key {
  font-size: 13px; font-weight: 700; color: #409EFF;
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
}
.gv-item-badge {
  display: inline-block; font-size: 10px; font-weight: 600; padding: 1px 6px;
  border-radius: 5px; text-transform: uppercase; letter-spacing: 0.3px;
  line-height: 1.4;
}
.badge-manual { background: #ecf5ff; color: #409EFF; }
.badge-node_output { background: #f0f9eb; color: #67C23A; }
.badge-hook { background: #fdf6ec; color: #E6A23C; }

.gv-item-ref {
  display: flex; align-items: center; gap: 3px;
  font-size: 11px; color: #909399; flex-shrink: 0;
}

.gv-item-value {
  font-size: 12px; color: #606266; margin-top: 3px;
  overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; font-family: monospace; font-size: 11px;
}

.gv-item-desc {
  font-size: 11px; color: #C0C4CC; margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.gv-item-type-row {
  display: flex; align-items: center; gap: 6px; margin-top: 4px;
}
.gv-item-type-label {
  font-size: 10px; color: #C0C4CC; text-transform: uppercase; letter-spacing: 0.3px;
}
.gv-item-unused-label {
  font-size: 10px; color: #f5222d; font-weight: 500;
}

/* ---------- Drawer ---------- */
.gv-drawer :deep(.el-drawer__header) { padding: 16px 20px 0; margin: 0; }
.gv-drawer-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: #1a1a2e; }
.gv-drawer-icon {
  width: 26px; height: 26px; border-radius: 7px; display: flex; align-items: center; justify-content: center;
}
.icon-edit { background: $of-gradient-accent; }
.icon-add { background: linear-gradient(135deg, #52c41a, #73d13d); }
.gv-form { padding: 0 20px; }
.gv-form :deep(.el-form-item__label) { font-weight: 600; color: #606266; padding-bottom: 2px; }
.gv-drawer-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 4px 12px;
}
.gv-footer-left { display: flex; align-items: center; }
.gv-footer-right { display: flex; align-items: center; gap: 8px; }
.gv-unhook-btn { color: #E6A23C; }
.gv-unhook-btn:hover { color: #cf9236; }
</style>
