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
			
			<!-- 日历热力图 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation14 chart-container">
					<div ref="calendarHeatmapRef" class="chart-ref"></div>
				</div>
			</el-col>
			
			<!-- 资金曲线 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation15 chart-container">
					<div ref="equityCurveRef" class="chart-ref"></div>
				</div>
			</el-col>
			
			<!-- 资金回撤曲线 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation16 chart-container">
					<div ref="drawdownCurveRef" class="chart-ref"></div>
				</div>
			</el-col>

			<!-- 平仓盈亏曲线 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation17 chart-container">
					<div ref="closedPnlCurveRef" class="chart-ref"></div>
				</div>
			</el-col>
			
			<!-- 多窗口绩效对比雷达图 - 占据全宽且高度加倍 -->
			<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
				<div class="grid-card-item grid-large-item grid-animation18 chart-container">
					<MultiWindowRadarChart :account-id="accountId" />
				</div>
			</el-col>
		</el-row>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import MultiWindowRadarChart from './components/MultiWindowRadarChart.vue';
import { 
	getAccountSummary, 
	getEquitySnapshots, 
	getLatestRollingMetric,
	getSymbolWinRate,
	getCumulativeStats,
	getDailyReturnsCalendar,
	getDrawdownCurve,  // 新增：回撤曲线数据接口
	type AccountSummary,
	type EquitySnapshot
} from './api';

// ==================== 配置 ====================
// TODO: 从 Pinia Store 或 URL 参数获取账户ID
const accountId = ref(1); // 假设账户ID为1

// ==================== 响应式工具函数 ====================
/**
 * 根据屏幕宽度获取响应式字体配置
 * 
 * @returns 包含各元素字体大小的配置对象
 */
const getResponsiveFontConfig = () => {
	const width = window.innerWidth;
	
	if (width < 480) {
		// 手机竖屏
		return {
			title: 13,
			subtitle: 9,
			axisName: 9,
			legend: 10,
			tooltip: 11,
			label: 10
		};
	} else if (width < 768) {
		// 平板或手机横屏
		return {
			title: 15,
			subtitle: 11,
			axisName: 11,
			legend: 11,
			tooltip: 12,
			label: 11
		};
	} else {
		// 桌面端
		return {
			title: 16,
			subtitle: 12,
			axisName: 12,
			legend: 12,
			tooltip: 12,
			label: 12
		};
	}
};

// ==================== 状态管理 ====================
const loading = ref(false);
const normalItems = ref<any[]>([]);
const symbolWinRateRef = ref();
const calendarHeatmapRef = ref();
const equityCurveRef = ref();
const drawdownCurveRef = ref();  // 新增：回撤曲线引用
const closedPnlCurveRef = ref();

// ==================== 辅助函数 ====================

/**
 * 根据数值返回颜色类名
 */
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

/**
 * 格式化金额显示
 */
