<template>
  <div class="cmdb-page">
    <!-- ===== Hero Section ===== -->
    <div class="cmdb-hero">
      <div class="cmdb-hero-bg" />
      <div class="cmdb-hero-inner">
        <div class="cmdb-hero-left">
          <h1 class="cmdb-hero-title">CMDB</h1>
          <p class="cmdb-hero-subtitle">Configuration management database — 资产与拓扑管理</p>
        </div>
        <div class="cmdb-hero-center">
          <el-input v-model="searchQuery" placeholder="Search IP, hostname, model..." clearable size="default"
            class="cmdb-search-input" @keyup.enter="doSearch" @clear="clearSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="cmdb-hero-stats">
          <div class="cmdb-stat-item"><span class="cmdb-stat-value">{{ bizList.length }}</span><span class="cmdb-stat-label">Businesses</span></div>
          <div class="cmdb-stat-divider" />
          <div class="cmdb-stat-item"><span class="cmdb-stat-value">{{ hostList.length }}</span><span class="cmdb-stat-label">Hosts</span></div>
          <div class="cmdb-stat-divider" />
          <div class="cmdb-stat-item"><span class="cmdb-stat-value">{{ modelDefs.length }}</span><span class="cmdb-stat-label">Models</span></div>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="cmdb-hero-tabs">
        <div class="cmdb-hero-tab" :class="{ active: activeView === 'biz' }" @click="activeView = 'biz'">
          <el-icon><Folder /></el-icon> 业务管理
        </div>
        <div class="cmdb-hero-tab" :class="{ active: activeView === 'host' }" @click="activeView = 'host'">
          <el-icon><Monitor /></el-icon> 主机管理
        </div>
        <div class="cmdb-hero-tab" :class="{ active: activeView === 'topology' }" @click="activeView = 'topology'">
          <el-icon><Connection /></el-icon> 拓扑视图
        </div>
        <div class="cmdb-hero-tab" :class="{ active: activeView === 'model' }" @click="activeView = 'model'">
          <el-icon><Grid /></el-icon> 模型管理
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="cmdb-body">

      <!-- ── Biz View ── -->
      <div v-show="activeView === 'biz'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-table-card">
          <div class="cmdb-table-header">
            <span class="cmdb-table-title">业务树</span>
            <el-button type="primary" size="small" @click="showAddBiz = true">
              <el-icon><Plus /></el-icon> 新增业务
            </el-button>
          </div>
          <el-table :data="bizList" v-loading="loading" row-key="biz_id" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无业务数据'">
            <el-table-column prop="name" label="业务名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="lifecycle" label="生命周期" width="120" />
            <el-table-column prop="operator" label="负责人" width="140" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="showTopology(row.biz_id)">
                  <el-icon><Connection /></el-icon> 拓扑
                </el-button>
                <el-button size="small" text type="primary" @click="editBiz(row)">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                <el-popconfirm title="确认删除?" @confirm="deleteBiz(row.biz_id)">
                  <template #reference>
                    <el-button size="small" text type="danger">
                      <el-icon><Delete /></el-icon> 删除
                    </el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Host View ── -->
      <div v-show="activeView === 'host'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-table-card">
          <div class="cmdb-table-header">
            <span class="cmdb-table-title">主机列表</span>
            <div style="display:flex;gap:8px;align-items:center;">
              <el-input v-model="hostSearch" placeholder="搜索 IP / 主机名" style="width:240px;" size="small"
                clearable @keyup.enter="loadHosts" @clear="loadHosts" />
              <el-button type="primary" size="small" @click="showImportHost = true">
                <el-icon><Upload /></el-icon> 批量导入
              </el-button>
            </div>
          </div>
          <el-table :data="hostList" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无主机数据'">
            <el-table-column prop="ip" label="IP" width="150" />
            <el-table-column prop="hostname" label="主机名" width="160" show-overflow-tooltip />
            <el-table-column prop="os_type" label="系统" width="100" />
            <el-table-column prop="cpu_cores" label="CPU" width="80" />
            <el-table-column prop="memory_mb" label="内存(MB)" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="cmdb-status-badge" :class="'cmdb-status-' + (row.status || 'unknown')">
                  <span class="cmdb-status-dot" />{{ row.status === 'normal' ? '正常' : row.status === 'alarm' ? '告警' : row.status || '未知' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="showHostGraph(row)">
                  <el-icon><Connection /></el-icon> 关联图
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Topology View ── -->
      <div v-if="activeView === 'topology'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-topo-card">
          <div class="cmdb-topo-header">
            <div class="cmdb-topo-header-left">
              <span class="cmdb-table-title">拓扑视图</span>
              <el-select v-model="selectedBizId" size="small" placeholder="选择业务" style="width:200px;margin-left:12px;"
                @change="loadTopology" clearable>
                <el-option v-for="b in bizList" :key="b.biz_id" :label="b.name" :value="b.biz_id" />
              </el-select>
            </div>
            <div style="display:flex;gap:8px;">
              <el-button size="small" @click="doSearch">
                <el-icon><Search /></el-icon> 搜索
              </el-button>
              <el-button size="small" type="danger" v-if="searchResults.length" @click="clearSearch">
                清除结果
              </el-button>
            </div>
          </div>
          <div class="cmdb-topo-body">
            <!-- No biz selected -->
            <div v-if="!selectedBizId && !searchResults.length" class="cmdb-topo-empty">
              <el-icon :size="48" color="#dcdfe6"><Monitor /></el-icon>
              <p>请从左侧选择业务或搜索节点查看拓扑</p>
            </div>
            <!-- Loading -->
            <div v-else-if="topologyLoading" class="cmdb-topo-empty">
              <el-icon :size="48" color="#409EFF" class="is-loading"><Loading /></el-icon>
              <p>加载拓扑数据...</p>
            </div>
            <!-- Search results -->
            <div v-else-if="searchResults.length" class="cmdb-topo-results">
              <div class="cmdb-topo-info">
                找到 {{ searchResults.length }} 个匹配节点
              </div>
              <TopologyCanvas :nodes="searchNodes" :edges="searchEdges" ref="topologyRef" />
            </div>
            <!-- Topology canvas -->
            <TopologyCanvas v-else-if="topologyData.nodes?.length" :nodes="topologyData.nodes" :edges="topologyData.edges"
              ref="topologyRef" @node-click="onTopologyNodeClick" />
            <!-- Empty -->
            <div v-else class="cmdb-topo-empty">
              <el-empty description="该业务没有拓扑数据" :image-size="60" />
            </div>
          </div>
        </div>
      </div>

      <!-- ── Model Management ── -->
      <div v-show="activeView === 'model'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-table-card">
          <div class="cmdb-table-header">
            <span class="cmdb-table-title">模型定义</span>
          </div>
          <el-table :data="modelDefs" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无模型定义'">
            <el-table-column prop="name" label="模型名称" width="160" show-overflow-tooltip />
            <el-table-column prop="code" label="编码" width="140" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="is_builtin" label="内置" width="80" align="center">
              <template #default="{ row }"><el-tag v-if="row.is_builtin" size="small" type="info">内置</el-tag></template>
            </el-table-column>
            <el-table-column label="字段数" width="80" align="center">
              <template #default="{ row }">{{ row.field_count || 0 }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- ── Host Graph Dialog ── -->
    <el-dialog v-model="showHostGraphDialog" :title="hostGraphTitle" fullscreen
               :close-on-click-modal="false" destroy-on-close
               class="cmdb-hostgraph-dialog">
      <div v-if="hostGraphLoading" class="hostgraph-loading">
        <el-icon :size="36" color="#409EFF" class="is-loading"><Loading /></el-icon>
        <p>加载关联图数据...</p>
      </div>
      <div v-else-if="hostGraphError" class="hostgraph-error">
        <el-result icon="error" title="加载失败" :sub-title="hostGraphError">
          <template #extra>
            <el-button type="primary" @click="loadHostGraph">重试</el-button>
          </template>
        </el-result>
      </div>
      <TopologyCanvas v-else-if="hostGraphData.nodes?.length" :nodes="hostGraphData.nodes"
                      :edges="hostGraphData.edges" ref="hostGraphRef" />
      <el-empty v-else description="该主机暂无关联数据" :image-size="60" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { Search, Monitor, Loading, Plus, Edit, Delete, Upload, Folder, Connection, Grid } from '@element-plus/icons-vue'
import { bizApi, hostApi, modelDefinitionApi, GetBizTopology, GetHostGraph, SearchNodes, BatchImportHosts } from '/@/api/cmdb/index'
import TopologyCanvas from './components/TopologyCanvas.vue'
import { ElMessage } from 'element-plus'

const activeView = ref('biz')
const loading = ref(false)
const bizList = ref<any[]>([])
const hostList = ref<any[]>([])
const modelDefs = ref<any[]>([])
const hostSearch = ref('')
const searchQuery = ref('')
const showAddBiz = ref(false)
const showImportHost = ref(false)

// ── Topology ──
const selectedBizId = ref<string | null>(null)
const topologyData = ref<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })
const topologyLoading = ref(false)
const searchResults = ref<any[]>([])
const searchNodes = ref<any[]>([])
const searchEdges = ref<any[]>([])
const topologyRef = ref<InstanceType<typeof TopologyCanvas> | null>(null)

