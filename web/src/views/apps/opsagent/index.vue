<template>
  <div class="opsagent-page">
    <!-- ===== Hero Section ===== -->
    <div class="opsagent-hero">
      <div class="opsagent-hero-bg" />
      <div class="opsagent-hero-inner">
        <div class="opsagent-hero-left">
          <h1 class="opsagent-hero-title">{{ $t('message.opsagent.title') }}</h1>
          <p class="opsagent-hero-subtitle">{{ $t('message.opsagent.subtitle') }}</p>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="opsagent-hero-tabs">
        <div v-for="tab in pageConfig?.tabs" :key="tab.key"
          class="opsagent-hero-tab"
          :class="{ active: activeTab === tab.key, locked: !tab.has_access }"
          @click="onTabClick(tab)">
          <el-icon><component :is="iconMap[tab.icon]" /></el-icon>
          {{ isEn ? tab.label_en : tab.label_zh }}
          <span v-if="!tab.has_access" class="tab-lock">🔒</span>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="opsagent-body">
      <div v-show="activeTab === 'console' && tabHasAccess('console')" class="opsagent-section g-fade-in-up">
        <OpsConsole embedded :btnPerms="tabButtons('console')" />
      </div>
      <div v-show="activeTab === 'sessions' && tabHasAccess('sessions')" class="opsagent-section g-fade-in-up">
        <OpsSessions embedded />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePermissionStore } from '/@/stores/permission'
import { Monitor, Clock } from '@element-plus/icons-vue'
import { request } from '/@/utils/service'
import OpsConsole from './Console.vue'
import OpsSessions from './Sessions.vue'

const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))
const permissionStore = usePermissionStore()

const pageConfig = ref<any>(null)
const activeTab = ref('')

const iconMap: Record<string, any> = {
  Monitor, Clock,
}

function tabHasAccess(key: string): boolean {
  return pageConfig.value?.tabs?.find((t: any) => t.key === key)?.has_access ?? false
}

function tabButtons(key: string): Record<string, boolean> {
  const tab = pageConfig.value?.tabs?.find((t: any) => t.key === key)
  if (!tab?.buttons) return {}
  const map: Record<string, boolean> = {}
  for (const b of tab.buttons) {
    map[b.key] = b.has_access
  }
  return map
}

function onTabClick(tab: any) {
  if (!tab.has_access) {
    permissionStore.requestPerm(tab.label_zh, tab.required_perm)
    return
  }
  activeTab.value = tab.key
}

async function loadPageConfig() {
  try {
    const res = await request({ url: '/api/iam/page-permissions/', params: { app: 'opsagent' } })
    pageConfig.value = res.data
    const defaultTab = res.data.tabs.find((t: any) => t.is_default) || res.data.tabs[0]
    if (defaultTab) activeTab.value = defaultTab.key
  } catch { /* show empty */ }
}

onMounted(() => { loadPageConfig() })
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.opsagent-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.opsagent-hero {
  position: relative; flex-shrink: 0; overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.opsagent-hero-bg {
  position: absolute; inset: 0; opacity: 0.06;
  background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}
.opsagent-hero-inner {
  position: relative; z-index: 1; padding: 14px 24px;
  display: flex; flex-direction: row; align-items: center; gap: 16px;
}
.opsagent-hero-left { flex: 1 1 auto; }
.opsagent-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; }
.opsagent-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); }

.opsagent-hero-tabs {
  position: relative; z-index: 1; display: flex; gap: 0; padding: 0 16px; margin-top: -4px;
}
.opsagent-hero-tab {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6);
  cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; user-select: none;
  .el-icon { font-size: 16px; }
}
.opsagent-hero-tab:hover { color: rgba(255,255,255,0.9); }
.opsagent-hero-tab.active { color: #fff; border-bottom-color: #409EFF; }
.opsagent-hero-tab.locked { opacity: 0.6; }
.opsagent-hero-tab.locked:hover { opacity: 0.9; background: rgba(255,193,7,0.1); border-bottom-color: #ffc107; }
.opsagent-hero-tab .tab-lock { font-size: 11px; margin-left: 3px; }

/* ===== Body ===== */
.opsagent-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.opsagent-section { padding-top: 16px; min-height: 200px; }
</style>
