<template>
	<div class="trading-page">
				<el-tag v-if="lastUpdated" type="default" effect="plain" size="small">
					最后更新: {{ lastUpdated }}
				</el-tag>

		<!-- 指标卡片 -->
		<div class="metric-card-grid">
			<MetricCard
				v-for="(item, index) in normalItems"
				:key="index"
				:label="item.label"
				:value="item.value"
				:color-type="item.colorType"
				:border-color="getBorderColor(index)"
				:delay="index * 50"
				:tooltip="item.tooltip"
				:html="item.html"
			/>
		</div>

		<!-- 品种胜率统计 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">品种胜率统计</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="symbolWinRateRef" class="chart-container"></div>
				<div v-if="chartLoading.symbolWinRate" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 品种盈亏排行 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">品种盈亏排行</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="symbolPnlRankingRef" class="chart-container"></div>
				<div v-if="chartLoading.symbolPnlRanking" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 日历热力图 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">交易日收益热力图</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="calendarHeatmapRef" class="chart-container"></div>
				<div v-if="chartLoading.calendarHeatmap" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 资金曲线 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">资金曲线</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="equityCurveRef" class="chart-container"></div>
				<div v-if="chartLoading.equityCurve" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 月度收益柱状图 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">月度收益柱状图</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="monthlyReturnsRef" class="chart-container"></div>
				<div v-if="chartLoading.monthlyReturns" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 资金回撤曲线 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">资金回撤曲线</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="drawdownCurveRef" class="chart-container"></div>
				<div v-if="chartLoading.drawdownCurve" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 平仓盈亏曲线 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">平仓盈亏曲线</h3>
			</div>
			<div class="section-body" style="position: relative;">
				<div ref="closedPnlCurveRef" class="chart-container"></div>
				<div v-if="chartLoading.closedPnlCurve" class="chart-skeleton-overlay" />
			</div>
		</div>

		<!-- 多窗口绩效对比雷达图 -->
		<div class="section-card">
			<div class="section-header">
				<h3 class="section-title">多窗口绩效对比</h3>
			</div>
			<div class="section-body">
				<MultiWindowRadarChart :account-id="accountId" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import MultiWindowRadarChart from './components/MultiWindowRadarChart.vue';
import MetricCard from '/@/views/apps/components/MetricCard.vue';
import {
	getAccountSummary,
	getEquitySnapshots,
	getLatestRollingMetric,
	getSymbolWinRate,
	getCumulativeStats,
	getDailyReturnsCalendar,
	getDrawdownCurve,
	type AccountSummary,
	type EquitySnapshot
} from './api';
import { useAccountStore } from '/@/stores/account';

// ==================== 配置 ====================
const accountStore = useAccountStore();
const accountId = computed(() => accountStore.currentAccountId ?? 0);

// ==================== 响应式工具函数 ====================
const getResponsiveFontConfig = () => {
	const width = window.innerWidth;
	if (width < 480) {
		return { title: 12, subtitle: 9, axisName: 9, legend: 9, tooltip: 11, label: 9 };
	} else if (width < 768) {
		return { title: 13, subtitle: 10, axisName: 10, legend: 10, tooltip: 12, label: 10 };
	} else {
		return { title: 14, subtitle: 11, axisName: 11, legend: 11, tooltip: 12, label: 11 };
	}
};

// ==================== 状态管理 ====================
const lastUpdated = ref('');
const loading = ref(false);
const normalItems = ref<any[]>([]);
const chartLoading = reactive({
	symbolWinRate: true,
	calendarHeatmap: true,
	equityCurve: true,
	drawdownCurve: true,
	closedPnlCurve: true,
	monthlyReturns: true,
	symbolPnlRanking: true,
});
const symbolWinRateRef = ref();
const symbolPnlRankingRef = ref();
const calendarHeatmapRef = ref();
const equityCurveRef = ref();
const monthlyReturnsRef = ref();
const drawdownCurveRef = ref();
const closedPnlCurveRef = ref();

// ==================== 辅助函数 ====================

const borderColors = ["blue", "green", "orange", "red"] as const;
const getBorderColor = (index: number) => borderColors[index % borderColors.length];

const formatCurrency = (value: number | string) => {
	const num = typeof value === 'string' ? parseFloat(value) : value;
	return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};

const formatPercent = (value: number | string | null, decimals: number = 2) => {
	if (value === null || value === undefined) return '0.00%';
	const num = typeof value === 'string' ? parseFloat(value) : value;
	return `${num.toFixed(decimals)}%`;
};

