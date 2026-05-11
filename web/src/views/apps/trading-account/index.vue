<template>
  <div class="trading-page">
    <div class="section-card">
      <div class="section-body" style="padding: 0;">
        <el-table :data="list" border stripe v-loading="loading" class="trading-table" style="width: 100%">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="name" label="账户名称" min-width="150" />
          <el-table-column prop="strategy_name" label="策略名称" min-width="150" />
          <el-table-column prop="user_email" label="邮箱" min-width="180" />
          <el-table-column prop="user_mobile" label="手机号" min-width="130" />
          <el-table-column prop="initial_balance" label="初始资金" min-width="120" align="right">
            <template #default="{ row }">
              {{ row.initial_balance ? Number(row.initial_balance).toLocaleString() : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="current_equity" label="当前权益" min-width="120" align="right">
            <template #default="{ row }">
              {{ row.current_equity ? Number(row.current_equity).toLocaleString() : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_active"
                :loading="togglingId === row.id"
                @change="(val: boolean) => toggleActive(row, val)"
              />
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无交易账户" />
          </template>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAccountList, patchAccount } from '/@/api/stock/account'

interface AccountItem {
  id: number
  name: string
  strategy_name: string
  user_email: string
  user_mobile: string
  initial_balance: string
  current_equity: string
  is_active: boolean
}

const list = ref<AccountItem[]>([])
const loading = ref(false)
const togglingId = ref<number | null>(null)

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getAccountList()
    if (res.code === 2000) {
      list.value = res.data || []
    }
  } catch (e) {
    console.error('获取账户列表失败', e)
  } finally {
    loading.value = false
  }
}

async function toggleActive(row: AccountItem, val: boolean) {
  togglingId.value = row.id
  const prev = row.is_active
  row.is_active = val  // 乐观更新：立即切换
  try {
    const res: any = await patchAccount(row.id, { is_active: val })
    if (res.code === 2000) {
      ElMessage.success(val ? '已激活' : '已停用')
    } else {
      row.is_active = prev  // 失败回退
    }
  } catch (e) {
    row.is_active = prev  // 失败回退
    console.error('更新账户状态失败', e)
    ElMessage.error('操作失败')
  } finally {
    togglingId.value = null
  }
}

onMounted(fetchData)
</script>
