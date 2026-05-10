import { ref, reactive, watch, computed, nextTick, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useAccountStore } from '/@/stores/account'
import * as api from './api'
import type { KlineRecord, TradeMarker, AvailableContract } from '/@/types/trading'

// 交易标记样式映射
const MARKER_STYLES: Record<string, { symbol: string; color: string; symbolSize: number }> = {
  ENTRY: { symbol: 'pin', color: '#00c853', symbolSize: 35 },
  ADD_ON: { symbol: 'circle', color: '#2196f3', symbolSize: 18 },
  ROLLOVER: { symbol: 'diamond', color: '#ff9800', symbolSize: 22 },
  EXIT: { symbol: 'pin', color: '#f44336', symbolSize: 35 },
}

export function useKline() {
  const accountStore = useAccountStore()
  // 确保账户列表已加载（否则 currentAccountId 可能为 null）
  if (!accountStore.loaded) accountStore.fetchAccounts()

  // ===== ECharts 实例管理（直接管理，不使用 useECharts 代理层） =====
  const chartRef = ref<HTMLElement | null>(null)
  let chartInstance: echarts.ECharts | null = null

  function initChart() {
    if (!chartRef.value) return null
    if (chartInstance) chartInstance.dispose()
    chartInstance = echarts.init(chartRef.value)
    return chartInstance
  }

  function resize() {
    chartInstance?.resize()
  }

  function getResponsiveFontConfig() {
    const width = window.innerWidth
    if (width < 480) {
      return { title: 13, subtitle: 9, axisName: 9, legend: 10, tooltip: 11, label: 10 }
    } else if (width < 768) {
      return { title: 15, subtitle: 11, axisName: 11, legend: 11, tooltip: 12, label: 11 }
    }
    return { title: 16, subtitle: 12, axisName: 12, legend: 12, tooltip: 12, label: 12 }
  }

  // ===== State =====
  const loading = ref(false)
  const klineList = ref<KlineRecord[]>([])
  const tradeMarkers = ref<TradeMarker[]>([])
  const symbolList = ref<AvailableContract[]>([])
  const selectedSymbol = ref('')
  const selectedProductCode = ref('')
  const dateRange = reactive<[string, string]>(['', ''])

  // 请求序号，用于丢弃过期响应（快速切换品种时的竞态保护）
  let fetchSeq = 0

  const fonts = getResponsiveFontConfig()

  // ===== Computed: ECharts option =====
  const chartOption = computed<echarts.EChartsOption>(() => {
    if (!klineList.value.length) return {}

    const data = klineList.value
    const dates = data.map((k) => k.date)
    const ohlc = data.map((k) => [k.open, k.close, k.low, k.high])
    const closes = data.map((k) => k.close)

    // 计算 MA 均线
    function calcMA(period: number): [number, ...number[]][] {
      const result: [number, ...number[]][] = []
      for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
          result.push([i, NaN])
        } else {
          let sum = 0
          for (let j = 0; j < period; j++) sum += closes[i - j]
          result.push([i, sum / period])
        }
      }
      return result
    }

    // 计算唐奇安通道 20HL
    function calcDonchianHL(period: number): { upper: number[]; lower: number[] } {
      const upper: number[] = []
      const lower: number[] = []
      for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
          upper.push(NaN)
          lower.push(NaN)
        } else {
          let max = -Infinity
          let min = Infinity
          for (let j = i - period + 1; j <= i; j++) {
            if (data[j].high > max) max = data[j].high
            if (data[j].low < min) min = data[j].low
          }
          upper.push(max)
          lower.push(min)
        }
      }
      return { upper, lower }
    }

    const donchian = calcDonchianHL(20)

    const ma10 = calcMA(10)
    const ma20 = calcMA(20)
    const ma40 = calcMA(40)

    // 构建交易标记 markPoint data
    const markers = tradeMarkers.value || []
    const markData: echarts.MarkPointDataType[] = markers
      .map((m) => {
        const style = MARKER_STYLES[m.trade_type] || MARKER_STYLES.ENTRY
        const dateIndex = dates.indexOf(m.date)
        if (dateIndex === -1) return null
        // 若后端未返回价格，以当日收盘价作为标记位置
        const price = m.price ?? data[dateIndex].close
        return {
          name: m.label,
          coord: [dateIndex, price] as [number, number],
          symbol: style.symbol,
          symbolSize: style.symbolSize,
          itemStyle: { color: style.color },
          label: {
            show: true,
            formatter: m.label,
            fontSize: fonts.label,
            color: style.color,
            fontWeight: 'bold' as const,
            position: 'top' as const,
          },
        }
      })
      .filter(Boolean) as echarts.MarkPointDataType[]

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#dcdfe6',
        textStyle: { color: '#303133', fontSize: fonts.tooltip },
        formatter: function (params: any) {
          const candle = params.find((p: any) => p.seriesName === 'K线')
          if (!candle) return ''
          const k = data[candle.dataIndex]
          if (!k || k.open == null) return ''
          return [
            `<b>${k.date}</b>`,
            `开: ${k.open.toFixed(2)}`,
            `高: ${k.high.toFixed(2)}`,
            `低: ${k.low.toFixed(2)}`,
            `收: ${k.close.toFixed(2)}`,
          ].join('<br/>')
        },
      },
      grid: {
        left: '8%',
        right: '8%',
        top: '14%',
        bottom: '14%',
      },
      legend: {
        data: ['K线', 'MA10', 'MA20', 'MA40', '通道上轨', '通道下轨'],
        top: 0,
        left: 'center',
        textStyle: { fontSize: fonts.legend },
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: fonts.axisName, rotate: 30 },
        axisLine: { show: false },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { fontSize: fonts.axisName },
        splitLine: { lineStyle: { type: 'dashed', color: '#e0e0e0' } },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          show: true,
          start: 0,
          end: 100,
          bottom: 15,
          height: 22,
          borderColor: '#d0d0d0',
          textStyle: { fontSize: 11 },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#f44336',
            color0: '#00c853',
            borderColor: '#f44336',
            borderColor0: '#00c853',
          },
          markPoint: {
            data: markData,
            symbolSize: 0,
          },
        },
        {
          name: 'MA10',
          type: 'line',
          data: ma10,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#42a5f5' },
        },
        {
          name: 'MA20',
          type: 'line',
          data: ma20,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#ffa726' },
        },
        {
          name: 'MA40',
          type: 'line',
          data: ma40,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#ab47bc' },
        },
        {
          name: '通道上轨',
          type: 'line',
          data: donchian.upper,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#9c27b0', type: 'dashed' as const },
        },
        {
          name: '通道下轨',
          type: 'line',
          data: donchian.lower,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#9c27b0', type: 'dashed' as const },
        },
      ],
    }
  })

  // ===== Methods =====
  async function fetchContracts() {
    if (!accountStore.currentAccountId) return
    try {
      const res = await api.GetAvailableContracts({ account: accountStore.currentAccountId })
      if (res.code === 2000) {
        symbolList.value = res.data || []
      }
    } catch (e) {
      console.error('获取合约列表失败:', e)
    }
  }

  async function fetchData() {
    const seq = ++fetchSeq
    if (!selectedProductCode.value || !accountStore.currentAccountId) return
    loading.value = true
    try {
      const params: any = {
        product_code: selectedProductCode.value,
      }
      if (dateRange[0]) params.date__gte = dateRange[0]
      if (dateRange[1]) params.date__lte = dateRange[1]

      const [klineRes, markerRes] = await Promise.all([
        api.GetKlineData(params),
        api.GetTradeMarkers({
          account: accountStore.currentAccountId,
          product_code: selectedProductCode.value,
        }),
      ])

      // 丢弃过期响应：快速切换品种时，旧品种的响应不应覆盖最新数据
      if (seq !== fetchSeq) return

      if (klineRes.code === 2000) {
        const rawData = (klineRes.data || []) as KlineRecord[]
        rawData.sort((a, b) => a.date.localeCompare(b.date))
        // 后端 DecimalField 序列化为字符串，转成数字确保 toFixed 可用
        rawData.forEach((k) => {
          k.open = Number(k.open)
          k.high = Number(k.high)
          k.low = Number(k.low)
          k.close = Number(k.close)
        })
        klineList.value = rawData
      }

      if (markerRes.code === 2000) {
        tradeMarkers.value = markerRes.data || []
      }
    } catch (e) {
      console.error('获取K线数据失败:', e)
    } finally {
      if (seq === fetchSeq) loading.value = false
    }

    // DOM 更新后直接初始化图表（确保 DOM 已渲染、chartRef 可用）
    await nextTick()
    // 再检查一次，防止在 await nextTick 期间品种已切换
    if (seq !== fetchSeq) return
    if (!chartRef.value || !klineList.value.length) return
    if (!chartInstance) initChart()
    if (chartInstance) {
      chartInstance.setOption(chartOption.value, true)
    }
  }

  function onSymbolChange(symbol: string) {
    selectedSymbol.value = symbol
    const found = symbolList.value.find((c) => c.symbol === symbol)
    selectedProductCode.value = found?.product_code || ''
    fetchData()
  }

  function refresh() {
    fetchData()
  }

  // ===== Watchers =====
  watch(() => accountStore.currentAccountId, () => {
    selectedSymbol.value = ''
    klineList.value = []
    tradeMarkers.value = []
    fetchContracts()
  }, { immediate: true })

  // ===== Lifecycle =====
  onMounted(() => {
    window.addEventListener('resize', resize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', resize)
    chartInstance?.dispose()
    chartInstance = null
  })

  return {
    klineList,
    tradeMarkers,
    symbolList,
    selectedSymbol,
    selectedProductCode,
    dateRange,
    loading,
    chartRef,
    onSymbolChange,
    refresh,
    resize,
  }
}
