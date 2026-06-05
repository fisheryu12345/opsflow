<template>
  <div class="collect-page">
    <div class="page-header">
      <h2 class="page-title">采集器管理</h2>
      <el-button type="primary" size="small" @click="showDialog=true">新建采集</el-button>
    </div>
    <div class="page-body">
      <el-table :data="items" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="数据源" width="120">
          <template #default="{row}">{{ row.data_source_label }}</template>
        </el-table-column>
        <el-table-column prop="interval" label="周期(秒)" width="90" />
        <el-table-column label="启用" width="80">
          <template #default="{row}"><el-switch :model-value="row.is_enabled" size="small" @click="toggleItem(row)" /></template>
        </el-table-column>
        <el-table-column prop="create_user" label="创建人" width="100" />
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" text @click="testItem(row)">测试</el-button>
            <el-button size="small" text type="danger" @click="deleteItem(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDialog" title="新建采集配置" width="500px">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="form.data_source_label" style="width:100%">
            <el-option label="Prometheus" value="prometheus" />
            <el-option label="InfluxDB" value="influxdb" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="采集周期">
          <el-input-number v-model="form.interval" :min="10" :max="3600" /> 秒
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
import { collectConfigApi } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref<any[]>([])
const showDialog = ref(false)
const form = reactive({ name: '', data_source_label: 'prometheus', interval: 60 })

async function load() { loading.value = true; try { const r = await collectConfigApi.list(); items.value = r.data || [] } finally { loading.value = false } }
async function toggleItem(row: any) { await collectConfigApi.toggle(row.id); ElMessage.success('操作成功'); load() }
async function deleteItem(row: any) { await collectConfigApi.delete(row.id); ElMessage.success('已删除'); load() }
async function testItem(row: any) { await collectConfigApi.test(row.id); ElMessage.success('测试连接完成') }
async function saveItem() { await collectConfigApi.create({ ...form }); ElMessage.success('创建成功'); showDialog.value = false; load() }
onMounted(() => load())
</script>

<style scoped>
.collect-page { padding:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-title { margin:0; font-size:18px; font-weight:600; }
.page-body { background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
</style>
