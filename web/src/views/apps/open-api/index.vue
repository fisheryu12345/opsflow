<template>
  <div class="open-api-page">
    <!-- ===== Hero Section ===== -->
    <div class="openapi-hero">
      <div class="openapi-hero-bg" />
      <div class="openapi-hero-inner">
        <div class="openapi-hero-left">
          <h1 class="openapi-hero-title">Open API</h1>
          <p class="openapi-hero-subtitle">Manage third-party apps, access tokens & event subscriptions</p>
        </div>
        <div class="openapi-hero-stats">
          <div class="openapi-stat-item"><span class="openapi-stat-value">{{ apps.length }}</span><span class="openapi-stat-label">Apps</span></div>
          <div class="openapi-stat-divider" />
          <div class="openapi-stat-item"><span class="openapi-stat-value">{{ tokens.length }}</span><span class="openapi-stat-label">Tokens</span></div>
          <div class="openapi-stat-divider" />
          <div class="openapi-stat-item"><span class="openapi-stat-value">{{ callLogs.length }}</span><span class="openapi-stat-label">Recent Calls</span></div>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="openapi-hero-tabs">
        <div class="openapi-hero-tab" :class="{ active: activeTab === 'apps' }" @click="activeTab = 'apps'">
          <el-icon><Grid /></el-icon> 第三方应用
        </div>
        <div class="openapi-hero-tab" :class="{ active: activeTab === 'tokens' }" @click="activeTab = 'tokens'">
          <el-icon><Key /></el-icon> 访问凭证
        </div>
        <div class="openapi-hero-tab" :class="{ active: activeTab === 'webhooks' }" @click="activeTab = 'webhooks'">
          <el-icon><Link /></el-icon> 事件订阅
        </div>
        <div class="openapi-hero-tab" :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
          <el-icon><Document /></el-icon> 调用日志
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="openapi-body">

      <!-- ── Apps ── -->
      <div v-show="activeTab === 'apps'" class="openapi-section g-fade-in-up">
        <div class="openapi-table-card">
          <div class="openapi-table-header">
            <span class="openapi-table-title">第三方应用管理</span>
            <el-button type="primary" size="small" @click="showAddApp = true">
              <el-icon><Plus /></el-icon> 添加应用
            </el-button>
          </div>
          <el-table :data="apps" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无第三方应用'">
            <el-table-column prop="name" label="应用名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
            <el-table-column prop="contact_email" label="联系邮箱" min-width="180" show-overflow-tooltip />
            <el-table-column prop="rate_limit" label="QPS" width="80" align="center" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <span class="openapi-status-badge" :class="'openapi-status-' + row.status">
                  <span class="openapi-status-dot" />{{ row.status === 'active' ? '活跃' : '停用' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="editApp(row)">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Tokens ── -->
      <div v-show="activeTab === 'tokens'" class="openapi-section g-fade-in-up">
        <div class="openapi-table-card">
          <div class="openapi-table-header">
            <span class="openapi-table-title">访问凭证</span>
            <el-button type="primary" size="small" @click="showAddToken = true">
              <el-icon><Plus /></el-icon> 生成凭证
            </el-button>
          </div>
          <el-table :data="tokens" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无访问凭证'">
            <el-table-column prop="access_key" label="Access Key" width="160" />
            <el-table-column prop="app.name" label="所属应用" width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <span class="openapi-status-badge" :class="'openapi-status-' + row.status">
                  <span class="openapi-status-dot" />{{ row.status === 'active' ? '活跃' : '已吊销' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="expire_at" label="过期时间" width="170" />
            <el-table-column prop="last_used_at" label="最后使用" width="170" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status==='active'" size="small" text type="danger" @click="revokeToken(row)">
                  <el-icon><Close /></el-icon> 吊销
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ── Webhooks ── -->
      <div v-show="activeTab === 'webhooks'" class="openapi-section g-fade-in-up">
        <div class="openapi-table-card">
          <div class="openapi-table-header">
            <span class="openapi-table-title">事件订阅</span>
          </div>
          <el-empty description="事件订阅模块开发中" :image-size="60" />
        </div>
      </div>

      <!-- ── Call Logs ── -->
      <div v-show="activeTab === 'logs'" class="openapi-section g-fade-in-up">
        <div class="openapi-table-card">
          <div class="openapi-table-header">
            <span class="openapi-table-title">调用日志</span>
            <el-button :icon="Refresh" text size="small" @click="loadData" :loading="loading">刷新</el-button>
          </div>
          <el-table :data="callLogs" v-loading="loading" stripe style="width:100%" size="small"
            :empty-text="loading ? '加载中...' : '暂无调用日志'">
            <el-table-column prop="request_method" label="方法" width="80">
              <template #default="{ row }">
                <span class="openapi-method-badge" :class="'openapi-method-' + (row.request_method || '').toLowerCase()">{{ row.request_method }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="request_path" label="路径" min-width="240" show-overflow-tooltip />
            <el-table-column prop="response_status" label="状态码" width="90">
              <template #default="{ row }">
                <span class="openapi-code-badge" :class="row.response_status >= 400 ? 'code-error' : 'code-ok'">{{ row.response_status }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="duration_ms" label="耗时(ms)" width="100">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.duration_ms > 3000 }">{{ row.duration_ms ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="ip_address" label="来源 IP" width="140" />
            <el-table-column prop="create_datetime" label="时间" width="170" />
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiAppApi, apiTokenApi, webhookSubApi, openApiLogApi, RevokeToken } from '/@/api/open-api/index'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Close, Refresh, Grid, Key, Link, Document } from '@element-plus/icons-vue'

const activeTab = ref('apps')
const loading = ref(false)
const apps = ref<any[]>([])
const tokens = ref<any[]>([])
const webhooks = ref<any[]>([])
const callLogs = ref<any[]>([])
const showAddApp = ref(false)
const showAddToken = ref(false)

async function loadData() {
  loading.value = true
  try {
    const [a, t, l] = await Promise.all([
      apiAppApi.list(),
      apiTokenApi.list(),
      openApiLogApi.list({ limit: 50 }),
    ])
    apps.value = a.data || []
    tokens.value = t.data || []
    callLogs.value = l.data || []
  } finally { loading.value = false }
}

async function revokeToken(row: any) {
  await RevokeToken(row.id)
  ElMessage.success('凭证已吊销')
  await loadData()
}

function editApp(row: any) { /* TODO */ }

onMounted(async () => {
  await loadData()

  const key = 'opsflow_tour_openapi'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🔑 Open API — 第三方应用管理与 API 访问凭证生命周期管理', duration: 6000 })
    localStorage.setItem(key, 'true')
  }
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.open-api-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.openapi-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.openapi-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.openapi-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.openapi-hero-left { flex: 1 1 auto; }
.openapi-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; }
.openapi-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); }
.openapi-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.openapi-stat-item { text-align: center; padding: 0 14px; }
.openapi-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.openapi-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.openapi-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.openapi-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 24px; margin-top: -4px;
}
.openapi-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.openapi-hero-tab:hover { color: rgba(255,255,255,0.9); }
.openapi-hero-tab.active { color: #fff; border-bottom-color: #409EFF; }

/* ===== Body ===== */
.openapi-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.openapi-section { padding-top: 16px; }

/* ===== Table Card ===== */
.openapi-table-card {
  background: #fff; border-radius: 14px; box-shadow: $g-shadow-card; overflow: hidden;
}
.openapi-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.openapi-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.openapi-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.openapi-table-title { font-size: 15px; font-weight: 600; color: $g-text-primary; }

/* ===== Status Badge ===== */
.openapi-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.openapi-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.openapi-status-active .openapi-status-dot { background: #67C23A; }
.openapi-status-active { background: #f0f9eb; color: #67C23A; }
.openapi-status-inactive .openapi-status-dot,
.openapi-status-revoked .openapi-status-dot { background: #c0c4cc; }
.openapi-status-inactive { background: #f5f7fa; color: #909399; }
.openapi-status-revoked { background: #f5f7fa; color: #909399; }

/* ===== Method Badge ===== */
.openapi-method-badge {
  display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
}
.openapi-method-get { background: #ecf5ff; color: #409EFF; }
.openapi-method-post { background: #f0f9eb; color: #67C23A; }
.openapi-method-put { background: #fdf6ec; color: #E6A23C; }
.openapi-method-patch { background: #fdf6ec; color: #E6A23C; }
.openapi-method-delete { background: #fef0f0; color: #F56C6C; }

/* ===== Code Badge ===== */
.openapi-code-badge {
  display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 6px;
}
.code-ok { background: #f0f9eb; color: #67C23A; }
.code-error { background: #fef0f0; color: #F56C6C; }

/* ===== Utilities ===== */
.text-warning { color: #E6A23C; font-weight: 500; }
</style>
