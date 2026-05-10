import { ref, watch, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '/@/stores/account'
import { GetAvailable, ToggleProduct, BatchToggle } from '/@/api/stock/accountContract'

export function useAccountContract() {
  const accountStore = useAccountStore()

  const loading = ref(false)
  const toggling = ref(false)
  const batchLoading = ref(false)
  const list = ref<any[]>([])
  const filterText = ref('')
  const filterExchange = ref('')
  const initError = ref('')
  const selectedProductCodes = ref<string[]>([])

  const exchangeLabels: Record<string, string> = {
    SHFE: '上期所',
    DCE: '大商所',
    CZCE: '郑商所',
    CFFEX: '中金所',
    GFEX: '广期所',
  }

  const filteredList = computed(() => {
    let data = list.value
    if (filterText.value) {
      const q = filterText.value.toLowerCase()
      data = data.filter(
        (item) =>
          item.product_code.toLowerCase().includes(q) ||
          (item.name && item.name.toLowerCase().includes(q)) ||
          (item.symbol && item.symbol.toLowerCase().includes(q))
      )
    }
    if (filterExchange.value) {
      data = data.filter((item) => item.exchange === filterExchange.value)
    }
    return data
  })

  const activeCount = computed(() => list.value.filter((item) => item.is_active).length)
  const selectedCount = computed(() => selectedProductCodes.value.length)

  async function fetchData() {
    const accountId = accountStore.currentAccountId
    if (!accountId) {
      initError.value = '未找到交易账户，请确认用户已关联 TradingAccount'
      return
    }
    initError.value = ''
    loading.value = true
    try {
      const res: any = await GetAvailable({ account: accountId })
      if (res.code === 2000) {
        list.value = res.data || []
        if (list.value.length === 0) {
          initError.value = 'FullContractList 为空，请执行 python manage.py sync_contracts --seed 初始化合约数据'
        }
      } else {
        initError.value = `API 返回错误: ${res.msg || res.code}`
      }
    } catch (e: any) {
      initError.value = `获取数据失败: ${e.message || e}`
      console.error('获取可用合约列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  function handleSelectionChange(rows: any[]) {
    selectedProductCodes.value = rows.map((r) => r.product_code)
  }

  async function handleToggle(product_code: string) {
    if (!accountStore.currentAccountId) return
    toggling.value = true
    try {
      const res: any = await ToggleProduct({
        product_code,
        account: accountStore.currentAccountId,
      })
      if (res.code === 2000) {
        const item = list.value.find((i) => i.product_code === product_code)
        if (item) item.is_active = res.data.is_active
        ElMessage.success(res.msg || '操作成功')
      }
    } catch (e) {
      console.error('切换品种失败:', e)
    } finally {
      toggling.value = false
    }
  }

  async function handleBatchToggle(active: boolean) {
    if (!accountStore.currentAccountId || !selectedProductCodes.value.length) return
    batchLoading.value = true
    try {
      const res: any = await BatchToggle({
        product_codes: selectedProductCodes.value,
        active,
        account: accountStore.currentAccountId,
      })
      if (res.code === 2000) {
        ElMessage.success(res.msg || '操作成功')
        selectedProductCodes.value = []
        fetchData()
      }
    } catch (e) {
      console.error('批量操作失败:', e)
    } finally {
      batchLoading.value = false
    }
  }

  // 初始化: 等账户加载完成再获取数据
  onMounted(async () => {
    if (!accountStore.loaded) {
      await accountStore.fetchAccounts()
    }
    if (!accountStore.currentAccountId) {
      initError.value = '未找到交易账户，请确认用户已关联 TradingAccount'
    }
  })

  // 账户加载/切换时自动获取数据（immediate 替代显式 fetchData 调用，避免重复请求）
  watch(
    () => accountStore.currentAccountId,
    (val) => {
      if (val) fetchData()
    },
    { immediate: true }
  )

  return {
    loading,
    toggling,
    batchLoading,
    list,
    filteredList,
    filterText,
    filterExchange,
    activeCount,
    selectedCount,
    selectedProductCodes,
    initError,
    exchangeLabels,
    fetchData,
    handleToggle,
    handleBatchToggle,
    handleSelectionChange,
  }
}
