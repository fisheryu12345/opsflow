// ==================== Shared Types for Trading Pages ====================

// === Pagination ===
export interface PaginatedResponse<T> {
  code: number
  msg: string
  page: number
  limit: number
  total: number
  data: T[]
}

// === Common ===
export interface BasicEntity {
  id: number
  created_at?: string
  updated_at?: string
}

// === Position ===
export interface PositionRecord extends BasicEntity {
  account: number
  symbol: string
  product_code: string
  units: number
  direction: -1 | 0 | 1
  contract_total_position: number
  cost_price: number
  last_add_price: number
  highest_close: number
  lowest_close: number
  stop_loss_price: number
  trend_info: string
  latest_close_price: number
  is_rollover_needed: boolean
  protect_cost_enabled: boolean
  float_profit: number | null
  indicators?: {
    atr_20: number
    trend_factor: number
  }
  h20_price: number
  l20_price: number
  volume_multiple: number
  last_update_time: string
}

// === Closed Position ===
export interface ClosedPositionRecord extends BasicEntity {
  account_name: string
  symbol: string
  product_code: string
  direction: -1 | 1
  volume: number
  exit_price: number
  cost_price: number
  pnl: number
  trade_date: string
  executed_at: string
  holding_days: number
  // 趋势分析字段
  entry_trend_factor: number | null
  entry_trend_label: string | null
  entry_atr: number | null
  exit_trend_factor: number | null
  exit_trend_label: string | null
  exit_atr: number | null
  max_favorable_excursion: number | null
  max_adverse_excursion: number | null
}

// === Trade Log ===
export interface TradeLogRecord extends BasicEntity {
  timestamp: string
  function_name: string
  log_level: 'DEBUG' | 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'CRITICAL'
  symbol: string
  log_message: string
}

// === Error Log ===
export interface ErrorLogRecord extends BasicEntity {
  timestamp: string
  function_name: string
  error_message: string
}

// === Contract ===
export interface ContractRecord extends BasicEntity {
  exchange: string
  product_code: string
  symbol: string
  name: string
  category: string
  volume_multiple: number
  price_tick: number
  is_active: boolean
  night_trading: boolean
  min_position: number
  allow_open: boolean
}

export interface ContractStats {
  total: number
  active: number
  inactive: number
  by_exchange: { exchange: string; label: string; count: number }[]
}

// === Strategy Config ===
export interface StrategyConfigRecord extends BasicEntity {
  account: number
  name: string
  // 资金管理
  max_units: number
  entry_units: number
  risk_per_unit: number
  position_risk_multiplier: number
  protect_cost_enabled_ratio: number
  timeout_seconds: number
  // 技术指标
  atr_period: number
  entry_period: number
  ma_periods: string
  // 趋势因子
  gap_atr_limit: number
  trend_factor_max: number
  trend_label_strong_ratio: number
  trend_label_weak_ratio: number
  // 过滤
  gap_threshold: number
  product_codes: string
  // TqSDK
  tqapi_account: string
  tqapi_password?: string
  // 期货账户
  future_broker: string
  future_account: string
  future_password?: string
  // 模式
  is_simulation: boolean
  // 跳过震荡行情开仓
  skip_choppy_entry: boolean
}

// === Daily Signal ===
export interface DailySignalRecord extends BasicEntity {
  trade_date: string
  symbol: string
  product_code: string
  trend_factor: number
  trend_label: string
  donchian_upper: number
  donchian_lower: number
  is_breakout: boolean
  signal_direction: number
  trade_type: string
  executed_status: string
  remark: string
}

// === Dashboard ===
export interface AccountSummary {
  id: number
  account: number
  account_name: string
  snapshot_date: string
  total_return: string
  annualized_return: string | null
  max_drawdown_all_time: string
  current_drawdown: string
  max_drawdown_duration: number
  calmar_ratio: string | null
  total_trades_all_time: number
  overall_win_rate: string | null
  overall_profit_factor: string | null
  best_single_trade: string | null
  worst_single_trade: string | null
  consecutive_wins: number
  consecutive_losses: number
  current_long_position: number
  current_short_position: number
  avg_holding_days: string | null
  latest_sharpe_20d: string | null
  latest_volatility_20d: string | null
  latest_sortino_20d: string | null
  trading_frequency: string
  closed_profit_total: string
  commission_total: string
  updated_at: string
}

export interface EquitySnapshot {
  id: number
  account: number
  account_name: string
  trade_date: string
  balance: string
  available: string
  float_profit: string
  margin: string
  risk_ratio: string
  commission: string
  daily_return: string
  daily_pnl: string
  closed_pnl: string
  created_at: string
  updated_at: string
}

export interface RollingMetrics {
  id: number
  account: number
  account_name: string
  calc_date: string
  window_days: number
  sharpe_ratio: string | null
  sortino_ratio: string | null
  volatility: string | null
  win_rate: string | null
  profit_loss_ratio: string | null
  total_trades: number
  data_quality: string
  calculated_at: string
}

export interface SymbolWinRate {
  name: string
  product_code: string
  winRate: number
  trades: number
  LongNum: number
  ShortNum: number
  profit: number
}

export interface CumulativeStats {
  total_closed_pnl: number
  total_commission: number
}

export interface DailyReturnCalendar {
  date: string
  daily_return: number
  month: number
  day: number
  year: number
}

export interface DrawdownPoint {
  date: string
  equity: number
  peak_equity: number
  drawdown_pct: number
  is_new_peak: boolean
}

// === Kline ===
export interface KlineRecord {
  id: number
  symbol: string
  product_code: string
  exchange: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  open_interest: number | null
}

export interface TradeMarker {
  date: string
  trade_type: 'ENTRY' | 'ADD_ON' | 'ROLLOVER' | 'EXIT'
  price: number | null
  direction: number
  label: string
  description: string
}

export interface AvailableContract {
  symbol: string
  product_code: string
  name: string | null
  exchange: string
}
