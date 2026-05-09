import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import * as api from './api'
import type { TradeLogRecord } from '/@/types/trading'

export function useTradeLog() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<TradeLogRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    log_level: '',
    function_name: '',
    symbol: '',
    timestamp__gte: '',
    timestamp__lte: '',
  })

  async function fetchData() {
    loading.value = true
    try {
      const params: any = {
        page: page.value,
        limit: pageSize.value,
        ordering: '-timestamp',
      }
      if (filters.log_level) params.log_level = filters.log_level
      if (filters.function_name) params.function_name__contains = filters.function_name
      if (filters.symbol) params.symbol = filters.symbol
      if (filters.timestamp__gte) params.timestamp__gte = filters.timestamp__gte
      if (filters.timestamp__lte) params.timestamp__lte = filters.timestamp__lte

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取交易日志失败', e)
    } finally {
      loading.value = false
    }
  }

  watch([page, pageSize], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return { list, loading, page, pageSize, total, filters, onPageChange, onSizeChange, fetchData, refresh }
}
