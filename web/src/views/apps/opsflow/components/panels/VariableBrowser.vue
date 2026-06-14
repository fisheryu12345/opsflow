<template>
  <el-dialog v-model="visible" :title="t('message.opsflowPage.varBrowserTitle')" width="680px" top="8vh" :close-on-click-modal="true" class="var-browser-dialog">
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('message.opsflowPage.varBrowserTabGlobal')" name="global">
        <div class="global-tab-header">
          <span class="global-tab-count" v-if="globalVars.length">{{ globalVars.length }} {{ globalVars.length > 1 ? 'variables' : 'variable' }}</span>
          <el-button size="small" type="primary" :icon="Plus" @click="openAddDialog">{{ t('message.opsflowPage.varBrowserBtnAdd') }}</el-button>
        </div>
        <div v-if="globalVars.length === 0" class="tab-empty">
          <el-empty :description="t('message.opsflowPage.varBrowserEmptyGlobal')" :image-size="40" />
        </div>
        <div v-for="v in globalVars" :key="v.key" class="var-item" @click="selectVar(v)">
          <div class="var-item-left">
            <div class="var-item-top">
              <code class="var-code">{{ v.key }}</code>
              <span class="var-desc">{{ v.description || v.type }}</span>
            </div>
            <div v-if="v.reference_count > 0" class="var-refs">
              <el-icon size="11"><Link /></el-icon>
              <span>{{ v.reference_count }} {{ v.reference_count > 1 ? 'references' : 'reference' }}</span>
            </div>
            <div v-else class="var-noref">{{ t('message.opsflowPage.varBrowserNoRefs') }}</div>
          </div>
          <div class="var-item-actions" @click.stop>
            <el-button size="small" type="primary" text @click="insert(v.key)">
              <el-icon><Link /></el-icon> {{ t('message.opsflowPage.varBrowserBtnInsert') }}
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane :label="t('message.opsflowPage.varBrowserTabNode')" name="node">
        <div class="tab-search">
          <el-input v-model="nodeSearch" :placeholder="t('message.opsflowPage.varBrowserNodeFilter')" size="small" prefix-icon="Search" clearable />
        </div>
        <div v-if="filteredNodeOutputs.length === 0" class="tab-empty">
          <el-empty :description="t('message.opsflowPage.varBrowserEmptyNode')" :image-size="40" />
        </div>
        <div v-for="v in filteredNodeOutputs" :key="v.key" class="var-item">
          <div class="var-item-left">
            <code class="var-code">{{ v.key }}</code>
            <span class="var-node">{{ v.node_label }}</span>
          </div>
          <div class="var-item-actions">
            <el-button size="small" type="primary" text @click="insert(v.key)">
              <el-icon><Link /></el-icon> {{ t('message.opsflowPage.varBrowserBtnInsert') }}
            </el-button>
            <el-button v-if="templateId" size="small" type="success" text @click="promoteNodeOutput(v)">
              <el-icon><Upload /></el-icon> {{ t('message.opsflowPage.varBrowserBtnPromote') }}
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane :label="t('message.opsflowPage.varBrowserTabProject')" name="project">
        <div v-if="projectVars.length === 0" class="tab-empty">
          <el-empty :description="t('message.opsflowPage.varBrowserEmptyProject')" :image-size="40" />
        </div>
        <div v-for="v in projectVars" :key="v.key" class="var-item">
          <div class="var-item-left">
            <div class="var-item-top">
              <code class="var-code">{{ v.key }}</code>
              <span class="var-desc">{{ v.description || 'Project env var' }}</span>
            </div>
            <div class="var-noref">{{ t('message.opsflowPage.varBrowserDescProject') }}</div>
          </div>
          <el-button size="small" type="primary" text @click="insert(v.key)">
            <el-icon><Link /></el-icon> {{ t('message.opsflowPage.varBrowserBtnInsert') }}
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Edit/Create drawer -->
    <el-drawer v-model="detailVisible" size="420px" class="vb-drawer">
      <template #header>
        <div class="vb-drawer-title">
          <div class="vb-drawer-icon" :class="editKey ? 'icon-edit' : 'icon-add'">
            <el-icon :size="14" color="#fff">
              <Edit v-if="editKey" />
              <Plus v-else />
            </el-icon>
          </div>
          <span>{{ editKey ? editKey : t('message.opsflowPage.varBrowserDrawerTitleNew') }}</span>
        </div>
      </template>
      <el-form label-position="top" size="small" class="vb-form">
        <el-form-item :label="t('message.opsflowPage.varBrowserDrawerKey')">
          <el-input v-model="editForm.key" :placeholder="t('message.opsflowPage.varBrowserDrawerKeyPlaceholder')" :disabled="!!editKey" />
        </el-form-item>
        <el-form-item :label="t('message.opsflowPage.varBrowserDrawerType')">
          <el-select v-model="editForm.type" style="width:100%">
            <el-option label="Text" value="input" />
            <el-option label="Textarea" value="textarea" />
            <el-option label="Select" value="select" />
            <el-option label="Number" value="int" />
            <el-option label="Float" value="float" />
            <el-option label="Password" value="password" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('message.opsflowPage.varBrowserDrawerValue')">
          <el-input v-if="editForm.type === 'textarea'" v-model="editForm.value" type="textarea" :rows="4" />
          <el-input v-else v-model="editForm.value" />
        </el-form-item>
        <el-form-item :label="t('message.opsflowPage.varBrowserDrawerDesc')">
          <el-input v-model="editForm.description" type="textarea" :rows="2" :placeholder="t('message.opsflowPage.varBrowserDrawerDescPlaceholder')" />
        </el-form-item>
        <el-form-item v-if="editForm.source_info && editForm.source_type === 'node_output'" :label="t('message.opsflowPage.varBrowserDrawerSource')">
          <el-tag type="success" size="small" effect="light">
            <el-icon size="11" style="margin-right:3px"><Link /></el-icon>
            {{ editForm.source_info.node_id }}.{{ editForm.source_info.tag_code }}
          </el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="vb-drawer-footer">
          <div class="vb-footer-left">
            <el-button v-if="editKey" @click="onDelete" type="danger" plain>
              <el-icon><Delete /></el-icon> {{ t('message.opsflowPage.varBrowserDrawerDelete') }}
            </el-button>
          </div>
          <div class="vb-footer-right">
            <el-button v-if="editForm.source_type === 'node_output'" @click="onUnhook" text class="vb-unhook-btn">
              <el-icon><Link /></el-icon> {{ t('message.opsflowPage.varBrowserDrawerUnhook') }}
            </el-button>
            <el-button @click="detailVisible = false">{{ t('message.opsflowPage.varBrowserDrawerCancel') }}</el-button>
            <el-button type="primary" @click="onSave">{{ t('message.opsflowPage.varBrowserDrawerSave') }}</el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link, Search, Upload, Plus, Delete, Edit } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { GetVariableBrowser, GetGlobalVariables, HookVariable, PatchGlobalVariables, UpdateGlobalVariables, UnhookVariable } from '../../api/templates'
