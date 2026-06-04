<template>
  <div class="sys-page opsflow-dashboard">
    <!-- Hero Banner / 顶部问候横幅 -->
    <div class="of-fade-in-up home-hero">
      <div class="home-hero-content">
        <div class="home-hero-icon">
          <el-icon :size="28"><DataBoard /></el-icon>
        </div>
        <div class="home-hero-info">
          <h2 class="home-hero-title">OpsFlow Dashboard</h2>
          <p class="home-hero-desc">运维流程自动化平台 · 概览数据与快捷入口</p>
        </div>
      </div>
    </div>

    <!-- Stats Cards / 统计卡片 -->
    <div class="stat-cards">
      <div
        v-for="(card, i) in statCards"
        :key="card.label"
        class="of-card stat-card of-stagger-item"
        :style="{ animationDelay: `${i * 0.08}s` }"
      >
        <div class="stat-icon" :style="{ background: card.bg }">
          <component :is="card.icon" style="width:24px;height:24px;color:#fff" />
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- Overview Section / 概览说明 -->
    <div class="of-card home-section of-fade-in-up" style="animation-delay:0.2s">
      <div class="home-section-header">
        <span class="home-section-icon">
          <el-icon :size="16"><InfoFilled /></el-icon>
        </span>
        <span>OpsFlow 概览</span>
      </div>
      <div class="home-section-body">
        <p class="home-section-text">
          OpsFlow 是一个基于 Django + Vue3 的运维流程自动化平台。
          通过可视化 DAG 编辑器构建自动化流程，支持审批流、Webhook 触发、
          定时调度、子流程嵌套等高级特性。
        </p>
        <el-space direction="vertical" alignment="flex-start" style="width:100%;margin-top:16px;">
          <el-alert
            v-for="(tip, i) in quickTips" :key="i"
            :title="tip"
            type="info"
            show-icon
            :closable="false"
          />
        </el-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { GetDashboardStats } from './api'
import { DataBoard, Tickets, Clock, Aim, InfoFilled } from '@element-plus/icons-vue'

const statCards = ref([
  { label: '项目总数', value: '--', icon: DataBoard, bg: '#409eff' },
  { label: '流程模板', value: '--', icon: Tickets, bg: '#67c23a' },
  { label: '运行实例', value: '--', icon: Clock, bg: '#e6a23c' },
  { label: '接入节点', value: '--', icon: Aim, bg: '#909399' },
])

const quickTips = [
  '前往 OpsFlow 页面创建您的第一个自动化流程',
  '通过模板市场快速部署常用运维场景',
  '支持定时调度、Webhook 触发、手动触发三种模式',
  '内置审批流引擎，支持多级审批与权限控制',
]

onMounted(async () => {
  try {
    const res = await GetDashboardStats()
    if (res.code === 2000 && res.data) {
      statCards.value = [
        { label: '项目总数', value: res.data.project_count ?? '--', icon: DataBoard, bg: '#409eff' },
        { label: '流程模板', value: res.data.template_count ?? '--', icon: Tickets, bg: '#67c23a' },
        { label: '运行实例', value: res.data.execution_count ?? '--', icon: Clock, bg: '#e6a23c' },
        { label: '接入节点', value: res.data.plugin_count ?? '--', icon: Aim, bg: '#909399' },
      ]
    }
  } catch (e) {
    console.warn('Dashboard stats not available yet', e)
  }
})
</script>

<style scoped lang="scss">
// ============================================================
// OPSflow Design Tokens (inline for system page independence)
// ============================================================
$of-color-primary: #409EFF;
$of-color-primary-dark: #337ecc;
$of-color-accent: #667eea;
$of-color-accent-dark: #764ba2;
$of-bg-card: #f8f9fb;
$of-bg-page: #f0f2f5;
$of-text-primary: #303133;
$of-text-secondary: #666;
$of-text-muted: #909399;
$of-border-card: #f0f0f0;
$of-radius-card: 10px;
$of-shadow-card: 0 1px 4px rgba(0, 0, 0, 0.06);
$of-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.06);
$of-transition-default: 0.2s;
$of-padding-card: 16px 18px;

// ============================================================
// Reusable Classes (inline, matching opsflow-global)
// ============================================================
.of-card {
  background: $of-bg-card;
  border: 1px solid $of-border-card;
  border-radius: $of-radius-card;
  padding: $of-padding-card;
  transition: transform $of-transition-default, box-shadow $of-transition-default;
}
.of-card:hover {
  transform: translateY(-1px);
  box-shadow: $of-shadow-hover;
}

.of-fade-in-up {
  animation: ofFadeInUp 0.5s ease both;
}
.of-stagger-item {
  animation: ofFadeInUp 0.4s ease both;
}
@keyframes ofFadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

// ============================================================
// Page
// ============================================================
.sys-page.opsflow-dashboard {
  width: 100%;
}

// ============================================================
// Hero Banner
// ============================================================
.home-hero {
  background: linear-gradient(135deg, #ecf5ff 0%, #f8f9fb 100%);
  border: 1px solid $of-border-card;
  border-radius: $of-radius-card;
  padding: 20px 24px;
  margin-bottom: 18px;
  box-shadow: $of-shadow-card;
  transition: box-shadow $of-transition-default;

  &:hover {
    box-shadow: $of-shadow-hover;
  }
}

.home-hero-content {
  display: flex;
  align-items: center;
  gap: 18px;
}

.home-hero-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.3);
}

.home-hero-info {
  flex: 1;
  min-width: 0;
}

.home-hero-title {
  font-size: 20px;
  font-weight: 700;
  color: $of-text-primary;
  margin: 0 0 4px;
}

.home-hero-desc {
  font-size: 13px;
  color: $of-text-muted;
  margin: 0;
}

// ============================================================
// Stats Cards Grid
// ============================================================
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;

  &:hover {
    transform: translateY(-1px);
    box-shadow: $of-shadow-hover;
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: $of-text-primary;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: $of-text-muted;
  margin-top: 4px;
}

// ============================================================
// Overview Section
// ============================================================
.home-section {
  margin-top: 0;
}

.home-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid $of-border-card;
  font-size: 15px;
  font-weight: 600;
  color: $of-text-primary;
}

.home-section-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.home-section-text {
  color: $of-text-secondary;
  line-height: 2;
  margin: 0;
}

.home-section-body {
  // spacing handled by .of-card padding
}
</style>
