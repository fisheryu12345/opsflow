<template>
  <div class="itsm-settings">
    <div class="itsm-settings-toolbar">
      <span class="itsm-settings-title">团队看板 — 负载分布</span>
    </div>
    <div class="td-stats" v-if="stats.length">
      <div v-for="s in stats" :key="s.group_id" class="td-group-card">
        <div class="td-group-header">{{ s.group_name }}</div>
        <div class="td-group-total">总待办: {{ s.total }}</div>
        <div class="td-member-list">
          <div v-for="m in s.members" :key="m.id" class="td-member-row">
            <span class="td-member-name">{{ m.name }}</span>
            <div class="td-bar-bg">
              <div class="td-bar-fill" :style="{ width: barWidth(m.count, s.total) + '%' }" />
            </div>
            <span class="td-member-count">{{ m.count }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="td-empty">暂无数据</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { skillGroupApi } from '/@/api/itsm/index'
import { request } from '/@/utils/service'

interface MemberStat { id: number; name: string; username: string; count: number }
interface GroupStat { group_id: number; group_name: string; total: number; members: MemberStat[] }
const stats = ref<GroupStat[]>([])

function barWidth(count: number, total: number) { return total > 0 ? Math.max(3, (count / total) * 100) : 0 }

async function loadStats() {
  try {
    const gRes = await skillGroupApi.list()
    const groups = ((gRes as any).results || (gRes as any).data || [])
    const results: GroupStat[] = []
    for (const g of groups) {
      const members = (g.members || []).map((m: any) => typeof m === 'object' ? m : { id: m, name: '', username: '' })
      results.push({
        group_id: g.id,
        group_name: g.name,
        total: members.length,
        members: members.map((m: any) => ({ id: m.id, name: m.name || m.username, username: m.username, count: 0 })),
      })
    }
    stats.value = results
  } catch { stats.value = [] }
}
onMounted(loadStats)
</script>

<style scoped>
.itsm-settings { padding: 4px 0; }
.td-stats { display: flex; flex-wrap: wrap; gap: 16px; }
.td-group-card { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; width: 320px; }
.td-group-header { font-weight: 600; font-size: 14px; color: #303133; margin-bottom: 4px; }
.td-group-total { font-size: 12px; color: #909399; margin-bottom: 12px; }
.td-member-list { display: flex; flex-direction: column; gap: 6px; }
.td-member-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.td-member-name { width: 70px; color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-bar-bg { flex: 1; height: 8px; background: #f0f2f5; border-radius: 4px; overflow: hidden; }
.td-bar-fill { height: 100%; background: #409EFF; border-radius: 4px; transition: width 0.3s; }
.td-member-count { width: 30px; text-align: right; font-weight: 600; color: #303133; }
.td-empty { color: #C0C4CC; font-size: 14px; padding: 40px 0; text-align: center; }
</style>
