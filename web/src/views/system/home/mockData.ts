// 资金曲线模拟数据
export const equityCurveData = {
	dates: [
		'2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
		'2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'
	],
	equity: [
		100000, 105000, 103000, 108000, 112000, 110000,
		115000, 118000, 122000, 120000, 125000, 128000
	],
	returns: [
		0, 5.0, -1.9, 4.9, 3.7, -1.8,
		4.5, 2.6, 3.4, -1.6, 4.2, 2.4
	]
};

// 品种胜率统计模拟数据
export const symbolWinRateData = [
	{ name: '螺纹钢', winRate: 68.5, trades: 45, profit: 12500 },
	{ name: '铁矿石', winRate: 72.3, trades: 38, profit: 15800 },
	{ name: 'PTA', winRate: 65.2, trades: 52, profit: 9800 },
	{ name: '甲醇', winRate: 58.7, trades: 41, profit: 7200 },
	{ name: '豆粕', winRate: 75.0, trades: 32, profit: 18500 },
	{ name: '棉花', winRate: 62.4, trades: 29, profit: 6500 },
	{ name: '白糖', winRate: 70.1, trades: 35, profit: 11200 },
	{ name: '原油', winRate: 55.8, trades: 27, profit: 5800 },
	{ name: '黄金', winRate: 78.2, trades: 23, profit: 21000 },
	{ name: '铜', winRate: 66.9, trades: 31, profit: 10500 }
];

// 其他指标模拟数据
export const metricsData = {
	// === 资金与收益类 ===
	currentEquity: 128000,           // 当前权益
	cumulativeReturn: 28.0,          // 累计收益率 (%)
	annualizedReturn: 32.5,          // 年化收益率 (%)
	profitFactor: 2.35,              // 盈利因子
	
	// === 风险与回撤类 ===
	maxDrawdown: -8.5,               // 最大回撤 (%)
	riskLevel: 15.2,                 // 风险度 (%)
	volatility: 12.8,                // 波动率 (%)
	
	// === 策略质量指标 ===
	sharpeRatio: 1.85,               // 夏普指数
	calmarRatio: 3.82,               // 卡玛指数
	sortinoRatio: 2.45,              // 索提诺比率
	winRate: 67.3,                   // 胜率 (%)
	
	// === 持仓与交易行为 ===
	totalPosition: 156,              // 持仓总量
	longPosition: 89,                // 多单总数
	shortPosition: 67,               // 空单总数
	avgHoldingTime: 3.5,             // 平均持仓时长 (天)
	tradingFrequency: {              // 交易频率
		daily: 2.3,                  // 日均交易次数
		weekly: 16.1,                // 周均交易次数
		monthly: 69.0                // 月均交易次数
	},
	
	// === 盈亏详情 ===
	closedProfit: 18500,             // 平仓盈亏
	unrealizedProfit: 3200,          // 持仓盈亏
	totalCommission: 2850,           // 手续费总数
	
	// === 连续表现 ===
	consecutiveLosses: 3,            // 连续亏损次数
	consecutiveWins: 8               // 最大连续盈利
};
