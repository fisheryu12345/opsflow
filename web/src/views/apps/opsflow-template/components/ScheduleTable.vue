<template>
  <el-table :data="list" v-loading="loading" stripe style="width: 100%">
    <el-table-column v-if="showTemplate" prop="template_name" label="所属模板" min-width="140" />
    <el-table-column prop="name" label="名称" min-width="140" />
    <el-table-column label="类型" width="90">
      <template #default="{ row }">
        <el-tag v-if="row.schedule_type === 'one_time'" type="warning" size="small">一次性</el-tag>
        <el-tag v-else type="primary" size="small">周期性</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="触发信息" min-width="170">
      <template #default="{ row }">
        <template v-if="row.schedule_type === 'one_time'">
          <span>{{ row.scheduled_at ? formatTime(row.scheduled_at) : '-' }}</span>
        </template>
        <template v-else>
          <div><code style="font-size: 12px">{{ row.cron_expr }}</code></div>
          <div v-if="row.cron_description" style="font-size: 12px; color: #909399">{{ row.cron_description }}</div>
        </template>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="90">
      <template #default="{ row }">
        <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="上次执行" width="160">
      <template #default="{ row }">{{ row.last_run_at ? formatTime(row.last_run_at) : '-' }}</template>
    </el-table-column>
    <el-table-column label="下次执行" width="160">
      <template #default="{ row }">{{ row.next_run_at ? formatTime(row.next_run_at) : '-' }}</template>
    </el-table-column>
    <el-table-column prop="total_run_count" label="次数" width="60" align="center" />
    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" size="small" @click="emit('edit', row)">编辑</el-button>
        <el-button
          v-if="row.status === 'active'"
          link
          type="warning"
          size="small"
          @click="emit('pause', row)"
        >
          暂停
        </el-button>
        <el-button
          v-if="row.status === 'paused'"
          link
          type="success"
          size="small"
          @click="emit('resume', row)"
        >
          恢复
        </el-button>
        <el-button link type="primary" size="small" @click="emit('trigger', row)">触发</el-button>
        <el-button link type="danger" size="small" @click="emit('delete', row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
defineProps<{
  list: any[]
  loading: boolean
  showTemplate?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', row: any): void
  (e: 'pause', row: any): void
  (e: 'resume', row: any): void
  (e: 'trigger', row: any): void
  (e: 'delete', row: any): void
}>()

function formatTime(dt: string) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

function statusType(status: string) {
  switch (status) {
    case 'active': return 'success'
    case 'paused': return 'warning'
    case 'completed': return 'info'
    case 'expired': return 'danger'
    default: return 'info'
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'active': return '运行中'
    case 'paused': return '已暂停'
    case 'completed': return '已完成'
    case 'expired': return '已过期'
    default: return status
  }
}
</script>
