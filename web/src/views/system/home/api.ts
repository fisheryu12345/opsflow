/**
 * Dashboard 绩效数据 API
 * 
 * 💡 用途：
 * - 获取账户绩效总览（Dashboard 首页数据）
 * - 获取日权益快照（资金曲线数据）
 * - 获取滚动绩效指标（多窗口对比）
 */

import request from '/@/utils/request';

// ==================== 类型定义 ====================

/**
 * CustomPagination 标准响应格式
 * 注意：后端使用的是 dvadmin 的 CustomPagination，返回格式为：
 * {
 *   code: 2000,
 *   msg: "success",
 *   page: 1,
 *   limit: 10,
 *   total: 100,
 *   data: [...]  // ← 直接是数组，不是 {results: []}
 * }
 */
export interface PaginatedResponse<T> {
	code: number;
	msg: string;
	page: number;
	limit: number;
	total: number;
	is_next: boolean;
	is_previous: boolean;
	data: T[];  // ← 关键：data 直接是数组
}

/**
 * 账户绩效总览响应数据
 */
export interface AccountSummary {
	id: number;
	account: number;
	account_name: string;
	snapshot_date: string;
	
	// === 全局收益指标 ===
	total_return: string;           // 累计收益率 (%)
	annualized_return: string | null; // 年化收益率 (%)
	
	// === 全局风险指标 ===
	max_drawdown_all_time: string;  // 历史最大回撤 (%)
	current_drawdown: string;       // 当前回撤 (%)
	max_drawdown_duration: number;  // 最大回撤持续天数
	max_drawdown_recovery_days: number; // 最大回撤恢复天数
	calmar_ratio: string | null;    // 卡尔玛比率
	
	// === 全局交易统计 ===
	total_trades_all_time: number;  // 总交易次数
	overall_win_rate: string | null; // 整体胜率 (%)
	overall_profit_factor: string | null; // 整体盈利因子
	
	// === 极端值统计 ===
	best_single_trade: string | null;   // 最佳单笔盈利
	worst_single_trade: string | null;  // 最差单笔亏损
	consecutive_wins: number;       // 最大连续盈利次数
	consecutive_losses: number;     // 最大连续亏损次数
	
	// === 持仓统计 ===
	current_long_position: number;  // 当前多头手数
	current_short_position: number; // 当前空头手数
	avg_holding_days: string | null; // 平均持仓天数
	
	// === 引用滚动指标 ===
	latest_sharpe_20d: string | null;      // 最新20日夏普
	latest_volatility_20d: string | null;  // 最新20日波动率
	latest_sortino_20d: string | null;     // 最新20日索提诺比率
	
	// === 交易行为统计 ===
	trading_frequency: string;             // 交易频率（次/日）
	
	// === 累计财务数据 ===
	closed_profit_total: string;           // 累计平仓盈亏
	commission_total: string;              // 累计手续费
	
	updated_at: string;
}

/**
 * 日权益快照响应数据
 */
export interface EquitySnapshot {
	id: number;
	account: number;
	account_name: string;
	trade_date: string;
	balance: string;          // 当前权益
	available: string;        // 可用资金
	float_profit: string;     // 浮动盈亏
	margin: string;           // 保证金占用
	risk_ratio: string;       // 风险度
	commission: string;       // 当日手续费
	daily_return: string;     // 日收益率 (%)
	daily_pnl: string;        // 日盈亏
	closed_pnl: string;       // 当日平仓盈亏（新增）
	created_at: string;
	updated_at: string;
}

/**
 * 滚动绩效指标响应数据
 */
export interface RollingMetrics {
	id: number;
	account: number;
	account_name: string;
	calc_date: string;
	window_days: number;      // 窗口天数 (20/60/120)
	sharpe_ratio: string | null;      // 夏普比率
	sortino_ratio: string | null;     // 索提诺比率
	volatility: string | null;        // 年化波动率
	win_rate: string | null;          // 胜率
	profit_loss_ratio: string | null; // 盈亏比
	total_trades: number;
	data_quality: string;     // COMPLETE/PARTIAL/INSUFFICIENT
	calculated_at: string;
}

// ==================== API 函数 ====================

/**
 * 获取账户绩效总览（Dashboard 主要数据源）
 * 
 * @param accountId 账户ID
 * @returns Promise<AccountSummary>
 * 
 * @example
 * const summary = await getAccountSummary(1);
 * console.log(summary.total_return); // "12.3456"
 */
export function getAccountSummary(accountId: number) {
	return request({
		url: '/api/stock/account-summaries/',
		method: 'get',
		params: {
			account: accountId,
			ordering: '-snapshot_date',
			limit: 1
		}
	});
}

/**
 * 获取日权益快照列表（用于绘制资金曲线）
 * 
 * @param params 查询参数
 * @returns Promise<{results: EquitySnapshot[]}>
 * 
 * @example
 * const snapshots = await getEquitySnapshots({
 *   account: 1,
 *   trade_date__gte: '2024-01-01',
 *   trade_date__lte: '2024-12-31',
 *   ordering: 'trade_date',
 *   limit: 100
 * });
 */
export function getEquitySnapshots(params: {
	account: number;
	trade_date__gte?: string;
	trade_date__lte?: string;
	ordering?: string;
	page?: number;
	limit?: number;
}) {
	return request({
		url: '/api/stock/equity-snapshots/',
		method: 'get',
		params
	});
}