async function loadBiz() {
  const res = await bizApi.list()
  bizList.value = res.data || []
}

async function loadHosts() {
  const res = await hostApi.list({ search: hostSearch.value || undefined })
  hostList.value = res.data || []
}

async function loadModels() {
  const res = await modelDefinitionApi.list()
  modelDefs.value = res.data || []
}

async function deleteBiz(id: string) {
  await bizApi.delete(id)
  ElMessage.success('已删除')
  await loadBiz()
}

function showTopology(id: string) {
  selectedBizId.value = id
  activeView.value = 'topology'
  nextTick(() => loadTopology())
}

// ── Host Graph Dialog ──
const showHostGraphDialog = ref(false)
const hostGraphLoading = ref(false)
const hostGraphData = ref<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })
const hostGraphError = ref('')
const hostGraphTitle = ref('')
const currentHost = ref<any>(null)
const hostGraphRef = ref<InstanceType<typeof TopologyCanvas> | null>(null)

function showHostGraph(row: any) {
  currentHost.value = row
  hostGraphTitle.value = `关联图 — ${row.hostname || row.ip} (${row.ip || ''})`
  hostGraphData.value = { nodes: [], edges: [] }
  hostGraphError.value = ''
  showHostGraphDialog.value = true
  nextTick(() => loadHostGraph())
}

