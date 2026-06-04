<template>
  <div class="opsflow-dashboard">
    <!-- Stats Cards -->
    <div class="stat-cards">
      <div class="stat-card" v-for="card in statCards" :key="card.label">
        <div class="stat-icon" :style="{ background: card.bg }">
          <component :is="card.icon" style="width:24px;height:24px;color:#fff" />
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="section-card">
      <div class="section-header">
        <h3>OpsFlow 概览</h3>
      </div>
      <div class="section-body">
        <p style="color:#8c8c8c;line-height:2;">
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
import { DataBoard, Tickets, Clock, Aim } from '@element-plus/icons-vue'

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
.opsflow-dashboard {
  padding: 16px;

  .stat-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    transition: transform .2s, box-shadow .2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,.12);
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
    color: #303133;
    line-height: 1.2;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }

  .section-card {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }

  .section-header h3 {
    margin: 0 0 12px;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }
}
</style>
