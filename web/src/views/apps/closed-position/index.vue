<template>
  <div class="trading-page">

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="filters.symbol" placeholder="合约代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-input v-model="filters.product_code" placeholder="品种代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-select v-model="filters.direction" placeholder="方向" clearable class="filter-item" @change="refresh">
        <el-option label="多头" :value="1" />
        <el-option label="空头" :value="-1" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        class="filter-item-wide"
        @change="onDateChange"
      />
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="symbol" label="合约代码" min-width="130" sortable />
          <el-table-column prop="product_code" label="品种" min-width="80" sortable />
          <el-table-column label="方向" width="70" align="center">
            <template #default="{ row }">
              <StatusTag type="direction" :value="row.direction" />
            </template>
          </el-table-column>
          <el-table-column prop="volume" label="手数" min-width="70" align="right" sortable />
          <el-table-column prop="cost_price" label="开仓价" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.cost_price" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="exit_price" label="平仓价" min-width="110" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.exit_price" type="number" :precision="1" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="pnl" label="平仓盈亏" min-width="130" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.pnl" type="currency" />
            </template>
          </el-table-column>
          <el-table-column prop="holding_days" label="持仓天数" min-width="90" align="right" sortable />
          <el-table-column prop="trade_date" label="交易日期" min-width="110" sortable />
          <el-table-column prop="executed_at" label="执行时间" min-width="160" sortable />
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
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import ValueCell from '/@/views/apps/components/ValueCell.vue'
import { useClosedPosition } from './useClosedPosition'

const {
  list, loading, page, pageSize, total,
  filters, onPageChange, onSizeChange, refresh,
} = useClosedPosition()

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
</script>