async function loadHostGraph() {
  if (!currentHost.value) return
  hostGraphLoading.value = true
  hostGraphError.value = ''
  try {
    const params: any = {}
    if (currentHost.value.ip) params.ip = currentHost.value.ip
    else if (currentHost.value.hostname) params.hostname = currentHost.value.hostname
    if (!params.ip && !params.hostname) {
      hostGraphError.value = '主机缺少 IP 和主机名'
      return
    }
    const res = await GetHostGraph(params)
    hostGraphData.value = res.data?.data || res.data || { nodes: [], edges: [] }
    if (!hostGraphData.value.nodes?.length) {
      hostGraphError.value = '该主机在 CMDB 中无关联数据'
    }
  } catch (e: any) {
    hostGraphError.value = e?.msg || e?.message || '获取关联图失败'
    hostGraphData.value = { nodes: [], edges: [] }
  } finally {
    hostGraphLoading.value = false
  }
}

function editBiz(row: any) { /* TODO */ }

async function loadTopology() {
  if (!selectedBizId.value) {
    topologyData.value = { nodes: [], edges: [] }
    return
  }
  topologyLoading.value = true
  try {
    const res = await GetBizTopology(selectedBizId.value)
    topologyData.value = res.data?.data || res.data || { nodes: [], edges: [] }
  } catch (e: any) {
    topologyData.value = { nodes: [], edges: [] }
    console.error('Failed to load topology:', e)
  } finally {
    topologyLoading.value = false
  }
}

