<template>
  <div class="trading-page">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-item">
        <span class="filter-label">合约代码</span>
        <el-select
          :model-value="selectedSymbol"
          placeholder="选择合约"
          style="width: 200px"
          filterable
          @change="onSymbolChange"
        >
          <el-option
            v-for="c in symbolList"
            :key="c.symbol"
            :label="`${c.symbol} (${c.product_code})`"
            :value="c.symbol"
          />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">开始日期</span>
        <el-date-picker
          v-model="dateRange[0]"
          type="date"
          placeholder="开始日期"
          style="width: 150px"
          value-format="YYYY-MM-DD"
        />
      </div>
      <div class="filter-item">
        <span class="filter-label">结束日期</span>
        <el-date-picker
          v-model="dateRange[1]"
          type="date"
          placeholder="结束日期"
          style="width: 150px"
          value-format="YYYY-MM-DD"
        />
      </div>
      <el-button type="primary" @click="refresh">查询</el-button>
    </div>

    <!-- Kline Chart -->
    <div class="section-card" style="margin-top: 16px">
      <div class="section-header">
        <span class="section-title">
          {{ selectedSymbol || 'K线图' }}
          <span v-if="selectedProductCode" class="section-subtitle">({{ selectedProductCode }})</span>
        </span>
        <div class="legend-group">
          <span class="legend-item"><span class="legend-dot" style="background:#00c853" />入场</span>
          <span class="legend-item"><span class="legend-dot" style="background:#2196f3" />加仓</span>
          <span class="legend-item"><span class="legend-dot" style="background:#ff9800" />移仓</span>
          <span class="legend-item"><span class="legend-dot" style="background:#f44336" />平仓</span>
        </div>
      </div>
      <div class="section-body">
        <div v-loading="loading" class="chart-container">
          <div
            v-if="!selectedSymbol"
            class="chart-placeholder"
          >请选择合约查看K线图</div>
          <div
            v-else-if="!klineList.length && !loading"
            class="chart-placeholder"
          >暂无K线数据，请先执行K线数据同步</div>
          <div
            v-else
            ref="chartRef"
            class="chart-instance"
          />
        </div>
      </div>
    </div>

    <!-- Trade Details -->
    <div class="section-card" style="margin-top: 16px">
      <div class="section-header">
        <span class="section-title">交易明细</span>
      </div>
      <div class="section-body" style="padding: 0">
        <el-table
          :data="tradeMarkers"
          border
          stripe
          class="trading-table"
          style="width: 100%"
          size="small"
        >
          <el-table-column prop="date" label="日期" min-width="100" />
          <el-table-column label="类型" min-width="80">
            <template #default="{ row }">
              <el-tag :type="tagType(row.trade_type)" size="small">{{ row.label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" min-width="80" align="right">
            <template #default="{ row }">{{ row.price != null ? row.price.toFixed(2) : '-' }}</template>
          </el-table-column>
          <el-table-column label="方向" min-width="70" align="center">
            <template #default="{ row }">
              <span :style="{ color: row.direction === 1 ? '#f44336' : row.direction === -1 ? '#00c853' : '#999' }">
                {{ row.direction === 1 ? '多头' : row.direction === -1 ? '空头' : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="200" />
        </el-table>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { onUnmounted } from 'vue'
import { useKline } from './useKline'

const {
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
} = useKline()

// 交易类型标签样式映射
const TYPE_TAG_MAP: Record<string, string> = {
  ENTRY: 'success',
  ADD_ON: 'primary',
  ROLLOVER: 'warning',
  EXIT: 'danger',
  STOP_LOSS: 'danger',
}
function tagType(tradeType: string) {
  return TYPE_TAG_MAP[tradeType] || 'info'
}

// ECharts 自适应
window.addEventListener('resize', resize)
onUnmounted(() => {
  window.removeEventListener('resize', resize)
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 12px 16px;
  border-radius: 4px;
  gap: 20px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.chart-container {
  width: 100%;
  min-height: 500px;
  position: relative;
}

.chart-instance {
  width: 100%;
  height: 620px;
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 520px;
  color: #999;
  font-size: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.section-subtitle {
  font-size: 13px;
  color: #909399;
  font-weight: 400;
}

.legend-group {
  display: flex;
  gap: 16px;
  align-items: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
</style>
