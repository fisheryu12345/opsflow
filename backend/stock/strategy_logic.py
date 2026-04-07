import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class TrendInfo:
    """
    趋势信息数据类
    用于标准化返回结果
    """
    factor: float       # 趋势因子 (-1.0 到 1.0)
    label: str          # 趋势标签 (strong_bull, choppy, etc.)
    rank: int           # 趋势等级 (-2 到 2)

def calculate_atr(klines: pd.DataFrame, period: int = 20) -> float:
    """
    计算 ATR (平均真实波幅)
    
    参数:
        klines: 包含 'open', 'high', 'low', 'close' 列的 DataFrame
        period: ATR 周期，默认 20
    
    返回:
        当前的 ATR 数值
    """
    if len(klines) < period:
        return 0.0

    high = klines['high']
    low = klines['low']
    close = klines['close']
    
    # 计算 TR (True Range)
    # TR = Max( (High - Low), Abs(High - Close[1]), Abs(Low - Close[1]) )
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 计算 ATR (SMA of TR)
    atr = tr.rolling(window=period).mean()
    
    # 返回最后一个有效值
    return atr.iloc[-1]

def calculate_trend_factor(klines: pd.DataFrame, ma_periods: list = [10, 20, 40]) -> TrendInfo:
    """
    计算趋势因子
    基于均线排列状态打分
    
    参数:
        klines: K线数据
        ma_periods: 均线周期列表
    
    返回:
        TrendInfo 对象
    """
    close = klines['close']
    
    # 1. 计算均线
    ma_values = {}
    for period in ma_periods:
        ma_values[f'ma{period}'] = close.rolling(window=period).mean().iloc[-1]
    
    # 检查数据是否充足 (如果均线是 NaN，说明数据不够)
    if any(np.isnan(v) for v in ma_values.values()):
        return TrendInfo(factor=0.0, label='neutral', rank=0)

    # 2. 均线排列打分逻辑
    # 假设 ma_periods = [10, 20, 40]
    ma10, ma20, ma40 = [ma_values[f'ma{p}'] for p in ma_periods]
    current_price = close.iloc[-1]
    
    score = 0
    
    # 多头排列逻辑
    if current_price > ma10 > ma20 > ma40:
        score = 2  # 极强多
    elif ma10 > ma20 > ma40:
        score = 1  # 强多
    elif current_price > ma40:
        score = 0.5 # 偏多
    # 空头排列逻辑
    elif current_price < ma10 < ma20 < ma40:
        score = -2 # 极强空
    elif ma10 < ma20 < ma40:
        score = -1 # 强空
    elif current_price < ma40:
        score = -0.5 # 偏空
    else:
        score = 0    # 震荡

    # 3. 映射标签
    label_map = {
        2: 'strong_bull',
        1: 'strong_bull', # 简化处理，也可以细分
        0.5: 'weak_bull',
        0: 'choppy',
        -0.5: 'weak_bear',
        -1: 'strong_bear',
        -2: 'strong_bear'
    }
    
    # 这里的 rank 直接取整数部分作为等级
    rank = int(np.sign(score) * min(abs(score), 2)) 
    if score == 0.5: rank = 1 # 修正弱趋势的rank
    if score == -0.5: rank = -1

    # 简单的因子归一化 (将 -2～2 映射到 -1.0～1.0 左右，或者直接作为因子)
    # 这里我们直接用 score / 2.0 作为因子，范围 -1.0 ～ 1.0
    factor = score / 2.0

    # 特殊处理震荡市的标签
    final_label = label_map.get(score, 'choppy')
    if abs(score) < 0.6:
        final_label = 'choppy'

    return TrendInfo(factor=factor, label=final_label, rank=rank)

def calculate_breakout_levels(klines: pd.DataFrame, entry_period: int = 20, exit_period: int = 10) -> dict:
    """
    计算唐奇安通道突破点位
    对应海龟交易法则的入场和离场标准
    
    参数:
        klines: K线数据
        entry_period: 入场周期 (默认20)
        exit_period: 离场周期 (默认10)
    
    返回:
        包含上下轨的字典
    """
    high = klines['high']
    low = klines['low']
    
    # 确保数据足够
    if len(klines) < max(entry_period, exit_period):
        return {
            'entry_high': np.nan,
            'entry_low': np.nan,
            'exit_high': np.nan,
            'exit_low': np.nan
        }

    # 1. 计算入场通道 (唐奇安通道)
    # 上轨：过去 N 天的最高价
    entry_high = high.rolling(window=entry_period).max().iloc[-1]
    # 下轨：过去 N 天的最低价
    entry_low = low.rolling(window=entry_period).min().iloc[-1]
    
    # 2. 计算离场通道
    # 上轨：过去 M 天的最高价 (用于空头离场)
    exit_high = high.rolling(window=exit_period).max().iloc[-1]
    # 下轨：过去 M 天的最低价 (用于多头离场)
    exit_low = low.rolling(window=exit_period).min().iloc[-1]
    
    return {
        'entry_high': entry_high,
        'entry_low': entry_low,
        'exit_high': exit_high,
        'exit_low': exit_low
    }