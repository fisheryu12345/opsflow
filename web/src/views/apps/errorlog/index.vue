<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="filters.function_name" placeholder="函数名称" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-input v-model="filters.error_message" placeholder="错误关键字" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
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
      <el-button type="danger" @click="handleClearAll">清除全部</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="expand" width="40">
            <template #default="{ row }">
              <div style="padding: 12px; background: #fff2f0; border-radius: 4px;">
                <pre style="margin: 0; white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #cf1322;">{{ row.error_message }}</pre>
              </div>
            </template>
          </el-table-column>
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="timestamp" label="时间" min-width="160" sortable />
          <el-table-column prop="function_name" label="函数名称" min-width="160" sortable />
          <el-table-column prop="error_message" label="错误信息" min-width="300">
            <template #default="{ row }">
              <span class="error-truncate">{{ row.error_message }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" size="small" text @click="handleDelete(row.id)">删除</el-button>
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
import { ElMessageBox, ElMessage } from 'element-plus'
import { useErrorLog } from './useErrorLog'

const {
  list, loading, page, pageSize, total,
  filters, onPageChange, onSizeChange, refresh, deleteLog,
} = useErrorLog()

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

function handleDelete(id: number) {
  ElMessageBox.confirm('确认删除此错误记录？', '提示', { type: 'warning' }).then(async () => {
    const ok = await deleteLog(id)
    if (ok) ElMessage.success('已删除')
  }).catch(() => {})
}

function handleClearAll() {
  ElMessageBox.confirm('确认清除全部错误日志？此操作不可恢复', '警告', { type: 'warning' }).then(async () => {
    // Delete all visible items one by one (simplified approach)
    for (const item of list.value) {
      await deleteLog(item.id)
    }
    ElMessage.success('已清除')
    refresh()
  }).catch(() => {})
}
</script>

<style scoped>
.error-truncate {
  display: inline-block;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #cf1322;
}
</style>
