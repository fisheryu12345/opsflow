<template>
	<div class="radar-chart-container" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import type { ECharts } from 'echarts';
import { getMultiWindowMetrics } from '../api';

const props = defineProps<{ accountId: number }>();

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: ECharts | null = null;

const getFontConfig = () => {
	const w = window.innerWidth;
	if (w < 480) return { radar: 10, legend: 10, tooltip: 11, title: 13 };
	if (w < 768) return { radar: 11, legend: 11, tooltip: 12, title: 15 };
	return { radar: 12, legend: 12, tooltip: 12, title: 16 };
};

const MOCK_METRICS = [
	{ window_days: 20, sharpe_ratio: '1.25', win_rate: '56.50', profit_loss_ratio: '1.85', sortino_ratio: '1.52', volatility: '12.30', total_trades: 45, data_quality: 'MOCK', color: '#1890ff' },
	{ window_days: 60, sharpe_ratio: '1.45', win_rate: '58.20', profit_loss_ratio: '2.10', sortino_ratio: '1.78', volatility: '11.50', total_trades: 128, data_quality: 'MOCK', color: '#52c41a' },
	{ window_days: 120, sharpe_ratio: '1.35', win_rate: '57.00', profit_loss_ratio: '1.95', sortino_ratio: '1.65', volatility: '10.80', total_trades: 256, data_quality: 'MOCK', color: '#faad14' },
	{ window_days: 250, sharpe_ratio: '1.50', win_rate: '59.50', profit_loss_ratio: '2.20', sortino_ratio: '1.85', volatility: '9.80', total_trades: 520, data_quality: 'MOCK', color: '#722ed1' }
];

const INDICATORS = [
	{ key: 'sharpe_ratio', label: '夏普比率', factor: 1 },
	{ key: 'win_rate', label: '胜率', factor: 1 },
	{ key: 'profit_loss_ratio', label: '盈亏比', factor: 1 },
	{ key: 'sortino_ratio', label: '索提诺', factor: 1 },
	{ key: 'volatility_inv', label: '低波动指数', factor: 1 },
];

const safeParse = (v: string | null | undefined, def = 0) => {
	if (v === null || v === undefined) return def;
	const n = parseFloat(v);
	return isNaN(n) ? def : n;
};

const calcIndicatorValue = (m: any, key: string): number => {
	if (key === 'volatility_inv') {
		const vol = safeParse(m.volatility, 1);
		return vol > 0 ? 1 / vol : 0;
	}
	return safeParse(m[key]);
};

const transformData = (metrics: any[]) => {
	const valid = metrics.filter(m => m.data_quality !== 'INSUFFICIENT' && m.sharpe_ratio !== null);
	if (valid.length === 0) return null;

	const colorMap: Record<number, string> = { 20: '#1890ff', 60: '#52c41a', 120: '#faad14', 250: '#722ed1' };

	// 每个维度独立算 max
	const maxValues = INDICATORS.map(ind => {
		const vals = valid.map(m => calcIndicatorValue(m, ind.key));
		return Math.max(Math.max(...vals, 0.1) * 1.3, 0.5);
	});

	return {
		maxValues,
		series: valid.map(m => ({
			name: `${m.window_days}日`,
			value: INDICATORS.map(ind => calcIndicatorValue(m, ind.key)),
			raw: m,
			isMock: m.data_quality === 'MOCK',
			color: m.color || colorMap[m.window_days] || '#1890ff'
		}))
	};
};

