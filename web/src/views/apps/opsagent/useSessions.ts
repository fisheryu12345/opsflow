import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import * as api from './api'

export interface SessionRecord {
  id: number
  session_id: string
  operator: string
  user_input: string
  mode: string
  status: string
  task_status: string
  started_at: string
  ended_at: string | null
  summary: string
  audit_count: number
}

export function useSessions() {
  const { page, pageSize, total, onPageChange, onSizeChange, reset } = usePagination(20)
  const list = ref<SessionRecord[]>([])
  const loading = ref(false)
  const filters = reactive({
    status: '',
    mode: '',
    search: '',
  })

  async function fetchData() {
    loading.value = true
    try {
      const params: any = {
        page: page.value,
        limit: pageSize.value,
        ordering: '-started_at',
      }
      if (filters.status) params.status = filters.status
      if (filters.mode) params.mode = filters.mode
      if (filters.search) params.search = filters.search

      const res = await api.GetSessions(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取会话列表失败', e)
    } finally {
      loading.value = false
    }
  }

  watch([page, pageSize], fetchData, { immediate: true })

  function refresh() {
    page.value = 1
    fetchData()
  }

  return {
    list, loading, page, pageSize, total,
    filters, onPageChange, onSizeChange, refresh,
  }
}
