<template>
  <div class="trading-page">

    <!-- Summary Cards -->
    <div class="metric-card-grid">
      <MetricCard label="总持仓手数" :value="totalHoldings" color-type="neutral" border-color="blue" />
      <MetricCard label="多单品种数" :value="longCount" color-type="positive" border-color="green" />
      <MetricCard label="空单品种数" :value="shortCount" color-type="negative" border-color="red" />
      <MetricCard label="当前浮动盈亏" :value="totalUnrealizedPnl" color-type="sign" border-color="purple" :format-currency="true" />
      <MetricCard label="需移仓品种" :value="rolloverCount" color-type="negative" border-color="orange" />
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="filters.symbol" placeholder="合约代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-input v-model="filters.product_code" placeholder="品种代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-select v-model="filters.direction" placeholder="方向" clearable class="filter-item" @change="refresh">
        <el-option label="多头" :value="1" />
        <el-option label="空头" :value="-1" />
      </el-select>
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%" @sort-change="handleSortChange">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="symbol" label="合约代码" min-width="130" sortable />
          <el-table-column label="方向" width="70" align="center">
            <template #default="{ row }">
              <StatusTag type="direction" :value="row.direction" />
            </template>
          </el-table-column>
          <el-table-column prop="contract_total_position" label="持仓手数" min-width="90" align="right" sortable />
          <el-table-column prop="last_add_price" label="开仓均价" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.last_add_price" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="latest_close_price" label="收盘价" min-width="90" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.latest_close_price" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="stop_loss_price" label="止损价" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.stop_loss_price" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column label="浮动盈亏" min-width="130" align="right" sortable="custom" prop="float_profit">
            <template #default="{ row }">
              <ValueCell :value="Number(row.float_profit) || 0" type="currency" />
            </template>
          </el-table-column>
          <el-table-column label="趋势因子" min-width="100" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.indicators?.trend_factor ?? row.trend_info" type="number" :precision="4" />
            </template>
          </el-table-column>
          <el-table-column label="需移仓" width="80" align="center">
            <template #default="{ row }">
              <StatusTag type="active" :value="!row.is_rollover_needed" />
            </template>
          </el-table-column>
          <el-table-column label="保本激活" width="80" align="center">
            <template #default="{ row }">
              <StatusTag type="active" :value="row.protect_cost_enabled" />
            </template>
          </el-table-column>
          <el-table-column prop="last_update_time" label="更新时间" min-width="160" sortable />
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
import { computed } from 'vue'
import MetricCard from '/@/views/apps/components/MetricCard.vue'
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import ValueCell from '/@/views/apps/components/ValueCell.vue'
import { usePosition } from './usePosition'

const {
  list, loading, page, pageSize, total,
  filters, totalHoldings, longCount, shortCount, rolloverCount,
  onPageChange, onSizeChange, refresh,
} = usePosition()

const totalUnrealizedPnl = computed(() =>
  list.value.reduce((sum, row) => sum + (Number(row.float_profit) || 0), 0)
)

function handleSortChange({ prop, order }: { prop?: string; order?: 'ascending' | 'descending' | null }) {
  if (prop !== 'float_profit' || !order) return
  list.value.sort((a, b) => {
    const diff = (Number(a.float_profit) || 0) - (Number(b.float_profit) || 0)
    return order === 'ascending' ? diff : -diff
  })
}
</script>
