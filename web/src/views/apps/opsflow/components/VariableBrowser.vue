<template>
  <el-dialog v-model="visible" title="Variable Browser" width="560px" top="8vh" class="var-browser-dialog">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="Global Variables" name="global">
        <div v-if="globalVars.length === 0" class="tab-empty">
          <el-empty description="No global variables" :image-size="40" />
        </div>
        <div v-for="v in globalVars" :key="v.key" class="var-item">
          <div class="var-item-left">
            <div class="var-item-top">
              <code class="var-code">{{ v.key }}</code>
              <span class="var-desc">{{ v.description || v.type }}</span>
            </div>
            <div v-if="v.references && v.references.length" class="var-refs">
              <span class="var-ref-toggle" @click="v._refExpanded = !v._refExpanded">
                {{ v.references.length }} reference{{ v.references.length > 1 ? 's' : '' }}
                <el-icon :class="{ expanded: v._refExpanded }"><ArrowDown /></el-icon>
              </span>
              <div v-if="v._refExpanded" class="var-ref-detail">
                <div v-for="(ref, ri) in v.references.slice(0, 10)" :key="ri" class="var-ref-item">
                  <span class="ref-node">{{ ref.node_label }}</span>
                  <span class="ref-path">{{ ref.field_path }}</span>
                </div>
                <div v-if="v.references.length > 10" class="var-ref-more">
                  ... and {{ v.references.length - 10 }} more
                </div>
              </div>
            </div>
            <div v-else class="var-noref">No references</div>
          </div>
          <el-button size="small" type="primary" text @click="insert(v.key)">
            <el-icon><Link /></el-icon> Insert
          </el-button>
        </div>
      </el-tab-pane>
      <el-tab-pane label="Node Outputs" name="node">
        <div class="tab-search">
          <el-input v-model="nodeSearch" placeholder="Filter by node or key..." size="small" prefix-icon="Search" clearable />
        </div>
        <div v-if="filteredNodeOutputs.length === 0" class="tab-empty">
          <el-empty description="No node outputs available" :image-size="40" />
        </div>
        <div v-for="v in filteredNodeOutputs" :key="v.key" class="var-item">
          <div class="var-item-left">
            <code class="var-code">{{ v.key }}</code>
            <span class="var-node">{{ v.node_label }}</span>
          </div>
          <el-button size="small" type="primary" text @click="insert(v.key)">
            <el-icon><Link /></el-icon> Insert
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Link, Search, ArrowDown } from '@element-plus/icons-vue'
import { GetVariableBrowser } from '/@/api/opsflow/templates'

const props = defineProps<{
  modelValue: boolean
  templateId: number | null
}>()
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
const nodeSearch = ref('')

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

async function fetchData() {
  if (!props.templateId) return
  try {
    const res = await GetVariableBrowser(props.templateId)
    const data = res.data?.data || res.data || {}
    globalVars.value = data.global_variables || []
    nodeOutputs.value = data.node_outputs || []
  } catch { /* silent */ }
}

watch(() => props.templateId, fetchData)
watch(() => props.modelValue, (v) => { if (v) fetchData() })
</script>

<style scoped>
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
.var-refs { margin-top: 2px; }
.var-ref-toggle { font-size: 11px; color: #909399; cursor: pointer; display: inline-flex; align-items: center; gap: 2px; }
.var-ref-toggle:hover { color: #409EFF; }
.var-ref-toggle .el-icon { font-size: 10px; transition: transform 0.2s; }
.var-ref-toggle .el-icon.expanded { transform: rotate(180deg); }
.var-ref-detail { margin-top: 4px; padding: 4px 8px; background: #f5f7fa; border-radius: 4px; }
.var-ref-item { font-size: 11px; color: #606266; display: flex; gap: 6px; padding: 2px 0; }
.var-ref-item .ref-node { color: #67C23A; font-weight: 500; }
.var-ref-item .ref-path { color: #909399; font-family: monospace; }
.var-ref-more { font-size: 10px; color: #C0C4CC; margin-top: 2px; }
</style>
