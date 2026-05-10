import { ref, reactive, watch, computed, onMounted } from 'vue'
import * as echarts from 'echarts'
import { useAccountStore } from '/@/stores/account'
import { useECharts } from '/@/composables/useECharts'
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
  const { chartRef, initChart, resize, dispose, getResponsiveFontConfig } = useECharts()

  // ===== State =====
  const loading = ref(false)
  const klineList = ref<KlineRecord[]>([])
  const tradeMarkers = ref<TradeMarker[]>([])
  const symbolList = ref<AvailableContract[]>([])
  const selectedSymbol = ref('')
  const selectedProductCode = ref('')
  const dateRange = reactive<[string, string]>(['', ''])
  const chartInstance = ref<echarts.ECharts | null>(null)

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

    const ma10 = calcMA(10)
    const ma20 = calcMA(20)
    const ma40 = calcMA(40)

    // 构建交易标记 markPoint data
    const markers = tradeMarkers.value || []
    const markData: echarts.MarkPointDataType[] = markers
      .map((m, idx) => {
        const style = MARKER_STYLES[m.trade_type] || MARKER_STYLES.ENTRY
        const dateIndex = dates.indexOf(m.date)
        if (dateIndex === -1 || m.price === null) return null
        return {
          name: m.label,
          coord: [dateIndex, m.price] as [number, number],
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
        top: '8%',
        bottom: '14%',
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
        {
          type: 'inside',
          xAxisIndex: 0,
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          start: Math.max(0, 100 - 60),
          end: 100,
          bottom: 24,
          height: 18,
          borderColor: '#dcdfe6',
          fillerColor: 'rgba(64,158,255,0.15)',
          backgroundColor: '#f5f7fa',
          handleStyle: {
            borderColor: '#409eff',
            color: '#fff',
          },
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
            symbolSize: 0, // each point has its own symbolSize
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

      if (klineRes.code === 2000) {
        // 按日期升序排列（ECharts 从左到右展示）
        const rawData = klineRes.data || []
        rawData.sort((a: KlineRecord, b: KlineRecord) => a.date.localeCompare(b.date))
        klineList.value = rawData
      }

      if (markerRes.code === 2000) {
        tradeMarkers.value = markerRes.data || []
      }
    } catch (e) {
      console.error('获取K线数据失败:', e)
    } finally {
      loading.value = false
      // DOM 更新后渲染图表
      nextTick(renderChart)
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

  // 组件挂载后初始化图表
  onMounted(() => {
    if (klineList.value.length) {
      chartInstance.value = initChart()
      chartInstance.value?.setOption(chartOption.value, true)
    }
  })

  // k线数据变化时更新图表（flush:post 确保 DOM 已渲染、chartRef 可用）
  watch(klineList, () => {
    if (chartRef.value && klineList.value.length) {
      if (!chartInstance.value) {
        chartInstance.value = initChart()
      }
      if (chartInstance.value) {
        chartInstance.value.setOption(chartOption.value, true)
      }
    }
  }, { flush: 'post' })

  return {
    klineList,
    tradeMarkers,
    symbolList,
    selectedSymbol,
    selectedProductCode,
    dateRange,
    loading,
    chartRef,
    chartInstance,
    onSymbolChange,
    refresh,
    resize,
  }
}