import { extractNodeOutputFields } from '../../composables/useGraphCanvas'

const { t } = useI18n()

const props = withDefaults(defineProps<{
  modelValue: boolean
  templateId: number | null
  /** 画布实时节点列表 — 传入后优先用于计算 node_outputs，避免 DB 未保存的延迟 */
  graphNodes?: { id: string; node_type: string; label: string; [key: string]: any }[]
  /** 全量节点列表（用于引用计数，需要扫描所有节点而非仅上游） */
  allGraphNodes?: { id: string; node_type: string; label: string; [key: string]: any }[]
}>(), {
  graphNodes: () => [],
  allGraphNodes: () => [],
})
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  insert: [key: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const activeTab = ref('global')
const globalVars = ref<any[]>([])
const nodeOutputs = ref<any[]>([])
const projectVars = ref<any[]>([])
const nodeSearch = ref('')

/* ── CRUD state ── */
const detailVisible = ref(false)
const editKey = ref('')
const editForm = ref({ key: '', value: '', type: 'input', description: '', source_type: 'manual', source_info: null as any })

const filteredNodeOutputs = computed(() => {
  if (!nodeSearch.value) return nodeOutputs.value
  const q = nodeSearch.value.toLowerCase()
  return nodeOutputs.value.filter(
    (v) => v.key.toLowerCase().includes(q) || (v.node_label || '').toLowerCase().includes(q)
  )
})

function insert(key: string) {
  emit('insert', key)
  visible.value = false
}

/* ── CRUD: select/add/save/delete/unhook ── */
function selectVar(v: any) {
  editKey.value = v.key
  editForm.value = {
    key: v.key,
    value: typeof v.value === 'object' ? JSON.stringify(v.value) : String(v.value ?? ''),
    type: v.type || 'input',
    description: v.description || '',
    source_type: v.source_type || 'manual',
    source_info: v.source_info || null,
  }
  detailVisible.value = true
}

function openAddDialog() {
  editKey.value = ''
  editForm.value = { key: '', value: '', type: 'input', description: '', source_type: 'manual', source_info: null }
  detailVisible.value = true
}

async function onSave() {
  if (!props.templateId || !editForm.value.key) return
  const key = editForm.value.key
  const entry: any = {
    value: editForm.value.value,
    type: editForm.value.type,
    description: editForm.value.description,
    source_type: editForm.value.source_type,
  }
  if (editForm.value.source_info) entry.source_info = editForm.value.source_info
  try {
    await PatchGlobalVariables(props.templateId, { global_vars: { [key]: entry } })
    ElMessage.success(t('message.opsflowPage.varBrowserSaved'))
    detailVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Save failed')
  }
}

async function onDelete() {
  if (!props.templateId || !editKey.value) return
  const keyToDelete = editKey.value

  // 检查引用：被引用的变量不能删除
  const target = globalVars.value.find((v: any) => v.key === keyToDelete)
  const refCount = target?.reference_count || 0
  if (refCount > 0) {
    await ElMessageBox.alert(
      t('message.opsflowPage.varBrowserRefDeleteBlock', { key: keyToDelete, count: refCount }),
      t('message.opsflowPage.varBrowserRefDeleteTitle'),
      { type: 'warning', confirmButtonText: 'OK' },
    )
    return
  }

  try {
    await ElMessageBox.confirm(
      t('message.opsflowPage.varBrowserConfirmDelete', { key: keyToDelete }),
      t('message.opsflowPage.varBrowserDrawerConfirmTitle'),
      { type: 'warning' },
    )
    // 从 GetGlobalVariables 获取完整结构化数据（含 source_type/source_info 等字段）
    const getResp = await GetGlobalVariables(props.templateId)
    const full: Record<string, any> = getResp.data?.data || getResp.data || {}
    delete full[keyToDelete]
    await UpdateGlobalVariables(props.templateId, { global_vars: full })
    ElMessage.success(t('message.opsflowPage.varBrowserDeleted'))
    detailVisible.value = false
    await fetchData()
  } catch { /* cancelled */ }
}

async function onUnhook() {
  if (!props.templateId || !editKey.value) return
  try {
    await UnhookVariable(props.templateId, { var_key: editKey.value })
    ElMessage.success(t('message.opsflowPage.varBrowserUnhooked'))
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Unhook failed')
  }
}

/** 将节点输出提升为全局变量 */
async function promoteNodeOutput(v: any) {
  const parts = (v.key || '').split('.')
  const nodeId = v.node_id || parts[0] || ''
  const fieldName = parts[1] || ''
  if (!nodeId || !fieldName) return

  const defaultVarName = fieldName
  try {
    const { value } = await ElMessageBox.prompt(
      'Enter a name for the global variable:',
      'Promote Node Output to Global',
      {
        inputValue: defaultVarName,
        inputPlaceholder: 'Variable name (used as ${name})',
        confirmButtonText: 'Promote',
        cancelButtonText: 'Cancel',
      },
    )
    if (!value || !value.trim()) return
    const varKey = value.trim()
    await HookVariable(props.templateId, {
      var_key: varKey,
      node_id: nodeId,
      tag_code: fieldName,
      var_type: 'output',
      description: v.description || fieldName,
    })
    ElMessage.success(`Global variable "${varKey}" created from ${v.key}`)
    await fetchData()
  } catch {
    // user cancelled
  }
}

/** 在对象中递归扫描 ${key} 的出现次数 */
function countRefsInValue(value: any, pattern: RegExp): number {
  if (typeof value === 'string') return (value.match(pattern) || []).length
  if (Array.isArray(value)) return value.reduce((s, v) => s + countRefsInValue(v, pattern), 0)
  if (value && typeof value === 'object') return Object.values(value).reduce((s, v) => s + countRefsInValue(v, pattern), 0)
  return 0
}

/** 从画布节点 params 中扫描 ${key} 引用次数 */
function computeFrontendRefCount(nodes: any[], varKey: string): number {
  const escaped = varKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`\\$\\{${escaped}}`, 'g')
  let count = 0
  for (const n of nodes) {
    const params = n.params || n.plugin_params || {}
    count += countRefsInValue(params, pattern)
  }
  return count
}