const formatCurrency = (value: number | string) => {
	const num = typeof value === 'string' ? parseFloat(value) : value;
	return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

/**
 * 格式化百分比
 */
const formatPercent = (value: number | string | null, decimals: number = 2) => {
	if (value === null || value === undefined) return '0.00%';
	const num = typeof value === 'string' ? parseFloat(value) : value;
	return `${num.toFixed(decimals)}%`;
};

/**
 * 从后端数据构建 normalItems
 * @param summary 账户总览数据
 * @param latestBalance 最新权益余额（可选，来自日权益快照）
 * @param latestRiskRatio 最新风险度（可选，来自日权益快照）
 * @param latestFloatProfit 最新浮动盈亏（可选，来自日权益快照）
 * @param totalClosedPnl 累计平仓盈亏（可选，来自聚合查询）
 * @param totalCommission 累计手续费总数（可选，来自聚合查询）
 */
const buildNormalItems = (
	summary: AccountSummary, 
	latestBalance?: number, 
	latestRiskRatio?: number,
	latestFloatProfit?: number,
	totalClosedPnl?: number,
	totalCommission?: number
) => {
	// 优先使用传入的最新余额，否则默认为 0
	const currentEquity = latestBalance !== undefined ? latestBalance : 0;
	// 优先使用传入的最新风险度，否则默认为 0
	const riskRatio = latestRiskRatio !== undefined ? latestRiskRatio * 100 : 0; // 转换为百分比
	// 优先使用传入的最新浮动盈亏，否则默认为 0
	const floatProfit = latestFloatProfit !== undefined ? latestFloatProfit : 0;
	
	return [
		// === 资金与收益类 ===
		{ number: 1, label: '当前权益', value: formatCurrency(currentEquity), colorType: 'positive' },
		{ 
			number: 2, 
			label: '累计收益率/年化收益率', 
			value: `${formatPercent(summary.total_return)} / ${formatPercent(summary.annualized_return)}`, 
			colorType: 'positive' 
		},
		{ number: 3, label: '盈利因子', value: summary.overall_profit_factor ? parseFloat(summary.overall_profit_factor).toFixed(2) : '0.00', colorType: 'positive' },
		
		// === 风险与回撤类 ===
		{ number: 4, label: '最大回撤', value: formatPercent(summary.max_drawdown_all_time), colorType: 'negative' },
		{ number: 5, label: '风险度', value: `${riskRatio.toFixed(2)}%`, colorType: 'negative' },
		{ number: 6, label: '波动率', value: formatPercent(summary.latest_volatility_20d), colorType: 'negative' },
		
		// === 策略质量指标 ===
		{ number: 7, label: '夏普指数', value: summary.latest_sharpe_20d ? parseFloat(summary.latest_sharpe_20d).toFixed(2) : '0.00', colorType: 'positive' },
		{ number: 8, label: '卡玛指数', value: summary.calmar_ratio ? parseFloat(summary.calmar_ratio).toFixed(2) : '0.00', colorType: 'positive' },
		{ number: 9, label: '索提诺比率', value: summary.latest_sortino_20d ? parseFloat(summary.latest_sortino_20d).toFixed(2) : '0.00', colorType: 'positive' },
		{ number: 10, label: '胜率', value: formatPercent(summary.overall_win_rate), colorType: 'positive' },
		
		// === 持仓与交易行为 ===
		{ 
			number: 11, 
			label: '持仓总量/多单/空单', 
			value: `${summary.current_long_position + summary.current_short_position} / ${summary.current_long_position} / ${summary.current_short_position}`, 
			colorType: 'neutral' 
		},
		{ 
			number: 12, 
			label: '平均持仓时长/交易频率', 
			value: `${summary.avg_holding_days ? parseFloat(summary.avg_holding_days).toFixed(1) + '天' : '0.0天'} / ${summary.trading_frequency ? parseFloat(summary.trading_frequency).toFixed(2) + '次/日' : '0.00次/日'}`,
			colorType: 'neutral' 
		},
		
		// === 盈亏详情 ===
		{ 
			number: 13, 
			label: '平仓盈亏/持仓盈亏', 
			value: `${formatCurrency(summary.closed_profit_total || totalClosedPnl || 0)} / ${formatCurrency(latestFloatProfit || 0)}`,
			colorType: ((parseFloat(summary.closed_profit_total || '0') || totalClosedPnl || 0) + (latestFloatProfit || 0)) >= 0 ? 'positive' : 'negative'
		},
		{ 
			number: 14, 
			label: '手续费总数', 
			value: formatCurrency(summary.commission_total || totalCommission || 0), 
			colorType: 'neutral' 
		},
		
		// === 连续表现 ===
		{ 
			number: 15, 
			label: '连续亏损/最大连盈', 
			value: `${summary.consecutive_losses}次 / ${summary.consecutive_wins}次`, 
			colorType: 'negative' 
		},
		{ 
			number: 16, 
			label: '最大盈利/最大亏损', 
			value: `${summary.best_single_trade ? formatCurrency(summary.best_single_trade) : '¥0.00'} / ${summary.worst_single_trade ? formatCurrency(summary.worst_single_trade) : '¥0.00'}`, 
			colorType: 'positive' 
		}
	];
};

// ==================== 图表初始化 ====================

/**
 * 初始化品种胜率统计图表
 */
const initSymbolWinRateChart = async () => {
	if (!symbolWinRateRef.value) return;
	
	const chart = echarts.init(symbolWinRateRef.value);
	
	// 获取响应式字体配置
	const fontConfig = getResponsiveFontConfig();
	
	// 从后端获取真实数据
	try {
		const res = await getSymbolWinRate(accountId.value);
		
		// 确保 res.data 存在且为数组
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			ElMessage.warning('暂无品种交易数据');
			return;
		}
		
		const symbolData = res.data;
		
		const option = {
		title: {
			text: '品种胜率统计',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: fontConfig.title,
				fontWeight: 'bold'
			}
		},
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			formatter: (params: any) => {
				const data = params[0];
				const item = symbolData[data.dataIndex];
				return `${data.name}<br/>胜率: ${data.value}%<br/>交易次数: ${item.trades}<br/>多单: ${item.LongNum} / 空单: ${item.ShortNum}<br/>盈利: ¥${item.profit.toLocaleString()}`;
			},
			textStyle: {
				fontSize: fontConfig.tooltip
			}
		},
		grid: {
			left: window.innerWidth < 480 ? '8%' : '3%',
			right: window.innerWidth < 480 ? '5%' : '4%',
			bottom: window.innerWidth < 480 ? '15%' : '3%',
			top: '15%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: symbolData.map(item => item.name),
			axisLabel: {
				interval: 0,
				rotate: window.innerWidth < 480 ? 45 : 30,
				fontSize: fontConfig.axisName,
				// 小屏幕时缩短过长的品种名称
				formatter: (value: string) => {
					if (window.innerWidth < 480 && value.length > 6) {
						return value.substring(0, 5) + '...';
					}
					return value;
				}
			}
		},
		yAxis: {
			type: 'value',
			name: '胜率 (%)',
			max: 100,
			nameTextStyle: {
				fontSize: fontConfig.axisName
			},
			axisLabel: {
				formatter: '{value}%',
				fontSize: fontConfig.axisName
			}
		},
		series: [
			{
				name: '胜率',
				type: 'bar',
				data: symbolData.map(item => item.winRate),
				itemStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: '#83bff6' },
						{ offset: 0.5, color: '#188df0' },
						{ offset: 1, color: '#188df0' }
					])
				},
				barWidth: window.innerWidth < 480 ? '50%' : '60%',
				label: {
					show: window.innerWidth >= 480, // 小屏幕隐藏标签避免拥挤
					position: 'top',
					formatter: '{c}%',
					fontSize: fontConfig.label
				}
			}
		]
	};
	
	chart.setOption(option);
	window.addEventListener('resize', () => chart.resize());
		
	} catch (error: any) {
		console.error('加载品种胜率数据失败:', error);
		ElMessage.error('加载品种胜率数据失败');
	}
};

