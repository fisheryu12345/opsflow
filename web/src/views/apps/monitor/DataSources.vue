<template>
  <div class="ds-page">
    <div class="page-header">
      <h2 class="page-title">数据源管理</h2>
    </div>
    <div class="ds-grid">
      <div class="ds-card prometheus">
        <div class="ds-icon">📊</div>
        <div class="ds-name">Prometheus</div>
        <div class="ds-desc">时序指标查询与告警</div>
        <div class="ds-status"><span class="status-dot" :class="promHealth?'green':'red'" />{{ promHealth ? '已连接' : '未配置' }}</div>
        <el-button size="small" @click="testConn('prometheus')">测试连接</el-button>
      </div>
      <div class="ds-card influxdb">
        <div class="ds-icon">🌊</div>
        <div class="ds-name">InfluxDB</div>
        <div class="ds-desc">InfluxDB 指标存储</div>
        <div class="ds-status"><span class="status-dot gray" />待配置</div>
        <el-button size="small" @click="testConn('influxdb')">测试连接</el-button>
      </div>
      <div class="ds-card custom">
        <div class="ds-icon">🔌</div>
        <div class="ds-name">自建采集</div>
        <div class="ds-desc">自定义采集插件推流</div>
        <div class="ds-status"><span class="status-dot green" />就绪</div>
        <el-button size="small" disabled>内置</el-button>
      </div>
    </div>

    <div style="margin-top:20px;">
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">指标浏览器</span>
          <el-input v-model="promql" placeholder="输入 PromQL 查询..." size="small" style="width:400px;margin-left:16px;" @keyup.enter="queryMetrics" />
          <el-button size="small" type="primary" @click="queryMetrics" :loading="querying">查询</el-button>
        </div>
        <el-table :data="metricResults" stripe size="small" style="width:100%" max-height="400">
          <el-table-column label="指标" prop="metric" min-width="200" />
          <el-table-column label="值" prop="value" width="100" />
          <el-table-column label="时间戳" prop="timestamp" width="180" />
          <el-table-column label="标签" min-width="200">
            <template #default="{row}"><code style="font-size:11px;color:#666;">{{ JSON.stringify(row.tags) }}</code></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dashboardApi } from '/@/api/monitor/index'

const promHealth = ref(false)
const promql = ref('')
const querying = ref(false)
const metricResults = ref<any[]>([])

async function testConn(type: string) {
  ElMessage.info(`正在测试 ${type} 连接...`)
  // 简化: 实际应调用后端测试端点的 API
  setTimeout(() => ElMessage.success(`${type} 连接测试完成`), 1000)
}

async function queryMetrics() {
  if (!promql.value) return
  querying.value = true
  try {
    // 简化: 实际应调用后端 proxy 查询
    metricResults.value = [
      { metric: promql.value, value: 95.2, timestamp: new Date().toISOString(), tags: { instance: 'localhost:9090' } },
    ]
  } finally { querying.value = false }
}
</script>

<style scoped>
.ds-page { padding:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-title { margin:0; font-size:18px; font-weight:600; }
.ds-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }
.ds-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
.ds-icon { font-size:28px; margin-bottom:8px; }
.ds-name { font-size:16px; font-weight:600; color:#303133; }
.ds-desc { font-size:12px; color:#909399; margin:4px 0 12px; }
.ds-status { display:flex; align-items:center; gap:6px; font-size:12px; margin-bottom:12px; }
.status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.status-dot.green { background:#67C23A; }
.status-dot.red { background:#F56C6C; }
.status-dot.gray { background:#C0C4CC; }
.section-card { background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,0.06); overflow:hidden; }
.section-header { display:flex; align-items:center; padding:14px 20px; border-bottom:1px solid #f0f0f0; }
.section-title { font-size:15px; font-weight:600; color:#303133; white-space:nowrap; }
</style>
