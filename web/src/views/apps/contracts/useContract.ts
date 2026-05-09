import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import * as api from './api'
import type { ContractRecord, ContractStats } from '/@/types/trading'

export function useContract() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<ContractRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    exchange: '',
    product_code: '',
  })
  const stats = ref<ContractStats | null>(null)

  async function fetchData() {
    loading.value = true
    try {
      const params: any = { page: page.value, limit: pageSize.value }
      if (filters.exchange) params.exchange = filters.exchange
      if (filters.product_code) params.product_code__contains = filters.product_code

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取合约列表失败', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const res = await api.GetStatistics()
      if (res && res.total !== undefined) {
        stats.value = res
      }
    } catch (e) {
      console.error('获取统计信息失败', e)
    }
  }

  watch([page, pageSize], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return {
    list, loading, page, pageSize, total,
    filters, stats,
    onPageChange, onSizeChange, fetchData, refresh,
    fetchStats,
  }
}
