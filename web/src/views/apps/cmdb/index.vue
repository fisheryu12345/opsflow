<template>
  <div class="cmdb-page">
    <!-- Top navigation tabs -->
    <div class="of-card" style="margin-bottom:16px;">
      <el-tabs v-model="activeView" class="of-tabs" style="padding:0 24px;">
        <el-tab-pane label="业务管理" name="biz" />
        <el-tab-pane label="主机管理" name="host" />
        <el-tab-pane label="拓扑视图" name="topology" />
        <el-tab-pane label="模型管理" name="model" />
      </el-tabs>
    </div>

    <!-- Biz View -->
    <div v-show="activeView === 'biz'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">业务树</h3>
        <el-button type="primary" @click="showAddBiz = true">+ 新增业务</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="bizList" v-loading="loading" row-key="biz_id" stripe>
          <el-table-column prop="name" label="业务名称" min-width="180" />
          <el-table-column prop="lifecycle" label="生命周期" width="120" />
          <el-table-column prop="operator" label="负责人" width="140" />
          <el-table-column prop="description" label="描述" min-width="200" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="showTopology(row.biz_id)">拓扑</el-button>
              <el-button size="small" link @click="editBiz(row)">编辑</el-button>
              <el-popconfirm title="确认删除?" @confirm="deleteBiz(row.biz_id)">
                <template #reference><el-button size="small" type="danger" link>删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Host View -->
    <div v-show="activeView === 'host'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">主机列表</h3>
        <el-button type="primary" @click="showImportHost = true">批量导入</el-button>
      </div>
      <div class="of-card-body">
        <el-table :data="hostList" v-loading="loading" stripe>
          <el-table-column prop="ip" label="IP" width="150" />
          <el-table-column prop="hostname" label="主机名" width="160" />
          <el-table-column prop="os_type" label="系统" width="100" />
          <el-table-column prop="cpu_cores" label="CPU" width="80" />
          <el-table-column prop="memory_mb" label="内存(MB)" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'normal' ? 'success' : row.status === 'alarm' ? 'danger' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <el-button size="small" type="primary" link @click="showHostGraph(row)">关联图</el-button>
          </el-table-column>
        </el-table>
        <div style="margin-top:12px;">
          <el-input v-model="hostSearch" placeholder="搜索 IP / 主机名" style="width:280px;" @keyup.enter="loadHosts" />
        </div>
      </div>
    </div>

    <!-- Topology View -->
    <div v-show="activeView === 'topology'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">拓扑视图</h3>
        <div>
          <el-input v-model="searchQuery" placeholder="搜索 CMDB 节点..." style="width:260px;margin-right:8px;" @keyup.enter="doSearch" />
          <el-button @click="doSearch">搜索</el-button>
        </div>
      </div>
      <div class="of-card-body" style="min-height:500px;text-align:center;padding:60px;">
        <p style="color:#8b949e;">拓扑图需集成 D3.js / vis-network 可视化库</p>
        <p style="color:#8b949e;font-size:13px;">选择业务后点击「拓扑」按钮查看</p>
      </div>
    </div>

    <!-- Model Management -->
    <div v-show="activeView === 'model'" class="of-card">
      <div class="of-card-header">
        <h3 class="of-card-title">模型定义</h3>
      </div>
      <div class="of-card-body">
        <el-table :data="modelDefs" v-loading="loading" stripe>
          <el-table-column prop="name" label="模型名称" width="160" />
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="is_builtin" label="内置" width="80">
            <template #default="{ row }"><el-tag v-if="row.is_builtin" size="small">内置</el-tag></template>
          </el-table-column>
          <el-table-column label="字段数" width="80">
            <template #default="{ row }">{{ row.field_count || 0 }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { bizApi, hostApi, modelDefinitionApi, GetBizTopology, GetHostGraph, SearchNodes, BatchImportHosts } from '/@/api/cmdb/index'

const activeView = ref('biz')
const loading = ref(false)
const bizList = ref<any[]>([])
const hostList = ref<any[]>([])
const modelDefs = ref<any[]>([])
const hostSearch = ref('')
const searchQuery = ref('')
const showAddBiz = ref(false)
const showImportHost = ref(false)

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
  await loadBiz()
}

function showTopology(id: string) { activeView.value = 'topology' }
function editBiz(row: any) { /* TODO */ }
function showHostGraph(row: any) { /* TODO */ }
async function doSearch() {
  if (!searchQuery.value) return
  const res = await SearchNodes(searchQuery.value)
  // TODO: show results in topology view
}

onMounted(() => { loadBiz(); loadHosts(); loadModels() })
</script>

<style scoped>
.cmdb-page { padding: 20px; }
.of-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.of-card-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; }
.of-card-title { font-size: 16px; font-weight: 600; margin: 0; }
.of-card-body { padding: 0 24px 24px; }
</style>
