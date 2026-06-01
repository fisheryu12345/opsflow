<template>
  <div class="ss-page">
    <!-- Hero Section -->
    <div class="ss-hero">
      <div class="ss-hero-bg" />
      <div class="ss-hero-inner">
        <div class="ss-hero-left">
          <h1 class="ss-hero-title">Sessions</h1>
          <p class="ss-hero-subtitle">OpsAgent conversation history</p>
        </div>
        <div class="ss-hero-center">
          <el-input v-model="filters.search" placeholder="Search sessions..." clearable size="default"
            class="ss-search-input" @keyup.enter="refresh" @clear="refresh">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="ss-hero-stats">
          <div class="ss-stat-item"><span class="ss-stat-value">{{ total }}</span><span class="ss-stat-label">Total</span></div>
          <div class="ss-stat-divider" />
          <div class="ss-stat-item"><span class="ss-stat-value">{{ activeCount }}</span><span class="ss-stat-label">Active</span></div>
          <div class="ss-stat-divider" />
          <div class="ss-stat-item"><span class="ss-stat-value">{{ doneCount }}</span><span class="ss-stat-label">Done</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="ss-body">
      <!-- Filter bar -->
      <div class="ss-filter-bar">
        <div class="ss-filter-tabs">
          <div class="ss-tab" :class="{ active: filterStatus === '' }" @click="filterStatus = ''; refresh()">
            <span class="ss-tab-dot" style="background:#409EFF" />All
          </div>
          <div class="ss-tab" :class="{ active: filterStatus === 'active' }" @click="filterStatus = 'active'; refresh()">
            <span class="ss-tab-dot" style="background:#E6A23C" />Active
          </div>
          <div class="ss-tab" :class="{ active: filterStatus === 'completed' }" @click="filterStatus = 'completed'; refresh()">
            <span class="ss-tab-dot" style="background:#67C23A" />Completed
          </div>
          <div class="ss-tab" :class="{ active: filterStatus === 'aborted' }" @click="filterStatus = 'aborted'; refresh()">
            <span class="ss-tab-dot" style="background:#F56C6C" />Aborted
          </div>
        </div>
        <div class="ss-filter-actions">
          <el-select v-model="filterMode" placeholder="Mode" clearable size="small" style="width:120px" @change="refresh">
            <el-option label="REPL" value="repl" />
            <el-option label="Oneshot" value="oneshot" />
          </el-select>
          <el-button :icon="Refresh" @click="refresh" :loading="loading" text size="small">Refresh</el-button>
        </div>
      </div>

      <!-- Table card -->
      <div class="ss-table-card">
        <el-table :data="displayList" v-loading="loading" stripe style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column label="#" width="50">
            <template #default="{ $index }">{{ page * pageSize - pageSize + $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="Session ID" min-width="200">
            <template #default="{ row }">
              <router-link :to="`/ops/console?session=${row.id}`" class="ss-session-link">{{ row.session_id }}</router-link>
            </template>
          </el-table-column>
          <el-table-column label="Input" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">{{ row.user_input || row.summary?.slice(0,80) || '-' }}</template>
          </el-table-column>
          <el-table-column prop="operator" label="Operator" width="100" align="center" />
          <el-table-column label="Status" width="100" align="center">
            <template #default="{ row }">
              <span class="ss-status-badge" :class="'sts-' + statusKey(row)">{{ statusLabel(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="audit_count" label="Ops" width="60" align="center" />
          <el-table-column prop="started_at" label="Started" min-width="160" sortable />
        </el-table>
        <div class="ss-pagination" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" background
            @current-change="onPageChange" @size-change="onSizeChange" small />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { useSessions } from './useSessions'

const { list, loading, page, pageSize, total, filters, onPageChange, onSizeChange, refresh: baseRefresh } = useSessions()

const filterStatus = ref('')
const filterMode = ref('')

const activeCount = computed(() => displayList.value.filter(s => statusKey(s) === 'active').length)
const doneCount = computed(() => displayList.value.filter(s => statusKey(s) === 'completed').length)
const emptyText = computed(() => loading.value ? 'Loading...' : 'No sessions found')

const displayList = computed(() => {
  let items = list.value
  if (filterStatus.value) items = items.filter(s => statusKey(s) === filterStatus.value)
  if (filterMode.value) items = items.filter(s => s.mode === filterMode.value)
  return items
})

function statusKey(row: any): string {
  return row.task_status || row.status || ''
}

function statusLabel(row: any): string {
  const m: Record<string, string> = { completed: 'Completed', failed: 'Failed', running: 'Running', pending: 'Pending', active: 'Active', aborted: 'Aborted' }
  return m[statusKey(row)] || statusKey(row) || '-'
}

function refresh() {
  if (filterMode.value) filters.mode = filterMode.value
  else filters.mode = ''
  baseRefresh()
}

onMounted(() => { filters.status = ''; refresh() })
</script>

<style scoped>
.ss-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.ss-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.ss-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.ss-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.ss-hero-left { flex: 0 0 auto; }
.ss-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.ss-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.ss-hero-center { flex: 1 1 auto; min-width: 0; }
.ss-search-input { width: 100%; max-width: 320px; }
.ss-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.ss-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.ss-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.ss-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.ss-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.ss-stat-item { text-align: center; padding: 0 14px; }
.ss-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.ss-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.ss-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.ss-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.ss-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.ss-filter-tabs { display: flex; gap: 4px; }
.ss-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.ss-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.ss-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.ss-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.ss-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table card ===== */
.ss-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.ss-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.ss-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.ss-session-link { color: #409eff; text-decoration: none; font-family: 'Courier New', monospace; font-size: 12px; }
.ss-session-link:hover { text-decoration: underline; }
.ss-status-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; text-transform: uppercase; }
.sts-active { background: #fdf6ec; color: #E6A23C; }
.sts-completed { background: #f0f9eb; color: #67C23A; }
.sts-running { background: #e6f7ff; color: #1890ff; }
.sts-failed { background: #fef0f0; color: #F56C6C; }
.sts-pending { background: #f5f5f5; color: #909399; }
.sts-aborted { background: #fbe9e7; color: #D32F2F; }
.ss-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }
</style>