/** 从 graphNodes 提取节点输出字段 */
function computeNodeOutputs(nodes: any[]): any[] {
  const result: any[] = []
  for (const n of nodes) {
    if (n.node_type === 'end_event' || n.node_type === 'start_event') continue
    const nid = n.id || ''
    const label = n.label || nid
    for (const f of extractNodeOutputFields(n, n.node_type || '')) {
      result.push({ key: `${nid}.${f.key}`, node_id: nid, node_label: label, source: 'node_output', description: f.description || f.key })
    }
  }
  return result
}

async function fetchData() {
  if (!props.templateId) return
  try {
    // 如果传入了 graphNodes，优先在前端计算 node_outputs（实时，无需等待 DB 保存）
    if (props.graphNodes && props.graphNodes.length > 0) {
      nodeOutputs.value = computeNodeOutputs(props.graphNodes)
    } else {
      nodeOutputs.value = []
    }
    // 全局变量和项目变量仍需从 API 获取
    const res = await GetVariableBrowser(props.templateId)
    const data = res.data?.data || res.data || {}
    // 用前端实时图数据（全量节点，不依赖 DB 保存）覆盖 DB 引用数
    const allNodes = props.allGraphNodes?.length ? props.allGraphNodes : (props.graphNodes || [])
    globalVars.value = (data.global_variables || []).map((v: any) => ({
      ...v,
      reference_count: allNodes.length > 0
        ? computeFrontendRefCount(allNodes, v.key)
        : (v.reference_count || 0),
    }))
    projectVars.value = data.project_variables || []
  } catch { /* silent */ }
}