const buildNormalItems = (
	summary: AccountSummary,
	latestBalance?: number,
	latestRiskRatio?: number,
	latestFloatProfit?: number,
	totalClosedPnl?: number,
	totalCommission?: number
) => {
	const currentEquity = latestBalance !== undefined ? latestBalance : 0;
	const riskRatio = latestRiskRatio !== undefined ? latestRiskRatio * 100 : 0;
	const floatProfit = latestFloatProfit !== undefined ? latestFloatProfit : 0;
	return [
		{ number: 1, label: '当前权益', value: formatCurrency(currentEquity), colorType: 'positive', tooltip: '账户当前总权益 = 可用资金 + 保证金占用 + 浮动盈亏' },
		{ number: 2, label: '累计收益率/年化收益率', value: `<span style="color:${(parseFloat(summary.total_return) || 0) >= 0 ? '#f5222d' : '#52c41a'}">${formatPercent(summary.total_return)}</span> / <span style="color:${(parseFloat(summary.annualized_return || '0') || 0) >= 0 ? '#f5222d' : '#52c41a'}">${formatPercent(summary.annualized_return)}</span>`, colorType: 'neutral', html: true, tooltip: '累计收益率: 总盈亏 / 初始本金。年化收益率: 按时间折算的年均收益率' },
		{ number: 3, label: '盈利因子', value: summary.overall_profit_factor ? parseFloat(summary.overall_profit_factor).toFixed(2) : '0.00', colorType: 'positive', tooltip: '总盈利 / 总亏损。>1 表示整体盈利，>2 表示优秀' },
		{ number: 4, label: '最大回撤', value: formatPercent(summary.max_drawdown_all_time), colorType: 'negative', tooltip: '历史最高点到最低点的最大跌幅。衡量策略风险的核心指标' },
		{ number: 5, label: '风险度', value: `${riskRatio.toFixed(2)}%`, colorType: 'negative', tooltip: '保证金占用 / 总权益。越高代表杠杆使用越重，风险越大' },
		{ number: 6, label: '波动率', value: formatPercent(summary.latest_volatility_20d), colorType: 'negative', tooltip: '20日年化波动率。衡量收益的波动幅度，越高代表风险越大' },
		{ number: 7, label: '夏普指数', value: summary.latest_sharpe_20d ? parseFloat(summary.latest_sharpe_20d).toFixed(2) : '0.00', colorType: 'positive', tooltip: '(策略收益率 - 无风险利率) / 波动率。>1 良好，>2 优秀，>3 极佳' },
		{ number: 8, label: '卡玛指数', value: summary.calmar_ratio ? parseFloat(summary.calmar_ratio).toFixed(2) : '0.00', colorType: 'positive', tooltip: '年化收益率 / 最大回撤。衡量收益与回撤的平衡能力' },
		{ number: 9, label: '索提诺比率', value: summary.latest_sortino_20d ? parseFloat(summary.latest_sortino_20d).toFixed(2) : '0.00', colorType: 'positive', tooltip: '类似夏普比率，但只考虑下行波动。越高代表下行风险控制越好' },
		{ number: 10, label: '胜率', value: formatPercent(summary.overall_win_rate), colorType: 'positive', tooltip: '盈利交易次数 / 总交易次数。海龟策略胜率通常在 35%-50%' },
		{ number: 11, label: '持仓总量/多单/空单', value: `${summary.current_long_position + summary.current_short_position} / ${summary.current_long_position} / ${summary.current_short_position}`, colorType: 'neutral', tooltip: '当前总持仓手数 / 多单手数 / 空单手数' },
		{ number: 12, label: '平均持仓时长/交易频率', value: `${summary.avg_holding_days ? parseFloat(summary.avg_holding_days).toFixed(1) + '天' : '0.0天'} / ${summary.trading_frequency ? parseFloat(summary.trading_frequency).toFixed(2) + '次/日' : '0.00次/日'}`, colorType: 'neutral', tooltip: '平均每笔持仓天数 / 每日平均交易次数' },
		{ number: 13, label: '平仓盈亏/持仓盈亏', value: `<span style="color:${(parseFloat(summary.closed_profit_total || '0') || totalClosedPnl || 0) >= 0 ? '#f5222d' : '#52c41a'}">${formatCurrency(summary.closed_profit_total || totalClosedPnl || 0)}</span> / <span style="color:${(latestFloatProfit || 0) >= 0 ? '#f5222d' : '#52c41a'}">${formatCurrency(latestFloatProfit || 0)}</span>`, colorType: 'neutral', html: true, tooltip: '已实现盈亏(平仓) / 未实现盈亏(浮动)。红色盈利，绿色亏损' },
		{ number: 14, label: '手续费总数', value: formatCurrency(summary.commission_total || totalCommission || 0), colorType: 'neutral', tooltip: '累计交易手续费。影响净收益的重要成本项' },
		{ number: 15, label: '连续亏损/最大连盈', value: `${summary.consecutive_losses}次 / ${summary.consecutive_wins}次`, colorType: 'negative', tooltip: '最大连续亏损次数 / 最大连续盈利次数。连续亏损次数是重要的风控指标' },
		{ number: 16, label: '最大盈利/最大亏损', value: `<span style="color:#f5222d">${summary.best_single_trade ? formatCurrency(summary.best_single_trade) : '¥0.00'}</span> / <span style="color:#52c41a">${summary.worst_single_trade ? formatCurrency(summary.worst_single_trade) : '¥0.00'}</span>`, colorType: 'neutral', html: true, tooltip: '单笔最佳盈利(红) / 单笔最大亏损(绿)。反映策略的盈亏分布特征' }
	];
};

