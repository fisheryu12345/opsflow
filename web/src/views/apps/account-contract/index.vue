<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-tag type="success" effect="dark" size="large" class="active-count-tag">
        已激活 {{ activeCount }} / {{ list.length }}
      </el-tag>
      <el-checkbox v-model="showActiveOnly" border size="large" style="margin-right: 12px;">
        仅显示已激活
      </el-checkbox>
      <el-select v-model="filterExchange" placeholder="交易所" clearable class="filter-item" @clear="fetchData">
        <el-option v-for="(label, key) in exchangeLabels" :key="key" :label="label" :value="key" />
      </el-select>
      <el-input v-model="filterText" placeholder="搜索品种代码/名称" clearable class="filter-item" style="width: 240px" />
      <el-button
        v-if="selectedCount"
        type="success"
        :loading="batchLoading"
        @click="handleBatchToggle(true)"
      >
        批量激活 ({{ selectedCount }})
      </el-button>
      <el-button
        v-if="selectedCount"
        type="warning"
        :loading="batchLoading"
        @click="handleBatchToggle(false)"
      >
        批量停用 ({{ selectedCount }})
      </el-button>
    </div>

    <!-- Contract Grid -->
    <div class="section-card">
      <div class="section-body">
        <el-table
          :data="filteredList"
          border
          stripe
          v-loading="loading"
          class="trading-table"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="40" align="center" />
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column label="交易所" width="90" sortable prop="exchange">
            <template #default="{ row }">
              {{ exchangeLabels[row.exchange] || row.exchange }}
            </template>
          </el-table-column>
          <el-table-column prop="product_code" label="品种代码" width="100" sortable />
          <el-table-column prop="symbol" label="主力合约" min-width="150" />
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                :loading="toggling"
                @click="handleToggle(row.product_code)"
              />
            </template>
          </el-table-column>
        </el-table>

        <!-- Empty State -->
        <el-empty v-if="!loading && filteredList.length === 0" :description="initError || '暂无数据'" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAccountContract } from './useAccountContract'

const {
  loading,
  toggling,
  batchLoading,
  list,
  filteredList,
  filterText,
  filterExchange,
  showActiveOnly,
  activeCount,
  selectedCount,
  initError,
  exchangeLabels,
  fetchData,
  handleToggle,
  handleBatchToggle,
  handleSelectionChange,
} = useAccountContract()
</script>

<style scoped>
.filter-bar {
  margin-bottom: 16px;
}
.active-count-tag {
  margin-right: 12px;
  flex-shrink: 0;
}
</style>
