import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR, SMA,MA
from tqsdk.tafunc import hhv, llv
import json
import math


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,  DailyPerformance, DailyStrategySignal,  PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk


def clean_nan_for_decimal(value):
    """
    将 NaN/inf/None 转换为 None，确保 Django DecimalField 能接受
    
    参数:
        value: 任意数值（int, float, Decimal, None）
    
    返回:
        None 或有效数字
    """
    if value is None:
        return None
    try:
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
        return value
    except (TypeError, ValueError):
        return None


def check_breakout_signal(klines, entry_period=20):
    if len(klines) < entry_period + 2:
        return {
            'is_breakout': False,
            'signal_direction': 0,
            'entry_high': None,
            'entry_low': None,
            'latest_close': None,
            'trade_date': None,
            'remark': '数据不足'
        }
    
    high_prior = klines["high"].iloc[-entry_period - 1:-1]
    low_prior = klines["low"].iloc[-entry_period - 1:-1]
    
    entry_high = float(high_prior.max()) if len(high_prior) > 0 else None
    entry_low = float(low_prior.min()) if len(low_prior) > 0 else None
    latest_close = float(klines.iloc[-1]['close'])
    trade_date = pd.to_datetime(klines.iloc[-1]['datetime'], unit='ns').date()
    
    is_breakout = False
    signal_direction = 0
    remark = ""
    
    if entry_high and entry_low:
        if latest_close > entry_high:
            is_breakout = True
            signal_direction = 1
            remark = f"收盘价 {latest_close:.2f} 突破唐奇安上轨 {entry_high:.2f}"
        elif latest_close < entry_low:
            is_breakout = True
            signal_direction = -1
            remark = f"收盘价 {latest_close:.2f} 跌破唐奇安下轨 {entry_low:.2f}"
    
    return {
        'is_breakout': is_breakout,
        'signal_direction': signal_direction,
        'entry_high': entry_high,
        'entry_low': entry_low,
        'latest_close': latest_close,
        'trade_date': trade_date,
        'remark': remark
    }