// ==================== 图表初始化 ====================

const initSymbolWinRateChart = async () => {
	if (!symbolWinRateRef.value) return;
	const chart = echarts.init(symbolWinRateRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	try {
		const res = await getSymbolWinRate(accountId.value);
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			chart.setOption({ title: { text: '品种胜率统计', left: 'center', textStyle: { fontSize: fontConfig.title } }, graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fontSize: 14, fill: '#999' } }] });
			return;
		}

		const symbolData = res.data.slice().sort((a: any, b: any) => b.winRate - a.winRate);

		chart.setOption({
			tooltip: {
				trigger: 'axis', axisPointer: { type: 'shadow' },
				formatter: (params: any) => {
					const item = symbolData[params[0].dataIndex];
					const wr = params[0].value;
					const wrColor = wr >= 50 ? '#f5222d' : '#52c41a';
					return `<div style="font-weight:600;margin-bottom:4px;">${params[0].name}</div>
						<div>胜率: <span style="color:${wrColor};font-weight:700;">${wr}%</span></div>
						<div>交易次数: ${item.trades} 次</div>
						<div>多单: ${item.LongNum} / 空单: ${item.ShortNum}</div>
						<div>累计盈亏: <span style="color:${item.profit >= 0 ? '#f5222d' : '#52c41a'};font-weight:600;">¥${item.profit.toLocaleString()}</span></div>`;
				},
				textStyle: { fontSize: fontConfig.tooltip }
			},
			grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
			xAxis: {
				type: 'category', data: symbolData.map((item: any) => item.name),
				axisLabel: {
					interval: 0, rotate: 30, fontSize: fontConfig.axisName,
					formatter: (v: string) => isMobile && v.length > 6 ? v.substring(0, 5) + '...' : v
				}
			},
			yAxis: {
				type: 'value', name: '胜率 (%)', max: 100, min: 0,
				splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
				nameTextStyle: { fontSize: fontConfig.axisName },
				axisLabel: { formatter: '{value}%', fontSize: fontConfig.axisName }
			},
			series: [{
				name: '胜率', type: 'bar',
				data: symbolData.map((item: any) => ({
					value: item.winRate,
					itemStyle: {
						color: item.winRate >= 50 ? '#f5222d' : '#52c41a',
						borderRadius: [2, 2, 0, 0]
					}
				})),
				barWidth: isMobile ? '50%' : '55%',
				label: {
					show: !isMobile, position: 'top',
					formatter: (p: any) => `${p.value}%`,
					fontSize: fontConfig.label, fontWeight: 600,
					color: (p: any) => p.value >= 50 ? '#f5222d' : '#52c41a'
				},
				markLine: {
					silent: true,
					lineStyle: { color: '#fa8c16', type: 'dashed', width: 2 },
					label: { position: 'end', formatter: '基准 50%', fontSize: fontConfig.label, color: '#fa8c16' },
					data: [{ yAxis: 50 }]
				}
			}]
		});

		window.addEventListener('resize', () => chart.resize());
	} catch (error: any) {
		console.error('加载品种胜率数据失败:', error);
	} finally {
		chartLoading.symbolWinRate = false;
	}
};

