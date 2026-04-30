<template>
	<div class="home-container">
		<el-row :gutter="15" class="grid-container">
			<!-- 前20个普通网格 -->
			<el-col
				:xs="12"
				:sm="8"
				:md="6"
				:lg="6"
				:xl="6"
				v-for="(item, index) in normalItems"
				:key="index"
				class="grid-item-wrapper"
			>
				<div class="grid-card-item" :class="`grid-animation${index}`">
					<div class="grid-content flex-margin">
						<div class="grid-value" :class="getValueColor(item.value, item.colorType)">
							{{ item.value }}
						</div>
						<div class="grid-label">{{ item.label }}</div>
					</div>
				</div>
			</el-col>
			
			<!-- 品种胜率统计 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation13 chart-container">
					<div ref="symbolWinRateRef" class="chart-ref"></div>
				</div>
			</el-col>
			
			<!-- 资金曲线 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation14 chart-container">
					<div ref="equityCurveRef" class="chart-ref"></div>
				</div>
			</el-col>
		</el-row>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import { equityCurveData, symbolWinRateData, metricsData } from './mockData';

// 辅助函数：根据数值返回颜色类名
const getValueColor = (value: any, type: string) => {
	if (type === 'positive') {
		// 越大越好（如收益率、盈利）
		const num = parseFloat(String(value).replace(/[¥,%]/g, ''));
		return num >= 0 ? 'text-success' : 'text-danger';
	} else if (type === 'negative') {
		// 越小越好（如回撤、风险）
		const num = parseFloat(String(value).replace(/[%,]/g, ''));
		return num <= 0 ? 'text-success' : 'text-warning';
	} else if (type === 'neutral') {
		// 中性指标
		return 'text-primary';
	}
	return 'text-primary';
};

const normalItems = ref([
	// === 资金与收益类 ===
	{ number: 1, label: '当前权益', value: `¥${metricsData.currentEquity.toLocaleString()}`, colorType: 'positive' },
	{ number: 2, label: '累计收益率', value: `${metricsData.cumulativeReturn}%`, colorType: 'positive' },
	{ number: 3, label: '年化收益率', value: `${metricsData.annualizedReturn}%`, colorType: 'positive' },
	{ number: 4, label: '盈利因子', value: metricsData.profitFactor.toFixed(2), colorType: 'positive' },
	
	// === 风险与回撤类 ===
	{ number: 5, label: '最大回撤', value: `${metricsData.maxDrawdown}%`, colorType: 'negative' },
	{ number: 6, label: '风险度', value: `${metricsData.riskLevel}%`, colorType: 'negative' },
	{ number: 7, label: '波动率', value: `${metricsData.volatility}%`, colorType: 'negative' },
	
	// === 策略质量指标 ===
	{ number: 8, label: '夏普指数', value: metricsData.sharpeRatio.toFixed(2), colorType: 'positive' },
	{ number: 9, label: '卡玛指数', value: metricsData.calmarRatio.toFixed(2), colorType: 'positive' },
	{ number: 10, label: '索提诺比率', value: metricsData.sortinoRatio.toFixed(2), colorType: 'positive' },
	{ number: 11, label: '胜率', value: `${metricsData.winRate}%`, colorType: 'positive' },
	
	// === 持仓与交易行为 ===
	{ number: 12, label: '持仓总量', value: `${metricsData.totalPosition}手`, colorType: 'neutral' },
	{ number: 13, label: '多单/空单', value: `${metricsData.longPosition}/${metricsData.shortPosition}`, colorType: 'neutral' },
	{ number: 14, label: '平均持仓时长', value: `${metricsData.avgHoldingTime}天`, colorType: 'neutral' },
	{ number: 15, label: '交易频率', value: `${metricsData.tradingFrequency.daily}次/日`, colorType: 'neutral' },
	
	// === 盈亏详情 ===
	{ number: 16, label: '平仓盈亏', value: `¥${metricsData.closedProfit.toLocaleString()}`, colorType: 'positive' },
	{ number: 17, label: '持仓盈亏', value: `¥${metricsData.unrealizedProfit.toLocaleString()}`, colorType: 'positive' },
	{ number: 18, label: '手续费总数', value: `¥${metricsData.totalCommission.toLocaleString()}`, colorType: 'neutral' },
	
	// === 连续表现 ===
	{ number: 19, label: '连续亏损', value: `${metricsData.consecutiveLosses}次`, colorType: 'negative' },
	{ number: 20, label: '最大连盈', value: `${metricsData.consecutiveWins}次`, colorType: 'positive' },
]);