/**
 * 初始化日历热力图（日收益率）
 */
const initCalendarHeatmap = async () => {
	if (!calendarHeatmapRef.value) return;
	
	const chart = echarts.init(calendarHeatmapRef.value);
	
	// 获取响应式字体配置
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;
	
	try {
		// 从后端获取真实数据
		const res = await getDailyReturnsCalendar(accountId.value);
		
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			ElMessage.warning('暂无交易日收益数据');
			return;
		}
		
		const calendarData = res.data;
		
		// 转换为 ECharts heatmap 需要的格式：[month, day, value]
		// month: 0-11, day: 0-30, value: daily_return
		const heatmapData = calendarData.map(item => [
			item.month - 1,  // ECharts月份从0开始
			item.day - 1,    // ECharts日期从0开始
			item.daily_return
		]);
		
		// 获取年份范围
		const years = [...new Set(calendarData.map(item => item.year))].sort();
		const currentYear = years[years.length - 1]; // 使用最新年份
		
		const option = {
			title: {
				text: '交易日收益热力图',
				left: 'center',
				top: 10,
				textStyle: {
					fontSize: fontConfig.title,
					fontWeight: 'bold'
				}
			},
			tooltip: {
				position: 'top',
				formatter: (params: any) => {
					const month = params.data[0] + 1;
					const day = params.data[1] + 1;
					const value = params.data[2];
					const color = value >= 0 ? '🔴' : '🟢';
					return `${currentYear}年${month}月${day}日<br/>${color} 收益率: ${value.toFixed(2)}%`;
				},
				textStyle: {
					fontSize: fontConfig.tooltip
				}
			},
			grid: {
				left: isMobile ? '8%' : '3%',
				right: isMobile ? '5%' : '4%',
				bottom: isMobile ? '15%' : '10%',
				top: isMobile ? '18%' : '15%',
				containLabel: true
			},
			xAxis: {
				type: 'category',
				data: Array.from({ length: 31 }, (_, i) => i + 1),
				splitArea: {
					show: true
				},
				axisLabel: {
					fontSize: fontConfig.axisName,
					interval: isMobile ? 4 : 2  // 移动端每5天显示一个标签
				}
			},
			yAxis: {
				type: 'category',
				data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
				splitArea: {
					show: true
				},
				axisLabel: {
					fontSize: fontConfig.axisName
				}
			},
			visualMap: {
				min: -5,
				max: 5,
				calculable: true,
				orient: 'horizontal',
				left: 'center',
				bottom: isMobile ? '2%' : '1%',
				inRange: {
					color: [
						'#16a34a',  // 深绿（<-5%）
						'#4ade80',  // 浅绿（-5% ~ -1%）
						'#f3f4f6',  // 白色（-1% ~ 1%）
						'#fb7185',  // 浅红（1% ~ 5%）
						'#dc2626'   // 深红（>5%）
					]
				},
				textStyle: {
					fontSize: fontConfig.legend
				}
			},
			series: [{
				name: '日收益率',
				type: 'heatmap',
				data: heatmapData,
				label: {
					show: !isMobile,  // 小屏幕隐藏标签避免拥挤
					fontSize: fontConfig.label
				},
				emphasis: {
					itemStyle: {
						shadowBlur: 10,
						shadowColor: 'rgba(0, 0, 0, 0.5)'
					}
				}
			}]
		};
		
		chart.setOption(option);
		window.addEventListener('resize', () => chart.resize());
		
	} catch (error: any) {
		console.error('加载日历热力图数据失败:', error);
		ElMessage.error('加载日历热力图数据失败');
	}
};