const initCalendarHeatmap = async () => {
	if (!calendarHeatmapRef.value) return;
	const chart = echarts.init(calendarHeatmapRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	try {
		const res = await getDailyReturnsCalendar(accountId.value);
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			chart.setOption({ title: { text: '交易日收益热力图', left: 'center', textStyle: { fontSize: fontConfig.title } }, graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fontSize: 14, fill: '#999' } }] });
			return;
		}

		const calendarData = res.data;
		const years = [...new Set(calendarData.map((item: any) => item.year))].sort();
		const year = years[years.length - 1];
		const yearData = calendarData.filter((item: any) => item.year === year);

		chart.setOption({
			title: {
				text: year + '年 交易日收益热力图',
				left: 'center', top: 10,
				textStyle: { fontSize: fontConfig.title, fontWeight: 'bold' }
			},
			tooltip: {
				position: 'top',
				formatter: (params: any) => {
					const val = params.value;
					return val[0] + '<br/>' + (val[1] >= 0 ? '🔴' : '🟢') + ' 收益率: ' + val[1].toFixed(2) + '%';
				}
			},
			visualMap: {
				min: -10, max: 10,
				calculable: true,
				orient: 'horizontal', left: 'center', bottom: 10,
				inRange: { color: ['#003300', '#004d00', '#228B22', '#ffffff', '#ff9999', '#ff3333', '#b30000'] },
				textStyle: { fontSize: fontConfig.legend }
			},
			calendar: {
				left: isMobile ? 10 : 30, right: isMobile ? 10 : 30,
				top: 50, bottom: isMobile ? 60 : 50,
				range: year,
				cellSize: isMobile ? ['auto', 14] : ['auto', 18],
				splitLine: { lineStyle: { color: '#fff', width: 2 } },
				itemStyle: { color: '#fff', borderWidth: 0 },
				yearLabel: { show: false },
				dayLabel: {
					fontSize: fontConfig.axisName,
					firstDay: 1,
					formatter: (params: any) => {
						const d = params.date.getDay();
						return d === 0 || d === 6 ? '' : ['日','一','二','三','四','五','六'][d];
					}
				},
				monthLabel: { fontSize: fontConfig.axisName, nameMap: 'zh-cn' }
			},
			series: [{
				type: 'heatmap', coordinateSystem: 'calendar',
				data: yearData.map((item: any) => [item.date, item.daily_return]),
				label: {
					show: !isMobile,
					fontSize: fontConfig.label,
					color: '#000',
					formatter: (params: any) => params.value[1].toFixed(1)
				},
				emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } }
			}]
		});
		chartLoading.calendarHeatmap = false;
		} catch (error: any) {
		console.error('加载日历热力图失败:', error);
		chartLoading.calendarHeatmap = false;
	}
};

