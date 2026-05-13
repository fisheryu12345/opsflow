import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '/@/stores/account'
import { GetSignalStats } from './api'

export interface SignalStatsData {
  summary: {
    total: number
    success: number
    failed: number
    cancelled: number
    pending: number
    overall_rate: number
    avg_execution_delay_seconds: number | null
  }
  by_type: Array<{
    trade_type: string
    total: number
    success: number
    failed: number
    cancelled: number
    pending: number
    rate: number
  }>
  failure_reasons: Array<{
    reason: string
    count: number
  }>
}

export function useSignalStats() {
  const loading = ref(false)
  const stats = ref<SignalStatsData | null>(null)
  const accountStore = useAccountStore()

  // 默认统计最近7天
  const now = new Date()
  const sevenDaysAgo = new Date(now)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

  const filters = reactive({
    date_from: sevenDaysAgo.toISOString().split('T')[0],
    date_to: now.toISOString().split('T')[0],
    account: accountStore.currentAccountId ?? undefined,
  })

  // Sync account from store
  watch(() => accountStore.currentAccountId, (id) => {
    filters.account = id ?? undefined
  })

  async function fetchStats() {
    loading.value = true
    try {
      const params: any = {}
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      if (filters.account) params.account = filters.account

      const res = await GetSignalStats(params)
      stats.value = res.data
    } catch (err: any) {
      ElMessage.error('获取统计失败: ' + (err.message || '未知错误'))
    } finally {
      loading.value = false
    }
  }

  // 指令执行：直接加载数据，只有看指定日期时用按钮筛选
  onMounted(() => {
    fetchStats()
  })

  return {
    loading,
    stats,
    filters,
    fetchStats,
  }
}
