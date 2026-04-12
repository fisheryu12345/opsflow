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


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal, RolloverLog, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk


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

def calculate_indicators(symbol="SHFE.rb2610", product_code="rb", days=60):
    try:
        api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
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
        latest_hhv = close_high_20.iloc[-1]

        # 获取最新的 llv20_excl_today 值
        latest_llv = close_low_20.iloc[-1]
        
        # 3.5 计算趋势因子
        if ma_10_value and ma_20_value and ma_40_value and not any(np.isnan(v) for v in [ma_10_value, ma_20_value, ma_40_value]):
            diff10_20 = ma_10_value - ma_20_value
            diff20_40 = ma_20_value - ma_40_value
            threshold = 0.0045 * abs(ma_20_value)
            
            if ma_10_value > ma_20_value > ma_40_value:
                trend_factor = 0.5
                trend_label = "strong_bull"
            elif ma_10_value < ma_20_value < ma_40_value:
                trend_factor = 0.5
                trend_label = "strong_bear"
            elif abs(diff10_20) < threshold and abs(diff20_40) < threshold:
                trend_factor = -0.3
                trend_label = "choppy"
            elif (ma_10_value > ma_20_value and ma_20_value >= ma_40_value) or \
                (ma_10_value >= ma_20_value and ma_20_value > ma_40_value):
                trend_factor = -0.15
                trend_label = "weak_bull"
            elif (ma_10_value < ma_20_value and ma_20_value <= ma_40_value) or \
                (ma_10_value <= ma_20_value and ma_20_value < ma_40_value):
                trend_factor = -0.15
                trend_label = "weak_bear"
            else:
                trend_factor = -0.3
                trend_label = "choppy"
        else:
            trend_factor = 0.0
            trend_label = "neutral"

        # 3.6 检查突破信号（只返回结果，不保存数据库）
        breakout_info = check_breakout_signal(klines, entry_period=20)
        # print(f"突破检测结果: {breakout_info}")
        
        # 4. 整理结果
        results = {
            'symbol': symbol,
            'product_code': product_code,
            'latest_date': breakout_info['trade_date'].strftime('%Y-%m-%d') if breakout_info['trade_date'] else None,
            'latest_close': lastest_close,
            'atr_20': atr_20_value,
            'ma_10': ma_10_value,
            'ma_20': ma_20_value,
            'ma_40': ma_40_value,
            'close_high_20': float(latest_hhv),
            'close_low_20': float(latest_llv),
            'data_points': len(klines),
            'trend_factor': trend_factor,
            'trend_label': trend_label,
            'breakout_info': breakout_info,
        }
        return results
    except Exception as e:
        print(str(e))
    finally:
        api.close()