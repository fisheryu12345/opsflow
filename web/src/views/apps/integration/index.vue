<template>
  <div class="int-page">
    <!-- ===== Hero Section ===== -->
    <div class="int-hero">
      <div class="int-hero-bg" />
      <div class="int-hero-inner">
        <div class="int-hero-left">
          <h1 class="int-hero-title">集成中心</h1>
          <p class="int-hero-subtitle">统一管理所有外部系统的连接器、凭证和调用审计</p>
        </div>
        <div class="int-hero-center">
          <el-input v-model="searchQuery" placeholder="Search connector or instance..." clearable size="default"
            class="int-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="int-hero-stats">
          <div class="int-stat-item"><span class="int-stat-value">{{ definitions.length }}</span><span class="int-stat-label">Definitions</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ onlineCount }}</span><span class="int-stat-label">Online</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ credentials.length }}</span><span class="int-stat-label">Credentials</span></div>
          <div class="int-stat-divider" />
          <div class="int-stat-item"><span class="int-stat-value">{{ callLogs.length }}</span><span class="int-stat-label">Recent Calls</span></div>
        </div>
      </div>
      <!-- Hero bottom tabs -->
      <div class="int-hero-tabs">
        <div class="int-hero-tab" :class="{ active: activeTab === 'instances' }" @click="activeTab = 'instances'">
          <el-icon><Connection /></el-icon> 连接器实例
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'definitions' }" @click="activeTab = 'definitions'">
          <el-icon><List /></el-icon> 连接器定义
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'credentials' }" @click="activeTab = 'credentials'">
          <el-icon><Key /></el-icon> 凭证管理
        </div>
        <div class="int-hero-tab" :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
          <el-icon><Document /></el-icon> 调用日志
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="int-body">

      <!-- ── Tab: 连接器定义 ── -->
      <div v-show="activeTab === 'definitions'" class="int-section g-fade-in-up">
        <div class="int-filter-bar">
          <div class="int-filter-tabs">
            <div class="int-tab" :class="{ active: defCategoryFilter === 'all' }" @click="defCategoryFilter = 'all'">
              <span class="int-tab-dot" style="background:#409EFF" />All
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'ai' }" @click="defCategoryFilter = 'ai'">
              <span class="int-tab-dot" style="background:#E6A23C" />AI 服务
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'cloud' }" @click="defCategoryFilter = 'cloud'">
              <span class="int-tab-dot" style="background:#409EFF" />云厂商
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'notification' }" @click="defCategoryFilter = 'notification'">
              <span class="int-tab-dot" style="background:#67C23A" />通知通道
            </div>
            <div class="int-tab" :class="{ active: defCategoryFilter === 'other' }" @click="defCategoryFilter = 'other'">
              <span class="int-tab-dot" style="background:#909399" />其他
            </div>
          </div>
          <div class="int-filter-actions">
            <el-button :icon="Refresh" @click="loadData" :loading="loading" text size="small">刷新</el-button>
          </div>
        </div>

        <div class="int-def-grid" v-if="filteredDefinitions.length">
          <div v-for="(def, idx) in filteredDefinitions" :key="def.id"
               class="int-def-card g-stagger-item"
               :style="{ animationDelay: `${idx * 0.04}s` }"
               :class="{ 'int-def-card-ai': def.category === 'ai' }">
            <div class="int-def-card-inner">
              <div class="int-def-card-header">
                <span class="int-def-icon" :class="'int-def-icon-' + (def.category || 'other')">
                  <el-icon><component :is="defIcon(def.category)" /></el-icon>
                </span>
                <el-tag :type="def.category === 'ai' ? 'warning' : ''" size="small" effect="dark" class="int-cat-tag">
                  {{ categoryLabel(def.category) }}
                </el-tag>
              </div>
              <div class="int-def-name">{{ def.name }}</div>
              <div class="int-def-code"><code>{{ def.code }}</code></div>
              <div class="int-def-desc" v-if="def.description">{{ def.description }}</div>
              <div class="int-def-footer">
                <el-tag size="small" type="info" effect="plain">v{{ def.version }}</el-tag>
                <el-button size="small" text @click="createInstance(def)">
                  <el-icon><Plus /></el-icon> 添加实例
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else description="没有找到匹配的连接器" :image-size="60" />
      </div>

      <!-- ── Tab: 连接器实例 ── -->
      <div v-show="activeTab === 'instances'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">连接器实例</span>
            <el-button type="primary" size="small" @click="showAddInstance = true">
              <el-icon><Plus /></el-icon> 添加实例
            </el-button>
          </div>
          <el-table :data="instances" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无连接器实例'">
            <el-table-column prop="name" label="实例名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="definition.name" label="连接器类型" min-width="140">
              <template #default="{ row }">
                <span>{{ row.definition?.name || row.definition_name || '-' }}</span>
                <el-tag v-if="row.definition?.category === 'ai' || row.definition_category === 'ai'"
                        size="small" type="warning" effect="dark" style="margin-left:6px">AI</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="definition.category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag :type="tagType(row.definition?.category || row.definition_category)" size="small" effect="plain">
                  {{ categoryLabel(row.definition?.category || row.definition_category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <span class="int-status-badge" :class="'int-status-' + (row.status || 'unknown')">
                  <span class="int-status-dot" />{{ statusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="启用" width="80" align="center">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" @change="toggleInstance(row)" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="runHealthCheck(row)">
                  <el-icon><Finished /></el-icon> 检查
                </el-button>
                <el-button size="small" text @click="editInstance(row)">
                  <el-icon><Edit /></el-icon> 配置
                </el-button>
                <el-button v-if="row.definition?.category === 'ai' || row.definition_category === 'ai'"
                           size="small" text type="warning" @click="testAiChat(row)">
                  <el-icon><ChatDotSquare /></el-icon> 测试
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Tab: 凭证管理 ── -->
      <div v-show="activeTab === 'credentials'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">凭证管理</span>
          </div>
          <el-table :data="credentials" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无凭证'">
            <el-table-column prop="name" label="凭证名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="instance.name" label="所属实例" min-width="140" show-overflow-tooltip />
            <el-table-column prop="cred_type" label="类型" width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.cred_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="expire_at" label="过期时间" width="180">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.expire_at && isExpiring(row.expire_at) }">
                  {{ row.expire_at || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="warning" @click="showDecrypt(row)">
                  <el-icon><View /></el-icon> 查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Tab: 调用日志 ── -->
      <div v-show="activeTab === 'logs'" class="int-section g-fade-in-up">
        <div class="int-table-card">
          <div class="int-table-header">
            <span class="int-table-title">调用日志</span>
            <el-button :icon="Refresh" text size="small" @click="loadData" :loading="loading">刷新</el-button>
          </div>
          <el-table :data="callLogs" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无调用日志'">
            <el-table-column prop="instance" label="实例" min-width="140" show-overflow-tooltip />
            <el-table-column prop="action" label="操作" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="int-status-badge" :class="'int-status-' + row.status">
                  <span class="int-status-dot" />{{ row.status === 'success' ? '成功' : '失败' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="duration_ms" label="耗时(ms)" width="100">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.duration_ms > 3000 }">{{ row.duration_ms ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="create_datetime" label="时间" width="180" />
          </el-table>
        </div>
      </div>
    </div>

    <!-- ===== Add Instance Dialog ===== -->
    <el-dialog v-model="showAddInstance" title="添加连接器实例" width="520px" top="8vh"
      destroy-on-close class="int-dialog">
      <el-form label-width="100px" class="int-form">
        <el-form-item label="连接器类型">
          <el-select v-model="newInstance.definition_id" placeholder="选择连接器类型" style="width:100%">
            <el-option v-for="d in definitions" :key="d.id"
                       :label="`${d.name} (${d.code})`" :value="d.id">
              <span>{{ d.name }}</span>
              <el-tag v-if="d.category === 'ai'" size="small" type="warning" style="margin-left:8px">AI</el-tag>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="实例名称">
          <el-input v-model="newInstance.name" placeholder="如 生产环境 OpenAI" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddInstance = false">取消</el-button>
        <el-button type="primary" @click="onAddInstance" :loading="submitting">确认</el-button>
      </template>
    </el-dialog>

    <!-- ===== AI Chat Test Dialog ===== -->
    <el-dialog v-model="showChatTest" title="AI 对话测试" width="560px" top="8vh"
      destroy-on-close class="int-dialog">
      <div class="int-chat-area">
        <el-input v-model="chatPrompt" type="textarea" :rows="3"
          placeholder="输入测试消息，例如: 你好，请用中文回复" />
      </div>
      <div v-if="chatResponse" class="int-chat-response g-fade-in-up">
        <div class="int-chat-response-header">响应结果：</div>
        <pre class="int-chat-response-body">{{ chatResponse }}</pre>
      </div>
      <template #footer>
        <el-button @click="showChatTest = false">关闭</el-button>
        <el-button type="warning" :loading="chatTesting" @click="onTestChat">
          <el-icon><Promotion /></el-icon> 发送测试
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { connectorDefinitionApi, connectorInstanceApi, credentialApi, callLogApi, HealthCheck, ToggleInstance, DecryptCredential } from '/@/api/integration/index'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'
import { Search, Refresh, Plus, Connection, List, Key, Document, Edit, Finished, ChatDotSquare, View, Promotion } from '@element-plus/icons-vue'

const activeTab = ref('instances')
const defCategoryFilter = ref('all')
const searchQuery = ref('')

const loading = ref(false)
const submitting = ref(false)
const definitions = ref<any[]>([])
const instances = ref<any[]>([])
const credentials = ref<any[]>([])
const callLogs = ref<any[]>([])

const showAddInstance = ref(false)
const newInstance = ref({ definition_id: null, name: '' })

const showChatTest = ref(false)
const chatTesting = ref(false)
const chatPrompt = ref('你好，请用中文回复')
const chatResponse = ref('')
const chatInstanceId = ref<number | null>(null)

const categoryLabels: Record<string, string> = {
  cloud: '云厂商', notification: '通知通道', auth: '认证源',
  paas: 'PaaS', monitor: '监控系统', ai: 'AI 服务', other: '其他',
}
function categoryLabel(cat: string) { return categoryLabels[cat] || cat || '未知' }

function statusLabel(s: string) {
  const map: Record<string, string> = { online: '在线', offline: '离线', error: '异常', unknown: '未知', connected: '已连接', success: '成功', failed: '失败' }
  return map[s] || s || '未知'
}

function tagType(cat: string) {
  const map: Record<string, string> = { cloud: '', notification: 'success', ai: 'warning', monitor: 'danger', other: 'info' }
  return map[cat] || 'info'
}

const onlineCount = computed(() => instances.value.filter(i => i.status === 'online' || i.status === 'connected').length)

const filteredDefinitions = computed(() => {
  let items = definitions.value
  if (defCategoryFilter.value !== 'all') {
    items = items.filter(d => d.category === defCategoryFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(d => d.name.toLowerCase().includes(q) || d.code?.toLowerCase().includes(q))
  }
  return items
})

function defIcon(cat: string) {
  const map: Record<string, any> = { ai: ChatDotSquare, cloud: Connection, notification: Promotion, monitor: Finished, other: List }
  return map[cat] || List
}

function isExpiring(dateStr: string) {
  return new Date(dateStr).getTime() < Date.now() + 7 * 24 * 60 * 60 * 1000
}

function onSearch() {
  // Filtering is reactive via filteredDefinitions
}

async function loadData() {
  loading.value = true
  try {
    const [defRes, insRes, credRes, logRes] = await Promise.all([
      connectorDefinitionApi.list(),
      connectorInstanceApi.list(),
      credentialApi.list(),
      callLogApi.list({ limit: 50 }),
    ])
    definitions.value = defRes.data || []
    instances.value = insRes.data || []
    credentials.value = credRes.data || []
    callLogs.value = logRes.data || []
  } finally {
    loading.value = false
  }
}

async function runHealthCheck(row: any) {
  try {
    await HealthCheck(row.id)
    ElMessage.success('健康检查完成')
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || '健康检查失败')
  }
}

async function toggleInstance(row: any) {
  try {
    await ToggleInstance(row.id)
    ElMessage.success('操作成功')
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  }
}

async function showDecrypt(row: any) {
  try {
    const res = await DecryptCredential(row.id)
    ElMessage.info(`凭证值: ${res.data.decrypted_value}`)
  } catch (e: any) {
    ElMessage.error(e?.msg || '解密失败')
  }
}

function editInstance(row: any) {
  ElMessage.info('编辑功能开发中')
}

function createInstance(def: any) {
  newInstance.value = { definition_id: def.id, name: `${def.name} 实例` }
  showAddInstance.value = true
}

async function onAddInstance() {
  if (!newInstance.value.definition_id || !newInstance.value.name) {
    ElMessage.warning('请填写完整信息')
    return
  }
  submitting.value = true
  try {
    await connectorInstanceApi.create({
      definition: newInstance.value.definition_id,
      name: newInstance.value.name,
      config: {},
      is_active: true,
    })
    ElMessage.success('实例创建成功')
    showAddInstance.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || '创建失败')
  } finally {
    submitting.value = false
  }
}

function testAiChat(row: any) {
  chatInstanceId.value = row.id
  chatPrompt.value = '你好，请用中文回复'
  chatResponse.value = ''
  showChatTest.value = true
}

async function onTestChat() {
  if (!chatInstanceId.value || !chatPrompt.value) {
    ElMessage.warning('请输入测试消息')
    return
  }
  chatTesting.value = true
  chatResponse.value = ''
  try {
    const res = await request({
      url: `/api/integration/connector-instances/${chatInstanceId.value}/ai_chat/`,
      method: 'post',
      data: { prompt: chatPrompt.value },
    })
    chatResponse.value = res.data?.content || res.data?.message || JSON.stringify(res.data)
  } catch (e: any) {
    chatResponse.value = `调用失败: ${e?.msg || e?.message || '未知错误'}`
  } finally {
    chatTesting.value = false
  }
}

onMounted(async () => {
  await loadData()

  // Onboarding tour message
  const key = 'opsflow_tour_integration'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🔌 集成中心 — 统一管理外部系统连接器、凭证和调用审计，支持 AI 服务对话测试', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

// ===== Page Layout =====
.int-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: #f5f6fa;
  overflow: hidden;
}

// ===== Hero =====
.int-hero {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.int-hero-bg {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  background-image:
    radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px),
    radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.int-hero-inner {
  position: relative;
  z-index: 1;
  padding: 14px 24px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
}
.int-hero-left { flex: 0 0 auto; }
.int-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.int-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.int-hero-center { flex: 1 1 auto; min-width: 0; max-width: 360px; }
.int-search-input { width: 100%; }
.int-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: none;
  border-radius: 10px;
  padding: 2px 12px;
}
.int-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.int-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.int-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.int-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.int-stat-item { text-align: center; padding: 0 14px; }
.int-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.int-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.int-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

// ===== Hero Tabs =====
.int-hero-tabs {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 0;
  padding: 0 24px;
  margin-top: -4px;
}
.int-hero-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
  user-select: none;
  .el-icon { font-size: 16px; }
}
.int-hero-tab:hover { color: rgba(255,255,255,0.9); }
.int-hero-tab.active {
  color: #fff;
  border-bottom-color: #409EFF;
}

// ===== Body =====
.int-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 24px;
}
.int-section {
  padding-top: 16px;
}

// ===== Filter bar =====
.int-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 16px;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: #f5f6fa;
}
.int-filter-tabs { display: flex; gap: 4px; }
.int-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.int-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.int-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.int-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.int-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

// ===== Definition Grid =====
.int-def-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.int-def-card {
  border-radius: $g-radius-card;
  overflow: hidden;
  @include g-hover-lift;
}
.int-def-card-inner {
  background: #fff;
  border: 1px solid $g-border-default;
  border-radius: $g-radius-card;
  padding: 18px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.int-def-card-ai .int-def-card-inner {
  border-color: #e6a23c;
  background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%);
}
.int-def-card-ai .int-def-card-inner::before {
  content: 'AI';
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  font-weight: 700;
  background: #e6a23c;
  color: #fff;
  padding: 1px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}
.int-def-card-ai .int-def-card-inner { position: relative; }
.int-def-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.int-def-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;
}
.int-def-icon-ai { background: linear-gradient(135deg, #e6a23c, #f4c152); }
.int-def-icon-cloud { background: linear-gradient(135deg, #409EFF, #337ecc); }
.int-def-icon-notification { background: linear-gradient(135deg, #67C23A, #85ce61); }
.int-def-icon-monitor { background: linear-gradient(135deg, #F56C6C, #f78989); }
.int-def-icon-other { background: linear-gradient(135deg, #909399, #a6a9ad); }
.int-cat-tag { font-size: 11px; }
.int-def-name { font-weight: 600; font-size: 15px; color: $g-text-primary; margin-bottom: 4px; }
.int-def-code { margin-bottom: 6px; }
.int-def-code code { font-size: 12px; color: $g-text-muted; }
.int-def-desc { font-size: 12px; color: $g-text-secondary; margin-bottom: 10px; line-height: 1.5; flex: 1; }
.int-def-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid $g-border-light;
}

// ===== Table Card =====
.int-table-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
}
.int-table-card :deep(.el-table th.el-table__cell) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
  font-size: 12px;
}
.int-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.int-table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px 0;
}
.int-table-title {
  font-size: 15px;
  font-weight: 600;
  color: $g-text-primary;
}

// ===== Status Badges =====
.int-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 10px;
}
.int-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.int-status-online .int-status-dot { background: #67C23A; }
.int-status-online { background: #f0f9eb; color: #67C23A; }
.int-status-connected .int-status-dot { background: #67C23A; }
.int-status-connected { background: #f0f9eb; color: #67C23A; }
.int-status-offline .int-status-dot { background: #c0c4cc; }
.int-status-offline { background: #f5f7fa; color: #909399; }
.int-status-error .int-status-dot { background: #F56C6C; }
.int-status-error { background: #fef0f0; color: #F56C6C; }
.int-status-unknown .int-status-dot { background: #c0c4cc; }
.int-status-unknown { background: #f5f7fa; color: #909399; }
.int-status-success .int-status-dot { background: #67C23A; }
.int-status-success { background: #f0f9eb; color: #67C23A; }
.int-status-failed .int-status-dot { background: #F56C6C; }
.int-status-failed { background: #fef0f0; color: #F56C6C; }

// ===== Dialog =====
.int-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.int-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.int-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
.int-form .el-form-item:last-child { margin-bottom: 0; }

// ===== Chat =====
.int-chat-area { margin-bottom: 16px; }
.int-chat-response {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px;
  background: #f5f7fa;
}
.int-chat-response-header { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #606266; }
.int-chat-response-body {
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: $g-text-primary;
}

// ===== Utilities =====
.text-danger { color: #F56C6C; font-weight: 500; }
.text-warning { color: #E6A23C; font-weight: 500; }
</style>