/**
 * 获取滚动绩效指标（多窗口对比）
 * 
 * @param params 查询参数
 * @returns Promise<{results: RollingMetrics[]}>
 * 
 * @example
 * const metrics = await getRollingMetrics({
 *   account: 1,
 *   window_days__in: '20,60,120',
 *   calc_date: '2024-01-15'
 * });
 */
export function getRollingMetrics(params: {
	account: number;
	window_days?: number;
	window_days__in?: string;
	calc_date?: string;
	calc_date__gte?: string;
	calc_date__lte?: string;
	ordering?: string;
	page?: number;
	limit?: number;
}) {
	return request({
		url: '/api/stock/rolling-metrics/',
		method: 'get',
		params
	});
}

/**
 * 获取最新的指定窗口绩效指标
 * 
 * @param accountId 账户ID
 * @param windowDays 窗口天数 (默认20)
 * @returns Promise<RollingMetrics>
 * 
 * @example
 * const sharpe20d = await getLatestRollingMetric(1, 20);
 * console.log(sharpe20d.sharpe_ratio); // "1.2345"
 */
export function getLatestRollingMetric(accountId: number, windowDays: number = 20) {
	return request({
		url: '/api/stock/rolling-metrics/',
		method: 'get',
		params: {
			account: accountId,
			window_days: windowDays,
			ordering: '-calc_date',
			limit: 1
		}
	});
}

/**
 * 获取品种胜率统计数据
 */
export function getSymbolWinRate(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			name: string;
			product_code: string;
			winRate: number;
			trades: number;
			LongNum: number;
			ShortNum: number;
			profit: number;
		}>;
	}>(`/api/stock/symbol-win-rate/?account=${accountId}`);
}

/**
 * 获取账户累计统计数据（平仓盈亏、手续费总数）
 */
export function getCumulativeStats(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: {
			total_closed_pnl: number;
			total_commission: number;
		};
	}>(`/api/stock/cumulative-stats/?account=${accountId}`);
}

/**
 * 获取多窗口滚动绩效指标（用于雷达图对比）
 * @param accountId 账户ID
 * @returns Promise<RollingMetrics[]> 返回4个窗口的数据数组
 * 
 * @example
 * const metrics = await getMultiWindowMetrics(1);
 * // 返回: [{window_days: 20, ...}, {window_days: 60, ...}, ...]
 */
export function getMultiWindowMetrics(accountId: number) {
	return request({
		url: '/api/stock/rolling-metrics/',
		method: 'get',
		params: {
			account: accountId,
			window_days__in: '20,60,120,250',
			ordering: 'window_days'  // 按窗口天数升序排列
		}
	});
}

/**
 * 获取日历热力图数据（日收益率）
 * @param accountId 账户ID
 * @returns Promise<{date: string, daily_return: number, month: number, day: number, year: number}[]>
 * 
 * @example
 * const calendarData = await getDailyReturnsCalendar(1);
 * // 返回: [{date: "2024-01-15", daily_return: 1.25, month: 1, day: 15, year: 2024}, ...]
 */
export function getDailyReturnsCalendar(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			date: string;
			daily_return: number;
			month: number;
			day: number;
			year: number;
		}>;
	}>(`/api/stock/daily-returns-calendar/?account=${accountId}`);
}

/**
 * 获取资金回撤曲线数据
 * @param accountId 账户ID
 * @returns Promise<{date: string, equity: number, peak_equity: number, drawdown_pct: number, is_new_peak: boolean}[]>
 * 
 * @example
 * const drawdownData = await getDrawdownCurve(1);
 * // 返回: [{date: "2024-01-15", equity: 105000, peak_equity: 110000, drawdown_pct: -4.55, is_new_peak: false}, ...]
 */
export function getDrawdownCurve(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			date: string;
			equity: number;
			peak_equity: number;
			drawdown_pct: number;
			is_new_peak: boolean;
		}>;
	}>(`/api/stock/drawdown-curve/?account=${accountId}`);
}

/**
 * 获取多账户资金曲线对比数据
 * @returns Promise 包含所有活跃账户的资金曲线
 *
 * @example
 * const curves = await getEquityCurves();
 * // 返回: [{account_id: 1, account_name: "510988", strategy: "海龟策略", curve: [{trade_date, balance}, ...]}, ...]
 */
export function getEquityCurves() {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			account_id: number;
			account_name: string;
			strategy: string;
			curve: Array<{ trade_date: string; balance: number }>;
		}>;
	}>('/api/stock/equity-curves/');
}

// ==================== 滑点统计 ====================

export interface SlippageStats {
	total_records: number;
	avg_slippage_ticks: number;
	favorable_ratio: number;
	by_type: Array<{
		trade_type: string;
		count: number;
		avg_slippage_ticks: number;
		favorable_ratio: number;
	}>;
	by_symbol?: Array<{
		product_code: string;
		count: number;
		avg_slippage_ticks: number;
		favorable_ratio: number;
	}>;
}

/**
 * 获取账户滑点统计汇总
 * @param accountId 账户ID
 * @returns Promise<SlippageStats>
 */
export function getSlippageStats(accountId: number, tradeType?: string) {
	let url = `/api/stock/slippage-stats/?account=${accountId}`;
	if (tradeType) url += `&trade_type=${tradeType}`;
	return request.get<{
		code: number;
		msg: string;
		data: SlippageStats;
	}>(url);
}
