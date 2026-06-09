<template>
  <div class="cmdb-page">
    <!-- ===== Hero Section ===== -->
    <div class="cmdb-hero">
      <div class="cmdb-hero-bg" />
      <div class="cmdb-hero-inner">
        <div class="cmdb-hero-left">
          <h1 class="cmdb-hero-title">CMDB</h1>
          <p class="cmdb-hero-subtitle">配置管理数据库 — 模型驱动的资产与拓扑管理</p>
        </div>
        <div class="cmdb-hero-center">
          <el-input v-model="store.searchQuery" placeholder="全局搜索 IP/主机名/模型..." clearable size="default"
            class="cmdb-search-input" @keyup.enter="doGlobalSearch" @clear="store.clearSearch()">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>
      <!-- Tabs -->
      <div class="cmdb-hero-tabs">
        <div class="cmdb-hero-tab" :class="{ active: store.activeView === 'schema' }"
          @click="store.setActiveView('schema')">
          <el-icon><Grid /></el-icon> 模型管理
        </div>
        <div class="cmdb-hero-tab" :class="{ active: store.activeView === 'instance' }"
          @click="store.setActiveView('instance')">
          <el-icon><Folder /></el-icon> 实例管理
        </div>
        <div class="cmdb-hero-tab" :class="{ active: store.activeView === 'topology' }"
          @click="store.setActiveView('topology')">
          <el-icon><Connection /></el-icon> 拓扑视图
        </div>
        <div class="cmdb-hero-tab" :class="{ active: store.activeView === 'sync' }"
          @click="store.setActiveView('sync')">
          <el-icon><Upload /></el-icon> 数据同步
        </div>
        <div class="cmdb-hero-tab" :class="{ active: store.activeView === 'events' }"
          @click="store.setActiveView('events')">
          <el-icon><Bell /></el-icon> 事件订阅
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="cmdb-body">

      <!-- ─── Tab 1: 模型管理 ─── -->
      <div v-show="store.activeView === 'schema'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-schema-layout">
          <!-- Left: Model List -->
          <div class="cmdb-schema-sidebar">
            <div class="cmdb-table-card">
              <div class="cmdb-table-header">
                <span class="cmdb-table-title">模型列表</span>
                <el-button size="small" type="primary" @click="showAddModel = true">
                  <el-icon><Plus /></el-icon>
                </el-button>
              </div>
              <el-table :data="store.modelDefinitions" v-loading="store.loading" stripe size="small" style="width:100%"
                :row-class-name="({ row }) => row.code === store.selectedModelCode ? 'cmdb-row-active' : ''"
                highlight-current-row @row-click="selectModel">
                <el-table-column prop="code" label="编码" width="100" />
                <el-table-column prop="name" label="名称" min-width="120" />
                <el-table-column width="60" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.is_builtin" size="small" type="info">内</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <!-- Classification section -->
            <div class="cmdb-table-card" style="margin-top:12px;">
              <div class="cmdb-table-header">
                <span class="cmdb-table-title">分类</span>
                <el-button size="small" text @click="showAddClass = true"><el-icon><Plus /></el-icon></el-button>
              </div>
              <el-table :data="store.classifications" size="small" stripe style="width:100%">
                <el-table-column prop="cls_id" label="标识" width="140" />
                <el-table-column prop="name" label="名称" min-width="100" />
              </el-table>
            </div>
          </div>

          <!-- Right: Model Detail / Field Editor -->
          <div class="cmdb-schema-detail" v-if="selectedModel">
            <div class="cmdb-table-card">
              <div class="cmdb-table-header">
                <span class="cmdb-table-title">{{ selectedModel.name }} — 字段定义</span>
                <div style="display:flex;gap:8px;">
                  <el-button size="small" @click="showAssociations = !showAssociations">
                    <el-icon><Connection /></el-icon> 关联
                  </el-button>
                  <el-button size="small" @click="addField">
                    <el-icon><Plus /></el-icon> 添加字段
                  </el-button>
                </div>
              </div>
              <el-table :data="modelFieldsList" size="small" stripe style="width:100%">
                <el-table-column prop="name" label="字段名" width="120" />
                <el-table-column prop="label" label="显示名" width="120" />
                <el-table-column prop="field_type" label="类型" width="100">
                  <template #default="{ row }">
                    <el-tag size="small">{{ row.field_type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="required" label="必填" width="60" align="center">
                  <template #default="{ row }"><el-icon v-if="row.required" color="#F56C6C"><Star /></el-icon></template>
                </el-table-column>
                <el-table-column prop="is_unique" label="唯一" width="60" align="center">
                  <template #default="{ row }"><el-icon v-if="row.is_unique" color="#E6A23C"><Warning /></el-icon></template>
                </el-table-column>
                <el-table-column prop="sort_order" label="排序" width="60" />
                <el-table-column prop="options" label="选项" min-width="120" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.options?.join(', ') || '-' }}</template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button size="small" text type="danger" @click="deleteField(row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- Associations section -->
            <div v-if="showAssociations" class="cmdb-table-card" style="margin-top:12px;">
              <div class="cmdb-table-header">
                <span class="cmdb-table-title">模型关联</span>
              </div>
              <el-table :data="modelAssocs" size="small" stripe style="width:100%">
                <el-table-column prop="source_model_name" label="源模型" width="100" />
                <el-table-column label="关系" width="120" align="center">
                  <template #default="{ row }">
                    <el-tag size="small">-{{ row.association_type_name }}-></el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="target_model_name" label="目标模型" width="100" />
                <el-table-column prop="mapping" label="基数" width="80" />
                <el-table-column prop="on_delete" label="级联" width="80" />
              </el-table>
            </div>
          </div>
          <div class="cmdb-schema-detail" v-else>
            <div class="cmdb-empty-detail">
              <el-icon :size="48" color="#dcdfe6"><Grid /></el-icon>
              <p>请从左侧选择一个模型查看详情</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 2: 实例管理 ─── -->
      <div v-show="store.activeView === 'instance'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-instance-layout">
          <div class="cmdb-instance-sidebar">
            <div class="cmdb-table-card">
              <div class="cmdb-table-header"><span class="cmdb-table-title">选择模型</span></div>
              <div class="cmdb-model-select">
                <div v-for="m in store.modelDefinitions" :key="m.code"
                  class="cmdb-model-item" :class="{ active: store.selectedModelCode === m.code }"
                  @click="store.selectedModelCode = m.code">
                  <span class="cmdb-model-item-name">{{ m.name }}</span>
                  <span class="cmdb-model-item-code">{{ m.code }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="cmdb-instance-content">
            <DynamicTable v-if="store.selectedModelCode && selectedModel"
              :key="store.selectedModelCode"
              :modelDef="selectedModel"
              :fields="modelFieldsList"
              :showDetailBtn="true"
              @detail="onInstanceDetail" />
            <div v-else class="cmdb-empty-detail">
              <el-icon :size="48" color="#dcdfe6"><Folder /></el-icon>
              <p>请从左侧选择一个模型</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 3: 拓扑视图 ─── -->
      <div v-show="store.activeView === 'topology'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-topo-card">
          <div class="cmdb-topo-toolbar">
            <div class="cmdb-topo-toolbar-left">
              <span class="cmdb-table-title">拓扑视图</span>
              <el-select v-model="topoBizFilter" size="small" placeholder="选择业务" style="width:200px;margin-left:12px;"
                @change="loadTopoTree" clearable>
                <el-option v-for="b in bizInstances" :key="b.instance_id" :label="b.name" :value="b.instance_id" />
              </el-select>
            </div>
            <div style="display:flex;gap:8px;">
              <el-button size="small" @click="loadGlobalTopo">
                <el-icon><Connection /></el-icon> 全局拓扑
              </el-button>
              <el-button size="small" type="primary" @click="showImpactDialog = true" :disabled="!topoClickedNode">
                <el-icon><Warning /></el-icon> 影响分析
              </el-button>
            </div>
          </div>
          <div class="cmdb-topo-body">
            <div v-if="store.topologyLoading" class="cmdb-topo-empty">
              <el-icon :size="48" color="#409EFF" class="is-loading"><Loading /></el-icon>
              <p>加载拓扑数据...</p>
            </div>
            <TopologyCanvas v-else-if="store.topology.nodes?.length"
              :nodes="store.topology.nodes" :edges="store.topology.edges"
              @node-click="onTopoNodeClick" />
            <div v-else class="cmdb-topo-empty">
              <el-icon :size="48" color="#dcdfe6"><Connection /></el-icon>
              <p>暂无拓扑数据</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 4: 数据同步 ─── -->
      <div v-show="store.activeView === 'sync'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-sync-grid">
          <div class="cmdb-table-card">
            <div class="cmdb-table-header">
              <span class="cmdb-table-title">批量导入</span>
            </div>
            <div style="padding:20px;">
              <el-upload drag accept=".csv,.json" :auto-upload="false" :on-change="onFileChange" style="margin-bottom:16px;">
                <el-icon :size="40" color="#409EFF"><Upload /></el-icon>
                <div style="margin-top:8px;">拖拽或点击上传 CSV/JSON 文件</div>
              </el-upload>
              <el-select v-model="importModelCode" placeholder="选择目标模型" style="width:100%;margin-bottom:12px;" size="small">
                <el-option v-for="m in store.modelDefinitions" :key="m.code" :label="m.name" :value="m.code" />
              </el-select>
              <el-button type="primary" size="small" :disabled="!importFile || !importModelCode"
                @click="doImport">开始导入</el-button>
            </div>
          </div>
          <div class="cmdb-table-card">
            <div class="cmdb-table-header">
              <span class="cmdb-table-title">云资产同步</span>
            </div>
            <div style="padding:20px;color:#909399;text-align:center;">
              <el-icon :size="40" color="#dcdfe6"><Cloudy /></el-icon>
              <p style="margin-top:8px;">云同步功能待集成中心就绪</p>
              <el-tag size="small" type="warning">TODO</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Tab 5: 事件订阅 ─── -->
      <div v-show="store.activeView === 'events'" class="cmdb-section of-fade-in-up">
        <div class="cmdb-table-card">
          <div class="cmdb-table-header">
            <span class="cmdb-table-title">事件订阅管理</span>
            <el-button size="small" type="primary" @click="showAddSubscription = true">
              <el-icon><Plus /></el-icon> 新建订阅
            </el-button>
          </div>
          <el-table :data="subscriptions" v-loading="subLoading" size="small" stripe style="width:100%"
            empty-text="暂无事件订阅">
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column prop="model_code" label="模型编码" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.model_code || '*' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="event_type" label="事件类型" width="140">
              <template #default="{ row }">
                <el-tag size="small" type="warning">{{ row.event_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="endpoint" label="回调地址" min-width="200" show-overflow-tooltip />
            <el-table-column prop="is_active" label="启用" width="70" align="center">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" size="small" @change="toggleSubscription(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="140" show-overflow-tooltip />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-popconfirm title="确认删除?" @confirm="deleteSubscription(row)">
                  <template #reference>
                    <el-button size="small" text type="danger">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- ── Add Model Dialog ── -->
    <el-dialog v-model="showAddModel" title="新增模型" width="500px" destroy-on-close>
      <el-form :model="newModel" label-width="100" size="small">
        <el-form-item label="编码" required>
          <el-input v-model="newModel.code" placeholder="如 Router, Firewall" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="newModel.name" placeholder="如 路由器, 防火墙" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="newModel.classification" placeholder="选择分类" style="width:100%;">
            <el-option v-for="c in store.classifications" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newModel.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddModel = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doAddModel">创建</el-button>
      </template>
    </el-dialog>

    <!-- ── Add Classification Dialog ── -->
    <el-dialog v-model="showAddClass" title="新增分类" width="400px" destroy-on-close>
      <el-form :model="newClass" label-width="80" size="small">
        <el-form-item label="标识" required>
          <el-input v-model="newClass.cls_id" placeholder="如 bk_network" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="newClass.name" placeholder="如 网络设备" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddClass = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doAddClass">创建</el-button>
      </template>
    </el-dialog>

    <!-- ── Add Field Dialog ── -->
    <el-dialog v-model="showAddField" title="添加字段" width="500px" destroy-on-close>
      <el-form :model="newField" label-width="100" size="small">
        <el-form-item label="字段名" required>
          <el-input v-model="newField.name" placeholder="如 brand, model_name" />
        </el-form-item>
        <el-form-item label="显示名" required>
          <el-input v-model="newField.label" placeholder="如 品牌, 型号" />
        </el-form-item>
        <el-form-item label="字段类型">
          <el-select v-model="newField.field_type" style="width:100%;">
            <el-option v-for="t in fieldTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="必填">
          <el-switch v-model="newField.required" />
        </el-form-item>
        <el-form-item label="唯一">
          <el-switch v-model="newField.is_unique" />
        </el-form-item>
        <el-form-item label="枚举选项" v-if="newField.field_type === 'enum'">
          <el-input v-model="newField.optionsText" type="textarea" :rows="2"
            placeholder="每行一个选项" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddField = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doAddField">添加</el-button>
      </template>
    </el-dialog>

    <!-- ── Impact Dialog ── -->
    <el-dialog v-model="showImpactDialog" title="影响分析" width="700px" destroy-on-close>
      <div v-if="impactLoading" style="text-align:center;padding:40px;">
        <el-icon :size="36" color="#409EFF" class="is-loading"><Loading /></el-icon>
        <p>分析中...</p>
      </div>
      <div v-else-if="impactResult">
        <el-alert :title="'共 ' + impactResult.total + ' 个受影响节点'" type="warning" :closable="false" style="margin-bottom:16px;" />
        <el-table :data="impactResult.impacted || []" size="small" stripe style="width:100%">
          <el-table-column prop="model_code" label="类型" width="100" />
          <el-table-column prop="label" label="名称" min-width="160" />
          <el-table-column prop="depth" label="影响深度" width="100" align="center" />
        </el-table>
      </div>
    </el-dialog>

    <!-- ── Instance Detail Dialog ── -->
    <el-dialog v-model="showInstanceDetail" title="实例详情" width="600px" destroy-on-close>
      <el-descriptions v-if="detailInstance" :column="2" border size="small">
        <el-descriptions-item v-for="(val, key) in detailInstance" :key="key" :label="key">
          {{ typeof val === 'object' ? JSON.stringify(val) : val }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- ── Event Subscription Dialog ── -->
    <el-dialog v-model="showAddSubscription" title="新建事件订阅" width="550px" destroy-on-close>
      <el-form :model="subForm" label-width="100" size="small">
        <el-form-item label="名称" required>
          <el-input v-model="subForm.name" placeholder="如 通知工单系统" />
        </el-form-item>
        <el-form-item label="模型编码">
          <el-select v-model="subForm.model_code" placeholder="留空=所有模型" style="width:100%;" clearable>
            <el-option v-for="m in store.modelDefinitions" :key="m.code" :label="m.name + ' (' + m.code + ')'" :value="m.code" />
          </el-select>
          <div style="font-size:11px;color:#909399;margin-top:4px;">留空表示订阅所有模型的事件</div>
        </el-form-item>
        <el-form-item label="事件类型" required>
          <el-select v-model="subForm.event_type" style="width:100%;">
            <el-option label="实例创建" value="instance.create" />
            <el-option label="实例更新" value="instance.update" />
            <el-option label="实例删除" value="instance.delete" />
          </el-select>
        </el-form-item>
        <el-form-item label="回调地址" required>
          <el-input v-model="subForm.endpoint" placeholder="https://example.com/webhook/cmdb" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="subForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSubscription = false">取消</el-button>
        <el-button type="primary" :loading="subSaving" @click="doCreateSubscription">创建</el-button>
      </template>
    </el-dialog>
  </div>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Search, Monitor, Loading, Plus, Edit, Delete, Upload, Bell,
  Folder, Connection, Grid, Warning, Star, View, Cloudy,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useCmdbStore } from './stores/cmdbStore'
import TopologyCanvas from './components/TopologyCanvas.vue'
import DynamicTable from './components/DynamicTable.vue'
import {
  getInstances, createInstance, globalSearch,
  modelDefinitionsApi, modelFieldsApi, classificationsApi,
  getTopology, getTopologyTree, getImpact,
  eventSubscriptionsApi,
} from '/@/api/cmdb/index'

const store = useCmdbStore()

// ─── Schema Tab ───
const showAddModel = ref(false)
const showAddClass = ref(false)
const showAddField = ref(false)
const showAssociations = ref(false)
const saving = ref(false)

const newModel = ref({ code: '', name: '', classification: null, description: '' })
const newClass = ref({ cls_id: '', name: '' })
const newField = ref({ name: '', label: '', field_type: 'string', required: false, is_unique: false, optionsText: '' })

const fieldTypes = [
  { label: '字符串', value: 'string' }, { label: '整数', value: 'integer' },
  { label: '浮点数', value: 'float' }, { label: '布尔', value: 'boolean' },
  { label: '枚举', value: 'enum' }, { label: '日期', value: 'date' },
  { label: 'IP 地址', value: 'ip' }, { label: 'JSON', value: 'json' },
]

const selectedModel = computed(() =>
  store.modelDefinitions.find((m: any) => m.code === store.selectedModelCode) || null
)

const modelFieldsList = computed(() =>
  store.modelFields.filter((f: any) => f.model_definition === selectedModel.value?.id)
)

const modelAssocs = computed(() =>
  store.modelAssociations.filter(
    (a: any) => a.source_model === selectedModel.value?.id || a.target_model === selectedModel.value?.id
  )
)

function selectModel(row: any) {
  store.selectedModelCode = row.code
}

async function doAddModel() {
  saving.value = true
  try {
    await modelDefinitionsApi.create(newModel.value)
    ElMessage.success('模型创建成功')
    showAddModel.value = false
    await store.fetchModelDefinitions()
    newModel.value = { code: '', name: '', classification: null, description: '' }
  } catch (e: any) {
    ElMessage.error(e?.msg || '创建失败')
  } finally {
    saving.value = false
  }
}

async function doAddClass() {
  saving.value = true
  try {
    await classificationsApi.create(newClass.value)
    ElMessage.success('分类创建成功')
    showAddClass.value = false
    await store.fetchClassifications()
    newClass.value = { cls_id: '', name: '' }
  } catch (e: any) {
    ElMessage.error(e?.msg || '创建失败')
  } finally {
    saving.value = false
  }
}

async function addField() {
  if (!selectedModel.value) return
  showAddField.value = true
}

async function doAddField() {
  if (!selectedModel.value) return
  saving.value = true
  try {
    const data: any = {
      model_definition: selectedModel.value.id,
      name: newField.value.name,
      label: newField.value.label,
      field_type: newField.value.field_type,
      required: newField.value.required,
      is_unique: newField.value.is_unique,
    }
    if (newField.value.field_type === 'enum' && newField.value.optionsText) {
      data.options = newField.value.optionsText.split('\n').map((s: string) => s.trim()).filter(Boolean)
    }
    await modelFieldsApi.create(data)
    ElMessage.success('字段添加成功')
    showAddField.value = false
    await store.fetchModelFields()
    newField.value = { name: '', label: '', field_type: 'string', required: false, is_unique: false, optionsText: '' }
  } catch (e: any) {
    ElMessage.error(e?.msg || '添加失败')
  } finally {
    saving.value = false
  }
}

async function deleteField(row: any) {
  try {
    await modelFieldsApi.delete(row.id)
    ElMessage.success('字段已删除')
    await store.fetchModelFields()
  } catch (e: any) {
    ElMessage.error('删除失败')
  }
}

// ─── Instance Tab ───
const showInstanceDetail = ref(false)
const detailInstance = ref<any>(null)

function onInstanceDetail(row: any) {
  detailInstance.value = row
  showInstanceDetail.value = true
}

// ─── Topology Tab ───
const topoBizFilter = ref('')
const topoClickedNode = ref<any>(null)
const showImpactDialog = ref(false)
const impactResult = ref<any>(null)
const impactLoading = ref(false)
const bizInstances = ref<any[]>([])

async function loadGlobalTopo() {
  topoBizFilter.value = ''
  topoClickedNode.value = null
  await store.fetchTopology()
}

async function loadTopoTree() {
  if (!topoBizFilter.value) {
    await store.fetchTopology()
    return
  }
  store.topologyLoading = true
  try {
    const res = await getTopologyTree(topoBizFilter.value)
    store.topology = res.data || { nodes: [], edges: [] }
  } finally {
    store.topologyLoading = false
  }
}

function onTopoNodeClick(node: any) {
  topoClickedNode.value = node
}

async function doImpactAnalysis() {
  if (!topoClickedNode.value) return
  impactLoading.value = true
  try {
    const res = await getImpact(topoClickedNode.value.instance_id, { direction: 'downstream' })
    impactResult.value = res.data || { impacted: [], total: 0 }
  } catch (e: any) {
    ElMessage.error('影响分析失败')
  } finally {
    impactLoading.value = false
  }
}

// ─── Sync Tab ───
const importFile = ref<File | null>(null)
const importModelCode = ref('')

function onFileChange(uploadFile: any) {
  importFile.value = uploadFile.raw || null
}

async function doImport() {
  if (!importFile.value || !importModelCode.value) {
    ElMessage.warning('请选择文件和目标模型')
    return
  }
  ElMessage.info('导入功能已就绪 — 后端 API 实现后即可使用')
}

// ─── Event Subscriptions ───
const subscriptions = ref<any[]>([])
const subLoading = ref(false)
const showAddSubscription = ref(false)
const subSaving = ref(false)
const subForm = ref({
  name: '',
  model_code: '',
  event_type: 'instance.update',
  endpoint: '',
  description: '',
})

async function fetchSubscriptions() {
  subLoading.value = true
  try {
    const res = await eventSubscriptionsApi.list()
    subscriptions.value = res.data || []
  } catch { /* ignore */ }
  finally { subLoading.value = false }
}

async function doCreateSubscription() {
  subSaving.value = true
  try {
    const data: any = { ...subForm.value }
    if (!data.model_code) data.model_code = '*'
    await eventSubscriptionsApi.create(data)
    ElMessage.success('订阅创建成功')
    showAddSubscription.value = false
    subForm.value = { name: '', model_code: '', event_type: 'instance.update', endpoint: '', description: '' }
    await fetchSubscriptions()
  } catch (e: any) {
    ElMessage.error(e?.msg || '创建失败')
  } finally { subSaving.value = false }
}

async function deleteSubscription(row: any) {
  try {
    await eventSubscriptionsApi.delete(row.id)
    ElMessage.success('订阅已删除')
    await fetchSubscriptions()
  } catch (e: any) {
    ElMessage.error('删除失败')
  }
}

async function toggleSubscription(row: any) {
  try {
    await eventSubscriptionsApi.update(row.id, { is_active: !row.is_active })
    row.is_active = !row.is_active
  } catch { /* ignore */ }
}

async function doGlobalSearch() {
  if (!store.searchQuery) return
  await store.doSearch(store.searchQuery)
  if (store.searchResults.length) {
    store.setActiveView('topology')
    store.topology = {
      nodes: store.searchResults.map((r: any) => ({
        instance_id: r.instance_id,
        label: r.label,
        model_code: r.model_code,
        _matched: true,
      })),
      edges: [],
    }
  }
}

// ─── Load Data ───
onMounted(async () => {
  store.loading = true
  await Promise.all([
    store.fetchClassifications(),
    store.fetchModelDefinitions(),
    store.fetchModelFields(),
    store.fetchAssociationTypes(),
    store.fetchModelAssociations(),
  ])
  store.loading = false

  // Load Biz instances for topology filter
  try {
    const res = await getInstances('Biz', { page_size: 100 })
    bizInstances.value = res.data?.items || res.data || []
  } catch { /* ignore */ }

  if (!store.topology.nodes?.length) {
    store.fetchTopology()
  }

  // Load event subscriptions
  fetchSubscriptions()
})
</script>

<style lang="scss" scoped>
@use '../../../styles/opsflow-global' as *;

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

.cmdb-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.cmdb-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
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

/* ===== Schema Layout ===== */
.cmdb-schema-layout { display: flex; gap: 16px; min-height: 500px; }
.cmdb-schema-sidebar { flex: 0 0 320px; }
.cmdb-schema-detail { flex: 1; min-width: 0; }
.cmdb-empty-detail {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 400px; gap: 16px; color: #909399;
}
.cmdb-row-active { background: #e6f7ff !important; }

/* ===== Instance Layout ===== */
.cmdb-instance-layout { display: flex; gap: 16px; min-height: 500px; }
.cmdb-instance-sidebar { flex: 0 0 240px; }
.cmdb-instance-content { flex: 1; min-width: 0; }
.cmdb-model-select { padding: 8px; }
.cmdb-model-item {
  padding: 10px 12px; cursor: pointer; border-radius: 8px; margin-bottom: 4px;
  transition: all 0.2s; display: flex; justify-content: space-between; align-items: center;
}
.cmdb-model-item:hover { background: #f5f7fa; }
.cmdb-model-item.active { background: #e6f7ff; color: #409EFF; font-weight: 500; }
.cmdb-model-item-code { font-size: 11px; color: #909399; font-family: monospace; }

/* ===== Topology ===== */
.cmdb-topo-card {
  background: #fff; border-radius: 14px; box-shadow: $of-shadow-card; overflow: hidden;
}
.cmdb-topo-toolbar {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px;
  border-bottom: 1px solid $of-border-light;
}
.cmdb-topo-toolbar-left { display: flex; align-items: center; }
.cmdb-topo-body { min-height: 560px; position: relative; }
.cmdb-topo-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 500px; gap: 16px; color: #909399;
}
.cmdb-topo-empty .is-loading { animation: rotating 1.5s linear infinite; }
@keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ===== Sync ===== */
.cmdb-sync-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
</style>
