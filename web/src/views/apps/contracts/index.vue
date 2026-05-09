<template>
  <div class="trading-page">
    <PageHeader title="合约管理">
      <template #actions>
        <el-button type="info" @click="handleShowStats">
          <el-icon><DataAnalysis /></el-icon>
          统计信息
        </el-button>
        <el-button type="primary" @click="handleAdd">新增合约</el-button>
      </template>
    </PageHeader>

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
      <el-select v-model="filters.is_active" placeholder="状态" clearable class="filter-item" @change="refresh">
        <el-option label="启用" :value="true" />
        <el-option label="停用" :value="false" />
      </el-select>
      <el-button type="primary" @click="refresh">查询</el-button>
      <el-button v-if="selectedIds.length" type="success" @click="handleBatchActive">批量激活</el-button>
      <el-button v-if="selectedIds.length" type="warning" @click="handleBatchDeactive">批量停用</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table
          :data="list" border stripe v-loading="loading"
          class="trading-table" style="width: 100%"
          @selection-change="(val: any[]) => selectedIds = val.map(v => v.id)"
        >
          <el-table-column type="selection" width="40" align="center" />
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
          <el-table-column label="交易状态" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @click="handleToggleActive(row)"
                style="--el-switch-on-color: var(--el-color-primary);"
              />
            </template>
          </el-table-column>
          <el-table-column label="允许开仓" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.allow_open ? 'success' : 'warning'" size="small" effect="plain">
                {{ row.allow_open ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" text @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" text @click="handleDelete(row.id)">删除</el-button>
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

    <!-- Dialogs -->
    <ContractFormDialog v-model="formVisible" :record="editingRecord" @saved="handleSave" />
    <ContractStatsDialog v-model="statsVisible" :stats="stats" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'
import PageHeader from '/@/views/apps/components/PageHeader.vue'
import StatusTag from '/@/views/apps/components/StatusTag.vue'
import { useContract } from './useContract'
import ContractFormDialog from './ContractFormDialog.vue'
import ContractStatsDialog from './ContractStatsDialog.vue'
import type { ContractRecord } from '/@/types/trading'

const {
  list, loading, page, pageSize, total,
  filters, selectedIds, stats,
  onPageChange, onSizeChange, refresh,
  toggleActive, batchActivate, batchDeactivate,
  saveContract, deleteContract, fetchStats,
} = useContract()

const formVisible = ref(false)
const statsVisible = ref(false)
const editingRecord = ref<ContractRecord | null>(null)

const exchangeMap: Record<string, string> = {
  SHFE: '上期所', DCE: '大商所', CZCE: '郑商所',
  CFFEX: '中金所', GFEX: '广期所',
}

function exchangeLabel(code: string) {
  return exchangeMap[code] || code
}

function handleAdd() {
  editingRecord.value = null
  formVisible.value = true
}

function handleEdit(row: ContractRecord) {
  editingRecord.value = row
  formVisible.value = true
}

function handleSave() {
  formVisible.value = false
}

async function handleToggleActive(row: ContractRecord) {
  await toggleActive(row)
  ElMessage.success(row.is_active ? '已停用' : '已激活')
}

async function handleBatchActive() {
  const ok = await ElMessageBox.confirm('确认批量激活所选合约？', '提示', { type: 'info' })
    .then(() => true).catch(() => false)
  if (ok) {
    const success = await batchActivate()
    if (success) ElMessage.success('批量激活成功')
  }
}

async function handleBatchDeactive() {
  const ok = await ElMessageBox.confirm('确认批量停用所选合约？', '提示', { type: 'warning' })
    .then(() => true).catch(() => false)
  if (ok) {
    const success = await batchDeactivate()
    if (success) ElMessage.success('批量停用成功')
  }
}

async function handleDelete(id: number) {
  const ok = await ElMessageBox.confirm('确认删除此合约？', '提示', { type: 'warning' })
    .then(() => true).catch(() => false)
  if (ok) {
    const success = await deleteContract(id)
    if (success) ElMessage.success('已删除')
  }
}

async function handleShowStats() {
  await fetchStats()
  statsVisible.value = true
}
</script>
