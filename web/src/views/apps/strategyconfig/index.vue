<template>
  <div class="trading-page">
    <PageHeader title="策略配置">
      <template #actions>
        <el-button type="primary" @click="handleAdd">新建策略</el-button>
      </template>
    </PageHeader>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="配置名称" clearable class="filter-item" @clear="refresh" @keyup.enter="refresh" />
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Table -->
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="name" label="配置名称" min-width="150" sortable />
          <el-table-column prop="max_units" label="最大持仓单位" min-width="120" align="center" sortable />
          <el-table-column prop="entry_units" label="建仓单位" min-width="100" align="center" sortable />
          <el-table-column prop="risk_per_unit" label="风险金额" min-width="120" align="right" sortable>
            <template #default="{ row }">
              <ValueCell :value="row.risk_per_unit" type="currency" :color-by-sign="false" />
            </template>
          </el-table-column>
          <el-table-column prop="atr_period" label="ATR周期" min-width="90" align="center" sortable />
          <el-table-column prop="entry_period" label="入场周期" min-width="90" align="center" sortable />
          <el-table-column prop="tqapi_account" label="TqSDK账号" min-width="150" />
          <el-table-column label="交易品种数" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ (row.product_codes || '').split(',').filter(Boolean).length }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" text @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" text @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无策略配置" />
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

    <!-- Dialog -->
    <StrategyFormDialog v-model="formVisible" :record="editingRecord" @saved="handleSave" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '/@/views/apps/components/PageHeader.vue'
import ValueCell from '/@/views/apps/components/ValueCell.vue'
import { useStrategyConfig } from './useStrategyConfig'
import StrategyFormDialog from './StrategyFormDialog.vue'
import type { StrategyConfigRecord } from '/@/types/trading'

const {
  list, loading, page, pageSize, total,
  search,
  onPageChange, onSizeChange, refresh,
  saveConfig, deleteConfig,
} = useStrategyConfig()

const formVisible = ref(false)
const editingRecord = ref<StrategyConfigRecord | null>(null)

function handleAdd() {
  editingRecord.value = null
  formVisible.value = true
}

function handleEdit(row: StrategyConfigRecord) {
  editingRecord.value = row
  formVisible.value = true
}

async function handleSave(form: any) {
  const id = editingRecord.value?.id || null
  const ok = await saveConfig(id, form)
  if (ok) {
    ElMessage.success(id ? '已更新' : '已创建')
    formVisible.value = false
  }
}

async function handleDelete(id: number) {
  const ok = await ElMessageBox.confirm('确认删除此策略配置？', '提示', { type: 'warning' })
    .then(() => true).catch(() => false)
  if (ok) {
    const success = await deleteConfig(id)
    if (success) ElMessage.success('已删除')
  }
}
</script>
