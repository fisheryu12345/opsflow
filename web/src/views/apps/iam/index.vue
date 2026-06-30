<template>
  <div class="iam-page">
    <!-- Hero Section -->
    <div class="iam-hero">
      <div class="iam-hero-bg" />
      <div class="iam-hero-inner">
        <div class="iam-hero-left">
          <h1 class="iam-hero-title">IAM</h1>
          <p class="iam-hero-subtitle">Identity & Access Management — 身份认证与权限管理</p>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="iam-hero-tabs">
        <div class="iam-hero-tab" :class="{ active: activeTab === 'permissions' }" @click="activeTab = 'permissions'">
          <el-icon><Key /></el-icon> 我的权限
        </div>
        <div class="iam-hero-tab" :class="{ active: activeTab === 'requests' }" @click="activeTab = 'requests'">
          <el-icon><List /></el-icon> 申请
        </div>
        <div class="iam-hero-tab" :class="{ active: activeTab === 'approval' }" @click="activeTab = 'approval'">
          <el-icon><Checked /></el-icon> 审批
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'business' }" @click="activeTab = 'business'">
          <el-icon><OfficeBuilding /></el-icon> 业务线
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'environment' }" @click="activeTab = 'environment'">
          <el-icon><Monitor /></el-icon> 环境
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">
          <el-icon><User /></el-icon> 用户
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'roles' }" @click="activeTab = 'roles'">
          <el-icon><Avatar /></el-icon> 角色
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'menus' }" @click="activeTab = 'menus'">
          <el-icon><Menu /></el-icon> 菜单
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'depts' }" @click="activeTab = 'depts'">
          <el-icon><Connection /></el-icon> 部门
        </div>
        <div v-if="isSuperuser" class="iam-hero-tab" :class="{ active: activeTab === 'operationLog' }" @click="activeTab = 'operationLog'">
          <el-icon><Document /></el-icon> 日志
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="iam-body">
      <div v-show="activeTab === 'permissions'" class="iam-section g-fade-in-up">
        <div class="iam-permissions" v-loading="permLoading">
          <template v-if="permData">
            <el-descriptions :column="1" border size="small" style="margin-bottom:16px">
              <el-descriptions-item label="当前项目">{{ permData.project_name || projectStore.currentProject?.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="IAM 角色">
                <el-tag :type="permData.role === 'admin' ? 'danger' : permData.role === 'editor' ? 'primary' : 'info'" size="small">{{ permData.role }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
            <h4 style="margin:12px 0 8px">可见页面</h4>
            <div style="display:flex;flex-wrap:wrap;gap:6px">
              <el-tag v-for="p in permData.pages" :key="p.key" :type="p.visible ? 'success' : 'info'" size="small" effect="plain">{{ p.label_zh }}</el-tag>
            </div>
            <h4 style="margin:16px 0 10px">操作权限</h4>
            <template v-if="permData.permission_groups?.length">
              <div class="iam-perm-groups">
                <div v-for="g in permissionGroupsFiltered" :key="g.app" class="iam-perm-group">
                  <div class="iam-perm-app" :style="{ background: appColor(g.app) }">{{ appLabel(g.app) }}</div>
                  <div class="iam-perm-keys">
                    <el-tag v-for="k in g.keys" :key="k" size="small" effect="plain" round>{{ k.replace(g.app.toLowerCase() + ':', '') }}</el-tag>
                  </div>
                </div>
              </div>
            </template>
            <span v-else-if="!permData.permissions?.length" style="color:#C0C4CC;font-size:12px">只读权限（viewer）</span>
          </template>
          <el-empty v-else-if="!permLoading" description="请先选择一个项目" :image-size="60" />
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
      <div v-if="isSuperuser" v-show="activeTab === 'operationLog'" class="iam-section g-fade-in-up"><OperationLogManage /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUserInfo } from '/@/stores/userInfo'
import { useProjectStore } from '/@/stores/project'
import { request } from '/@/utils/service'
import { Key, List, Checked, OfficeBuilding, Monitor, User, Avatar, Menu, Connection, Document } from '@element-plus/icons-vue'
import MyRequests from './MyRequests/index.vue'
import ApprovalDashboard from './ApprovalDashboard/index.vue'
import BusinessManage from './BusinessManage.vue'
import EnvironmentManage from './EnvironmentManage.vue'
import RoleManage from './admin/role/index.vue'
import UserManage from './admin/user/index.vue'
import MenuManage from './admin/menu/index.vue'
import DeptManage from './admin/dept/index.vue'
import OperationLogManage from './admin/log/operationLog/index.vue'

const projectStore = useProjectStore()
const permData = ref<any>(null)
const permLoading = ref(false)

async function fetchPermissions() {
  const pid = projectStore.currentProjectId
  if (!pid) { permData.value = null; return }
  permLoading.value = true
  try {
    const res: any = await request({ url: '/api/iam/my_permissions/', params: { project_id: pid } })
    permData.value = (res as any).data || res
    if (projectStore.currentProject) permData.value.project_name = projectStore.currentProject.name
  } catch { permData.value = null }
  permLoading.value = false
}
watch(() => projectStore.currentProjectId, () => { if (activeTab.value === 'permissions') fetchPermissions() })

const activeTab = ref('permissions')
const userInfo = useUserInfo()
const isSuperuser = computed(() => userInfo.userInfos?.roles?.includes('admin') || false)

const APP_COLORS: Record<string, string> = { ITSM: '#409EFF', OPSFLOW: '#67C23A', CMDB: '#E6A23C' }
const APP_LABELS: Record<string, string> = { ITSM: 'ITSM', OPSFLOW: 'OPSflow', CMDB: 'CMDB' }
function appColor(app: string) { return APP_COLORS[app] || '#909399' }
function appLabel(app: string) { return APP_LABELS[app] || app }
const permissionGroupsFiltered = computed(() =>
  (permData.value?.permission_groups || []).filter((g: any) => APP_LABELS[g.app])
)
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
.iam-permissions { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

.iam-perm-groups { display: flex; flex-direction: column; gap: 10px; }
.iam-perm-group { display: flex; align-items: flex-start; gap: 10px; }
.iam-perm-app {
  flex-shrink: 0; min-width: 72px; text-align: center;
  font-size: 11px; font-weight: 700; color: #fff;
  padding: 4px 8px; border-radius: 6px; letter-spacing: 0.5px;
}
.iam-perm-keys { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
</style>