watch(() => props.templateId, fetchData)
watch(() => props.modelValue, (v) => { if (v) fetchData() })
</script>

<style scoped>
@use '/@/styles/global' as *;

.var-browser-dialog :deep(.el-dialog__body) { padding-top: 8px; }
.tab-empty { padding: 20px 0; }
.tab-search { margin-bottom: 8px; }
.var-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.var-item:hover { background: #ecf5ff; }
.var-item-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.var-item-top { display: flex; align-items: center; gap: 6px; }
.var-code { font-size: 13px; font-weight: 600; color: #409EFF; font-family: monospace; }
.var-desc { font-size: 11px; color: #909399; }
.var-node { font-size: 11px; color: #67C23A; }
.var-noref { font-size: 10px; color: #C0C4CC; margin-top: 1px; }
.var-item-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.var-refs { margin-top: 2px; display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: #909399; }

/* Global tab header with Add button */
.global-tab-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; gap: 8px;
}
.global-tab-count { font-size: 12px; color: #909399; }

/* CRUD Drawer */
.vb-drawer :deep(.el-drawer__header) { padding: 16px 20px 0; margin: 0; }
.vb-drawer-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: #1a1a2e; }
.vb-drawer-icon {
  width: 26px; height: 26px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
}
.vb-drawer-icon.icon-edit { background: linear-gradient(135deg, #667eea, #764ba2); }
.vb-drawer-icon.icon-add { background: linear-gradient(135deg, #52c41a, #73d13d); }
.vb-form { padding: 0 20px; }
.vb-form :deep(.el-form-item__label) { font-weight: 600; color: #606266; padding-bottom: 2px; }
.vb-drawer-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 4px 12px;
}
.vb-footer-left { display: flex; align-items: center; }
.vb-footer-right { display: flex; align-items: center; gap: 8px; }
.vb-unhook-btn { color: #E6A23C; }
.vb-unhook-btn:hover { color: #cf9236; }
</style>
