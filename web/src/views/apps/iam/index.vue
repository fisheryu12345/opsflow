<template>
  <div class="iam-page">
    <!-- Hero Section -->
    <div class="iam-hero g-fade-in-up">
      <h1 class="iam-hero-title">{{ $t('message.iam.title') }}</h1>
      <p class="iam-hero-subtitle">{{ $t('message.iam.heroSubtitle') }}</p>
    </div>

    <!-- Body -->
    <div class="iam-body">
      <el-tabs v-model="activeTab">
        <el-tab-pane name="requests" :label="$t('message.iam.myRequests')">
          <div class="iam-tab-content">
            <MyRequests />
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="isSuperuser" name="approval" :label="$t('message.iam.approval')">
          <div class="iam-tab-content">
            <ApprovalDashboard />
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="isSuperuser" name="business" :label="$t('message.iam.business')">
          <div class="iam-tab-content">
            <BusinessManage />
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="isSuperuser" name="environment" :label="$t('message.iam.environment')">
          <div class="iam-tab-content">
            <EnvironmentManage />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUserInfo } from '/@/stores/userInfo'
import MyRequests from './MyRequests/index.vue'
import ApprovalDashboard from './ApprovalDashboard/index.vue'
import BusinessManage from './BusinessManage.vue'
import EnvironmentManage from './EnvironmentManage.vue'

const activeTab = ref('requests')
const userInfo = useUserInfo()
const isSuperuser = computed(() => userInfo.userInfos?.roles?.includes('admin') || false)
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.iam-page {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: $g-bg-page;
  overflow-y: auto;
}

// ── Hero ──
.iam-hero {
  background: $g-gradient-hero;
  padding: 24px 28px 20px;
  border-bottom: 1px solid $g-border-card;
}
.iam-hero-title {
  font-size: 20px;
  font-weight: 700;
  color: $g-text-primary;
  margin: 0 0 4px;
}
.iam-hero-subtitle {
  font-size: 13px;
  color: $g-text-muted;
  margin: 0;
}

// ── Body ──
.iam-body {
  padding: 0 20px 20px;
}
.iam-body :deep(.el-tabs__header) {
  margin-bottom: 0;
  padding-top: 8px;
}
.iam-tab-content {
  padding-top: 12px;
}
</style>
