<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        class="filter-item-wide"
        @change="onDateChange"
      />
      <el-button type="primary" @click="fetchStats" :loading="loading">
        <el-icon><DataAnalysis /></el-icon>
        统计
      </el-button>
    </div>

    <!-- Summary Cards -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.summary.total }}</div>
        <div class="stat-label">信号总数</div>
      </div>
      <div class="stat-card stat-success">
        <div class="stat-value">{{ stats.summary.success }}</div>
        <div class="stat-label">成功</div>
      </div>
      <div class="stat-card stat-failed">
        <div class="stat-value">{{ stats.summary.failed }}</div>
        <div class="stat-label">失败</div>
      </div>
      <div class="stat-card stat-warning">
        <div class="stat-value">{{ stats.summary.cancelled }}</div>
        <div class="stat-label">取消</div>
      </div>
      <div class="stat-card stat-pending">
        <div class="stat-value">{{ stats.summary.pending }}</div>
        <div class="stat-label">待执行</div>
      </div>
      <div class="stat-card stat-rate">
        <div class="stat-value">{{ stats.summary.overall_rate }}%</div>
        <div class="stat-label">整体成功率</div>
      </div>
    </div>

    <!-- By Type Table -->
    <div class="section-card" v-if="stats">
      <div class="section-header">按交易类型统计</div>
      <div class="section-body" style="padding: 0;">
        <el-table :data="stats.by_type" border stripe style="width: 100%">
          <el-table-column prop="trade_type" label="交易类型" min-width="130">
            <template #default="{ row }">
              <el-tag :type="typeTag(row.trade_type)" size="small" effect="plain">
                {{ typeLabel(row.trade_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total" label="总数" width="80" align="center" sortable />
          <el-table-column prop="success" label="成功" width="80" align="center" sortable>
            <template #default="{ row }">
              <span class="num-green">{{ row.success }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="failed" label="失败" width="80" align="center" sortable>
            <template #default="{ row }">
              <span class="num-red">{{ row.failed }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="cancelled" label="取消" width="80" align="center" sortable />
          <el-table-column prop="pending" label="待执行" width="80" align="center" sortable />
          <el-table-column prop="rate" label="成功率" width="100" align="center" sortable>
            <template #default="{ row }">
              <el-progress
                :percentage="row.rate"
                :color="rateColor(row.rate)"
                :stroke-width="16"
                :text-inside="true"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Failure Reasons -->
    <div class="section-card" v-if="stats && stats.failure_reasons.length > 0">
      <div class="section-header">失败原因分布</div>
      <div class="section-body" style="padding: 0;">
        <el-table :data="stats.failure_reasons" border stripe style="width: 100%">
          <el-table-column prop="reason" label="失败原因" min-width="200" />
          <el-table-column prop="count" label="次数" width="100" align="center" sortable>
            <template #default="{ row }">
              <span class="num-red">{{ row.count }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Empty State -->
    <el-empty v-if="!stats && !loading" description="点击「统计」按钮查看信号执行数据" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import { useSignalStats } from './useSignalStats'

const { loading, stats, filters, fetchStats } = useSignalStats()

const dateRange = ref<[Date, Date] | null>(null)

function onDateChange(val: [Date, Date] | null) {
  if (val) {
    filters.date_from = formatDate(val[0])
    filters.date_to = formatDate(val[1])
  } else {
    filters.date_from = ''
    filters.date_to = ''
  }
}

function formatDate(d: Date) {
  return d.toISOString().split('T')[0]
}

function typeLabel(t: string) {
  const map: Record<string, string> = {
    ENTRY: '开仓', ADD_ON: '加仓', STOP_LOSS: '止损', EXIT: '平仓', ROLLOVER: '移仓',
  }
  return map[t] || t
}

function typeTag(t: string) {
  const map: Record<string, string> = {
    ENTRY: 'success', ADD_ON: 'warning', STOP_LOSS: 'danger', EXIT: 'info', ROLLOVER: '',
  }
  return map[t] || ''
}

function rateColor(rate: number) {
  if (rate >= 80) return '#67c23a'
  if (rate >= 60) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 18px 12px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid #ebeef5;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1.3;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.stat-success .stat-value { color: #67c23a; }
.stat-failed .stat-value { color: #f56c6c; }
.stat-warning .stat-value { color: #e6a23c; }
.stat-pending .stat-value { color: #909399; }
.stat-rate .stat-value { color: #409eff; }

.num-green { color: #67c23a; font-weight: 600; }
.num-red { color: #f56c6c; font-weight: 600; }

.section-card {
  margin-bottom: 16px;
}
.section-header {
  font-size: 15px;
  font-weight: 600;
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  color: #303133;
}
</style>