const symbolWinRateRef = ref();
const equityCurveRef = ref();

// 初始化品种胜率统计图表
const initSymbolWinRateChart = () => {
	if (!symbolWinRateRef.value) return;
	
	const chart = echarts.init(symbolWinRateRef.value);
	const option = {
		title: {
			text: '品种胜率统计',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: 16,
				fontWeight: 'bold'
			}
		},
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			formatter: (params: any) => {
				const data = params[0];
				return `${data.name}<br/>胜率: ${data.value}%<br/>交易次数: ${symbolWinRateData[data.dataIndex].trades}<br/>盈利: ¥${symbolWinRateData[data.dataIndex].profit.toLocaleString()}`;
			}
		},
		grid: {
			left: '3%',
			right: '4%',
			bottom: '3%',
			top: '15%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: symbolWinRateData.map(item => item.name),
			axisLabel: {
				interval: 0,
				rotate: 30
			}
		},
		yAxis: {
			type: 'value',
			name: '胜率 (%)',
			max: 100,
			axisLabel: {
				formatter: '{value}%'
			}
		},
		series: [
			{
				name: '胜率',
				type: 'bar',
				data: symbolWinRateData.map(item => item.winRate),
				itemStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: '#83bff6' },
						{ offset: 0.5, color: '#188df0' },
						{ offset: 1, color: '#188df0' }
					])
				},
				barWidth: '60%',
				label: {
					show: true,
					position: 'top',
					formatter: '{c}%'
				}
			}
		]
	};
	
	chart.setOption(option);
	window.addEventListener('resize', () => chart.resize());
};

// 初始化资金曲线图表
const initEquityCurveChart = () => {
	if (!equityCurveRef.value) return;
	
	const chart = echarts.init(equityCurveRef.value);
	const option = {
		title: {
			text: '资金曲线',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: 16,
				fontWeight: 'bold'
			}
		},
		tooltip: {
			trigger: 'axis',
			formatter: (params: any) => {
				const equity = params[0];
				const returns = params[1];
				return `${equity.axisValue}<br/>权益: ¥${equity.value.toLocaleString()}<br/>收益率: ${returns.value}%`;
			}
		},
		legend: {
			data: ['账户权益', '月度收益率'],
			top: 35
		},
		grid: {
			left: '3%',
			right: '4%',
			bottom: '3%',
			top: '20%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: equityCurveData.dates
		},
		yAxis: [
			{
				type: 'value',
				name: '账户权益 (元)',
				position: 'left',
				axisLabel: {
					formatter: (value: number) => `¥${(value / 10000).toFixed(0)}万`
				}
			},
			{
				type: 'value',
				name: '收益率 (%)',
				position: 'right',
				axisLabel: {
					formatter: '{value}%'
				}
			}
		],
		series: [
			{
				name: '账户权益',
				type: 'line',
				smooth: true,
				data: equityCurveData.equity,
				yAxisIndex: 0,
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(24, 141, 240, 0.3)' },
						{ offset: 1, color: 'rgba(24, 141, 240, 0.05)' }
					])
				},
				lineStyle: {
					color: '#188df0',
					width: 2
				},
				itemStyle: {
					color: '#188df0'
				}
			},
			{
				name: '月度收益率',
				type: 'line',
				smooth: true,
				data: equityCurveData.returns,
				yAxisIndex: 1,
				lineStyle: {
					color: '#ff6b6b',
					width: 2,
					type: 'dashed'
				},
				itemStyle: {
					color: '#ff6b6b'
				}
			}
		]
	};
	
	chart.setOption(option);
	window.addEventListener('resize', () => chart.resize());
};

// 页面加载时初始化图表
onMounted(() => {
	nextTick(() => {
		initSymbolWinRateChart();
		initEquityCurveChart();
	});
});
</script>

<style scoped lang="scss">
$gridLength: 16;