const initEquityCurveChart = (snapshots: EquitySnapshot[]) => {
	if (!equityCurveRef.value || !snapshots.length) {
		chartLoading.equityCurve = false;
		return;
	}
	const chart = echarts.init(equityCurveRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	const dates = snapshots.map(s => s.trade_date);
	const equities = snapshots.map(s => parseFloat(s.balance));
	const returns = equities.map((equity, index) => {
		if (index === 0) return 0;
		const prev = equities[index - 1];
		return prev > 0 ? ((equity - prev) / prev * 100) : 0;
	});

	chart.setOption({
		tooltip: {
			trigger: 'axis', axisPointer: { type: 'cross' },
			formatter: (params: any) => {
				const eq = params[0], ret = params[1];
				return `${eq.axisValue}<br/>权益: ¥${parseFloat(eq.value).toLocaleString()}<br/>收益率: ${parseFloat(ret.value).toFixed(2)}%`;
			},
			textStyle: { fontSize: fontConfig.tooltip }
		},
		legend: {
			data: ['账户权益', '日收益率'],
			top: isMobile ? 30 : 35,
			textStyle: { fontSize: fontConfig.legend }
		},
		grid: { left: isMobile ? '10%' : '3%', right: isMobile ? '10%' : '4%', bottom: isMobile ? '22%' : '20%', top: isMobile ? '22%' : '20%', containLabel: true },
		xAxis: {
			type: 'category', boundaryGap: false, data: dates,
			axisLabel: { fontSize: fontConfig.axisName, formatter: (v: string) => isMobile && v.length > 10 ? v.substring(5) : v }
		},
		yAxis: [
			{
				type: 'value', name: '权益', position: 'left',
				nameTextStyle: { fontSize: fontConfig.axisName },
				axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万`, fontSize: fontConfig.axisName }
			},
			{
				type: 'value', name: '收益率 (%)', position: 'right',
				nameTextStyle: { fontSize: fontConfig.axisName },
				axisLabel: { formatter: '{value}%', fontSize: fontConfig.axisName }
			}
		],
		dataZoom: [
			{ type: 'slider', show: true, start: 0, end: 100, bottom: isMobile ? 10 : 15, height: isMobile ? 20 : 25, borderColor: '#d0d0d0', textStyle: { fontSize: fontConfig.legend } },
			{ type: 'inside', start: 0, end: 100 }
		],
		series: [
			{
				name: '账户权益', type: 'line', smooth: true, data: equities, yAxisIndex: 0,
				areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(24,141,240,0.3)' }, { offset: 1, color: 'rgba(24,141,240,0.05)' }]) },
				lineStyle: { color: '#188df0', width: isMobile ? 1.5 : 2 },
				itemStyle: { color: '#188df0' }, symbolSize: isMobile ? 3 : 4,
				markPoint: { data: [{ type: 'max', name: '最大值', symbolSize: 40 }, { type: 'min', name: '最小值', symbolSize: 40 }] }
			},
			{
				name: '日收益率', type: 'line', smooth: true, data: returns, yAxisIndex: 1,
				lineStyle: { color: '#ff6b6b', width: isMobile ? 1.5 : 2, type: 'dashed' },
				itemStyle: { color: '#ff6b6b' }, symbolSize: isMobile ? 3 : 4
			}
		]
	});

	window.addEventListener('resize', () => chart.resize());
	chartLoading.equityCurve = false;
};

const initDrawdownCurveChart = async () => {
	if (!drawdownCurveRef.value) return;
	const chart = echarts.init(drawdownCurveRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	try {
		const res = await getDrawdownCurve(accountId.value);
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			chart.setOption({ title: { text: '资金回撤曲线', left: 'center', textStyle: { fontSize: fontConfig.title } }, graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fontSize: 14, fill: '#999' } }] });
			return;
		}

		const drawdownData = res.data;
		const dates = drawdownData.map((item: any) => item.date);
		const drawdownPcts = drawdownData.map((item: any) => item.drawdown_pct);
		const maxDrawdown = Math.min(...drawdownPcts);

		chart.setOption({
			tooltip: {
				trigger: 'axis', axisPointer: { type: 'cross' },
				formatter: (params: any) => {
					const d = params[0];
					const val = parseFloat(d.value);
					const level = val <= -10 ? '🔴' : val <= -5 ? '🟠' : val <= -2 ? '🟡' : '⚪';
					return `${d.axisValue}<br/>${level} 回撤: ${val.toFixed(2)}%`;
				},
				textStyle: { fontSize: fontConfig.tooltip }
			},
			grid: { left: isMobile ? '10%' : '3%', right: '4%', bottom: isMobile ? '22%' : '20%', top: '15%', containLabel: true },
			xAxis: {
				type: 'category', boundaryGap: false, data: dates,
				axisLabel: { fontSize: fontConfig.axisName, formatter: (v: string) => isMobile && v.length > 10 ? v.substring(5) : v }
			},
			yAxis: {
				type: 'value', name: '回撤 (%)', max: 2, min: Math.floor(maxDrawdown * 1.15),
				splitLine: { lineStyle: { color: '#e0e0e0', type: 'dashed' } },
				nameTextStyle: { fontSize: fontConfig.axisName },
				axisLabel: { formatter: '{value}%', fontSize: fontConfig.axisName }
			},
			dataZoom: [
				{ type: 'slider', show: true, start: 0, end: 100, bottom: isMobile ? 10 : 15, height: isMobile ? 20 : 25, borderColor: '#d0d0d0', textStyle: { fontSize: fontConfig.legend } },
				{ type: 'inside', start: 0, end: 100 }
			],
			visualMap: {
				show: false, dimension: 1,
				pieces: [
					{ lte: -10, color: '#dc2626' },
					{ gt: -10, lte: -5, color: '#fb7185' },
					{ gt: -5, lte: -2, color: '#fbbf24' },
					{ gt: -2, lte: 0, color: '#94a3b8' }
				]
			},
			series: [{
				name: '回撤', type: 'line', smooth: true, data: drawdownPcts,
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(220,38,38,0.3)' },
						{ offset: 1, color: 'rgba(220,38,38,0.02)' }
					])
				},
				lineStyle: { color: '#dc2626', width: isMobile ? 1.5 : 2 },
				itemStyle: { color: '#dc2626' }, symbolSize: isMobile ? 3 : 4,
				markLine: {
					silent: true,
					lineStyle: { color: '#ff4d4f', type: 'dashed', width: 2 },
					label: { position: 'end', formatter: `最大回撤 ${maxDrawdown.toFixed(2)}%`, fontSize: fontConfig.label, color: '#ff4d4f' },
					data: [{ yAxis: maxDrawdown }]
				},
				markPoint: {
					symbol: 'pin', symbolSize: isMobile ? 30 : 40,
					data: drawdownData
						.filter((item: any) => item.is_new_peak)
						.map((item: any) => ({
							name: '新高', coord: [dates.indexOf(item.date), 0], value: '新高',
							itemStyle: { color: '#52c41a' },
							label: { show: true, formatter: '新高', fontSize: fontConfig.label, color: '#fff' }
						}))
				}
			}]
		});

		window.addEventListener('resize', () => chart.resize());
	} catch (error: any) {
		console.error('加载回撤曲线数据失败:', error);
	} finally {
		chartLoading.drawdownCurve = false;
	}
};

const initClosedPnlCurveChart = (snapshots: EquitySnapshot[]) => {
	if (!closedPnlCurveRef.value || !snapshots.length) {
		chartLoading.closedPnlCurve = false;
		return;
	}
	const chart = echarts.init(closedPnlCurveRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	const dates = snapshots.map(s => s.trade_date);
	const dailyClosedPnls = snapshots.map(s => parseFloat(s.closed_pnl || '0'));
	let cumulativePnl = 0;
	const cumulativePnls = dailyClosedPnls.map(pnl => { cumulativePnl += pnl; return cumulativePnl; });

	chart.setOption({
		tooltip: {
			trigger: 'axis', axisPointer: { type: 'cross' },
			formatter: (params: any) => `${params[0].axisValue}<br/>累计平仓盈亏: ¥${parseFloat(params[0].value).toLocaleString()}`,
			textStyle: { fontSize: fontConfig.tooltip }
		},
		grid: { left: isMobile ? '10%' : '3%', right: '4%', bottom: isMobile ? '22%' : '20%', top: '15%', containLabel: true },
		xAxis: {
			type: 'category', boundaryGap: false, data: dates,
			axisLabel: { fontSize: fontConfig.axisName, formatter: (v: string) => isMobile && v.length > 10 ? v.substring(5) : v }
		},
		yAxis: {
			type: 'value', name: '累计盈亏', nameTextStyle: { fontSize: fontConfig.axisName },
			axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万`, fontSize: fontConfig.axisName }
		},
		dataZoom: [
			{ type: 'slider', show: true, start: 0, end: 100, bottom: isMobile ? 10 : 15, height: isMobile ? 20 : 25, borderColor: '#d0d0d0', textStyle: { fontSize: fontConfig.legend } },
			{ type: 'inside', start: 0, end: 100 }
		],
		series: [{
			name: '累计平仓盈亏', type: 'line', smooth: true, data: cumulativePnls,
			areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(102,187,106,0.3)' }, { offset: 1, color: 'rgba(102,187,106,0.05)' }]) },
			lineStyle: { color: '#66bb6a', width: isMobile ? 1.5 : 2 },
			itemStyle: { color: '#66bb6a' }, symbolSize: isMobile ? 3 : 4,
			markLine: { silent: true, data: [{ yAxis: 0, lineStyle: { color: '#999', type: 'dashed' } }] }
		}]
	});

	window.addEventListener('resize', () => chart.resize());
	chartLoading.closedPnlCurve = false;
};

const initMonthlyReturnsChart = (snapshots: EquitySnapshot[]) => {
	if (!monthlyReturnsRef.value || !snapshots.length) {
		chartLoading.monthlyReturns = false;
		return;
	}
	const chart = echarts.init(monthlyReturnsRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	const monthlyMap = new Map<string, number>();
	snapshots.forEach(s => {
		const month = s.trade_date.substring(0, 7);
		const pnl = parseFloat(s.daily_pnl || '0');
		monthlyMap.set(month, (monthlyMap.get(month) || 0) + pnl);
	});

	const months = Array.from(monthlyMap.keys()).sort();
	const pnls = months.map(m => monthlyMap.get(m) || 0);

	chart.setOption({
		tooltip: {
			trigger: 'axis', axisPointer: { type: 'shadow' },
			formatter: (params: any) => {
				const val = params[0].value;
				return `${params[0].name}<br/>月度盈亏: <span style="color:${val >= 0 ? '#f5222d' : '#52c41a'};font-weight:700;">¥${val.toLocaleString()}</span>`;
			},
			textStyle: { fontSize: fontConfig.tooltip }
		},
		grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
		xAxis: {
			type: 'category', data: months,
			axisLabel: { fontSize: fontConfig.axisName }
		},
		yAxis: {
			type: 'value', name: '盈亏 (¥)',
			splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
			nameTextStyle: { fontSize: fontConfig.axisName },
			axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万`, fontSize: fontConfig.axisName }
		},
		series: [{
			name: '月度收益', type: 'bar',
			data: pnls.map(v => ({
				value: Math.round(v * 100) / 100,
				itemStyle: {
					color: v >= 0
						? new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#f5222d' }, { offset: 1, color: '#a8071a' }])
						: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#52c41a' }, { offset: 1, color: '#237804' }])
				}
			})),
			barWidth: isMobile ? '50%' : '45%',
			label: {
				show: !isMobile, position: 'top',
				formatter: (p: any) => `¥${(p.value / 10000).toFixed(1)}万`,
				fontSize: fontConfig.label, fontWeight: 600,
				color: (p: any) => p.value >= 0 ? '#f5222d' : '#52c41a'
			},
			markLine: {
				silent: true,
				lineStyle: { color: '#999', type: 'dashed', width: 1 },
				data: [{ yAxis: 0 }]
			}
		}]
	});

	window.addEventListener('resize', () => chart.resize());
	chartLoading.monthlyReturns = false;
};

const initSymbolPnlRankingChart = async () => {
	if (!symbolPnlRankingRef.value) return;
	const chart = echarts.init(symbolPnlRankingRef.value);
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;

	try {
		const res = await getSymbolWinRate(accountId.value);
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			chart.setOption({
				title: { text: '品种盈亏排行', left: 'center', textStyle: { fontSize: fontConfig.title } },
				graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fontSize: 14, fill: '#999' } }]
			});
			return;
		}

		const sorted = [...res.data].sort((a: any, b: any) => a.profit - b.profit);

		chart.setOption({
			tooltip: {
				trigger: 'axis', axisPointer: { type: 'shadow' },
				formatter: (params: any) => {
					const item = sorted[params[0].dataIndex];
					return `<div style="font-weight:600;margin-bottom:4px;">${item.name}</div>
						<div>累计盈亏: <span style="color:${item.profit >= 0 ? '#f5222d' : '#52c41a'};font-weight:700;">¥${item.profit.toLocaleString()}</span></div>
						<div>胜率: ${item.winRate}%</div>
						<div>交易次数: ${item.trades} 次</div>`;
				},
				textStyle: { fontSize: fontConfig.tooltip }
			},
			grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
			xAxis: {
				type: 'value', name: '累计盈亏 (¥)',
				axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万`, fontSize: fontConfig.axisName },
				nameTextStyle: { fontSize: fontConfig.axisName },
				splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } }
			},
			yAxis: {
				type: 'category', data: sorted.map((item: any) => item.name),
				axisLabel: { fontSize: fontConfig.axisName },
				axisLine: { show: false },
				axisTick: { show: false }
			},
			series: [{
				name: '累计盈亏', type: 'bar',
				data: sorted.map((item: any) => ({
					value: item.profit,
					itemStyle: {
						color: item.profit >= 0
							? new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#f5222d' }, { offset: 1, color: '#a8071a' }])
							: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#52c41a' }, { offset: 1, color: '#237804' }])
					}
				})),
				barWidth: isMobile ? '50%' : '55%',
				label: {
					show: !isMobile, position: 'right',
					formatter: (p: any) => `¥${(p.value / 10000).toFixed(1)}万`,
					fontSize: fontConfig.label, fontWeight: 600,
					color: (p: any) => p.value >= 0 ? '#f5222d' : '#52c41a'
				},
				markLine: {
					silent: true,
					lineStyle: { color: '#999', type: 'dashed', width: 1 },
					data: [{ xAxis: 0 }]
				}
			}]
		});

		window.addEventListener('resize', () => chart.resize());
	} catch (error: any) {
		console.error('加载品种盈亏排行数据失败:', error);
	} finally {
		chartLoading.symbolPnlRanking = false;
	}
};