def calculate_indicators(api, symbol="SHFE.rb2610", product_code="rb", days=60):
    """
    计算技术指标（使用传入的TqApi实例）
    
    :param api: TqApi实例（由调用者管理生命周期）
    :param symbol: 合约代码
    :param product_code: 品种代码
    :param days: K线数据天数
    :return: 指标结果字典
    """
    try:
        klines = api.get_kline_serial(symbol, days=days, duration_seconds=24 * 60 * 60) 
        if len(klines) < 20:
            return {
                'symbol': symbol,
                'product_code': product_code,
                'latest_date': None,
                'latest_close': None,
                'atr_20': None,
                'ma_10': None,
                'ma_20': None,
                'ma_40': None,
                'h_20': None,
                'l_20': None,
                'close_high_20': None,
                'close_low_20': None,
                'data_points': len(klines),
                'trend_factor': 0.0,
                'trend_label': "neutral",
                'breakout_info': {
                    'is_breakout': False,
                    'signal_direction': 0,
                    'entry_high': None,
                    'entry_low': None,
                    'latest_close': None,
                    'trade_date': None,
                    'remark': '数据不足'
                },
            }
        
        lastest_close = float(klines.iloc[-1]['close'])
        # 3.1 计算ATR
        atr_20 = ATR(klines, 20)
        atr_20_value = float(atr_20.iloc[-1]['atr']) if len(atr_20) > 0 else None
        
        # 3.2 计算MA
        ma_10_result = MA(klines, 10)  # 10日均线
        ma_20_result = MA(klines, 20)  # 20日均线
        ma_40_result = MA(klines, 40)  # 40日均线
        
        ma_10_value = float(ma_10_result.iloc[-1]['ma']) if len(ma_10_result) > 0 else None
        ma_20_value = float(ma_20_result.iloc[-1]['ma']) if len(ma_20_result) > 0 else None
        ma_40_value = float(ma_40_result.iloc[-1]['ma']) if len(ma_40_result) > 0 else None
        
        # 3.3 计算20日内收盘价高低点（使用tqsdk.tafunc  hhv,llv）
        close_high_20 = hhv(klines['high'].shift(1), 20)
        close_low_20 = llv(klines['low'].shift(1), 20)
        
        # 获取最新的 hhv20 和 llv20 值，并将 NaN 转换为 None
        latest_hhv_raw = close_high_20.iloc[-1]
        latest_llv_raw = close_low_20.iloc[-1]
        
        # 将 NaN 转换为 None，避免 Django DecimalField 验证错误
        latest_hhv = None if pd.isna(latest_hhv_raw) else float(latest_hhv_raw)
        latest_llv = None if pd.isna(latest_llv_raw) else float(latest_llv_raw)
        
        # 3.4 获取最新收盘价，并处理 NaN
        latest_close_raw = lastest_close
        latest_close = clean_nan_for_decimal(latest_close_raw)
        
        # 3.5 清理所有可能包含 NaN 的指标值
        atr_20_value = clean_nan_for_decimal(atr_20_value)
        ma_10_value = clean_nan_for_decimal(ma_10_value)
        ma_20_value = clean_nan_for_decimal(ma_20_value)
        ma_40_value = clean_nan_for_decimal(ma_40_value)
        
        # 3.5 计算趋势因子
        # 计算均线间距占比
        # 1. 核心判定标准（基于 gap_ratio）
        #         维度	强牛 (strong_bull)	弱牛 (weak_bull)
        #         均线排列	严格单调递增：<br>MA10 > MA20 > MA40	单调递增但发散不足：<br>MA10 > MA20 > MA40
        #         间距占比要求	双高：<br>gap_ratio_10_20 > 1% 且 gap_ratio_20_40 > 1%	至少一个达标：<br>gap_ratio_10_20 > 0.3% 或 gap_ratio_20_40 > 0.3%
        #         趋势因子	trend_factor = 0.5	trend_factor = -0.15
        #         止损倍数	3.0 倍 ATR<br>（宽松，给足波动空间）	1.7 倍 ATR<br>（收紧，防范假突破）

        # 总结对比表
        # 均线形态	        间距占比	        分类	                trend_factor	止损倍数
        # 完美发散	        > 1%	            Strong Bull/Bear	     0.5	        3.0 ATR
        # 微弱发散	        0.3% ~ 1%	        Weak Bull/Bear	        -0.15	        1.7 ATR
        # 高度粘合/交叉	    < 0.3%或非单调	    Choppy (震荡)	         -0.3	         1.4 ATR
        # 数据缺失	N/A	Neutral (中性)	0.0	2.0 ATR
        diff10_20 = ma_10_value - ma_20_value
        diff20_40 = ma_20_value - ma_40_value
        gap_ratio_10_20 = abs(diff10_20) / abs(ma_20_value) if ma_20_value != 0 else 0
        gap_ratio_20_40 = abs(diff20_40) / abs(ma_20_value) if ma_20_value != 0 else 0

        # 定义阈值
        STRONG_THRESHOLD = 0.01   # 1%
        WEAK_THRESHOLD = 0.003    # 0.3%

        if ma_10_value > ma_20_value > ma_40_value:
            # 多头排列
            if gap_ratio_10_20 > STRONG_THRESHOLD and gap_ratio_20_40 > STRONG_THRESHOLD:
                trend_factor = 0.5      # 强牛
                trend_label = "strong_bull"
            elif gap_ratio_10_20 > WEAK_THRESHOLD or gap_ratio_20_40 > WEAK_THRESHOLD:
                trend_factor = -0.15    # 弱牛（至少有一个间距 > 0.3%）
                trend_label = "weak_bull"
            else:
                trend_factor = -0.3     # 震荡（两个间距都 < 0.3%）
                trend_label = "choppy"

        elif ma_10_value < ma_20_value < ma_40_value:
            # 空头排列
            if gap_ratio_10_20 > STRONG_THRESHOLD and gap_ratio_20_40 > STRONG_THRESHOLD:
                trend_factor = 0.5      # 强熊
                trend_label = "strong_bear"
            elif gap_ratio_10_20 > WEAK_THRESHOLD or gap_ratio_20_40 > WEAK_THRESHOLD:
                trend_factor = -0.15    # 弱熊
                trend_label = "weak_bear"
            else:
                trend_factor = -0.3     # 震荡
                trend_label = "choppy"

        else:
            # 交叉形态或无明显方向
            trend_factor = -0.3
            trend_label = "choppy"

        # if ma_10_value and ma_20_value and ma_40_value and not any(np.isnan(v) for v in [ma_10_value, ma_20_value, ma_40_value]):
        #     diff10_20 = ma_10_value - ma_20_value
        #     diff20_40 = ma_20_value - ma_40_value
        #     threshold = 0.0045 * abs(ma_20_value)
            
        #     if ma_10_value > ma_20_value > ma_40_value:
        #         trend_factor = 0.5
        #         trend_label = "strong_bull"
        #     elif ma_10_value < ma_20_value < ma_40_value:
        #         trend_factor = 0.5
        #         trend_label = "strong_bear"
        #     elif abs(diff10_20) < threshold and abs(diff20_40) < threshold:
        #         trend_factor = -0.3
        #         trend_label = "choppy"
        #     elif (ma_10_value > ma_20_value and ma_20_value >= ma_40_value) or \
        #         (ma_10_value >= ma_20_value and ma_20_value > ma_40_value):
        #         trend_factor = -0.15
        #         trend_label = "weak_bull"
        #     elif (ma_10_value < ma_20_value and ma_20_value <= ma_40_value) or \
        #         (ma_10_value <= ma_20_value and ma_20_value < ma_40_value):
        #         trend_factor = -0.15
        #         trend_label = "weak_bear"
        #     else:
        #         trend_factor = -0.3
        #         trend_label = "choppy"
        # else:
        #     trend_factor = 0.0
        #     trend_label = "neutral"
        # # 3.6 检查突破信号（只返回结果，不保存数据库）
        breakout_info = check_breakout_signal(klines, entry_period=20)
        # print(f"突破检测结果: {breakout_info}")
        
        # 4. 整理结果
        results = {
            'symbol': symbol,
            'product_code': product_code,
            'latest_date': breakout_info['trade_date'].strftime('%Y-%m-%d') if breakout_info['trade_date'] else None,
            'latest_close': latest_close,  # ← 使用已处理 NaN 的值
            'atr_20': atr_20_value,
            'ma_10': ma_10_value,
            'ma_20': ma_20_value,
            'ma_40': ma_40_value,
            'h_20': latest_hhv,  # ← 已处理 NaN → None
            'l_20': latest_llv,  # ← 已处理 NaN → None
            'close_high_20': latest_hhv,  # ← 使用已处理的值
            'close_low_20': latest_llv,   # ← 使用已处理的值
            'data_points': len(klines),
            'trend_factor': trend_factor,
            'trend_label': trend_label,
            'breakout_info': breakout_info,
        }
        return results
    except Exception as e:
        print(f"[ERROR] 计算指标失败 {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None
