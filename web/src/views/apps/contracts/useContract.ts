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
    is_active: null as boolean | null,
  })
  const selectedIds = ref<number[]>([])

  async function fetchData() {
    loading.value = true
    try {
      const params: any = { page: page.value, limit: pageSize.value }
      if (filters.exchange) params.exchange = filters.exchange
      if (filters.product_code) params.product_code__contains = filters.product_code
      if (filters.is_active !== null) params.is_active = filters.is_active

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

  async function toggleActive(row: ContractRecord) {
    try {
      const res = await api.ToggleActive(row.id)
      // toggle_active returns { message, is_active } directly (no code wrapper)
      if (res && res.message) {
        fetchData()
        return true
      }
    } catch (e) {
      console.error('切换状态失败', e)
    }
    return false
  }

  async function batchActivate() {
    if (!selectedIds.value.length) return false
    try {
      const res = await api.ActivateContracts(selectedIds.value)
      // activate returns { message, count } directly (no code wrapper)
      if (res && (res.code === 2000 || res.message)) {
        selectedIds.value = []
        fetchData()
        return true
      }
    } catch (e) {
      console.error('批量激活失败', e)
    }
    return false
  }

  async function batchDeactivate() {
    if (!selectedIds.value.length) return false
    try {
      const res = await api.DeactivateContracts(selectedIds.value)
      // deactivate returns { message, count } directly (no code wrapper)
      if (res && (res.code === 2000 || res.message)) {
        selectedIds.value = []
        fetchData()
        return true
      }
    } catch (e) {
      console.error('批量停用失败', e)
    }
    return false
  }

  async function saveContract(id: number | null, form: Partial<ContractRecord>) {
    try {
      if (id) {
        const res = await api.UpdateObj({ ...form, id })
        if (res.code === 2000) { fetchData(); return true }
      } else {
        const res = await api.AddObj(form)
        if (res.code === 2000) { fetchData(); return true }
      }
    } catch (e) {
      console.error('保存合约失败', e)
    }
    return false
  }

  async function deleteContract(id: number) {
    try {
      const res = await api.DelObj(id)
      if (res.code === 2000) { fetchData(); return true }
    } catch (e) {
      console.error('删除合约失败', e)
    }
    return false
  }

  const stats = ref<ContractStats | null>(null)
  async function fetchStats() {
    try {
      const res = await api.GetStatistics()
      // statistics endpoint returns { total, active, ... } directly (no code wrapper)
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
    filters, selectedIds,
    stats,
    onPageChange, onSizeChange, fetchData, refresh,
    toggleActive, batchActivate, batchDeactivate,
    saveContract, deleteContract, fetchStats,
  }
}
