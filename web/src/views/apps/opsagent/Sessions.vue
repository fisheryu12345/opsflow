<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-select v-model="filters.status" placeholder="状态" clearable class="filter-item" @change="refresh">
        <el-option label="进行中" value="active" />
        <el-option label="已完成" value="completed" />
        <el-option label="已中止" value="aborted" />
      </el-select>
      <el-select v-model="filters.mode" placeholder="模式" clearable class="filter-item" @change="refresh">
        <el-option label="REPL" value="repl" />
        <el-option label="单次执行" value="oneshot" />
      </el-select>
      <el-input v-model="filters.search" placeholder="搜索..." clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="session_id" label="会话ID" min-width="180">
            <template #default="{ row }">
              <router-link :to="`/ops/console?session=${row.id}`" class="session-link">
                {{ row.session_id }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="输入内容" min-width="250">
            <template #default="{ row }">
              <span class="text-truncate">{{ row.user_input || row.summary?.slice(0, 60) || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="operator" label="操作人" width="100" align="center" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row)" size="small">
                {{ statusLabel(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="audit_count" label="操作数" width="80" align="center" />
          <el-table-column prop="started_at" label="开始时间" min-width="160" sortable />
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
import { useSessions } from './useSessions'

const { list, loading, page, pageSize, total, filters, onPageChange, onSizeChange, refresh } = useSessions()

function statusType(row: any) {
  if (row.task_status === 'completed' || row.status === 'completed') return 'success'
  if (row.task_status === 'failed' || row.status === 'aborted') return 'danger'
  if (row.task_status === 'running' || row.status === 'active') return 'warning'
  return 'info'
}

function statusLabel(row: any) {
  if (row.task_status === 'completed') return '已完成'
  if (row.task_status === 'failed') return '失败'
  if (row.task_status === 'running') return '执行中'
  if (row.task_status === 'pending') return '等待中'
  if (row.status === 'completed') return '已完成'
  if (row.status === 'aborted') return '已中止'
  if (row.status === 'active') return '进行中'
  return row.status || '-'
}
</script>

<style scoped>
.session-link {
  color: #409eff;
  text-decoration: none;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
.session-link:hover { text-decoration: underline; }
.text-truncate {
  display: inline-block;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
