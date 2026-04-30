<template>
	<div class="radar-chart-container" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import type { ECharts } from 'echarts';
import { getMultiWindowMetrics } from '../api';
import { ElMessage } from 'element-plus';

// ==================== Props ====================
const props = defineProps<{
	accountId: number;
}>();

// ==================== 状态管理 ====================
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: ECharts | null = null;

// ==================== 模拟数据配置 ====================
/**
 * 模拟数据（用于账户运行初期数据不足时展示）
 * 💡 数据来源：基于典型期货策略的历史表现估算
 * 🎨 颜色方案：
 * - 20日：蓝色系 (#1890ff) - 短期灵敏度高
 * - 60日：绿色系 (#52c41a) - 中期稳健
 * - 120日：橙色系 (#faad14) - 中长期平衡
 * - 250日：紫色系 (#722ed1) - 长期趋势稳定
 */
const MOCK_METRICS = [
	{ window_days: 20, sharpe_ratio: '1.25', win_rate: '56.50', profit_loss_ratio: '1.85', volatility: '12.30', data_quality: 'MOCK', color: '#1890ff' },
	{ window_days: 60, sharpe_ratio: '1.45', win_rate: '58.20', profit_loss_ratio: '2.10', volatility: '11.50', data_quality: 'MOCK', color: '#52c41a' },
	{ window_days: 120, sharpe_ratio: '1.35', win_rate: '57.00', profit_loss_ratio: '1.95', volatility: '10.80', data_quality: 'MOCK', color: '#faad14' },
	{ window_days: 250, sharpe_ratio: '1.50', win_rate: '59.50', profit_loss_ratio: '2.20', volatility: '9.80', data_quality: 'MOCK', color: '#722ed1' }
];

// ==================== 数据处理 ====================
/**
 * 判断是否应该使用模拟数据
 * 
 * @param metrics 真实数据数组
 * @returns boolean - true表示需要使用模拟数据
 */
const shouldUseMockData = (metrics: any[]): boolean => {
	if (!metrics || metrics.length === 0) {
		return true;
	}
	
	// 过滤掉数据质量不足的窗口
	const validMetrics = metrics.filter(m => 
		m.data_quality !== 'INSUFFICIENT' && 
		m.sharpe_ratio !== null
	);
	
	// 如果有效窗口少于2个，使用模拟数据
	return validMetrics.length < 2;
};

/**
/**
 * 安全解析数值，处理 null/undefined
 */
const safeParse = (value: string | null | undefined, defaultValue: number = 0): number => {
	if (value === null || value === undefined) {
		return defaultValue;
	}
	const parsed = parseFloat(value);
	return isNaN(parsed) ? defaultValue : parsed;
};

/**
 * 将后端数据转换为雷达图格式
 */
const transformDataForRadar = (metrics: any[]) => {
	// 过滤掉数据质量不足的窗口
	const validMetrics = metrics.filter(m => 
		m.data_quality !== 'INSUFFICIENT' && 
		m.sharpe_ratio !== null
	);

	if (validMetrics.length === 0) {
		return null;
	}

	// 定义不同窗口的颜色映射（用于真实数据）
	const colorMap: Record<number, string> = {
		20: '#1890ff',   // 蓝色 - 短期
		60: '#52c41a',   // 绿色 - 中期
		120: '#faad14',  // 橙色 - 中长期
		250: '#722ed1'   // 紫色 - 长期
	};

	// 转换为雷达图所需格式
	return validMetrics.map(m => ({
		name: `${m.window_days}日`,
		value: [
			safeParse(m.sharpe_ratio),                    // 夏普比率
			safeParse(m.win_rate),                        // 胜率(%)
			safeParse(m.profit_loss_ratio),               // 盈亏比
			m.volatility ? (1 / safeParse(m.volatility, 1)) : 0  // 波动率倒数（越大越好）
		],
		isMock: m.data_quality === 'MOCK',  // 标记是否为模拟数据
		color: m.color || colorMap[m.window_days] || '#1890ff'  // 使用配置颜色或默认颜色
	}));
};

// ==================== 图表配置 ====================
/**
 * 获取 ECharts 配置项
 * 
 * @param radarData 雷达图数据
 * @param isMockData 是否使用模拟数据
 */
