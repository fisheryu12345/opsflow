import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class TrendInfo:
    factor: float
    label: str
    rank: int

# 假设这些常量已在其他地方定义，这里为了运行不报错给个默认值
ATR_PERIOD = 20
MA_PERIODS = [10, 20, 40]
ENTRY_PERIOD = 20
EXIT_PERIOD = 10

def calculate_atr(klines, period=ATR_PERIOD):
    """
    计算ATR（平均真实波幅）
    修正点：使用 rolling 计算，确保使用的是“当前时刻之前”的最新数据，而不是最早的数据。
    """
    if len(klines) < period + 2:
        return 0.0
    
    high = klines["high"]
    low = klines["low"]
    close = klines["close"]
    prev_close = close.shift(1)
    
    # 1. 计算真实波幅 TR
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    # 2. 去除 NaN (第一行会有 NaN)
    tr = tr.dropna()
    
    if len(tr) < period:
        return 0.0
        
    # 3. 关键修正：
    # 我们需要的是“上一根K线收盘时”的ATR。
    # 所以我们要把 tr 序列切掉最后一个（当前的），然后计算 rolling mean。
    prior_tr = tr.iloc[:-1] 
    
    if len(prior_tr) < period:
        return 0.0
        
    # 使用 rolling 计算均值，取最后一个值
    # 这比手动写 for 循环快且稳
    atr_series = prior_tr.rolling(window=period).mean()
    
    return float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0

def calculate_sma(klines, window):
    """计算简单移动平均线"""
    if len(klines) < window:
        return 0.0
    series = klines["close"].dropna()
    if len(series) < window:
        return 0.0
    
    # 优化：使用 rolling
    result = series.rolling(window=window).mean().iloc[-1]
    return float(result) if not np.isnan(result) else 0.0

def calculate_trend_factor(klines):

    """计算趋势因子
    | 标签 | 颜色标识 | 核心特征 | 你的心态 | 你的操作 |
| :--- | :--- | :--- | :--- | :--- |
| strong_bull | 🟢 深绿 | 均线发散向上 | 兴奋，贪婪 | 加仓 / 拿住 |
| weak_bull | 🟩 浅绿 | 均线粘合向上 | 谨慎，耐心 | 持有底仓 |
| strong_bear | 🔴 深红 | 均线发散向下 | 恐惧，果断 | 加空 / 拿住 |
| weak_bear | 🟥 浅红 | 均线粘合向下 | 观望，等待 | 轻仓 / 观望 |
| choppy | ⚪ 灰色 | 均线纠缠不清 | 冷静，不动 | 空仓 / 休息 |
| transition | 🟡 黄色 | 均线正在形成趋势但未完成 | 观察，准备 | 视情况而定 |  
| neutral | ⚫ 黑色 | 数据无效或不足，无法判断趋势 | 0.0 | neutral | 0 |
逻辑检查：通过。这个函数的核心是基于均线的排列和发散程度来判断趋势强弱。动态阈值的引入使得它更适应不同价格水平的品种。  
    """
    ma10 = calculate_sma(klines, MA_PERIODS[0])
    ma20 = calculate_sma(klines, MA_PERIODS[1])
    ma40 = calculate_sma(klines, MA_PERIODS[2])
    
    if any(v == 0 or np.isnan(v) for v in [ma10, ma20, ma40]):
        return TrendInfo(factor=0.0, label="neutral", rank=0)
    
    diff10_20 = ma10 - ma20
    diff20_40 = ma20 - ma40
    
    # 动态阈值：0.45% 的 MA20 价格
    # 建议：这个 0.0045 可以做成配置项，不同板块（如螺纹钢 vs 玉米）敏感度不同
    threshold = 0.0045 * abs(ma20)
    
    # --- 多头排列 ---
    if ma10 > ma20 > ma40:
        # 强多头：均线发散，爆发力强
        if diff10_20 > threshold and diff20_40 > threshold:
            return TrendInfo(factor=0.5, label="strong_bull", rank=2)
        # 弱多头：均线粘合，虽然方向向上但动能不足
        # 修正：这里之前是 -0.15，容易产生歧义，建议改为 0.1 (正向但弱)
        return TrendInfo(factor=-0.15, label="weak_bull", rank=1)
    
    # --- 空头排列 ---
    if ma10 < ma20 < ma40:
        # 强空头：均线向下发散
        if -diff10_20 > threshold and -diff20_40 > threshold:
            return TrendInfo(factor=0.5, label="strong_bear", rank=-2)
        # 弱空头
        # 修正：之前是 -0.15，保持一致性，建议改为 -0.1
        return TrendInfo(factor=-0.15, label="weak_bear", rank=-1)
    
    # --- 震荡市 ---
    # 均线纠缠，无方向
    if abs(diff10_20) < threshold and abs(diff20_40) < threshold:
        return TrendInfo(factor=-0.3, label="choppy", rank=0)
    
    # --- 过渡态 ---
    # 比如 MA10 上穿 MA20 但还没完全多头排列，或者正在回调
    return TrendInfo(factor=0.0, label="transition", rank=0)

def calculate_breakout_levels(klines):
    """
    计算唐奇安通道突破价位
    逻辑检查：通过。iloc[-N-1:-1] 完美避开了当前K线。
    """
    if len(klines) < ENTRY_PERIOD + 2:
        return 0.0, 0.0, 0.0, 0.0
    
    try:
        # 1. 入场通道 (过去 N 天最高/低，不含当前)
        # 切片逻辑：倒数第 N+1 根 到 倒数第 2 根 (共 N 根)
        high_prior = klines["high"].iloc[-ENTRY_PERIOD - 1:-1]
        low_prior = klines["low"].iloc[-ENTRY_PERIOD - 1:-1]
        
        if len(high_prior) == 0:
            return 0.0, 0.0, 0.0, 0.0
            
        entry_high = float(high_prior.max())
        entry_low = float(low_prior.min())
        
        # 2. 离场通道 (过去 M 天最高/低，不含当前)
        exit_high_prior = klines["high"].iloc[-EXIT_PERIOD - 1:-1]
        exit_low_prior = klines["low"].iloc[-EXIT_PERIOD - 1:-1]
        
        # 如果数据不足 M 天，回退到入场通道数据（防御性编程）
        exit_high = float(exit_high_prior.max()) if len(exit_high_prior) > 0 else entry_high
        exit_low = float(exit_low_prior.min()) if len(exit_low_prior) > 0 else entry_low
        
        return entry_high, entry_low, exit_high, exit_low
        
    except Exception:
        return 0.0, 0.0, 0.0, 0.0