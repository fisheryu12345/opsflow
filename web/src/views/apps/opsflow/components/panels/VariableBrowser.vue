<template>
  <el-dialog v-model="visible" :title="t('message.opsflowPage.varBrowserTitle')" width="680px" top="8vh" :close-on-click-modal="true" class="var-browser-dialog">
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('message.opsflowPage.varBrowserTabGlobal')" name="global">
        <div class="global-tab-header">
          <span class="global-tab-count" v-if="globalVars.length">{{ globalVars.length }} {{ globalVars.length > 1 ? 'variables' : 'variable' }}</span>
        </div>
        <div v-if="globalVars.length === 0" class="tab-empty">
          <el-empty :description="t('message.opsflowPage.varBrowserEmptyGlobal')" :image-size="40" />
        </div>
        <div v-for="v in globalVars" :key="v.key">
          <div class="var-item" :class="{ expanded: expandedVar === v.key }" @click="expandedVar = expandedVar === v.key ? null : v.key">
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
              <el-button size="small" type="primary" text @click.stop="insert(v.key)">
                <el-icon><Link /></el-icon> {{ t('message.opsflowPage.varBrowserBtnInsert') }}
              </el-button>
              <el-button size="small" type="danger" text @click.stop="onDeleteVar(v)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <!-- Info card -->
          <div v-if="expandedVar === v.key" class="var-detail" @click.stop>
            <div class="detail-grid">
              <div class="detail-row"><span>Type</span><code>{{ v.type }}</code></div>
              <div class="detail-row"><span>Value</span><code>{{ v.value }}</code></div>
              <div class="detail-row"><span>Desc</span><span>{{ v.description || '-' }}</span></div>
              <div class="detail-row"><span>Source</span><span>{{ v.source_type || 'manual' }}</span></div>
              <div class="detail-row" v-if="v.source_info">
                <span>Source Info</span><code>{{ v.source_info.node_id }}.{{ v.source_info.tag_code }}</code>
              </div>
              <div class="detail-row" v-if="v.meta?.apiEndpoint">
                <span>API</span><code class="detail-mono">{{ v.meta.apiEndpoint }}</code>
              </div>
              <div class="detail-row" v-if="v.meta?.dependsOn">
                <span>Depends</span><code>{{ v.meta.dependsOn }}</code>
              </div>
              <div class="detail-row" v-if="v.meta?.options?.length">
                <span>Options</span><span>{{ v.meta.options.length }} items</span>
              </div>
            </div>
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
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link, Search, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { GetVariableBrowser, GetGlobalVariables, UpdateGlobalVariables } from '../../api/templates'
import { extractNodeOutputFields } from '../../composables/useGraphCanvas'

const { t } = useI18n()

const props = withDefaults(defineProps<{
  modelValue: boolean
  templateId: number | null
  graphNodes?: { id: string; node_type: string; label: string; [key: string]: any }[]
  allGraphNodes?: { id: string; node_type: string; label: string; [key: string]: any }[]
  /** 可选：外部提供的插入回调，优先于 clipboard */
  onFieldInsert?: ((key: string) => void) | null
}>(), {
  graphNodes: () => [],
  allGraphNodes: () => [],
  onFieldInsert: null,
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
const expandedVar = ref<string | null>(null)
const globalVars = ref<any[]>([])
const nodeOutputs = ref<any[]>([])
const projectVars = ref<any[]>([])
const nodeSearch = ref('')

const filteredNodeOutputs = computed(() => {
  if (!nodeSearch.value) return nodeOutputs.value
  const q = nodeSearch.value.toLowerCase()
  return nodeOutputs.value.filter(
    (v) => v.key.toLowerCase().includes(q) || (v.node_label || '').toLowerCase().includes(q)
  )
})

function insert(key: string) {
  const refStr = '${' + key + '}'
  if (props.onFieldInsert) {
    props.onFieldInsert(refStr)
  } else {
    navigator.clipboard.writeText(refStr)
    ElMessage.success(`Copied ${refStr} — paste into any field`)
  }
  visible.value = false
}

/** 删除全局变量（复用原有逻辑：检查引用 + 确认 + 删除） */
async function onDeleteVar(v: any) {
  if (!props.templateId) return
  const refCount = v.reference_count || 0
  if (refCount > 0) {
    await ElMessageBox.alert(
      t('message.opsflowPage.varBrowserRefDeleteBlock', { key: v.key, count: refCount }),
      t('message.opsflowPage.varBrowserRefDeleteTitle'),
      { type: 'warning', confirmButtonText: 'OK' },
    )
    return
  }
  try {
    await ElMessageBox.confirm(
      t('message.opsflowPage.varBrowserConfirmDelete', { key: v.key }),
      t('message.opsflowPage.varBrowserDrawerConfirmTitle'),
      { type: 'warning' },
    )
    const getResp = await GetGlobalVariables(props.templateId)
    const full: Record<string, any> = getResp.data?.data || getResp.data || {}
    delete full[v.key]
    await UpdateGlobalVariables(props.templateId, { global_vars: full })
    ElMessage.success(t('message.opsflowPage.varBrowserDeleted'))
    await fetchData()
  } catch { /* cancelled */ }
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

/* ── Info card ── */
.var-item.expanded {
  background: #ecf5ff;
  border-bottom-color: #d9ecff;
}
.var-detail {
  padding: 10px 16px 12px 28px;
  background: #f8faff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.detail-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
}
.detail-row span:first-child {
  color: #909399;
  min-width: 70px;
  flex-shrink: 0;
}
.detail-row code {
  font-family: monospace;
  font-size: 11px;
  color: #409EFF;
}
.detail-mono {
  font-size: 10px;
  word-break: break-all;
}
</style>
