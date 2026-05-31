<template>
  <div class="iam-container">
    <el-tabs v-model="activeTab" class="iam-tabs">
      <el-tab-pane name="my-requests" label="My Requests">
        <MyRequests />
      </el-tab-pane>
      <el-tab-pane v-if="isSuperuser" name="approval" label="Approval Dashboard">
        <ApprovalDashboard />
      </el-tab-pane>
    </el-tabs>
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
.iam-container { display: flex; flex-direction: column; height: 100%; background: #fff; }
.iam-tabs { flex: 1; display: flex; flex-direction: column; }
.iam-tabs :deep(.el-tabs__content) { flex: 1; overflow: auto; }
.iam-tabs :deep(.el-tab-pane) { height: 100%; }
.iam-tabs :deep(.el-tabs__header) { margin: 0 16px; }
</style>