.home-container {
	overflow: hidden;
	padding: 15px;

	.grid-container {
		.grid-item-wrapper {
			margin-bottom: 15px;

			.grid-card-item {
				width: 100%;
				min-height: 150px;
				border-radius: 8px;
				transition: all ease 0.3s;
				padding: 20px;
				overflow: hidden;
				background: linear-gradient(135deg, var(--el-color-white) 0%, #f8f9fa 100%);
				color: var(--el-text-color-primary);
				border: 1px solid var(--next-border-color-light);
				box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
				position: relative;

				&::before {
					content: '';
					position: absolute;
					top: 0;
					left: 0;
					right: 0;
					height: 3px;
					background: linear-gradient(90deg, var(--el-color-primary), var(--el-color-primary-light-3));
					opacity: 0;
					transition: opacity 0.3s ease;
				}

				&:hover {
					box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
					transform: translateY(-6px);
					transition: all ease 0.3s;
					
					&::before {
						opacity: 1;
					}
					
					.grid-value {
						transform: scale(1.05);
						transition: transform 0.3s ease;
					}
				}

				.grid-content {
					display: flex;
					flex-direction: column;
					align-items: center;
					justify-content: center;
					height: 100%;
					min-height: 110px;

					.grid-value {
						font-size: 32px;
						font-weight: bold;
						margin-bottom: 8px;
						line-height: 1.2;
						text-align: center;
						transition: all 0.3s ease;
						
						// 主色调（中性指标）
						&.text-primary {
							color: var(--el-color-primary);
						}
						
						// 成功色（正向指标）
						&.text-success {
							color: #52c41a;
							text-shadow: 0 2px 4px rgba(82, 196, 26, 0.2);
						}
						
						// 警告色（需要注意的指标）
						&.text-warning {
							color: #faad14;
							text-shadow: 0 2px 4px rgba(250, 173, 20, 0.2);
						}
						
						// 危险色（负向指标）
						&.text-danger {
							color: #ff4d4f;
							text-shadow: 0 2px 4px rgba(255, 77, 79, 0.2);
						}
					}

					.grid-label {
						font-size: 14px;
						color: var(--el-text-color-regular);
						text-align: center;
						font-weight: 500;
					}
				}
				
				// 大卡片样式（品种胜率统计、资金曲线）
				&.grid-large-item {
					min-height: 315px; // 150px * 2 + 15px gap
					padding: 15px;
					background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
					
					// 图表容器，确保铺满整个卡片
					&.chart-container {
						display: flex;
						flex-direction: column;
						
						.chart-ref {
							width: 100%;
							height: 100%;
							flex: 1;
							min-height: 280px; // 315px - padding(15px*2) - border approx
						}
					}
				}
			}

			// 动画效果
			@for $i from 0 through ($gridLength - 1) {
				.grid-animation#{$i} {
					opacity: 0;
					animation-name: gridFadeIn;
					animation-duration: 0.5s;
					animation-fill-mode: forwards;
					animation-delay: calc($i / 20) + s;
				}
			}
		}
	}
}

// 响应式调整
@media screen and (max-width: 768px) {
	.home-container {
		padding: 10px;

		.grid-container {
			.grid-item-wrapper {
				margin-bottom: 10px;

				.grid-card-item {
					min-height: 120px;
					padding: 15px;

					.grid-content {
						.grid-number {
							font-size: 36px;
						}

						.grid-label {
							font-size: 12px;
						}
					}
					
					&.grid-large-item {
						min-height: 250px;
						
						&.chart-container {
							.chart-ref {
								min-height: 215px; // 250px - padding(10px*2) - border
							}
						}
					}
				}
			}
		}
	}
}

@media screen and (max-width: 480px) {
	.home-container {
		padding: 8px;

		.grid-container {
			.grid-item-wrapper {
				margin-bottom: 8px;

				.grid-card-item {
					min-height: 100px;
					padding: 12px;

					.grid-content {
						.grid-number {
							font-size: 28px;
						}

						.grid-label {
							font-size: 11px;
						}
					}
					
					&.grid-large-item {
						min-height: 208px;
						
						&.chart-container {
							.chart-ref {
								min-height: 173px; // 208px - padding(10px*2) - border
							}
						}
					}
				}
			}
		}
	}
}

// 淡入动画
@keyframes gridFadeIn {
	from {
		opacity: 0;
		transform: translateY(20px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}
</style>
