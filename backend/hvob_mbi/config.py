"""
HVOB-MBI 策略配置：品种分类、时间参数、默认值
品种分类由 FullContractList.night_trading 字段提供
"""
from datetime import time

# === 优先品种（平今免费/优惠 + 高波动） ===
PREFERRED_PRODUCTS = {'SA', 'FG', 'RB', 'HC', 'MA', 'TA', 'SC', 'AG', 'P', 'Y', 'OI', 'SR'}

# === 回避品种（双边收费，除非ATR%极好） ===
AVOID_PRODUCTS = {'NI', 'SN', 'PB', 'ZN', 'CU'}

# === 冷门品种（流动性差，直接排除） ===
LOW_LIQUIDITY_PRODUCTS = {'FB', 'BB', 'RR', 'CS', 'B', 'JR', 'WH', 'PM', 'RI', 'LR', 'SF'}

NIGHT_OPEN = time(21, 0)
NIGHT_OR_CLOSE = time(21, 30)  # 夜盘开盘区间结束
DAY_OPEN = time(9, 0)
DAY_OR_CLOSE = time(9, 30)     # 日盘开盘区间结束
FORCE_CLOSE_TIME = time(14, 55)
LAST_ENTRY_TIME = time(13, 30)

# === 筛选参数（默认值，可被 HvobMbiConfig 覆盖） ===
ATR_PERCENT_RANK_TOP = 0.02    # ATR% > 2%
MIN_AMPLITUDE_5D = 0.015       # 近5日平均振幅 > 1.5%
OR_MIN_RATIO = 0.8             # 开盘区间高度 >= 0.8 × 20日平均
MAX_VOL_SCORE = 5              # 量比得分上限（防止爆量品种主导评分）

# === 交易参数 ===
BREAKOUT_OFFSET_RATIO = 0.3    # 突破偏移量（H+0.3R / L-0.3R）
STOP_OFFSET_RATIO = 0.2        # 止损偏移量（H+0.2R / L-0.2R）
DEFAULT_RISK_PERCENT = 0.005   # 单笔风险 0.5%

# === 时间衰减系数（日盘，按突破时间） ===
TIME_DECAY_SLOTS = [
    (time(9, 30), time(10, 30), 1.0),    # 9:30-10:30 正常仓位
    (time(10, 30), time(11, 30), 0.7),   # 10:30-11:30 70%
    (time(11, 30), time(13, 30), 0.5),   # 11:30-13:30 50%
    (time(13, 30), time(14, 55), 0.3),   # 13:30-14:55 30%
]