const getChartOption = (radarData: any[], isMockData: boolean = false) => {
	return {
		title: {
			text: isMockData ? '多窗口绩效对比（示例数据）' : '多窗口绩效对比',
			subtext: isMockData ? '数据积累中将自动切换为真实数据' : '',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: 16,
				fontWeight: 'bold'
			},
			subtextStyle: {
				fontSize: 12,
				color: '#999'
			}
		},
		tooltip: {
			trigger: 'item',
			formatter: (params: any) => {
				const windowName = params.name;
				const values = params.value;
				const isMock = params.data.isMock;
				return `
					<div style="padding: 8px;">
						<strong>${windowName}</strong>${isMock ? ' <span style="color:#999;font-size:12px;">(示例)</span>' : ''}<br/>
						夏普比率: ${values[0].toFixed(2)}<br/>
						胜率: ${values[1].toFixed(2)}%<br/>
						盈亏比: ${values[2].toFixed(2)}<br/>
						低波动指数: ${values[3].toFixed(2)}
					</div>
				`;
			}
		},
		legend: {
			data: radarData.map(d => d.name),
			bottom: 10,
			icon: 'circle'
		},
		radar: {
			indicator: [
				{ name: '夏普比率', max: 3, min: 0 },
				{ name: '胜率(%)', max: 100, min: 0 },
				{ name: '盈亏比', max: 5, min: 0 },
				{ name: '低波动', max: 1, min: 0 }
			],
			radius: '65%',
			center: ['50%', '50%'],
			axisName: {
				color: '#666',
				fontSize: 12
			},
			splitArea: {
				areaStyle: {
					color: ['#f8f9fa', '#fff']
				}
			}
		},
		series: [{
			type: 'radar',
			data: radarData.map((item, index) => ({
				value: item.value,
				name: item.name,
				lineStyle: {
					width: 2,
					type: item.isMock ? 'dashed' : 'solid',  // 模拟数据用虚线
					color: item.color || (item.isMock ? '#999' : undefined)  // 使用配置颜色
				},
				areaStyle: {
					opacity: item.isMock ? 0.08 : 0.15,  // 模拟数据更透明
					color: item.color || (item.isMock ? '#ccc' : undefined)
				},
				itemStyle: {
					borderWidth: 2,
					color: item.color || (item.isMock ? '#999' : undefined)
				}
			})),
			emphasis: {
				lineStyle: {
					width: 4
				}
			}
		}]
	};
};

// ==================== 数据加载 ====================
/**
 * 加载并渲染雷达图
 */
const loadRadarChart = async () => {
	try {
		const res = await getMultiWindowMetrics(props.accountId);
		
		let radarData: any[] | null = null;
		let isMockData = false;
		
		// 判断是否需要使用模拟数据
		// 注意：这里假设 res.code === 2000 为成功，如果接口失败通常会在 catch 中处理或 res.code 不为 2000
		// 如果 res.code !== 2000，res.data 可能为空或无效，shouldUseMockData 会处理空数组情况
		if (!res.data || res.data.length === 0 || shouldUseMockData(res.data)) {
			console.warn('[MultiWindowRadarChart] 数据不足，使用模拟数据展示');
			radarData = transformDataForRadar(MOCK_METRICS);
			isMockData = true;
		} else {
			radarData = transformDataForRadar(res.data);
			isMockData = false;
		}
		
		if (!radarData) {
			ElMessage.warning('无法生成雷达图数据');
			return;
		}

		// 初始化或更新图表
		if (!chartInstance && chartRef.value) {
			chartInstance = echarts.init(chartRef.value);
		}

		if (chartInstance) {
			const option = getChartOption(radarData, isMockData);
			chartInstance.setOption(option, true);
		}
	} catch (error: any) {
		console.error('加载多窗口雷达图失败:', error);
		ElMessage.error('加载图表失败');
	}
};

// ==================== 生命周期 ====================
onMounted(() => {
	loadRadarChart();
	
	// 监听窗口大小变化
	window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
	// 销毁图表实例
	if (chartInstance) {
		chartInstance.dispose();
		chartInstance = null;
	}
	
	// 移除事件监听
	window.removeEventListener('resize', handleResize);
});

// 监听 accountId 变化
watch(() => props.accountId, () => {
	loadRadarChart();
});

// ==================== 响应式处理 ====================
/**
 * 处理窗口大小变化
 */
const handleResize = () => {
	if (chartInstance) {
		chartInstance.resize();
	}
};
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
	
	@media (max-width: 768px) {
		min-height: 215px;
	}
	
	@media (max-width: 480px) {
		min-height: 173px;
	}
}
</style>