/**
 * 初始化资金曲线图表
 */
const initEquityCurveChart = (snapshots: EquitySnapshot[]) => {
	if (!equityCurveRef.value || !snapshots.length) return;
	
	const chart = echarts.init(equityCurveRef.value);
	
	// 获取响应式字体配置
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;
	
	// 从快照数据提取日期和权益
	const dates = snapshots.map(s => s.trade_date);
	const equities = snapshots.map(s => parseFloat(s.balance));
	
	// 计算收益率序列
	const returns = equities.map((equity, index) => {
		if (index === 0) return 0;
		const prevEquity = equities[index - 1];
		return prevEquity > 0 ? ((equity - prevEquity) / prevEquity * 100) : 0;
	});
	
	const option = {
		title: {
			text: '资金曲线',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: fontConfig.title,
				fontWeight: 'bold'
			}
		},
		tooltip: {
			trigger: 'axis',
			formatter: (params: any) => {
				const equity = params[0];
				const ret = params[1];
				return `${equity.axisValue}<br/>权益: ¥${parseFloat(equity.value).toLocaleString()}<br/>收益率: ${parseFloat(ret.value).toFixed(2)}%`;
			},
			textStyle: {
				fontSize: fontConfig.tooltip
			}
		},
		legend: {
			data: ['账户权益', '日收益率'],
			top: isMobile ? 30 : 35,
			textStyle: {
				fontSize: fontConfig.legend
			}
		},
		grid: {
			left: isMobile ? '10%' : '3%',
			right: isMobile ? '10%' : '4%',
			bottom: isMobile ? '12%' : '3%',
			top: isMobile ? '22%' : '20%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: dates,
			axisLabel: {
				fontSize: fontConfig.axisName,
				// 小屏幕时简化日期显示
				formatter: (value: string) => {
					if (isMobile && value.length > 10) {
						// 只显示月-日，如 "2024-01-15" -> "01-15"
						return value.substring(5);
					}
					return value;
				}
			}
		},
		yAxis: [
			{
				type: 'value',
				name: isMobile ? '权益(万)' : '账户权益 (元)',
				position: 'left',
				nameTextStyle: {
					fontSize: fontConfig.axisName
				},
				axisLabel: {
					formatter: (value: number) => {
						if (isMobile) {
							return `${(value / 10000).toFixed(0)}万`;
						}
						return `¥${(value / 10000).toFixed(0)}万`;
					},
					fontSize: fontConfig.axisName
				}
			},
			{
				type: 'value',
				name: '收益率 (%)',
				position: 'right',
				nameTextStyle: {
					fontSize: fontConfig.axisName
				},
				axisLabel: {
					formatter: '{value}%',
					fontSize: fontConfig.axisName
				}
			}
		],
		series: [
			{
				name: '账户权益',
				type: 'line',
				smooth: true,
				data: equities,
				yAxisIndex: 0,
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(24, 141, 240, 0.3)' },
						{ offset: 1, color: 'rgba(24, 141, 240, 0.05)' }
					])
				},
				lineStyle: {
					color: '#188df0',
					width: isMobile ? 1.5 : 2
				},
				itemStyle: {
					color: '#188df0'
				},
				symbolSize: isMobile ? 4 : 6
			},
			{
				name: '日收益率',
				type: 'line',
				smooth: true,
				data: returns,
				yAxisIndex: 1,
				lineStyle: {
					color: '#ff6b6b',
					width: isMobile ? 1.5 : 2,
					type: 'dashed'
				},
				itemStyle: {
					color: '#ff6b6b'
				},
				symbolSize: isMobile ? 4 : 6
			}
		]
	};
	
	chart.setOption(option);
	window.addEventListener('resize', () => chart.resize());
};

