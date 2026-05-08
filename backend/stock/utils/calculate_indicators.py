import pandas as pd
from tqsdk.ta import ATR, MA
from tqsdk.tafunc import hhv, llv
import math
from stock.utils.log_util import log_error

from stock.parameter_config import (
    TREND_GAP_LIMIT,
    TREND_FACTOR_MAX,
    TREND_LABEL_STRONG_RATIO,
    TREND_LABEL_WEAK_RATIO,
)


def clean_nan_for_decimal(value):
    """
    将 NaN/inf/None 转换为 None，确保 Django DecimalField 能接受
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
                'THRESHOLD': None,
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

        # 最新收盘价
        latest_close = clean_nan_for_decimal(float(klines.iloc[-1]['close']))

        # ATR
        atr_20 = ATR(klines, 20)
        atr_20_value = clean_nan_for_decimal(float(atr_20.iloc[-1]['atr'])) if len(atr_20) > 0 else None

        # MA
        ma_10_value = clean_nan_for_decimal(float(MA(klines, 10).iloc[-1]['ma']))
        ma_20_value = clean_nan_for_decimal(float(MA(klines, 20).iloc[-1]['ma']))
        ma_40_value = clean_nan_for_decimal(float(MA(klines, 40).iloc[-1]['ma']))
        print(f"[{symbol}] 基础数据: close={latest_close}, atr_20={atr_20_value}, ma_10={ma_10_value}, ma_20={ma_20_value}, ma_40={ma_40_value}")

        # 20日高低点（唐奇安通道）
        close_high_20 = hhv(klines['high'].shift(1), 20)
        close_low_20 = llv(klines['low'].shift(1), 20)
        latest_hhv = None if pd.isna(close_high_20.iloc[-1]) else float(close_high_20.iloc[-1])
        latest_llv = None if pd.isna(close_low_20.iloc[-1]) else float(close_low_20.iloc[-1])

        # ---- 趋势判断：均线排列 + 间距 → 连续 trend_factor [0, 0.5] ----
        # 设计意图：
        #   - 均线多头排列/空头排列才认为有趋势，否则 factor = 0
        #   - 趋势强度由最大均线间距比例决定，线性映射到 [0, 0.5]
        #   - 止损倍数 = 2.0 + trend_factor * 2.0，范围 [2.0, 3.0]，完全连续无跳变
        # TREND_GAP_LIMIT: 均线间距达到此值时 trend_factor 达到最大值
        trend_factor = 0.0
        trend_label = "choppy"

        if ma_10_value and ma_20_value and ma_40_value:
            is_bull = ma_10_value > ma_20_value > ma_40_value
            is_bear = ma_10_value < ma_20_value < ma_40_value
            print(f"[{symbol}] 均线排列: is_bull={is_bull}, is_bear={is_bear}")

            if is_bull or is_bear:
                # 最大间距比例（以MA20为基准）
                gap_10_20 = abs(ma_10_value - ma_20_value) / abs(ma_20_value)
                gap_20_40 = abs(ma_20_value - ma_40_value) / abs(ma_20_value)
                max_gap = max(gap_10_20, gap_20_40)
                print(f"[{symbol}] 间距计算: gap_10_20={gap_10_20:.4%}, gap_20_40={gap_20_40:.4%}, max_gap={max_gap:.4%}")

                # 连续映射：max_gap 从 0 到 TREND_GAP_LIMIT 线性映射到 factor [0, TREND_FACTOR_MAX]
                trend_strength = min(max_gap / TREND_GAP_LIMIT, 1.0)
                trend_factor = round(trend_strength * TREND_FACTOR_MAX, 3)
                print(f"[{symbol}] 趋势强度: TREND_GAP_LIMIT={TREND_GAP_LIMIT}, trend_strength={trend_strength:.4f}, trend_factor={trend_factor}")

                # label 基于 trend_strength 比例划分，与 factor 计算同源
                if trend_strength >= TREND_LABEL_STRONG_RATIO:
                    trend_label = "strong_bull" if is_bull else "strong_bear"
                elif trend_strength >= TREND_LABEL_WEAK_RATIO:
                    trend_label = "weak_bull" if is_bull else "weak_bear"
                else:
                    trend_label = "choppy"
                print(f"[{symbol}] 标签判定: STRONG_RATIO={TREND_LABEL_STRONG_RATIO}, WEAK_RATIO={TREND_LABEL_WEAK_RATIO}, trend_label={trend_label}")
            else:
                print(f"[{symbol}] 均线无排列 → 震荡, trend_factor=0")
        else:
            print(f"[{symbol}] MA数据缺失, trend_factor=0")

        breakout_info = check_breakout_signal(klines, entry_period=20)

        result = {
            'symbol': symbol,
            'product_code': product_code,
            'latest_date': breakout_info['trade_date'].strftime('%Y-%m-%d') if breakout_info['trade_date'] else None,
            'latest_close': latest_close,
            'atr_20': atr_20_value,
            'ma_10': ma_10_value,
            'ma_20': ma_20_value,
            'ma_40': ma_40_value,
            'h_20': latest_hhv,
            'l_20': latest_llv,
            'close_high_20': latest_hhv,
            'close_low_20': latest_llv,
            'data_points': len(klines),
            'trend_factor': trend_factor,
            'trend_label': trend_label,
            'THRESHOLD': f'{TREND_LABEL_WEAK_RATIO} ~ {TREND_LABEL_STRONG_RATIO} (trend_strength ratio)',
            'breakout_info': breakout_info,
        }
        print(f"[{symbol}] 最终结果: trend_factor={trend_factor}, trend_label={trend_label}")
        return result
    except Exception as e:
        print(f"[ERROR] 计算指标失败 {symbol}: {e}")
        log_error('calculate_indicators', f"计算指标失败 {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None
