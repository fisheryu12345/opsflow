<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-select v-model="filters.exchange" placeholder="交易所" clearable class="filter-item" @change="refresh">
        <el-option label="上期所" value="SHFE" />
        <el-option label="大商所" value="DCE" />
        <el-option label="郑商所" value="CZCE" />
        <el-option label="中金所" value="CFFEX" />
        <el-option label="广期所" value="GFEX" />
      </el-select>
      <el-input v-model="filters.product_code" placeholder="品种代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-button type="primary" @click="refresh">查询</el-button>
      <el-button type="info" @click="handleShowStats">
        <el-icon><DataAnalysis /></el-icon>
        统计信息
      </el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table
          :data="list" border stripe v-loading="loading"
          class="trading-table" style="width: 100%"
        >
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="exchange" label="交易所" min-width="90" sortable>
            <template #default="{ row }">{{ exchangeLabel(row.exchange) }}</template>
          </el-table-column>
          <el-table-column prop="product_code" label="品种代码" min-width="100" sortable />
          <el-table-column prop="symbol" label="主力合约" min-width="140" sortable />
          <el-table-column prop="name" label="合约名称" min-width="120" />
          <el-table-column prop="volume_multiple" label="乘数" min-width="80" align="right" sortable />
          <el-table-column prop="price_tick" label="最小变动" min-width="90" align="right" sortable />
          <el-table-column prop="min_position" label="最小开仓" min-width="80" align="right" sortable />
          <el-table-column label="夜盘" width="70" align="center">
            <template #default="{ row }">
              <StatusTag type="active" :value="row.night_trading" />
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无数据" />
          </template>
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

    <!-- Stats Dialog -->
    <ContractStatsDialog v-model="statsVisible" :stats="stats" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import { useContract } from './useContract'
import ContractStatsDialog from './ContractStatsDialog.vue'

const {
  list, loading, page, pageSize, total,
  filters, stats,
  onPageChange, onSizeChange, refresh,
  fetchStats,
} = useContract()

const statsVisible = ref(false)

const exchangeMap: Record<string, string> = {
  SHFE: '上期所', DCE: '大商所', CZCE: '郑商所',
  CFFEX: '中金所', GFEX: '广期所',
}

function exchangeLabel(code: string) {
  return exchangeMap[code] || code
}

async function handleShowStats() {
  await fetchStats()
  statsVisible.value = true
}
</script>