/**
 * 初始化资金回撤曲线图表
 */
const initDrawdownCurveChart = async () => {
	if (!drawdownCurveRef.value) return;
	
	const chart = echarts.init(drawdownCurveRef.value);
	
	// 获取响应式字体配置
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;
	
	try {
		// 从后端获取真实数据
		const res = await getDrawdownCurve(accountId.value);
		
		if (res.code !== 2000 || !res.data || !Array.isArray(res.data) || res.data.length === 0) {
			ElMessage.warning('暂无回撤数据');
			return;
		}
		
		const drawdownData = res.data;
		
		// 提取日期和回撤百分比
		const dates = drawdownData.map(item => item.date);
		const drawdownPcts = drawdownData.map(item => item.drawdown_pct);
		
		// 找出最大回撤（最小值）
		const maxDrawdown = Math.min(...drawdownPcts);
		
		const option = {
			title: {
				text: '资金回撤曲线',
				left: 'center',
				top: 10,
				textStyle: {
					fontSize: fontConfig.title,
					fontWeight: 'bold'
				}
			},
			tooltip: {
				trigger: 'axis',
				formatter: (params: any) => {
					const data = params[0];
					const date = data.axisValue;
					const value = parseFloat(data.value);
					const color = value <= -5 ? '🔴' : value <= -2 ? '🟠' : '⚪';
					return `${date}<br/>${color} 回撤: ${value.toFixed(2)}%`;
				},
				textStyle: {
					fontSize: fontConfig.tooltip
				}
			},
			grid: {
				left: isMobile ? '10%' : '3%',
				right: isMobile ? '5%' : '4%',
				bottom: isMobile ? '12%' : '3%',
				top: isMobile ? '18%' : '15%',
				containLabel: true
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: dates,
				axisLabel: {
					fontSize: fontConfig.axisName,
					// 小屏幕时简化日期显示
					formatter: (value: string) => {
						if (isMobile && value.length > 10) {
							return value.substring(5);
						}
						return value;
					}
				}
			},
			yAxis: {
				type: 'value',
				name: '回撤 (%)',
				max: 0,  // Y轴最大值设为0，只显示负值区域
				min: Math.floor(maxDrawdown * 1.2),  // 留出20%边距
				nameTextStyle: {
					fontSize: fontConfig.axisName
				},
				axisLabel: {
					formatter: '{value}%',
					fontSize: fontConfig.axisName
				},
				splitLine: {
					lineStyle: {
						color: '#e0e0e0',
						type: 'dashed'
					}
				}
			},
			visualMap: {
				show: false,
				dimension: 1,
				pieces: [
					{ lte: -10, color: '#dc2626' },  // 严重回撤 <-10%
					{ gt: -10, lte: -5, color: '#fb7185' },  // 中度回撤 -10% ~ -5%
					{ gt: -5, lte: -2, color: '#fbbf24' },  // 轻度回撤 -5% ~ -2%
					{ gt: -2, lte: 0, color: '#94a3b8' }  // 正常波动 -2% ~ 0%
				]
			},
			series: [{
				name: '回撤百分比',
				type: 'line',
				smooth: true,
				data: drawdownPcts,
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(220, 38, 38, 0.3)' },
						{ offset: 1, color: 'rgba(220, 38, 38, 0.05)' }
					])
				},
				lineStyle: {
					color: '#dc2626',
					width: isMobile ? 1.5 : 2
				},
				itemStyle: {
					color: '#dc2626'
				},
				symbolSize: isMobile ? 4 : 6,
				markLine: {
					silent: true,
					lineStyle: {
						color: '#ff4d4f',
						type: 'dashed',
						width: 2
					},
					label: {
						position: 'end',
						formatter: '最大回撤: {c}%',
						fontSize: fontConfig.label,
						color: '#ff4d4f'
					},
					data: [{
						yAxis: maxDrawdown
					}]
				},
				markPoint: {
					data: drawdownData
						.filter(item => item.is_new_peak)
						.map(item => ({
							name: '新高',
							coord: [dates.indexOf(item.date), item.drawdown_pct],
							value: '新高',
							itemStyle: {
								color: '#52c41a'
							},
							label: {
								show: false
							}
						}))
				}
			}]
		};
		
		chart.setOption(option);
		window.addEventListener('resize', () => chart.resize());
		
	} catch (error: any) {
		console.error('加载回撤曲线数据失败:', error);
		ElMessage.error('加载回撤曲线数据失败');
	}
};

