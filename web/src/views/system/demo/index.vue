<template>
  <div class="of-page">
    <div class="of-card of-fade-in-up">
      <div class="of-section-header">
        <el-icon :size="20" color="#409EFF"><Monitor /></el-icon>
        <span>Demo / 测试页</span>
      </div>
      <el-divider />
      <div class="of-body">
        <el-empty :image-size="80" description="This is a demo page for testing purposes 测试框架外显示" />
        <div class="of-hint">
          <el-tag type="info" effect="plain" size="small">/demo</el-tag>
          <span class="of-hint-text">路由已注册，无业务功能</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts" name="demo">
import { Monitor } from '@element-plus/icons-vue'
</script>

<style scoped lang="scss">
@use '../../apps/opsflow/styles/opsflow-global' as *;

.of-page {
  padding: 24px;
  min-height: calc(100vh - 88px);

  .of-card {
    max-width: 640px;
    margin: 0 auto;

    .of-section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: $of-text-primary;
    }
  }

  .of-body {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 20px 0 8px;
  }

  .of-hint {
    display: flex;
    align-items: center;
    gap: 10px;
    color: $of-text-muted;
    font-size: 13px;
  }

  .of-hint-text {
    color: $of-text-muted;
  }
}
</style>
