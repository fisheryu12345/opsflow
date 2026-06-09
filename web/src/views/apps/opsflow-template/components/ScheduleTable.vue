<template>
  <el-table :data="list" v-loading="loading" :empty-text="$t('message.common.noData')" stripe style="width: 100%" size="small" :header-cell-style="{background:'#fafafa', color:'#606266', fontWeight:600, fontSize:'12px'}">
    <el-table-column v-if="showTemplate" prop="template_name" :label="$t('message.execution.colTemplate')" min-width="140" show-overflow-tooltip />
    <el-table-column prop="name" :label="$t('message.common.name')" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">
        <div class="cell-name">
          <span class="name-text">{{ row.name }}</span>
          <span class="name-desc" v-if="row.description">{{ row.description }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.schedule.triggerType')" width="100">
      <template #default="{ row }">
        <el-tag v-if="row.schedule_type === 'one_time'" type="warning" size="small" effect="plain" class="type-tag">
          <el-icon size="12" style="margin-right:3px"><Clock /></el-icon> {{ $t('message.schedule.onceTrigger') }}
        </el-tag>
        <el-tag v-else type="primary" size="small" effect="plain" class="type-tag">
          <el-icon size="12" style="margin-right:3px"><Refresh /></el-icon> {{ $t('message.schedule.cronTrigger') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.schedule.triggerType')" min-width="180">
      <template #default="{ row }">
        <template v-if="row.schedule_type === 'one_time'">
          <div class="trigger-cell">
            <el-icon size="12" color="#909399"><Clock /></el-icon>
            <span>{{ row.scheduled_at ? formatTime(row.scheduled_at) : '-' }}</span>
          </div>
        </template>
        <template v-else>
          <div class="trigger-cell cron-cell">
            <code class="cron-expr">{{ row.cron_expr }}</code>
            <span v-if="row.cron_description" class="cron-desc">{{ row.cron_description }}</span>
          </div>
        </template>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.execution.status')" width="100">
      <template #default="{ row }">
        <div class="status-badge" :class="row.status">
          <span class="status-dot" />
          <span>{{ statusLabel(row.status) }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.schedule.lastRun')" width="155">
      <template #default="{ row }">
        <span class="time-cell">{{ row.last_run_at ? formatTime(row.last_run_at) : '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.schedule.nextRun')" width="155">
      <template #default="{ row }">
        <span class="time-cell">{{ row.next_run_at ? formatTime(row.next_run_at) : '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="total_run_count" :label="$t('message.schedule.runCount')" width="70" align="center">
      <template #default="{ row }">
        <el-tag :type="row.total_run_count > 0 ? 'primary' : 'info'" size="small" effect="plain" class="runs-tag">
          {{ row.total_run_count || 0 }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('message.execution.colActions')" width="240" fixed="right">
      <template #default="{ row }">
        <div class="action-btns">
          <el-tooltip :content="$t('message.common.edit')" placement="top">
            <el-button size="small" text type="primary" @click="emit('edit', row)" :icon="Edit" />
          </el-tooltip>
          <el-tooltip v-if="row.status === 'active'" :content="$t('message.execution.pause')" placement="top">
            <el-button size="small" text type="warning" @click="emit('pause', row)" :icon="VideoPause" />
          </el-tooltip>
          <el-tooltip v-if="row.status === 'paused'" :content="$t('message.execution.resume')" placement="top">
            <el-button size="small" text type="success" @click="emit('resume', row)" :icon="VideoPlay" />
          </el-tooltip>
          <el-tooltip :content="$t('message.schedule.schTriggerNow')" placement="top">
            <el-button size="small" text type="primary" @click="emit('trigger', row)" :icon="Lightning" />
          </el-tooltip>
          <el-tooltip :content="$t('message.common.delete')" placement="top">
            <el-button size="small" text type="danger" @click="emit('delete', row)" :icon="Delete" />
          </el-tooltip>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Clock, Refresh, Edit, VideoPause, VideoPlay, Lightning, Delete } from '@element-plus/icons-vue'

const { t } = useI18n()

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

function statusLabel(status: string) {
  switch (status) {
    case 'active': return t('message.schedule.enabled')
    case 'paused': return t('message.schedule.disabled')
    case 'completed': return t('message.execution.statCompleted')
    case 'expired': return t('message.schedule.schExpired')
    default: return status
  }
}
</script>

<style scoped>
.cell-name { display: flex; flex-direction: column; gap: 2px; }
.name-text { font-size: 13px; font-weight: 600; color: #303133; }
.name-desc { font-size: 11px; color: #909399; }

.type-tag { font-weight: 500; }

.trigger-cell { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.cron-cell { flex-direction: column; align-items: flex-start; gap: 2px; }
.cron-expr { font-size: 12px; background: #f5f7fa; padding: 2px 6px; border-radius: 4px; color: #606266; font-family: monospace; }
.cron-desc { font-size: 11px; color: #909399; }

.status-badge {
  display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%; display: inline-block;
}
.status-badge.active .status-dot { background: #67C23A; }
.status-badge.active { color: #67C23A; }
.status-badge.paused .status-dot { background: #E6A23C; }
.status-badge.paused { color: #E6A23C; }
.status-badge.completed .status-dot { background: #909399; }
.status-badge.completed { color: #909399; }
.status-badge.expired .status-dot { background: #F56C6C; }
.status-badge.expired { color: #F56C6C; }

.time-cell { font-size: 12px; color: #606266; font-family: monospace; }
.runs-tag { font-weight: 600; min-width: 28px; }

.action-btns {
  display: flex; align-items: center; gap: 2px;
}
.action-btns .el-button { padding: 5px; border-radius: 6px; }
.action-btns .el-button:hover { background: #f0f0f0; }
</style>