/**
 * 初始化平仓盈亏曲线图表
 */
const initClosedPnlCurveChart = (snapshots: EquitySnapshot[]) => {
	if (!closedPnlCurveRef.value || !snapshots.length) return;
	
	const chart = echarts.init(closedPnlCurveRef.value);
	
	// 获取响应式字体配置
	const fontConfig = getResponsiveFontConfig();
	const isMobile = window.innerWidth < 480;
	
	// 从快照数据提取日期和当日平仓盈亏
	const dates = snapshots.map(s => s.trade_date);
	const dailyClosedPnls = snapshots.map(s => parseFloat(s.closed_pnl || '0'));
	
	// 计算累计平仓盈亏序列
	let cumulativePnl = 0;
	const cumulativePnls = dailyClosedPnls.map(pnl => {
		cumulativePnl += pnl;
		return cumulativePnl;
	});
	
	const option = {
		title: {
			text: isMobile ? '平仓盈亏曲线' : '平仓盈亏曲线（纯策略盈利）',
			left: 'center',
			top: 10,
			textStyle: {
				fontSize: fontConfig.title,
				fontWeight: 'bold'
			}
		},
		tooltip: {
			trigger: 'axis',
			formatter: (params: any) => {
				const pnl = params[0];
				return `${pnl.axisValue}<br/>累计平仓盈亏: ¥${parseFloat(pnl.value).toLocaleString()}`;
			},
			textStyle: {
				fontSize: fontConfig.tooltip
			}
		},
		grid: {
			left: isMobile ? '10%' : '3%',
			right: isMobile ? '5%' : '4%',
			bottom: isMobile ? '12%' : '3%',
			top: isMobile ? '18%' : '15%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: dates,
			axisLabel: {
				fontSize: fontConfig.axisName,
				// 小屏幕时简化日期显示
				formatter: (value: string) => {
					if (isMobile && value.length > 10) {
						return value.substring(5);
					}
					return value;
				}
			}
		},
		yAxis: {
			type: 'value',
			name: isMobile ? '盈亏(万)' : '累计平仓盈亏 (元)',
			nameTextStyle: {
				fontSize: fontConfig.axisName
			},
			axisLabel: {
				formatter: (value: number) => {
					if (isMobile) {
						return `${(value / 10000).toFixed(0)}万`;
					}
					return `¥${(value / 10000).toFixed(0)}万`;
				},
				fontSize: fontConfig.axisName
			}
		},
		series: [
			{
				name: '累计平仓盈亏',
				type: 'line',
				smooth: true,
				data: cumulativePnls,
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(102, 187, 106, 0.3)' },
						{ offset: 1, color: 'rgba(102, 187, 106, 0.05)' }
					])
				},
				lineStyle: {
					color: '#66bb6a',
					width: isMobile ? 1.5 : 2
				},
				itemStyle: {
					color: '#66bb6a'
				},
				symbolSize: isMobile ? 4 : 6,
				markLine: {
					silent: true,
					data: [{ yAxis: 0, lineStyle: { color: '#999', type: 'dashed' } }]
				}
			}
		]
	};
	
	chart.setOption(option);
	window.addEventListener('resize', () => chart.resize());
};

