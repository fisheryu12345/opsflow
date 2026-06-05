<template>
  <div class="action-page">
    <div class="page-header">
      <h2 class="page-title">动作插件管理</h2>
    </div>
    <div class="plugin-grid">
      <div v-for="p in plugins" :key="p.id" class="plugin-card">
        <div class="plugin-icon" :class="'type-'+p.plugin_type">
          <el-icon><template v-if="p.plugin_type==='notice'"><Bell /></template><template v-else-if="p.plugin_type==='webhook'"><Link /></template><template v-else><Setting /></template></el-icon>
        </div>
        <div class="plugin-info">
          <div class="plugin-name">{{ p.name }}</div>
          <div class="plugin-desc">{{ p.description || p.plugin_type }}</div>
        </div>
        <div class="plugin-meta">
          <el-tag size="small" :type="p.is_builtin?'success':'warning'">{{ p.is_builtin ? '内置' : '自定义' }}</el-tag>
          <el-button size="small" text @click="testPlugin(p)">测试</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { actionPluginApi } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'
import { Bell, Link, Setting } from '@element-plus/icons-vue'

const plugins = ref<any[]>([])
async function load() { const r = await actionPluginApi.list(); plugins.value = r.data || [] }
async function testPlugin(row: any) { await actionPluginApi.test(row.id); ElMessage.success(`插件 "${row.name}" 测试完成`) }
onMounted(() => load())
</script>

<style scoped>
.action-page { padding:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-title { margin:0; font-size:18px; font-weight:600; }
.plugin-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:12px; }
.plugin-card { display:flex; align-items:center; gap:14px; background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
.plugin-icon { width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px; }
.plugin-icon.type-notice { background:#fef0f0;color:#F56C6C; }
.plugin-icon.type-webhook { background:#f0f9eb;color:#67C23A; }
.plugin-icon.type-opsflow, .plugin-icon.type-awx { background:#fdf6ec;color:#E6A23C; }
.plugin-icon.type-itsm { background:#ecf5ff;color:#409EFF; }
.plugin-info { flex:1; min-width:0; }
.plugin-name { font-size:14px;font-weight:600;color:#303133; }
.plugin-desc { font-size:12px;color:#909399;margin-top:2px; }
.plugin-meta { display:flex;align-items:center;gap:8px;flex-shrink:0; }
</style>
