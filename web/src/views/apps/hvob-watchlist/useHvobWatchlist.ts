import { ref, reactive, watch } from 'vue'
import { usePagination } from '/@/composables/usePagination'
import { useAccountStore } from '/@/stores/account'
import * as api from './api'

export interface WatchlistItem {
  id: number
  account: number
  account_name: string
  trade_date: string
  rank: number
  symbol: string
  product_code: string
  score: number
  atr_pct: number
  avg_amp: number
  vol_ratio: number
  atr_score: number
  amp_score: number
  vol_score: number
  bonus: number
  open_interest: number
}

export function useHvobWatchlist() {
  const { page, pageSize, total, onPageChange, onSizeChange } = usePagination(20)
  const list = ref<WatchlistItem[]>([])
  const loading = ref(false)
  const filters = reactive({
    trade_date: '',
  })
  const accountStore = useAccountStore()

  // 初始化账户（与 kline 页面相同的模式）
  if (!accountStore.loaded) accountStore.fetchAccounts()

  async function fetchData() {
    loading.value = true
    try {
      const params: any = { page: page.value, limit: pageSize.value }
      if (filters.trade_date) params.trade_date = filters.trade_date
      if (accountStore.currentAccountId) params.account = accountStore.currentAccountId

      const res = await api.GetWatchlist(params)
      if (res.code === 2000) {
        list.value = res.data || []
        total.value = res.total || 0
      }
    } catch (e) {
      console.error('获取观察池数据失败', e)
    } finally {
      loading.value = false
    }
  }

  watch(
    [page, pageSize, () => accountStore.currentAccountId],
    fetchData,
    { immediate: true },
  )

  function refresh() {
    page.value = 1
    fetchData()
  }

  function getProductLabel(item: WatchlistItem): string {
    const names: Record<string, string> = {
      ag: '沪银', sc: '原油', lu: '低硫燃油', fu: '燃油',
      eb: '苯乙烯', ps: '聚苯乙烯', TA: 'PTA', lc: '碳酸锂',
      MA: '甲醇', ec: '集运', rb: '螺纹钢', hc: '热卷',
      cu: '沪铜', al: '沪铝', zn: '沪锌', pb: '沪铅',
      ni: '沪镍', sn: '沪锡', au: '沪金', ru: '橡胶',
      b: '沥青', p: '棕榈', y: '豆油', m: '豆粕',
      cf: '棉花', sr: '白糖', rm: '菜粕', oi: '菜油',
      i: '铁矿', jd: '鸡蛋', pp: 'PP', l: '塑料',
      v: 'PVC', sa: '纯碱', ur: '尿素', c: '玉米',
      ap: '苹果', CJ: '红枣', eg: '乙二醇', pg: 'LPG',
    }
    return names[item.product_code.toUpperCase()] || ''
  }

  function getProductBonus(item: WatchlistItem): string {
    if (item.bonus > 0) return '优选品种'
    if (item.bonus < 0) return '回避品种'
    return ''
  }

  return {
    list, loading, page, pageSize, total,
    filters,
    accountStore,
    onPageChange, onSizeChange, fetchData, refresh,
    getProductLabel, getProductBonus,
  }
}