// ==================== 数据加载 ====================

/**
 * 加载 Dashboard 数据
 */
const loadDashboardData = async () => {
	loading.value = true;
	
	try {
		// Step 1: 获取账户总览
		const summaryRes = await getAccountSummary(accountId.value);
		
		// 注意：CustomPagination 返回的 data 直接是数组，不是 {results: []}
		if (summaryRes.code !== 2000 || !summaryRes.data || summaryRes.data.length === 0) {
			ElMessage.warning('未找到账户绩效数据');
			return;
		}
		
		const summary = summaryRes.data[0];
		
		// Step 2: 获取日权益快照（用于资金曲线和最新余额）
		const endDate = new Date();
		const startDate = new Date();
		startDate.setDate(startDate.getDate() - 100);
		
		const snapshotsRes = await getEquitySnapshots({
			account: accountId.value,
			trade_date__gte: startDate.toISOString().split('T')[0],
			trade_date__lte: endDate.toISOString().split('T')[0],
			ordering: 'trade_date',
			page_size: 100
		});
		
		let latestBalance = 0;
		let latestRiskRatio = 0;
		let latestFloatProfit = 0;
		
		if (snapshotsRes.code === 2000 && snapshotsRes.data && snapshotsRes.data.length > 0) {
			// 提取最新一天的余额和风险度
			const latestSnapshot = snapshotsRes.data[snapshotsRes.data.length - 1];
			latestBalance = parseFloat(latestSnapshot.balance);
			// 提取最新一天的风险度，增加空值保护
			latestRiskRatio = latestSnapshot.risk_ratio !== undefined && latestSnapshot.risk_ratio !== null 
				? parseFloat(latestSnapshot.risk_ratio) 
				: 0;
			// 提取最新一天的浮动盈亏
			latestFloatProfit = latestSnapshot.float_profit !== undefined && latestSnapshot.float_profit !== null 
				? parseFloat(latestSnapshot.float_profit) 
				: 0;
		
			// 初始化资金曲线图表和平仓盈亏曲线图表
			nextTick(() => {
				initEquityCurveChart(snapshotsRes.data);
				initClosedPnlCurveChart(snapshotsRes.data);
			});
		}
		
		// Step 3: 获取累计统计数据（平仓盈亏、手续费总数）
		let totalClosedPnl = 0;
		let totalCommission = 0;
		
		try {
			const cumulativeStatsRes: any = await getCumulativeStats(accountId.value);
			if (cumulativeStatsRes.code === 2000 && cumulativeStatsRes.data) {
				totalClosedPnl = Number(cumulativeStatsRes.data.total_closed_pnl) || 0;
				totalCommission = Number(cumulativeStatsRes.data.total_commission) || 0;
			}
		} catch (error) {
			console.warn('获取累计统计数据失败:', error);
			// 失败时使用默认值 0，不影响其他数据展示
		}
		
		// Step 4: 构建 normalItems（传入所有最新数据）
		normalItems.value = buildNormalItems(
			summary, 
			latestBalance, 
			latestRiskRatio, 
			latestFloatProfit,
			totalClosedPnl,
			totalCommission
		);

		ElMessage.success('数据加载成功');
		
	} catch (error: any) {
		console.error('加载 Dashboard 数据失败:', error);
		// request.ts 拦截器已经显示了错误消息，这里只记录日志
	} finally {
		loading.value = false;
	}
};

// ==================== 生命周期 ====================

onMounted(() => {
	// 加载真实数据
	loadDashboardData();
	
	// 初始化图表（在数据加载完成后调用）
	nextTick(() => {
		initSymbolWinRateChart();
		initCalendarHeatmap();
		initDrawdownCurveChart();  // 新增：初始化回撤曲线
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
						font-size: 24px;
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
					overflow: hidden; // 防止内容溢出

					.grid-content {
						.grid-value {
							font-size: 20px;
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
								overflow: hidden;
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
					overflow: hidden; // 防止内容溢出

					.grid-content {
						.grid-value {
							font-size: 12px;
						}

						.grid-label {
							font-size: 12px;
						}
					}
					
					&.grid-large-item {
						min-height: 208px;
						
						&.chart-container {
							.chart-ref {
								min-height: 173px; // 208px - padding(10px*2) - border
								width: 100%;
								overflow: hidden; // 防止内容溢出
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