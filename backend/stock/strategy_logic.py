import pandas as pd
import numpy as np
from dataclasses import dataclass


ENTRY_PERIOD = 20               # 入场突破周期
EXIT_PERIOD = 10                # 离场突破周期
ATR_PERIOD = 20                 # ATR计算周期
MA_PERIODS = (10, 20, 40)       # 均线周期

@dataclass
class TrendInfo:
    """
    趋势信息数据类
    用于标准化返回结果
    """
    factor: float       # 趋势因子 (-1.0 到 1.0)
    label: str          # 趋势标签 (strong_bull, choppy, etc.)
    rank: int           # 趋势等级 (-2 到 2)


def calculate_atr(klines, period=ATR_PERIOD):
    """计算ATR（平均真实波幅），使用前面已完成的K线数据，不包含当前待开仓K线。"""
    if len(klines) < period + 2:
        return 0.0
    
    high = klines["high"]
    low = klines["low"]
    close = klines["close"]
    prev_close = close.shift(1)
    
    # 计算真实波幅TR
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    tr = tr.dropna()
    if len(tr) < period + 1:
        return 0.0
    
    # 仅使用前一根K线之前的TR值，避免把当前K线TR纳入当日开仓判断
    prior_tr = tr.iloc[:-1]
    if len(prior_tr) < period:
        return 0.0
    
    # 计算ATR（使用RMA平滑）
    atr = prior_tr.iloc[:period].mean()
    for i in range(period, len(prior_tr)):
        atr = ((atr * (period - 1)) + prior_tr.iloc[i]) / period
    
    return float(atr) if not np.isnan(atr) else 0.0


def calculate_sma(klines, window):
    """计算简单移动平均线"""
    if len(klines) < window:
        return 0.0
    series = klines["close"].dropna()
    if len(series) < window:
        return 0.0
    result = float(series.iloc[-window:].mean())
    return result if not np.isnan(result) else 0.0


def calculate_trend_factor(klines):
    """计算趋势因子"""
    ma10 = calculate_sma(klines, MA_PERIODS[0])
    ma20 = calculate_sma(klines, MA_PERIODS[1])
    ma40 = calculate_sma(klines, MA_PERIODS[2])
    
    if any(v == 0 or np.isnan(v) for v in [ma10, ma20, ma40]):
        return TrendInfo(factor=0.0, label="neutral", rank=0)
    
    diff10_20 = ma10 - ma20
    diff20_40 = ma20 - ma40
    threshold = 0.0045 * abs(ma20)
    
    # 多头排列
    if ma10 > ma20 > ma40:
        if diff10_20 > threshold and diff20_40 > threshold:
            return TrendInfo(factor=0.5, label="strong_bull", rank=2)
        return TrendInfo(factor=-0.15, label="weak_bull", rank=1)
    
    # 空头排列
    if ma10 < ma20 < ma40:
        if -diff10_20 > threshold and -diff20_40 > threshold:
            return TrendInfo(factor=0.5, label="strong_bear", rank=-2)
        return TrendInfo(factor=-0.15, label="weak_bear", rank=-1)
    
    # 震荡市
    if abs(diff10_20) < threshold and abs(diff20_40) < threshold:
        return TrendInfo(factor=-0.3, label="choppy", rank=0)
    
    return TrendInfo(factor=-0.15, label="weak_trend", rank=0)


def calculate_breakout_levels(klines):
    """计算唐奇安通道突破价位 (修正版)"""
    if len(klines) < ENTRY_PERIOD + 2:
        return 0.0, 0.0, 0.0, 0.0
    
    try:
        # 1. 入场通道计算
        # 获取过去 ENTRY_PERIOD 天的数据 (不含当前K线，防止未来函数)
        # 切片 [-N-1 : -1] 表示：倒数第N+1根 到 倒数第2根 (共N根)
        high_prior = klines["high"].iloc[-ENTRY_PERIOD - 1:-1]
        low_prior = klines["low"].iloc[-ENTRY_PERIOD - 1:-1]
        
        if len(high_prior) == 0:
            return 0.0, 0.0, 0.0, 0.0
            
        entry_high = float(high_prior.max()) # 使用最高价
        entry_low = float(low_prior.min())   # 使用最低价
        
        # 2. 离场通道计算 (通常使用较短周期，如10日)
        exit_high_prior = klines["high"].iloc[-EXIT_PERIOD - 1:-1]
        exit_low_prior = klines["low"].iloc[-EXIT_PERIOD - 1:-1]
        
        exit_high = float(exit_high_prior.max()) if len(exit_high_prior) > 0 else entry_high
        exit_low = float(exit_low_prior.min()) if len(exit_low_prior) > 0 else entry_low
        
        return entry_high, entry_low, exit_high, exit_low
        
    except Exception:
        return 0.0, 0.0, 0.0, 0.0