import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import { useAccountStore } from '/@/stores/account'
import * as api from './api'
import type { DailySignalRecord } from '/@/types/trading'

export function useDailySignal() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<DailySignalRecord[]>([])
  const loading = ref(false)
  const accountStore = useAccountStore()
  const filters = reactive({
    trade_date__gte: '',
    trade_date__lte: '',
    signal_direction: null as number | null,
    executed_status: '',
    symbol: '',
    trend_label: '',
  })

  async function fetchData() {
    loading.value = true
    try {
      const params: any = {
        page: page.value,
        limit: pageSize.value,
        ordering: '-trade_date',
      }
      if (filters.trade_date__gte) params.trade_date__gte = filters.trade_date__gte
      if (filters.trade_date__lte) params.trade_date__lte = filters.trade_date__lte
      if (filters.signal_direction !== null) params.signal_direction = filters.signal_direction
      if (filters.executed_status) params.executed_status = filters.executed_status
      if (filters.symbol) params.symbol = filters.symbol
      if (filters.trend_label) params.trend_label = filters.trend_label
      if (accountStore.currentAccountId) params.account = accountStore.currentAccountId

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取交易信号失败', e)
    } finally {
      loading.value = false
    }
  }

  watch([page, pageSize, () => accountStore.currentAccountId], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return { list, loading, page, pageSize, total, filters, onPageChange, onSizeChange, fetchData, refresh }
}