const getChartOption = (data: any, isMock: boolean) => {
	const font = getFontConfig();
	const isMobile = window.innerWidth < 480;

	return {
		title: {
			text: '多窗口绩效对比',
			subtext: isMock ? '模拟数据 — 数据积累中自动切换' : '',
			left: 'center', top: 10,
			textStyle: { fontSize: font.title, fontWeight: 'bold' },
			subtextStyle: { fontSize: 12, color: '#999' }
		},
		tooltip: {
			trigger: 'item',
			formatter: (params: any) => {
				const v = params.value;
				const raw = params.data?.raw || {};
				const mockTag = params.data?.isMock ? ' <span style="color:#999;font-size:11px;">(模拟)</span>' : '';
				const q = raw.data_quality && raw.data_quality !== 'MOCK'
					? `<div style="color:#999;font-size:11px;margin-top:2px;">数据质量: ${raw.data_quality}</div>` : '';
				return `<div style="padding:6px;">
					<strong style="font-size:14px;">${params.name}</strong>${mockTag}<br/>
					<div style="margin-top:4px;line-height:1.7;">
						<span style="display:inline-block;width:76px;">夏普比率</span><b>${v[0].toFixed(2)}</b><br/>
						<span style="display:inline-block;width:76px;">胜率</span><b>${v[1].toFixed(1)}%</b><br/>
						<span style="display:inline-block;width:76px;">盈亏比</span><b>${v[2].toFixed(2)}</b><br/>
						<span style="display:inline-block;width:76px;">索提诺</span><b>${v[3].toFixed(2)}</b><br/>
						<span style="display:inline-block;width:76px;">低波动</span><b>${v[4].toFixed(2)}</b><br/>
						<span style="display:inline-block;width:76px;color:#999;">交易次数</span><span style="color:#999;">${raw.total_trades || 0} 次</span>
					</div>
					${q}
				</div>`;
			},
			textStyle: { fontSize: font.tooltip }
		},
		legend: {
			data: data.series.map((d: any) => d.name),
			bottom: 10, icon: 'circle',
			textStyle: { fontSize: font.legend }
		},
		radar: {
			indicator: INDICATORS.map((ind, i) => ({
				name: ind.label,
				max: data.maxValues[i],
				min: 0
			})),
			radius: isMobile ? '58%' : '65%',
			center: ['50%', '50%'],
			axisName: { color: '#666', fontSize: font.radar },
			splitArea: { areaStyle: { color: ['rgba(24,144,255,0.03)', 'rgba(24,144,255,0.06)'] } },
			splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
			axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }
		},
		series: [{
			type: 'radar',
			animationDuration: 800,
			data: data.series.map((item: any) => ({
				value: item.value, name: item.name,
				lineStyle: { width: isMobile ? 1.5 : 2, type: item.isMock ? 'dashed' : 'solid', color: item.color },
				areaStyle: { opacity: isMobile ? 0.1 : 0.15, color: item.color },
				itemStyle: { borderWidth: isMobile ? 1.5 : 2, color: item.color }
			})),
			emphasis: { lineStyle: { width: 3 }, areaStyle: { opacity: 0.25 } }
		}]
	};
};

const loadRadarChart = async () => {
	try {
		const res = await getMultiWindowMetrics(props.accountId);
		let data: any = null, isMock = false;
		if (!res.data || res.data.length === 0 || (res.data.filter((m: any) => m.data_quality !== 'INSUFFICIENT' && m.sharpe_ratio !== null).length < 2)) {
			data = transformData(MOCK_METRICS); isMock = true;
		} else {
			data = transformData(res.data); isMock = false;
		}
		if (!data) return;
		if (!chartInstance && chartRef.value) chartInstance = echarts.init(chartRef.value);
		if (chartInstance) chartInstance.setOption(getChartOption(data, isMock), true);
	} catch (error: any) {
		console.error('加载多窗口雷达图失败:', error);
	}
};

onMounted(() => { loadRadarChart(); window.addEventListener('resize', handleResize); });
onUnmounted(() => { if (chartInstance) { chartInstance.dispose(); chartInstance = null; } window.removeEventListener('resize', handleResize); });
watch(() => props.accountId, () => loadRadarChart());

const handleResize = () => { if (chartInstance) chartInstance.resize(); };
</script>

<style scoped>
.radar-chart-container {
	width: 100%;
	height: 400px;
	min-height: 280px;
	background: #fff;
	border-radius: 8px;
	padding: 16px;
	box-sizing: border-box;
	@media (max-width: 768px) { min-height: 215px; }
	@media (max-width: 480px) { min-height: 173px; }
}
</style>
