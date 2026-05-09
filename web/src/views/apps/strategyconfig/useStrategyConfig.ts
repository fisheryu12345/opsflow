import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import * as api from './api'
import type { StrategyConfigRecord } from '/@/types/trading'

export function useStrategyConfig() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<StrategyConfigRecord[]>([])
  const loading = ref(false)
  const search = ref('')

  async function fetchData() {
    loading.value = true
    try {
      const params: any = { page: page.value, limit: pageSize.value }
      if (search.value) params.name__contains = search.value

      const res = await api.GetList(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取策略配置失败', e)
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(id: number | null, form: Partial<StrategyConfigRecord>) {
    try {
      if (id) {
        const res = await api.UpdateObj({ ...form, id })
        if (res.code === 2000) { fetchData(); return true }
      } else {
        const res = await api.AddObj(form)
        if (res.code === 2000) { fetchData(); return true }
      }
    } catch (e) {
      console.error('保存策略配置失败', e)
    }
    return false
  }

  async function deleteConfig(id: number) {
    try {
      const res = await api.DelObj(id)
      if (res.code === 2000) { fetchData(); return true }
    } catch (e) {
      console.error('删除策略配置失败', e)
    }
    return false
  }

  watch([page, pageSize], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return {
    list, loading, page, pageSize, total,
    search,
    onPageChange, onSizeChange, fetchData, refresh,
    saveConfig, deleteConfig,
  }
}
