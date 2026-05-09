<template>
  <div class="trading-page">
    <PageHeader title="交易日志" />

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-select v-model="filters.log_level" placeholder="日志级别" clearable class="filter-item" @change="refresh">
        <el-option label="DEBUG" value="DEBUG" />
        <el-option label="INFO" value="INFO" />
        <el-option label="SUCCESS" value="SUCCESS" />
        <el-option label="WARNING" value="WARNING" />
        <el-option label="ERROR" value="ERROR" />
        <el-option label="CRITICAL" value="CRITICAL" />
      </el-select>
      <el-input v-model="filters.function_name" placeholder="函数名称" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-input v-model="filters.symbol" placeholder="合约代码" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        class="filter-item-wide"
        @change="onDateChange"
      />
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="expand" width="40">
            <template #default="{ row }">
              <div style="padding: 12px; background: #fafafa;">
                <pre style="margin: 0; white-space: pre-wrap; font-size: 13px;">{{ row.log_message }}</pre>
              </div>
            </template>
          </el-table-column>
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="timestamp" label="时间" min-width="160" sortable />
          <el-table-column label="级别" width="90" align="center">
            <template #default="{ row }">
              <StatusTag type="level" :value="row.log_level" />
            </template>
          </el-table-column>
          <el-table-column prop="function_name" label="函数名称" min-width="160" sortable />
          <el-table-column prop="symbol" label="合约代码" min-width="130" sortable />
          <el-table-column prop="log_message" label="日志内容" min-width="300">
            <template #default="{ row }">
              <span class="log-truncate">{{ row.log_message }}</span>
            </template>
          </el-table-column>
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
import PageHeader from '/@/views/apps/components/PageHeader.vue'
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import { useTradeLog } from './useTradeLog'

const {
  list, loading, page, pageSize, total,
  filters, onPageChange, onSizeChange, refresh,
} = useTradeLog()

const dateRange = ref<[Date, Date] | null>(null)

function onDateChange(val: [Date, Date] | null) {
  if (val) {
    filters.timestamp__gte = formatDate(val[0])
    filters.timestamp__lte = formatDate(val[1])
  } else {
    filters.timestamp__gte = ''
    filters.timestamp__lte = ''
  }
  refresh()
}

function formatDate(d: Date) {
  return d.toISOString().split('T')[0]
}
</script>

<style scoped>
.log-truncate {
  display: inline-block;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
