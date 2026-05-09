<template>
  <div class="trading-page">

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="filters.symbol" placeholder="合约代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        class="filter-item-wide"
        @change="onDateChange"
      />
      <el-select v-model="filters.trend_label" placeholder="趋势标签" clearable class="filter-item" @change="refresh">
        <el-option label="强多头" value="strong_bull" />
        <el-option label="多头" value="bull" />
        <el-option label="弱多头" value="weak_bull" />
        <el-option label="无趋势" value="none" />
        <el-option label="弱空头" value="weak_bear" />
        <el-option label="空头" value="bear" />
        <el-option label="强空头" value="strong_bear" />
      </el-select>
      <el-select v-model="filters.signal_direction" placeholder="信号方向" clearable class="filter-item" @change="refresh">
        <el-option label="多头" :value="1" />
        <el-option label="空头" :value="-1" />
        <el-option label="无" :value="0" />
      </el-select>
      <el-select v-model="filters.executed_status" placeholder="执行状态" clearable class="filter-item" @change="refresh">
        <el-option label="待执行" value="PENDING" />
        <el-option label="成功" value="SUCCESS" />
        <el-option label="失败" value="FAILED" />
        <el-option label="跳过" value="SKIPPED" />
      </el-select>
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="trade_date" label="日期" min-width="110" sortable />
          <el-table-column prop="symbol" label="合约代码" min-width="130" sortable />
          <el-table-column prop="trend_label" label="趋势" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="trendTagType(row.trend_label)" size="small" effect="plain">
                {{ trendLabel(row.trend_label) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="trend_factor" label="趋势因子" min-width="100" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.trend_factor" type="number" :precision="4" />
            </template>
          </el-table-column>
          <el-table-column prop="donchian_upper" label="唐奇安上轨" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.donchian_upper" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="donchian_lower" label="唐奇安下轨" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.donchian_lower" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column label="突破" width="70" align="center">
            <template #default="{ row }">
              <StatusTag type="breakout" :value="row.is_breakout" />
            </template>
          </el-table-column>
          <el-table-column label="信号方向" width="80" align="center">
            <template #default="{ row }">
              <StatusTag type="direction" :value="row.signal_direction" />
            </template>
          </el-table-column>
          <el-table-column prop="trade_type" label="交易类型" min-width="100" align="center" />
          <el-table-column label="执行状态" width="80" align="center">
            <template #default="{ row }">
              <StatusTag type="executed" :value="row.executed_status" />
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        </el-table>
      </div>
    </div>

    <!-- Pagination -->
    <div style="display: flex; justify-content: center; margin-top: 12px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ValueCell from '/@/views/apps/components/ValueCell.vue'
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import { useDailySignal } from './useDailySignal'

const {
  list, loading, page, pageSize, total,
  filters, onPageChange, onSizeChange, refresh,
} = useDailySignal()

const dateRange = ref<[Date, Date] | null>(null)

function onDateChange(val: [Date, Date] | null) {
  if (val) {
    filters.trade_date__gte = formatDate(val[0])
    filters.trade_date__lte = formatDate(val[1])
  } else {
    filters.trade_date__gte = ''
    filters.trade_date__lte = ''
  }
  refresh()
}

function formatDate(d: Date) {
  return d.toISOString().split('T')[0]
}

const trendLabels: Record<string, string> = {
  strong_bull: '强多头',
  bull: '多头',
  weak_bull: '弱多头',
  none: '无趋势',
  weak_bear: '弱空头',
  bear: '空头',
  strong_bear: '强空头',
}

const trendColors: Record<string, string> = {
  strong_bull: 'danger',
  bull: 'danger',
  weak_bull: 'warning',
  none: 'info',
  weak_bear: 'warning',
  bear: 'success',
  strong_bear: 'success',
}

function trendLabel(val: string) {
  return trendLabels[val] || val || '--'
}

function trendTagType(val: string) {
  return (trendColors[val] || 'info') as any
}
</script>
