"""
Technical indicator computation for futures trading strategies.
"""
import pandas as pd
import numpy as np
from tqsdk.ta import ATR, MA
from tqsdk.tafunc import hhv, llv
import math
import traceback
from stock.utils.log_util import log_error
from stock.core.config_loader import get_config

GAP_ATR_LIMIT = get_config('GAP_ATR_LIMIT')       # ATR归一化后的gap阈值 (默认2.0 = 2倍ATR)
TREND_FACTOR_MAX = get_config('TREND_FACTOR_MAX')
TREND_LABEL_STRONG_RATIO = get_config('TREND_LABEL_STRONG_RATIO')
TREND_LABEL_WEAK_RATIO = get_config('TREND_LABEL_WEAK_RATIO')


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

        latest_close = clean_nan_for_decimal(float(klines.iloc[-1]['close']))

        # ATR
        atr_20 = ATR(klines, 20)
        atr_20_value = clean_nan_for_decimal(float(atr_20.iloc[-1]['atr'])) if len(atr_20) > 0 else None

        # MA
        ma_10_value = clean_nan_for_decimal(float(MA(klines, 10).iloc[-1]['ma']))
        ma_20_value = clean_nan_for_decimal(float(MA(klines, 20).iloc[-1]['ma']))
        ma_40_value = clean_nan_for_decimal(float(MA(klines, 40).iloc[-1]['ma']))

        # 20日高低点（唐奇安通道）
        close_high_20 = hhv(klines['high'].shift(1), 20)
        close_low_20 = llv(klines['low'].shift(1), 20)
        latest_hhv = None if pd.isna(close_high_20.iloc[-1]) else float(close_high_20.iloc[-1])
        latest_llv = None if pd.isna(close_low_20.iloc[-1]) else float(close_low_20.iloc[-1])

        # ---- 趋势判断 ----
        trend_factor = 0.0
        trend_label = "choppy"

        if ma_10_value and ma_20_value and ma_40_value:
            is_bull = ma_10_value > ma_20_value > ma_40_value
            is_bear = ma_10_value < ma_20_value < ma_40_value

            if is_bull or is_bear:
                if not (atr_20_value and atr_20_value > 0):
                    trend_factor = 0.0
                    trend_label = "choppy"
                else:
                    gap_10_20 = abs(ma_10_value - ma_20_value) / atr_20_value
                    gap_20_40 = abs(ma_20_value - ma_40_value) / atr_20_value
                    max_gap = max(gap_10_20, gap_20_40)

                    trend_strength = min(max_gap / GAP_ATR_LIMIT, 1.0)
                    trend_factor = round(trend_strength * TREND_FACTOR_MAX, 3)

                    if trend_strength >= TREND_LABEL_STRONG_RATIO:
                        trend_label = "strong_bull" if is_bull else "strong_bear"
                    elif trend_strength >= TREND_LABEL_WEAK_RATIO:
                        trend_label = "weak_bull" if is_bull else "weak_bear"
                    else:
                        trend_label = "choppy"

        breakout_info = check_breakout_signal(klines, entry_period=20)

        return {
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
    except Exception as e:
        print(f"[ERROR] 计算指标失败 {symbol}: {e}")
        log_error('calculate_indicators', f"计算指标失败 {symbol}: {e}")
        traceback.print_exc()
        return None


def compute_batch_kline_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量计算 KlineData 的 Phase 2/3 指标字段（无 TqSDK 依赖）

    对传入的全部K线数据逐根计算：
      - 预计算指标 (Phase 2): ATR, Donchian, MA, trend_factor, trend_label, TR
      - K线分析元数据 (Phase 3): 实体比例, 影线, 成交量比, 跳空, 限价触碰

    Args:
        df: 包含 'open','high','low','close','volume' 列的 DataFrame，按日期升序排列

    Returns:
        带有计算结果的 DataFrame，已追加：
        'atr_20', 'donchian_upper_20', 'donchian_lower_20',
        'ma_10', 'ma_20', 'ma_40', 'trend_factor', 'trend_label', 'true_range',
        'body_ratio', 'upper_shadow_ratio', 'lower_shadow_ratio', 'close_in_range',
        'volume_ratio_20', 'gap_from_pre_close', 'hit_upper_limit', 'hit_lower_limit'

    Usage:
        df = compute_batch_kline_indicators(klines_df)
    """
    df = df.copy()

    # --- True Range ---
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    close = df['close'].values.astype(float)
    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan

    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_close),
                               np.abs(low - prev_close)))
    df['true_range'] = tr

    # --- ATR(20) SMA method ---
    atr_values = np.full(len(df), np.nan)
    for i in range(19, len(df)):
        atr_values[i] = np.mean(tr[i - 19:i + 1])
    df['atr_20'] = atr_values

    # --- Donchian(20) shifted ---
    df['donchian_upper_20'] = df['high'].shift(1).rolling(
        window=20, min_periods=20).max()
    df['donchian_lower_20'] = df['low'].shift(1).rolling(
        window=20, min_periods=20).min()

    # --- MA ---
    df['ma_10'] = df['close'].rolling(window=10, min_periods=10).mean()
    df['ma_20'] = df['close'].rolling(window=20, min_periods=20).mean()
    df['ma_40'] = df['close'].rolling(window=40, min_periods=40).mean()

    # --- Trend factor ---
    trend_factor_list = []
    trend_label_list = []
    for idx, row in df.iterrows():
        ma10 = row.get('ma_10')
        ma20 = row.get('ma_20')
        ma40 = row.get('ma_40')
        atr = row.get('atr_20')
        atr_val = float(atr) if pd.notna(atr) and atr > 0 else None
        if pd.isna(ma10) or pd.isna(ma20) or pd.isna(ma40):
            trend_factor_list.append(None)
            trend_label_list.append(None)
        else:
            tf, tl = compute_trend_factor_from_backtest(
                float(ma10), float(ma20), float(ma40), atr=atr_val
            )
            trend_factor_list.append(tf)
            trend_label_list.append(tl)
    df['trend_factor'] = trend_factor_list
    df['trend_label'] = trend_label_list

    # --- K线分析元数据 (Phase 3) ---
    o = df['open'].values.astype(float)
    h = df['high'].values.astype(float)
    l = df['low'].values.astype(float)
    c = df['close'].values.astype(float)
    v = df['volume'].values.astype(float)

    # range = h - l, 避免除零
    rng = np.maximum(h - l, 1e-10)
    df['body_ratio'] = np.abs(c - o) / rng
    df['upper_shadow_ratio'] = (h - np.maximum(o, c)) / rng
    df['lower_shadow_ratio'] = (np.minimum(o, c) - l) / rng
    df['close_in_range'] = (c - l) / rng

    # 成交量比 = 当日量 / 20日均量
    volume_series = df['volume'].rolling(window=20, min_periods=20).mean()
    df['volume_ratio_20'] = df['volume'] / volume_series
    df['volume_ratio_20'] = df['volume_ratio_20'].replace([np.inf, -np.inf], None)

    # 跳空 = (open - prev_close) / prev_close
    df['gap_from_pre_close'] = (o - prev_close) / np.maximum(prev_close, 1e-10)
    df['gap_from_pre_close'] = df['gap_from_pre_close'].replace([np.inf, -np.inf], None)

    # 限价触碰
    if 'upper_limit' in df.columns and 'lower_limit' in df.columns:
        ul = df['upper_limit'].values.astype(float)
        ll = df['lower_limit'].values.astype(float)
        df['hit_upper_limit'] = (h >= ul) & ~np.isnan(ul)
        df['hit_lower_limit'] = (l <= ll) & ~np.isnan(ll)
    else:
        df['hit_upper_limit'] = None
        df['hit_lower_limit'] = None

    return df


def compute_trend_factor_from_backtest(
    ma_10: float,
    ma_20: float,
    ma_40: float,
    atr: float = None,
    gap_atr_limit: float = 2.0,
    trend_factor_max: float = 0.5,
) -> tuple[float, str]:
    """
    纯函数计算趋势因子和标签（与 backtest/indicators.py compute_trend_factor 一致）

    atr 不可用时返回 (0.0, 'choppy')。

    Returns:
        (trend_factor, trend_label)
    """
    is_bull = ma_10 > ma_20 > ma_40
    is_bear = ma_10 < ma_20 < ma_40

    if not (is_bull or is_bear) or not (atr and atr > 0):
        return 0.0, 'choppy'

    gap_10_20 = abs(ma_10 - ma_20) / atr
    gap_20_40 = abs(ma_20 - ma_40) / atr
    max_gap = max(gap_10_20, gap_20_40)

    trend_strength = min(max_gap / gap_atr_limit, 1.0)
    trend_factor = round(trend_strength * trend_factor_max, 3)

    if trend_strength >= 0.80:
        trend_label = 'strong_bull' if is_bull else 'strong_bear'
    elif trend_strength >= 0.30:
        trend_label = 'weak_bull' if is_bull else 'weak_bear'
    else:
        trend_label = 'choppy'

    return trend_factor, trend_label
