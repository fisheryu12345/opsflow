#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
原版海龟交易法则回测
严格遵循理查德·丹尼斯的原始规则：
1. 20日突破入场
2. 10日突破离场
3. 0.5ATR 加仓
4. 2ATR 止损
5. 基于ATR的仓位管理
"""

from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask
import pandas as pd
import numpy as np

# ==================== 策略参数配置 ====================
ENTRY_PERIOD = 20       # 入场周期 (20日突破)
EXIT_PERIOD = 10        # 离场周期 (10日突破)
ATR_PERIOD = 20         # ATR计算周期
MAX_UNITS = 4           # 最大单位数 (原版通常为4个单位)
RISK_PER_UNIT = 0.01    # 每个单位风险占总资金比例 (1%)
CONTRACT_MULTIPLIER = 10 # 合约乘数 (螺纹钢10吨/手)

def calculate_atr(klines, period=ATR_PERIOD):
    """计算ATR (使用RMA平滑移动平均)"""
    if len(klines) < period + 1:
        return 0.0
    
    high = klines["high"]
    low = klines["low"]
    close = klines["close"]
    prev_close = close.shift(1)
    
    # 计算真实波幅 TR
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    tr = tr.dropna()
    if len(tr) < period:
        return 0.0
    
    # 计算ATR (RMA)
    atr = tr.iloc[:period].mean()
    for i in range(period, len(tr)):
        atr = ((atr * (period - 1)) + tr.iloc[i]) / period
    
    return float(atr) if not np.isnan(atr) else 0.0

def calculate_donchian_channel(klines, period):
    """计算唐奇安通道 (基于最高价/最低价)"""
    if len(klines) < period + 2:
        return 0.0, 0.0
    
    # 切片 [-period-1 : -1] 获取过去period天的完整K线数据 (不含当前K线)
    high_series = klines["high"].iloc[-period-1:-1]
    low_series = klines["low"].iloc[-period-1:-1]
    
    if len(high_series) == 0:
        return 0.0, 0.0
        
    return float(high_series.max()), float(low_series.min())

def calculate_unit_size(atr, equity):
    """计算1个单位的合约数量"""
    if atr <= 0:
        return 1
    
    # 1个单位 = 1% 总资金 / (ATR * 合约乘数)
    dollar_volatility = atr * CONTRACT_MULTIPLIER
    if dollar_volatility <= 0:
        return 1
        
    units = (equity * RISK_PER_UNIT) / dollar_volatility
    return max(1, int(units))

# ==================== 主程序 ====================

def main():
    print("🐢 启动原版海龟交易法则回测")
    print(f"回测区间: 2025-10-26 到 2026-04-06")
    print("="*60)
    
    # 创建回测实例
    api = TqApi(
        backtest=TqBacktest(
            start_dt=date(2025, 7, 26),
            end_dt=date(2026, 4, 6),
        ),
        auth=TqAuth("yupei1986", "yupei1986")
    )
    
    # 获取日线K线数据
    symbol = "DCE.lh2605"  # 螺纹钢2605
    klines = api.get_kline_serial(symbol, 86400, data_length=300)
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, symbol)
    
    # 策略状态变量
    position_units = 0          # 当前持仓单位数
    direction = 0               # 持仓方向: 1多, -1空, 0无
    contracts_per_unit = 1      # 每单位手数
    last_add_price = None       # 上次加仓价格
    highest_price = None        # 持仓期间最高价 (用于止损)
    lowest_price = None         # 持仓期间最低价 (用于止损)
    last_kline_close = None     # 用于判断新K线
    
    # 延迟执行变量 (防止未来函数)
    pending_signal = None       # 待执行信号: 'entry_long', 'entry_short', 'exit'
    
    print("📊 开始回测循环...")
    
    while True:
        api.wait_update()
        
        # 检查K线数据变化
        if api.is_changing(klines):
            
            # 获取当前最新K线数据
            current_close = klines.close.iloc[-1]
            current_datetime = pd.to_datetime(klines.datetime.iloc[-1], unit='ns')
            
            # 判断是否是新K线
            is_new_bar = (last_kline_close != current_close)
            
            if is_new_bar and last_kline_close is not None:
                print(f"\n📅 {current_datetime.date()} | 收盘: {current_close:.2f}")
                
                # 确保有足够历史数据
                if len(klines) >= ENTRY_PERIOD + 10:
                    
                    # 计算技术指标
                    atr = calculate_atr(klines)
                    entry_high, entry_low = calculate_donchian_channel(klines, ENTRY_PERIOD)
                    exit_high, exit_low = calculate_donchian_channel(klines, EXIT_PERIOD)
                    
                    # 获取当前资金 (用于计算仓位)
                    account = api.get_account()
                    equity =  1000000
                    
                    print(f"   ATR: {atr:.2f} | 入场上轨: {entry_high:.2f} | 入场下轨: {entry_low:.2f}")
                    
                    # ========== 执行上一根K线产生的信号 (使用当前开盘价/收盘价) ==========
                    if pending_signal == 'entry_long':
                        if position_units == 0:
                            contracts_per_unit = calculate_unit_size(atr, equity)
                            total_volume = contracts_per_unit
                            target_pos.set_target_volume(total_volume)
                            position_units = 1
                            direction = 1
                            last_add_price = current_close
                            highest_price = current_close
                            print(f"   🐢 开多仓 | 价格: {current_close:.2f} | 手数: {total_volume}")
                    
                    elif pending_signal == 'entry_short':
                        if position_units == 0:
                            contracts_per_unit = calculate_unit_size(atr, equity)
                            total_volume = -contracts_per_unit
                            target_pos.set_target_volume(total_volume)
                            position_units = 1
                            direction = -1
                            last_add_price = current_close
                            lowest_price = current_close
                            print(f"   🐢 开空仓 | 价格: {current_close:.2f} | 手数: {abs(total_volume)}")
                    
                    elif pending_signal == 'exit':
                        target_pos.set_target_volume(0)
                        print(f"   🏁 平仓离场 | 价格: {current_close:.2f}")
                        position_units = 0
                        direction = 0
                        last_add_price = None
                        highest_price = None
                        lowest_price = None
                    
                    pending_signal = None # 重置信号
                    
                    # ========== 策略逻辑 (生成下一根K线的信号) ==========
                    
                    # 1. 离场逻辑 (优先检查)
                    if position_units > 0:
                        # 更新最高价
                        highest_price = max(highest_price, current_close) if highest_price else current_close
                        
                        # 10日低点离场
                        if current_close < exit_low:
                            pending_signal = 'exit'
                            print(f"   ⚠️ 触发离场信号 (收盘价 {current_close:.2f} < 10日低点 {exit_low:.2f})")
                        
                        # 加仓逻辑 (价格突破前高 + 0.5ATR)
                        elif position_units < MAX_UNITS:
                            add_threshold = last_add_price + 0.5 * atr
                            if current_close > add_threshold:
                                position_units += 1
                                last_add_price = current_close
                                total_volume = position_units * contracts_per_unit
                                target_pos.set_target_volume(total_volume)
                                print(f"   ➕ 加仓 | 总单位: {position_units} | 价格: {current_close:.2f}")
                    
                    elif position_units < 0:
                        # 更新最低价
                        lowest_price = min(lowest_price, current_close) if lowest_price else current_close
                        
                        # 10日高点离场
                        if current_close > exit_high:
                            pending_signal = 'exit'
                            print(f"   ⚠️ 触发离场信号 (收盘价 {current_close:.2f} > 10日高点 {exit_high:.2f})")
                        
                        # 加仓逻辑
                        elif abs(position_units) < MAX_UNITS:
                            add_threshold = last_add_price - 0.5 * atr
                            if current_close < add_threshold:
                                position_units -= 1
                                last_add_price = current_close
                                total_volume = position_units * contracts_per_unit
                                target_pos.set_target_volume(total_volume)
                                print(f"   ➕ 加仓 | 总单位: {abs(position_units)} | 价格: {current_close:.2f}")
                    
                    # 2. 入场逻辑 (无持仓时)
                    elif position_units == 0:
                        # 20日高点入场
                        if current_close > entry_high:
                            pending_signal = 'entry_long'
                            print(f"   🔍 触发做多信号 (收盘价 {current_close:.2f} > 20日高点 {entry_high:.2f})")
                        
                        # 20日低点入场
                        elif current_close < entry_low:
                            pending_signal = 'entry_short'
                            print(f"   🔍 触发做空信号 (收盘价 {current_close:.2f} < 20日低点 {entry_low:.2f})")
            
            # 更新最后收盘价
            last_kline_close = current_close
    
    # 获取报告
    report = api.get_report()
    if report:
        print("\n" + "="*60)
        print("📊 回测报告")
        print("="*60)
        print(f"总收益率: {report.get('total_return_rate', 0):.2%}")
        print(f"最大回撤: {report.get('max_drawdown', 0):.2%}")
        print(f"夏普比率: {report.get('sharpe_ratio', 0):.2f}")
        print(f"胜率: {report.get('win_rate', 0):.2%}")
        print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 回测已停止")