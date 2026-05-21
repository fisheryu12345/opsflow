<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-date-picker v-model="filters.trade_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" clearable class="filter-item" @change="refresh" />
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="trade_date" label="日期" width="110" sortable />
          <el-table-column label="合约代码" min-width="160">
            <template #default="{ row }">
              <span>{{ row.symbol }}</span>
              <span v-if="getProductLabel(row)" style="color:#999;font-size:0.85em;margin-left:6px">({{ getProductLabel(row) }})</span>
            </template>
          </el-table-column>
          <el-table-column prop="product_code" label="品种" width="70" align="center" />
          <el-table-column prop="score" label="评分" width="80" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.score >= 10 ? 'var(--el-color-primary)' : row.score >= 7 ? '#d97706' : '#999', fontWeight: row.score >= 10 ? '700' : '400' }">{{ row.score.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="ATR%" width="80" align="right" sortable>
            <template #default="{ row }">
              {{ (row.atr_pct * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="5日振幅" width="80" align="right" sortable>
            <template #default="{ row }">
              {{ (row.avg_amp * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column prop="vol_ratio" label="量比" width="70" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.vol_ratio >= 1.5 ? 'var(--el-color-danger)' : row.vol_ratio >= 1.0 ? '#d97706' : '#999' }">{{ row.vol_ratio.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="奖惩" width="60" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.bonus > 0" type="success" size="small" effect="plain">+{{ row.bonus }}</el-tag>
              <el-tag v-else-if="row.bonus < 0" type="danger" size="small" effect="plain">{{ row.bonus }}</el-tag>
              <span v-else style="color:#ccc">0</span>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="100">
            <template #default="{ row }">
              {{ getProductBonus(row) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Pagination -->
    <div style="display: flex; justify-content: center; margin-top: 12px;">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @current-change="onPageChange" @size-change="onSizeChange" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useHvobWatchlist } from './useHvobWatchlist'

const {
  list, loading, page, pageSize, total,
  filters, onPageChange, onSizeChange, refresh,
  getProductLabel, getProductBonus,
} = useHvobWatchlist()
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-item {
  width: 180px;
}
.trading-page {
  padding: 16px;
}
.section-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
</style>
