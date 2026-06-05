<template>
  <div class="shield-page">
    <div class="page-header">
      <h2 class="page-title">告警屏蔽 / 静默管理</h2>
      <el-button type="primary" size="small" @click="showDialog=true">新建屏蔽计划</el-button>
    </div>
    <div class="page-body">
      <el-table :data="items" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="name" label="计划名称" min-width="160" />
        <el-table-column label="类型" width="100">
          <template #default="{row}">{{ {strategy:'按策略',target:'按目标',tag:'按标签',global:'全局'}[row.shield_type] || row.shield_type }}</template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{row}"><el-switch :model-value="row.is_enabled" size="small" @click="toggleItem(row)" /></template>
        </el-table-column>
        <el-table-column prop="create_user" label="创建人" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button size="small" text type="danger" @click="deleteItem(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDialog" title="新建屏蔽计划" width="500px">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="屏蔽类型">
          <el-select v-model="form.shield_type" style="width:100%">
            <el-option label="按策略" value="strategy" />
            <el-option label="按目标" value="target" />
            <el-option label="按标签" value="tag" />
            <el-option label="全局" value="global" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { shieldPlanApi } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref<any[]>([])
const showDialog = ref(false)
const form = reactive({ name: '', shield_type: 'strategy' })

async function load() { loading.value = true; try { const r = await shieldPlanApi.list(); items.value = r.data || [] } finally { loading.value = false } }
async function toggleItem(row: any) { await shieldPlanApi.toggle(row.id); ElMessage.success('操作成功'); load() }
async function deleteItem(row: any) { await shieldPlanApi.delete(row.id); ElMessage.success('已删除'); load() }
async function saveItem() { await shieldPlanApi.create({ ...form }); ElMessage.success('创建成功'); showDialog.value = false; load() }
onMounted(() => load())
</script>

<style scoped>
.shield-page { padding:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-title { margin:0; font-size:18px; font-weight:600; }
.page-body { background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
</style>