// ==================== 数据加载 ====================

const loadDashboardData = async () => {
	// 账户未就绪时跳过，由下方的 watch 驱动
	if (!accountStore.currentAccountId) return
	loading.value = true;
	try {
		const summaryRes = await getAccountSummary(accountId.value);
		if (summaryRes.code !== 2000 || !summaryRes.data || summaryRes.data.length === 0) {
			ElMessage.warning('未找到账户绩效数据');
			return;
		}
		const summary = summaryRes.data[0];

		const endDate = new Date();
		const startDate = new Date();
		startDate.setDate(startDate.getDate() - 365);
		const snapshotsRes = await getEquitySnapshots({
			account: accountId.value,
			trade_date__gte: startDate.toISOString().split('T')[0],
			trade_date__lte: endDate.toISOString().split('T')[0],
			ordering: 'trade_date',
			page_size: 500
		});

		let latestBalance = 0, latestRiskRatio = 0, latestFloatProfit = 0;
		if (snapshotsRes.code === 2000 && snapshotsRes.data && snapshotsRes.data.length > 0) {
			const latestSnapshot = snapshotsRes.data[snapshotsRes.data.length - 1];
			latestBalance = parseFloat(latestSnapshot.balance);
			latestRiskRatio = latestSnapshot.risk_ratio !== undefined && latestSnapshot.risk_ratio !== null ? parseFloat(latestSnapshot.risk_ratio) : 0;
			latestFloatProfit = latestSnapshot.float_profit !== undefined && latestSnapshot.float_profit !== null ? parseFloat(latestSnapshot.float_profit) : 0;

			nextTick(() => {
				initEquityCurveChart(snapshotsRes.data);
				initClosedPnlCurveChart(snapshotsRes.data);
				initMonthlyReturnsChart(snapshotsRes.data);
			});
		} else {
			chartLoading.equityCurve = false;
			chartLoading.closedPnlCurve = false;
			chartLoading.monthlyReturns = false;
		}

		let totalClosedPnl = 0, totalCommission = 0;
		try {
			const cumulativeStatsRes: any = await getCumulativeStats(accountId.value);
			if (cumulativeStatsRes.code === 2000 && cumulativeStatsRes.data) {
				totalClosedPnl = Number(cumulativeStatsRes.data.total_closed_pnl) || 0;
				totalCommission = Number(cumulativeStatsRes.data.total_commission) || 0;
			}
		} catch (error) {
			console.warn('获取累计统计数据失败:', error);
		}

		normalItems.value = buildNormalItems(summary, latestBalance, latestRiskRatio, latestFloatProfit, totalClosedPnl, totalCommission);
		lastUpdated.value = summary.updated_at
			? new Date(summary.updated_at).toLocaleString('zh-CN', { hour12: false })
			: new Date().toLocaleString('zh-CN', { hour12: false });
		ElMessage.success('数据加载成功');
	} catch (error: any) {
		console.error('加载 Dashboard 数据失败:', error);
	} finally {
		loading.value = false;
	}
};

// ==================== 生命周期 ====================

onMounted(async () => {
	// 确保账户已初始化（如果登录流程已加载，则为空操作）
	if (!accountStore.loaded) await accountStore.fetchAccounts()
	// 账户已就绪时加载数据，否则由下方 watch 驱动
	loadDashboardData();
	nextTick(() => {
		initSymbolWinRateChart();
		initSymbolPnlRankingChart();
		initCalendarHeatmap();
		initDrawdownCurveChart();
	});
});

// 账户切换时重新加载所有数据
watch(() => accountStore.currentAccountId, (newId) => {
  if (newId) {
    loadDashboardData();
    nextTick(() => {
      initSymbolWinRateChart();
      initSymbolPnlRankingChart();
      initCalendarHeatmap();
      initDrawdownCurveChart();
    });
  }
});
</script>

<style scoped lang="scss">
.chart-skeleton-overlay {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	border-radius: 8px;
	background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
	background-size: 200% 100%;
	animation: skeletonPulse 1.5s ease-in-out infinite;
	pointer-events: none;
}

@keyframes skeletonPulse {
	0% { background-position: 200% 0; }
	100% { background-position: -200% 0; }
}
</style>
