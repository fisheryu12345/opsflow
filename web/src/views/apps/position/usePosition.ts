import { ref, reactive, computed, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import { useAccountStore } from '/@/stores/account'
import * as api from './api'
import type { PositionRecord } from '/@/types/trading'

export function usePosition() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<PositionRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    symbol: '',
    product_code: '',
    direction: null as number | null,
  })
  const showHoldingsOnly = ref(false)
  const todayCommission = ref<string | number>('--')
  const lastDataUpdateTime = ref<string>('')
  const accountStore = useAccountStore()

  async function fetchData() {
    loading.value = true
    try {
      const params: any = { page: page.value, limit: pageSize.value }
      if (filters.symbol) params.symbol = filters.symbol
      if (filters.product_code) params.product_code = filters.product_code
      if (filters.direction !== null) params.direction = filters.direction
      if (accountStore.currentAccountId) params.account = accountStore.currentAccountId

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
        todayCommission.value = res.today_commission ?? '--'
        lastDataUpdateTime.value = res.last_data_update_time ?? ''
      }
    } catch (e) {
      console.error('获取持仓数据失败', e)
    } finally {
      loading.value = false
    }
  }

  const totalHoldings = computed(() =>
    list.value.reduce((sum, item) => sum + item.contract_total_position, 0)
  )
  const longCount = computed(() =>
    list.value.filter(item => item.direction === 1).length
  )
  const shortCount = computed(() =>
    list.value.filter(item => item.direction === -1).length
  )
  const rolloverCount = computed(() =>
    list.value.filter(item => item.is_rollover_needed).length
  )

  watch([page, pageSize, () => accountStore.currentAccountId], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return {
    list, loading, page, pageSize, total,
    filters, showHoldingsOnly,
    totalHoldings, longCount, shortCount, rolloverCount,
    todayCommission, lastDataUpdateTime,
    onPageChange, onSizeChange, fetchData, refresh,
  }
}
