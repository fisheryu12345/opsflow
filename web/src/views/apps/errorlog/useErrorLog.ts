import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import { useAccountStore } from '/@/stores/account'
import * as api from './api'
import type { ErrorLogRecord } from '/@/types/trading'

export function useErrorLog() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const accountStore = useAccountStore()
  const list = ref<ErrorLogRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    function_name: '',
    error_message: '',
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
      if (accountStore.currentAccountId) params.account = accountStore.currentAccountId
      if (filters.function_name) params.function_name__contains = filters.function_name
      if (filters.error_message) params.error_message__contains = filters.error_message
      if (filters.timestamp__gte) params.timestamp__gte = filters.timestamp__gte
      if (filters.timestamp__lte) params.timestamp__lte = filters.timestamp__lte

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取错误日志失败', e)
    } finally {
      loading.value = false
    }
  }

  async function deleteLog(id: number) {
    try {
      const res = await api.DelObj(id)
      if (res.code === 2000) {
        fetchData()
        return true
      }
    } catch (e) {
      console.error('删除错误日志失败', e)
    }
    return false
  }

  watch([page, pageSize, () => accountStore.currentAccountId], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return { list, loading, page, pageSize, total, filters, onPageChange, onSizeChange, fetchData, refresh, deleteLog }
}