async function doSearch() {
  if (!searchQuery.value) return
  searchResults.value = []
  topologyLoading.value = true
  try {
    const res = await SearchNodes(searchQuery.value)
    const results = res.data || res.data?.data || []
    searchResults.value = results
    if (results.length) {
      const nodeIds = new Set(results.map((r: any) => r.id))
      searchNodes.value = results.map((r: any) => ({ ...r, attrs: { ...(r.attrs || {}), _matched: true } }))
      if (selectedBizId.value && topologyData.value.edges) {
        searchEdges.value = topologyData.value.edges.filter((e: any) => nodeIds.has(e.from) && nodeIds.has(e.to))
      } else {
        searchEdges.value = []
      }
    } else {
      searchNodes.value = []; searchEdges.value = []
    }
  } catch (e: any) {
    console.error('Search failed:', e)
  } finally {
    topologyLoading.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchNodes.value = []
  searchEdges.value = []
}

function onTopologyNodeClick(node: any) {
  console.log('Node clicked:', node)
}

watch(activeView, (v) => {
  if (v === 'topology' && selectedBizId.value && !topologyData.value.nodes?.length) {
    loadTopology()
  }
})

onMounted(async () => {
  await Promise.all([loadBiz(), loadHosts(), loadModels()])

  const key = 'opsflow_tour_cmdb'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🗃️ CMDB — 配置管理数据库，管理业务、主机、拓扑视图和模型定义', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '../opsflow/styles/opsflow-global' as *;

.cmdb-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.cmdb-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.cmdb-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.cmdb-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.cmdb-hero-left { flex: 0 0 auto; }
.cmdb-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.cmdb-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.cmdb-hero-center { flex: 1 1 auto; min-width: 0; max-width: 360px; }
.cmdb-search-input { width: 100%; }
.cmdb-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none; border-radius: 10px; padding: 2px 12px;
}
.cmdb-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.cmdb-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.cmdb-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.cmdb-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.cmdb-stat-item { text-align: center; padding: 0 14px; }
.cmdb-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.cmdb-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.cmdb-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.cmdb-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.cmdb-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.cmdb-hero-tab:hover { color: rgba(255,255,255,0.9); }
.cmdb-hero-tab.active { color: #fff; border-bottom-color: #409EFF; }

/* ===== Body ===== */
.cmdb-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.cmdb-section { padding-top: 16px; }

/* ===== Table Card ===== */
.cmdb-table-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.cmdb-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.cmdb-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.cmdb-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.cmdb-table-title { font-size: 15px; font-weight: 600; color: $of-text-primary; }

/* ===== Status Badge ===== */
.cmdb-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.cmdb-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.cmdb-status-normal .cmdb-status-dot { background: #67C23A; }
.cmdb-status-normal { background: #f0f9eb; color: #67C23A; }
.cmdb-status-alarm .cmdb-status-dot { background: #F56C6C; }
.cmdb-status-alarm { background: #fef0f0; color: #F56C6C; }
.cmdb-status-unknown .cmdb-status-dot { background: #c0c4cc; }
.cmdb-status-unknown { background: #f5f7fa; color: #909399; }

/* ===== Topology ===== */
.cmdb-topo-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.cmdb-topo-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px;
  border-bottom: 1px solid $of-border-light;
}
.cmdb-topo-header-left { display: flex; align-items: center; }
.cmdb-topo-body { min-height: 560px; position: relative; }
.cmdb-topo-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 500px; gap: 16px; color: #909399;
}
.cmdb-topo-empty .is-loading { animation: rotating 1.5s linear infinite; }
@keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.cmdb-topo-results { height: 560px; }
.cmdb-topo-info {
  padding: 8px 20px; font-size: 13px; color: #909399;
  background: #f5f7fa; border-bottom: 1px solid $of-border-light;
}

/* ── Host Graph Dialog ── */
.cmdb-hostgraph-dialog :deep(.el-dialog__body) {
  padding: 0;
  height: calc(100vh - 110px);
  position: relative;
}
.hostgraph-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 500px; gap: 16px; color: #909399;
}
.hostgraph-loading .is-loading { animation: rotating 1.5s linear infinite; }
.hostgraph-error {
  display: flex; align-items: center; justify-content: center;
  height: 500px;
}
</style>
