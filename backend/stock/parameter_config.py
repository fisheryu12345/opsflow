POSITION_RISK_BASE_AMOUNT = 4000  # 每个Unit（单位）的固定风险资金基数（元）
POSITION_RISK_MULTIPLIER = 2      # ATR风险倍数系数（止损距离 = N × ATR）
POSITION_MIN_UNITS = 1            # 最小持仓单位数（海龟法则中的"Unit"数量，非手数）
POSITION_MAX_UNITS = 3            # 最大持仓3单位数（如1Unit=4手，最大持仓12手）
TIMEOUT_SECONDS = 60              # targetpostasks 交易执行超时时间（秒），防止长时间挂单未成交导致的风险暴露
PROTECT_COST_ENABLED_RATIO = 2.5  # 保本价保护机制启用比例控制 （如1.5，则保本价=1.5×ATR） LAST PRICE - FIRST_OPEN_PRICE > PROTECT_COST_ENABLED_RATIO * ATR
PRODUCT_CODES = ['rb','hc','al','ao','MA','TA','SA','FG','fu','ru','UR','m','p','CF','RM','AP','lh','jd','sp','si','lc','SR']
GAP_PROTECTION_RATIO = 1.5        # 价格跳空保护机制启用比例控制 （如1.5，则跳空幅度>1.5×ATR时触发保护）

# ==================== 趋势因子（Trend Factor）配置 ====================
# 说明：通过均线排列+间距识别趋势强度，动态调整止损倍数
#       止损倍数 = TREND_STOP_BASE + trend_factor * TREND_STOP_EXTRA
#       trend_factor 范围 [0, TREND_FACTOR_MAX]，由均线间距线性映射

'''
参数调整指南：
让趋势因子更快达到最大值     → TREND_GAP_LIMIT 调小（如 0.015 → 0.012）
扩大止损的浮动范围           → TREND_STOP_EXTRA 调大（如 2.0 → 3.0）
提高最低止损底线             → TREND_STOP_BASE 调大（如 2.0 → 2.5）
更容易被判定为"强趋势"       → TREND_LABEL_STRONG_RATIO 调小（如 0.67 → 0.50）
更容易被判定为"有趋势"       → TREND_LABEL_WEAK_RATIO 调小（如 0.20 → 0.10）
'''

TREND_GAP_LIMIT = 0.03           # 趋势因子封顶上限：均线间距达到 1.5% 时 trend_factor 达到最大值
TREND_FACTOR_MAX = 0.5            # 趋势因子最大值：对应最大止损放大倍数
# TREND_STOP_BASE = 2.0             # 止损基准倍数：trend_factor = 0 时的止损倍数（如 2.0 ATR）
# TREND_STOP_EXTRA = 2.0            # 止损额外倍数：trend_factor 每增加 0.5，止损额外增加的倍数

# trend_label 分级比例（基于 trend_strength [0,1]，无需额外绝对阈值）
# 例：STRONG_RATIO=0.67 表示 trend_strength ≥ 67% 视为强趋势，对应 max_gap = 0.67 * 1.5% = 1.0%
TREND_LABEL_STRONG_RATIO = 0.80   # 强趋势比例阈值
TREND_LABEL_WEAK_RATIO = 0.30     # 弱趋势比例阈值