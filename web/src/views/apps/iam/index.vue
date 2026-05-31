<template>
  <div class="iam-page">
    <div class="iam-body-card">
      <el-tabs v-model="activeTab" class="iam-tabs">
        <el-tab-pane name="my-requests" label="My Requests">
          <MyRequests />
        </el-tab-pane>
        <el-tab-pane v-if="isSuperuser" name="approval" label="Approval Dashboard">
          <ApprovalDashboard />
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

const activeTab = ref('my-requests')
const userInfo = useUserInfo()
const isSuperuser = computed(() => {
  return userInfo.userInfos?.roles?.includes('admin') || false
})
</script>

<style scoped>
.iam-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #f0f2f5;
  overflow: hidden;
}
.iam-body-card {
  height: 100%;
  margin: 8px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.iam-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.iam-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
  padding: 0;
}
.iam-tabs :deep(.el-tab-pane) {
  height: 100%;
}
.iam-tabs :deep(.el-tabs__header) {
  margin: 0 16px;
  padding-top: 4px;
}
</style>
