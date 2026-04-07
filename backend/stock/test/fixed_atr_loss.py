#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
海龟交易法则回测 - 基于天勤量化框架
正确处理K线回放和信号触发
"""

from datetime import date, datetime
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask
import pandas as pd
import numpy as np

# ==================== 策略参数配置 ====================
ENTRY_PERIOD = 20       # 入场突破周期
EXIT_PERIOD = 10        # 离场突破周期
ATR_PERIOD = 20         # ATR计算周期
MAX_POSITION = 10        # 最大持仓手数
RISK_PER_UNIT = 40000   # 每个单位风险金额
CONTRACT_MULTIPLIER = 10  # 合约乘数（螺纹钢10吨/手）


def calculate_atr(klines, period=20):
    """计算ATR（平均真实波幅）"""
    if len(klines) < period + 1:
        return 0
    
    high = klines["high"]
    low = klines["low"]
    close = klines["close"]
    prev_close = close.shift(1)
    
    # 计算真实波幅TR
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 计算ATR
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0


def calculate_donchian_channel(klines, period=20):
    """计算唐奇安通道"""
    if len(klines) < period + 1:
        return 0, 999999
    
    # 使用前N根K线，不包括当前K线，避免未来函数
    if len(klines) > period:
        high_series = klines["high"].iloc[-period-1:-1]
        low_series = klines["low"].iloc[-period-1:-1]
        upper = high_series.max()
        lower = low_series.min()
        return upper, lower
    else:
        upper = klines["high"].rolling(window=period).max().iloc[-1]
        lower = klines["low"].rolling(window=period).min().iloc[-1]
        return upper, lower


def calculate_position_size(atr, close_price):
    """根据ATR计算仓位大小"""
    if atr <= 0:
        return 1
    
    dollar_volatility = atr * CONTRACT_MULTIPLIER
    if dollar_volatility <= 0:
        return 1
    
    units = RISK_PER_UNIT / dollar_volatility
    position_size = int(units)
    
    return min(position_size, MAX_POSITION)


# ==================== 主程序 ====================

def main():
    print("🚀 启动海龟交易法则回测")
    print(f"回测区间: 2026-01-01 到 2026-04-06")
    print("="*60)
    
    # 创建回测实例
    api = TqApi(
        backtest=TqBacktest(
            start_dt=date(2025, 10, 26),
            end_dt=date(2026, 4, 6),
        ),
        auth=TqAuth("yupei1986", "yupei1986")
    )
    
    # 获取日线K线数据
    symbol = "SHFE.ag2606"
    klines = api.get_kline_serial(symbol, 86400, data_length=100)
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, symbol)
    
    # 策略状态变量
    current_position = 0
    entry_price = 0
    highest_close = 0
    lowest_close = 999999
    last_kline_close = None  # 记录上一根K线的收盘价，用于判断新K线
    
    # 回测结束标志
    backtest_finished = False
    
    print("📊 开始回测循环...")
    print("="*60)
    
    while not backtest_finished:
        api.wait_update()
        
        # # 检查回测是否结束（通过K线时间判断）
        # if api.is_changing(klines):
        #     # 获取当前K线的时间
        #     print(klines)
        #     print(klines.index[-1])
        #     current_time = klines.index[-2]
        #     print(f"\n⏰ 当前K线时间: {current_time}")
            
        #     # 如果当前时间已经超过回测结束时间，退出循环
        #     if current_time >= pd.Timestamp("2026-04-06"):
        #         print(f"\n⏰ 回测时间到达结束点: {current_time}")
        #         backtest_finished = True
        #         break
        
        # 关键：检查K线数据是否有变化（新K线产生或当前K线更新）
        if api.is_changing(klines):
            
            # 获取当前最新K线数据
            current_close = klines.close.iloc[-1]
            current_high = klines.high.iloc[-1]
            current_low = klines.low.iloc[-1]
            current_datetime = klines.index[-1]
            
            # 判断是否是新K线：通过比较收盘价是否变化
            is_new_bar = (last_kline_close != current_close)
            
            if is_new_bar and last_kline_close is not None:
                # 新K线产生，执行策略逻辑
                print(f"\n📅 新K线: {current_datetime}")
                print(f"   收盘价: {current_close:.2f} (上一根: {last_kline_close:.2f})")
                
                # 确保有足够的历史数据
                if len(klines) >= max(ENTRY_PERIOD, EXIT_PERIOD, ATR_PERIOD) + 1:
                    
                    # 计算技术指标（使用完整的历史数据）
                    atr = calculate_atr(klines, ATR_PERIOD)
                    upper_entry, lower_entry = calculate_donchian_channel(klines, ENTRY_PERIOD)
                    upper_exit, lower_exit = calculate_donchian_channel(klines, EXIT_PERIOD)
                    
                    # 打印状态
                    print(f"   ATR: {atr:.2f}")
                    print(f"   入场上轨: {upper_entry:.2f} | 入场下轨: {lower_entry:.2f}")
                    print(f"   离场上轨: {upper_exit:.2f} | 离场下轨: {lower_exit:.2f}")
                    print(f"   当前持仓: {current_position}手")
                    
                    # ========== 策略逻辑 ==========
                    
                    # 无持仓：寻找入场机会
                    if current_position == 0:
                        # 做多信号：收盘价突破上轨
                        if current_close > upper_entry:
                            position_size = calculate_position_size(atr, current_close)
                            if position_size > 0:
                                print(f"   🐢 买入信号！{current_close:.2f} > {upper_entry:.2f}")
                                print(f"      目标持仓: {position_size}手")
                                target_pos.set_target_volume(position_size)
                                current_position = position_size
                                entry_price = current_close
                                highest_close = current_close
                                lowest_close = current_close
                        
                        # 做空信号：收盘价跌破下轨
                        elif current_close < lower_entry:
                            position_size = calculate_position_size(atr, current_close)
                            if position_size > 0:
                                print(f"   🐢 卖出信号！{current_close:.2f} < {lower_entry:.2f}")
                                print(f"      目标持仓: -{position_size}手")
                                target_pos.set_target_volume(-position_size)
                                current_position = -position_size
                                entry_price = current_close
                                highest_close = current_close
                                lowest_close = current_close
                    
                    # 持有多头仓位
                    elif current_position > 0:
                        # 更新最高价
                        highest_close = max(highest_close, current_close)
                        stop_loss = highest_close - 2 * atr
                        
                        exit_signal = current_close < lower_exit
                        stop_signal = current_close < stop_loss
                        
                        if exit_signal:
                            print(f"   🏁 离场信号（通道）！{current_close:.2f} < {lower_exit:.2f}")
                            print(f"      平多仓，目标持仓: 0手")
                            target_pos.set_target_volume(0)
                            profit = (current_close - entry_price) * current_position * CONTRACT_MULTIPLIER
                            print(f"      盈亏: {profit:.2f}元")
                            current_position = 0
                        
                        elif stop_signal:
                            print(f"   🛑 移动止损！{current_close:.2f} < {stop_loss:.2f}")
                            print(f"      最高价: {highest_close:.2f}, 回撤: {highest_close - current_close:.2f}")
                            target_pos.set_target_volume(0)
                            profit = (current_close - entry_price) * current_position * CONTRACT_MULTIPLIER
                            print(f"      盈亏: {profit:.2f}元")
                            current_position = 0
                        
                        # 加仓信号
                        elif current_close > highest_close + 0.5 * atr:
                            add_size = min(calculate_position_size(atr, current_close), 
                                         MAX_POSITION - abs(current_position))
                            if add_size > 0:
                                new_position = current_position + add_size
                                print(f"   ➕ 加仓信号！{current_close:.2f} > 前高+0.5ATR")
                                print(f"      加仓{add_size}手，总持仓: {new_position}手")
                                target_pos.set_target_volume(new_position)
                                current_position = new_position
                                highest_close = current_close
                    
                    # 持有空头仓位
                    elif current_position < 0:
                        lowest_close = min(lowest_close, current_close)
                        stop_loss = lowest_close + 2 * atr
                        
                        exit_signal = current_close > upper_exit
                        stop_signal = current_close > stop_loss
                        
                        if exit_signal:
                            print(f"   🏁 离场信号（通道）！{current_close:.2f} > {upper_exit:.2f}")
                            print(f"      平空仓，目标持仓: 0手")
                            target_pos.set_target_volume(0)
                            profit = (entry_price - current_close) * abs(current_position) * CONTRACT_MULTIPLIER
                            print(f"      盈亏: {profit:.2f}元")
                            current_position = 0
                        
                        elif stop_signal:
                            print(f"   🛑 移动止损！{current_close:.2f} > {stop_loss:.2f}")
                            print(f"      最低价: {lowest_close:.2f}, 反弹: {current_close - lowest_close:.2f}")
                            target_pos.set_target_volume(0)
                            profit = (entry_price - current_close) * abs(current_position) * CONTRACT_MULTIPLIER
                            print(f"      盈亏: {profit:.2f}元")
                            current_position = 0
                        
                        elif current_close < lowest_close - 0.5 * atr:
                            add_size = min(calculate_position_size(atr, current_close), 
                                         MAX_POSITION - abs(current_position))
                            if add_size > 0:
                                new_position = current_position - add_size
                                print(f"   ➕ 加仓信号！{current_close:.2f} < 前低-0.5ATR")
                                print(f"      加仓{add_size}手，总持仓: {new_position}手")
                                target_pos.set_target_volume(new_position)
                                current_position = new_position
                                lowest_close = current_close
            
            # 更新最后收盘价记录（即使是同一根K线的更新也要记录）
            if last_kline_close is None:
                last_kline_close = current_close
    
    # 回测结束，获取报告
    print("\n" + "="*60)
    print("📊 回测完成，获取报告...")
    print("="*60)
    
    try:
        # 等待一下确保所有订单执行完成
        api.wait_update()
        
        # 获取回测报告
        report = api.get_report()
        if report:
            print(f"总收益率: {report.get('total_return_rate', 0):.2%}")
            print(f"年化收益率: {report.get('annual_return_rate', 0):.2%}")
            print(f"最大回撤: {report.get('max_drawdown', 0):.2%}")
            print(f"夏普比率: {report.get('sharpe_ratio', 0):.2f}")
            print(f"胜率: {report.get('win_rate', 0):.2%}")
            print(f"总交易次数: {report.get('total_trade_count', 0)}")
            print(f"初始资金: {report.get('init_balance', 0):.2f}")
            print(f"最终权益: {report.get('final_balance', 0):.2f}")
        else:
            print("无法获取回测报告")
    except Exception as e:
        print(f"获取报告时出错: {e}")
    
    # 关闭API连接
    api.close()
    print("\n✅ 回测程序正常结束")


if __name__ == "__main__":
    main()