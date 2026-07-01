<template>
  <div class="iam-page">
    <!-- Hero Section -->
    <div class="iam-hero">
      <div class="iam-hero-bg" />
      <div class="iam-hero-inner">
        <div class="iam-hero-left">
          <h1 class="iam-hero-title">IAM</h1>
          <p class="iam-hero-subtitle">{{ t('message.iam.heroSubtitle') }}</p>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="iam-hero-tabs">
        <div class="iam-hero-tab" :class="{ active: activeTab === 'permissions' }" @click="activeTab = 'permissions'">
          <el-icon><Key /></el-icon> {{ t('message.iam.myPermissions') }}
        </div>
        <div class="iam-hero-tab" :class="{ active: activeTab === 'requests' }" @click="activeTab = 'requests'">
          <el-icon><List /></el-icon> {{ t('message.iam.myRequests') }}
        </div>
        <div class="iam-hero-tab" :class="{ active: activeTab === 'approval' }" @click="activeTab = 'approval'">
          <el-icon><Checked /></el-icon> {{ t('message.iam.approval') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'business' }" @click="activeTab = 'business'">
          <el-icon><OfficeBuilding /></el-icon> {{ t('message.iam.business') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'environment' }" @click="activeTab = 'environment'">
          <el-icon><Monitor /></el-icon> {{ t('message.iam.environment') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">
          <el-icon><User /></el-icon> {{ t('message.iam.users') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'roles' }" @click="activeTab = 'roles'">
          <el-icon><Avatar /></el-icon> {{ t('message.iam.roles') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'menus' }" @click="activeTab = 'menus'">
          <el-icon><Menu /></el-icon> {{ t('message.iam.menus') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'depts' }" @click="activeTab = 'depts'">
          <el-icon><Connection /></el-icon> {{ t('message.iam.depts') }}
        </div>
        <div class="iam-hero-tab" :class="{ active: activeTab === 'operationLog' }" @click="activeTab = 'operationLog'">
          <el-icon><Document /></el-icon> {{ t('message.iam.operationLog') }}
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'loginLog' }" @click="activeTab = 'loginLog'">
          <el-icon><Connection /></el-icon> {{ t('message.iam.loginLog') }}
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="iam-body">
      <div v-show="activeTab === 'permissions'" class="iam-section g-fade-in-up">
        <div v-loading="permLoading" class="perm-page">
          <template v-if="myPerms">
            <!-- Header -->
            <div class="perm-header-bar">
              <div class="perm-header-left">
                <span class="perm-project-badge">{{ myPerms.project_name || t('message.iam.permissions') }}</span>
                <span class="perm-role-badge" :class="'perm-role--' + myPerms.role">
                  {{ myPerms.role === 'admin' ? t('message.iam.admin') : myPerms.role === 'editor' ? t('message.iam.editor') : t('message.iam.viewer') }}
                </span>
              </div>
              <div class="perm-header-right">
                <span class="perm-stat">{{ t('message.iam.permCount', { n: totalPermCount }) }}</span>
                <span class="perm-stat">{{ t('message.iam.permTotal', { n: userPerms.size }) }}</span>
              </div>
            </div>

            <!-- No permissions -->
            <div v-if="!userPerms.size" class="perm-empty-state">
              <el-icon :size="36" color="#dcdfe6"><Key /></el-icon>
              <p>{{ t('message.iam.noOperations') }}</p>
              <span class="perm-empty-hint">{{ isEn ? 'Submit permission requests from the Applications tab' : '从「申请」页面提交权限请求' }}</span>
            </div>

            <!-- App selector tabs -->
            <div v-else class="perm-app-tabs">
              <div v-for="app in appsWithPerms" :key="app.app"
                class="perm-app-tab"
                :class="{ active: app.app === selectedApp }"
                :style="{ '--app-color': appGradient(app.app) }"
                @click="selectedApp = app.app">
                {{ appLabel(app.app) }}
                <span class="perm-app-count">{{ app.permCount }}</span>
              </div>
            </div>

            <!-- Tab/Button table for selected app -->
            <div v-if="selectedApp" class="perm-struct-wrap">
              <table class="perm-struct-table">
                <thead>
                  <tr>
                    <th class="pst-th-tab">{{ t('message.iam.module') }}</th>
                    <th class="pst-th-sub">{{ t('message.iam.subPerms') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="tab in currentAppStructure" :key="tab.key" class="pst-tr">
                    <td class="pst-td-tab">
                      <div class="pst-tab-name">
                        <el-icon v-if="tabIcon(tab.icon)" size="15"><component :is="tabIcon(tab.icon)" /></el-icon>
                        <span>{{ isEn ? (tab.label_en || tab.label_zh) : tab.label_zh }}</span>
                        <span v-if="tabOpen(tab)" class="pst-tag-open"> {{ t('message.iam.openAccess') }}</span>
                      </div>
                    </td>
                    <td class="pst-td-sub">
                      <template v-if="tabHasPerms(tab)">
                        <div class="pst-perm-list">
                          <span v-for="p in tabPerms(tab)" :key="p.key" class="pst-perm-item"
                            :class="{ granted: p.granted }">
                            <el-icon v-if="p.granted" size="12" color="#67c23a"><SuccessFilled /></el-icon>
                            <el-icon v-else size="12" color="#e0e0e0"><CircleCloseFilled /></el-icon>
                            <span class="pst-perm-label">{{ p.label }}</span>
                            <span class="pst-perm-key">{{ p.shortKey }}</span>
                          </span>
                        </div>
                      </template>
                      <span v-else-if="tabPermRequired(tab)" class="pst-no-data">{{ t('message.iam.noAccessYet') }}</span>
                      <span v-else class="pst-open-label">{{ t('message.iam.defaultOpen') }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <div v-else-if="!permLoading" class="perm-empty-state">
            <el-icon :size="36" color="#dcdfe6"><Key /></el-icon>
            <p>{{ t('message.iam.noProjectSelected') }}</p>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'requests'" class="iam-section g-fade-in-up"><MyRequests /></div>
      <div v-show="activeTab === 'approval'" class="iam-section g-fade-in-up"><ApprovalDashboard /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'business'" class="iam-section g-fade-in-up"><BusinessManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'environment'" class="iam-section g-fade-in-up"><EnvironmentManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'roles'" class="iam-section g-fade-in-up"><RoleManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'users'" class="iam-section g-fade-in-up"><UserManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'menus'" class="iam-section g-fade-in-up"><MenuManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'depts'" class="iam-section g-fade-in-up"><DeptManage /></div>
      <div v-show="activeTab === 'operationLog'" class="iam-section g-fade-in-up"><OperationLogManage /></div>
      <div v-if="isSuperuser" v-show="activeTab === 'loginLog'" class="iam-section g-fade-in-up"><LoginLogManage /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserInfo } from '/@/stores/userInfo'
import { useProjectStore } from '/@/stores/project'
import { request } from '/@/utils/service'
import {
  Key, List, Checked, OfficeBuilding, Monitor, User, Avatar, Menu, Connection, Document,
  SuccessFilled, CircleCloseFilled,
  DataAnalysis, VideoPlay, Clock, Collection, Link, EditPen,
  Setting, WarningFilled, Edit, Refresh, Bell,
} from '@element-plus/icons-vue'
import MyRequests from './MyRequests/index.vue'
import ApprovalDashboard from './ApprovalDashboard/index.vue'
import BusinessManage from './BusinessManage.vue'
import EnvironmentManage from './EnvironmentManage.vue'
import RoleManage from './admin/role/index.vue'
import UserManage from './admin/user/index.vue'
import MenuManage from './admin/menu/index.vue'
import DeptManage from './admin/dept/index.vue'
import OperationLogManage from './admin/log/operationLog/index.vue'
import LoginLogManage from './admin/log/loginLog/index.vue'

const projectStore = useProjectStore()

// My permissions data (from /api/iam/my_permissions/)
const myPerms = ref<any>(null)
const permLoading = ref(false)

// Catalog structure (from /api/iam/permission-catalog/)
const catalog = ref<any[]>([])

// User's flat permission set
const userPerms = computed(() => new Set<string>(myPerms.value?.permissions || []))

const activeTab = ref('permissions')
const userInfo = useUserInfo()
const isSuperuser = computed(() => userInfo.userInfos?.roles?.includes('admin') || false)

// App selection for structure view
const selectedApp = ref('')

async function fetchPermissions() {
  const pid = projectStore.currentProjectId
  if (!pid) { myPerms.value = null; catalog.value = []; return }
  permLoading.value = true
  try {
    const [permRes, catRes] = await Promise.all([
      request({ url: '/api/iam/my_permissions/', params: { project_id: pid } }),
      request({ url: '/api/iam/permission-catalog/', method: 'get' }),
    ])
    const data = (permRes as any).data || permRes
    if (projectStore.currentProject) data.project_name = projectStore.currentProject.name
    myPerms.value = data
    catalog.value = catRes?.data || []
    // Default to first app with permissions
    if (appsWithPerms.value.length) {
      selectedApp.value = appsWithPerms.value[0].app
    }
  } catch {
    myPerms.value = null
    catalog.value = []
  }
  permLoading.value = false
}

watch(() => projectStore.currentProjectId, () => {
  if (activeTab.value === 'permissions' && projectStore.currentProjectId) fetchPermissions()
})
onMounted(() => {
  if (projectStore.currentProjectId && activeTab.value === 'permissions') fetchPermissions()
})

const i18n = useI18n()
const t = i18n.t
const isEn = computed(() => String(i18n.locale.value).startsWith('en'))

const APP_GRADIENTS: Record<string, string> = {
  OPSFLOW: 'linear-gradient(135deg, #43a047 0%, #66bb6a 100%)',
  ITSM: 'linear-gradient(135deg, #1e88e5 0%, #42a5f5 100%)',
  CMDB: 'linear-gradient(135deg, #ef6c00 0%, #ffa726 100%)',
  SYSTEM: 'linear-gradient(135deg, #546e7a 0%, #78909c 100%)',
  PORTAL: 'linear-gradient(135deg, #7b1fa2 0%, #ab47bc 100%)',
  IAM: 'linear-gradient(135deg, #37474f 0%, #607d8b 100%)',
}
const APP_LABELS: Record<string, string> = { ITSM: 'ITSM', OPSFLOW: 'OPSflow', CMDB: 'CMDB', SYSTEM: '系统', PORTAL: 'Portal', IAM: 'IAM' }
function appGradient(app: string) { return APP_GRADIENTS[app] || '#78909c' }
function appLabel(app: string) { return APP_LABELS[app] || app }

// Total perm count across all apps
const totalPermCount = computed(() => {
  if (!myPerms.value?.app_roles) return 0
  let count = 0
  for (const ar of Object.values(myPerms.value.app_roles) as any[]) {
    count += ar.permissions?.length || 0
  }
  return count
})

// Apps that have permissions for this user
const appsWithPerms = computed(() => {
  if (!myPerms.value?.app_roles) return []
  const list: { app: string; permCount: number }[] = []
  for (const [key, ar] of Object.entries(myPerms.value.app_roles) as [string, any][]) {
    if (ar.permissions?.length) {
      list.push({ app: ar.app, permCount: ar.permissions.length })
    }
  }
  return list
})

// Current app's structure from catalog
const currentAppStructure = computed(() => {
  const appLower = selectedApp.value?.toLowerCase()
  const cat = catalog.value.find((a: any) => a.app === appLower)
  return cat?.tabs || []
})

// Icon mapping (same as MyRequests)
const ICON_MAP: Record<string, any> = {
  DataAnalysis, Document, VideoPlay, Clock, Collection, List, Link,
  Setting, WarningFilled, Edit, User, Refresh, Bell, EditPen,
}
function tabIcon(name: string) {
  return ICON_MAP[name] || null
}

// Check if a tab is open (no perm required)
function tabOpen(tab: any): boolean {
  return !tab.required_perm_tab
}

// Check if a tab requires a perm that user has
function tabPermRequired(tab: any): boolean {
  return tab.required_perm_tab && !tab.buttons?.length
}

// Check if this tab has any buttons or perms to show
function tabHasPerms(tab: any): boolean {
  if (tab.buttons?.length) return true
  if (tab.required_perm_tab) return true
  return false
}

// Get perms for this tab (buttons + tab itself)
function tabPerms(tab: any): { key: string; label: string; shortKey: string; granted: boolean }[] {
  const items: { key: string; label: string; shortKey: string; granted: boolean }[] = []
  // Tab-level perm
  if (tab.required_perm_tab) {
    items.push({
      key: tab.required_perm_tab,
      label: (isEn.value ? 'Access ' : '访问 ') + (isEn.value ? (tab.label_en || tab.label_zh) : tab.label_zh),
      shortKey: tab.required_perm_tab.split(':').slice(1).join(':'),
      granted: userPerms.value.has(tab.required_perm_tab),
    })
  }
  // Button perms
  for (const btn of tab.buttons || []) {
    if (btn.required_perm) {
      items.push({
        key: btn.required_perm,
        label: isEn.value ? (btn.label_en || btn.label_zh) : btn.label_zh,
        shortKey: btn.required_perm.split(':').slice(1).join(':'),
        granted: userPerms.value.has(btn.required_perm),
      })
    }
  }
  return items
}
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.iam-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.iam-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.iam-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.iam-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; align-items: center; gap: 16px;
}
.iam-hero-left { flex: 1; }
.iam-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; }
.iam-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); }

.iam-hero-tabs {
  position: relative; z-index: 1; display: flex; justify-content: flex-start; gap: 0; padding: 0 24px; margin-top: -4px;
}
.iam-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 16px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.iam-hero-tab:hover { color: rgba(255,255,255,0.9); }
.iam-hero-tab.active { color: #fff; border-bottom-color: #409EFF; }

/* ===== Body ===== */
.iam-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.iam-section { padding-top: 16px; }

/* ===== Permissions Page ===== */
.perm-page { background: #fff; border-radius: 14px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

/* Header */
.perm-header-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 16px; border-bottom: 1px solid #f0f0f0; margin-bottom: 16px;
}
.perm-header-left { display: flex; align-items: center; gap: 10px; }
.perm-header-right { display: flex; gap: 14px; }
.perm-project-badge {
  font-size: 14px; font-weight: 600; color: #303133;
  background: #f0f5ff; padding: 3px 12px; border-radius: 6px;
}
.perm-role-badge {
  font-size: 11px; padding: 2px 10px; border-radius: 10px; font-weight: 600;
}
.perm-role--admin { background: #fef0f0; color: #f56c6c; }
.perm-role--editor { background: #ecf5ff; color: #409eff; }
.perm-role--viewer { background: #f4f4f5; color: #909399; }
.perm-stat { font-size: 12px; color: #909399; }

/* App selector tabs */
.perm-app-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.perm-app-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  &:hover { background: #ecf5ff; color: #409eff; }
  &.active {
    color: #fff;
    background: var(--app-color, #409eff);
  }
}
.perm-app-count {
  font-size: 11px;
  opacity: 0.7;
}

/* Structure table */
.perm-struct-wrap {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
}
.perm-struct-table {
  width: 100%;
  border-collapse: collapse;
}
.perm-struct-table thead th {
  background: #f5f7fa;
  padding: 9px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  text-align: left;
  border-bottom: 1px solid #e4e7ed;
}
.pst-th-tab { width: 180px; }
.pst-th-sub { }

.pst-tr {
  transition: background 0.12s;
  &:hover { background: #fafbfc; }
  & + & { border-top: 1px solid #f0f0f0; }
}

.pst-td-tab {
  padding: 10px 14px;
  vertical-align: middle;
}
.pst-td-sub {
  padding: 8px 14px;
  vertical-align: middle;
}

.pst-tab-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  .el-icon { color: #909399; flex-shrink: 0; }
}
.pst-tag-open {
  font-size: 10px;
  color: #67c23a;
  background: #f0f9eb;
  padding: 0 6px;
  border-radius: 4px;
  font-weight: 400;
}

.pst-perm-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pst-perm-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  padding: 3px 10px 3px 6px;
  border-radius: 14px;
  background: #f5f7fa;
  color: #c0c4cc;
  &.granted {
    background: #f0f9eb;
    color: #555;
  }
}
.pst-perm-label {
  white-space: nowrap;
}
.pst-perm-key {
  font-size: 10px;
  font-family: 'SF Mono', 'Cascadia Code', Menlo, monospace;
  color: #bbb;
  .pst-perm-item.granted & { color: #95d475; }
}

.pst-no-data {
  font-size: 12px;
  color: #c0c4cc;
}
.pst-open-label {
  font-size: 12px;
  color: #c0c4cc;
}

.perm-empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 0; gap: 8px;
  p { font-size: 14px; color: #909399; margin: 0; }
}
.perm-empty-hint { font-size: 12px; color: #c0c4cc; }
</style>
