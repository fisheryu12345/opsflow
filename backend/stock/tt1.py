#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交易系统回测 - 基于turtle_strategy.py抽取的策略逻辑
参考test1.py的回测框架
"""

from datetime import date, datetime
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask
import pandas as pd
import numpy as np
import dataclasses
from typing import Optional, Tuple

# ==================== 策略参数配置 ====================
MAX_UNITS = 3                 # 最大持仓单位数
ENTRY_UNITS = 1                 # 初始建仓单位数
ADD_UNITS = 1                   # 加仓单位数
ENTRY_PERIOD = 20               # 入场突破周期
EXIT_PERIOD = 10                # 离场突破周期
ATR_PERIOD = 20                 # ATR计算周期
MA_PERIODS = (10, 20, 40)       # 均线周期
RISK_PER_UNIT = 40000.0         # 每个单位的风险金额(元)
CONTRACT_MULTIPLIER = 10.0      # 合约乘数


@dataclasses.dataclass
class TrendInfo:
    """趋势信息数据类"""
    factor: float        # 趋势因子：-0.3~0.5
    label: str           # 趋势标签
    rank: int            # 趋势强度等级：-2~2


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


def calculate_stop_price(current_k_date,current_close, direction, highest_close, lowest_close, atr20, trend_factor):
    """计算动态止损价"""
    if atr20 == 0 or np.isnan(atr20):
        return 0.0
    
    multiplier = 2.0 * (1.0 + trend_factor)
    
    if direction > 0 and highest_close:
        print(f" {current_k_date}  计算止损价: 多头 | 最高价: {highest_close:.2f} | ATR: {atr20:.2f} | 趋势因子: {trend_factor:.2f} | 止损价: {highest_close - multiplier * atr20:.2f}")
        return highest_close - multiplier * atr20
    elif direction < 0 and lowest_close:
        print(f" {current_k_date}  计算止损价: 空头 | 最低价: {lowest_close:.2f} | ATR: {atr20:.2f} | 趋势因子: {trend_factor:.2f} | 止损价: {lowest_close + multiplier * atr20:.2f}")
        return lowest_close + multiplier * atr20
    
    return 0.0


def calculate_units(atr20, trend_factor):
    """计算每单位应持仓手数"""
    stop_distance = 2.0 * (1.0 + trend_factor) * atr20
    if stop_distance <= 0 or CONTRACT_MULTIPLIER <= 0:
        return 1
    print(f"   计算每单位手数: ATR={atr20:.2f} | 趋势因子={trend_factor:.2f} | 止损距离={stop_distance:.2f} | 每单位风险={RISK_PER_UNIT:.2f} | 合约乘数={CONTRACT_MULTIPLIER}")
    units = int(RISK_PER_UNIT / (stop_distance * CONTRACT_MULTIPLIER))
    return max(1, min(MAX_UNITS, units))


def check_entry_signal(current_k_time,current_close, entry_high, entry_low, trend_info):
    """检查入场信号"""
    print(f"   检查入场信号{current_k_time} | 当前收盘: {current_close:.2f} | 入场上轨: {entry_high:.2f} | 入场下轨: {entry_low:.2f} | 趋势: {trend_info.label}")
    if entry_high == 0 or entry_low == 0:
        return None
    
    # 震荡市过滤
    if trend_info.label == "choppy":
        print(f"   震荡市，放弃入场信号")
        return None
    
    # 做多信号
    if current_close > entry_high:
        return 1
    
    # 做空信号
    if current_close < entry_low:
        return -1
    
    return None


def check_exit_signal(current_close, exit_low, exit_high, direction):
    """检查离场信号"""
    if direction > 0:
        return current_close < exit_low
    elif direction < 0:
        return current_close > exit_high
    return False


def check_addon_signal(current_price, last_add_price, direction, atr20):
    """检查加仓信号"""
    if last_add_price is None:
        return False
    
    if direction > 0:
        add_threshold = last_add_price + 0.5 * atr20
        return current_price >= add_threshold
    elif direction < 0:
        add_threshold = last_add_price - 0.5 * atr20
        return current_price <= add_threshold
    
    return False


def check_stop_loss(current_k_date,current_close, direction, highest_close, lowest_close, atr20, trend_factor):
    """检查是否触发止损"""
    stop_price = calculate_stop_price(current_k_date,current_close, direction, highest_close, lowest_close, atr20, trend_factor)
    if stop_price == 0:
        return False
    
    if direction > 0:
        return current_close <= stop_price
    elif direction < 0:
        return current_close >= stop_price
    
    return False


def update_position_tracking(current_close, direction, highest_close, lowest_close):
    """更新持仓跟踪价格"""
    if direction > 0:
        if highest_close is None:
            highest_close = current_close
        else:
            highest_close = max(highest_close, current_close)
            print(f"   更新多头持仓最高价: {highest_close:.2f}")
    elif direction < 0:
        if lowest_close is None:
            lowest_close = current_close
        else:
            lowest_close = min(lowest_close, current_close)
            print(f"   更新空头持仓最低价: {lowest_close:.2f}")
    return highest_close, lowest_close


# ==================== 主程序 ====================

def main():
    print("🚀 启动交易系统回测")
    
    # 创建回测实例
    api = TqApi(
        backtest=TqBacktest(
            start_dt=date(2025, 7, 26),
            end_dt=date(2026, 4, 6),
        ),
        auth=TqAuth("yupei1986", "yupei1986")
    )
    
    # 获取日线K线数据
    symbol = "CZCE.MA605"
    klines = api.get_kline_serial(symbol, 86400, data_length=300)
    
    # 创建目标持仓任务
    target_pos = TargetPosTask(api, symbol)
    
    # 策略状态变量
    position_units = 0          # 当前持仓单位数
    direction = 0               # 持仓方向：1多 -1空 0无
    contracts_per_unit = 1      # 每单位手数
    last_add_price = None       # 上次加仓价格
    highest_close = None        # 多头持仓期间最高收盘价
    lowest_close = None         # 空头持仓期间最低收盘价
    pending_entry_direction = 0  # 下根K线开盘待开仓方向
    pending_entry_contracts = 1  # 下根K线开盘待开仓手数
    pending_entry_trend_factor = 0.0  # 下根K线开盘待开仓趋势因子
    last_kline_close = None     # 记录上一根K线的收盘价，用于判断新K线
    
    # 回测结束标志
    backtest_finished = False
    
    while not backtest_finished:
        api.wait_update()
        
        # 关键：检查K线数据是否有变化（新K线产生或当前K线更新）
        if api.is_changing(klines):
            
            # 获取当前最新K线数据
            current_close = klines.close.iloc[-1]
            current_open = klines.open.iloc[-1]
            current_datetime =  pd.to_datetime(klines.datetime.iloc[-1], unit='ns')
            
            # 判断是否是新K线：通过比较收盘价是否变化
            is_new_bar = (last_kline_close != current_close)
            
            if is_new_bar and last_kline_close is not None:
                # 如果存在前一根K线产生的突破信号，则使用本根K线开盘价开仓
                if pending_entry_direction != 0:
                    # 检查开盘跳动幅度，仅在与原计划开仓方向一致的跳空时放弃机会
                    if last_kline_close and last_kline_close != 0:
                        gap_pct = (current_open - last_kline_close) / last_kline_close
                        if pending_entry_direction > 0 and gap_pct > 0.01:
                            print(f"   ❌ 放弃开仓 {current_datetime} | 与多头方向正向跳空: {gap_pct:.2%} (>1%) | 开盘: {current_open:.2f} | 昨收: {last_kline_close:.2f}")
                            pending_entry_direction = 0
                            pending_entry_contracts = 1
                            pending_entry_trend_factor = 0.0
                            # 不continue，继续执行策略逻辑，重新寻找开仓机会
                        elif pending_entry_direction < 0 and gap_pct < -0.01:
                            print(f"   ❌ 放弃开仓 {current_datetime} | 与空头方向正向跳空: {abs(gap_pct):.2%} (>1%) | 开盘: {current_open:.2f} | 昨收: {last_kline_close:.2f}")
                            pending_entry_direction = 0
                            pending_entry_contracts = 1
                            pending_entry_trend_factor = 0.0
                            # 不continue，继续执行策略逻辑，重新寻找开仓机会
                    
                    if pending_entry_direction != 0:  # 如果没有放弃，继续开仓
                        direction = pending_entry_direction
                        position_units = ENTRY_UNITS
                        contracts_per_unit = pending_entry_contracts
                        last_add_price = current_open
                        highest_close = current_open
                        lowest_close = current_open
                        total_volume = position_units * contracts_per_unit
                        if direction < 0:
                            total_volume = -total_volume
                        
                        print(f"   🟢 开盘开仓 {current_datetime} | 开盘价: {current_open:.2f} | 方向: {'多' if direction > 0 else '空'} | 手数: {abs(total_volume)}")
                        target_pos.set_target_volume(total_volume)

                        pending_entry_direction = 0
                        pending_entry_contracts = 1
                        pending_entry_trend_factor = 0.0

                        last_kline_close = current_close
                        continue

                # 确保有足够的历史数据
                if len(klines) >= max(MA_PERIODS) + ATR_PERIOD:
                    
                    # 计算技术指标
                    atr20 = calculate_atr(klines)
                    if atr20 == 0:
                        continue
                    
                    trend_info = calculate_trend_factor(klines)
                    entry_high, entry_low, exit_high, exit_low = calculate_breakout_levels(klines)
                    
                    # 打印状态
                    print(f"   ATR: {atr20:.2f}")
                    print(f"   趋势: {trend_info.label} (因子={trend_info.factor})")
                    print(f"   入场上轨: {entry_high:.2f} | 入场下轨: {entry_low:.2f}")
                    print(f"   离场上轨: {exit_high:.2f} | 离场下轨: {exit_low:.2f}")
                    print(f"   当前持仓: {position_units}单位 ({direction})")
                    
                    # ========== 策略逻辑 ==========
                    
                    # 更新持仓跟踪价格
                    if position_units > 0:
                        highest_close, lowest_close = update_position_tracking(
                            current_close, direction, highest_close, lowest_close)
                        
                        # 检查止损
                        if check_stop_loss(current_k_date=current_datetime, current_close=current_close, direction=direction, highest_close=highest_close, lowest_close=lowest_close, atr20=atr20, trend_factor=trend_info.factor):
                            print(f" {current_datetime}  🛑 止损离场！")
                            target_pos.set_target_volume(0)
                            position_units = 0
                            direction = 0
                            last_add_price = None
                            highest_close = None
                            lowest_close = None
                        
                        # 检查离场信号
                        elif check_exit_signal(current_close, exit_low, exit_high, direction):
                            print(f"   🏁 通道离场！")
                            target_pos.set_target_volume(0)
                            position_units = 0
                            direction = 0
                            last_add_price = None
                            highest_close = None
                            lowest_close = None
                        
                        # 检查加仓
                        elif check_addon_signal(current_close, last_add_price, direction, atr20):
                            if position_units < MAX_UNITS:
                                position_units += ADD_UNITS
                                last_add_price = current_close
                                total_volume = position_units * contracts_per_unit
                                if direction < 0:
                                    total_volume = -total_volume
                                print(f"   ➕ 加仓！总单位: {position_units}")
                                target_pos.set_target_volume(total_volume)
                    
                    # 检查入场（无持仓时）
                    elif position_units == 0:
                        entry_direction = check_entry_signal(current_k_time=current_datetime, current_close=current_close, entry_high=entry_high, entry_low=entry_low, trend_info=trend_info)
                        if entry_direction:
                            pending_entry_direction = entry_direction
                            pending_entry_contracts = calculate_units(atr20, trend_info.factor)
                            pending_entry_trend_factor = trend_info.factor

                            print(f"   🐢 {current_datetime} { pending_entry_trend_factor } 突破信号成立，等待下一个交易日开盘开仓 | 收盘: {current_close:.2f} | 上轨: {entry_high:.2f} | 下轨: {entry_low:.2f}")
            
            # 更新最后收盘价记录
            last_kline_close = current_close
    
    # 回测结束，获取报告
    print("📊 回测完成，获取报告...")
    
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