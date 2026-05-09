import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import * as api from './api'
import type { ClosedPositionRecord } from '/@/types/trading'

export function useClosedPosition() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<ClosedPositionRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    symbol: '',
    product_code: '',
    direction: null as number | null,
    trade_date__gte: '',
    trade_date__lte: '',
  })

  async function fetchData() {
    loading.value = true
    try {
      const params: any = {
        page: page.value,
        limit: pageSize.value,
        ordering: '-trade_date',
      }
      if (filters.symbol) params.symbol = filters.symbol
      if (filters.product_code) params.product_code = filters.product_code
      if (filters.direction !== null) params.direction = filters.direction
      if (filters.trade_date__gte) params.trade_date__gte = filters.trade_date__gte
      if (filters.trade_date__lte) params.trade_date__lte = filters.trade_date__lte

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取平仓记录失败', e)
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
