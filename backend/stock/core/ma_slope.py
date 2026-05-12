"""
MA10 slope computation and ranking — pure domain logic for the comparison strategy.
"""
import pandas as pd
from decimal import Decimal

DEFAULTS = {
    'SLOPE_PERIOD': 3,
    'RANKING_TOP_N': 5,
    'EXIT_THRESHOLD_RANK': 12,
    'MIN_SLOPE_THRESHOLD': 0.05,
    'MAX_POSITIONS_PER_SIDE': 5,
    'RISK_PER_TRADE_PCT': 1.0,
    'ATR_STOP_MULTIPLIER': 2.5,
}


def compute_ma10_slope(kline_df, slope_period=3):
    """
    从 K 线 DataFrame 计算单个品种的 MA10 斜率。

    Args:
        kline_df: DataFrame，至少包含 close 列，按日期升序排列
        slope_period: MA10 变化率回溯周期（默认 3 日）

    Returns:
        (ma10, slope_pct) 或 (None, None)
    """
    if kline_df is None or len(kline_df) < 10 + slope_period:
        return None, None

    close = kline_df['close']
    ma10 = close.rolling(window=10).mean()

    latest_ma10 = ma10.iloc[-1]
    prev_ma10 = ma10.iloc[-1 - slope_period]

    if pd.isna(latest_ma10) or pd.isna(prev_ma10) or prev_ma10 == 0:
        return None, None

    slope_pct = float((latest_ma10 - prev_ma10) / prev_ma10 * 100)
    return float(latest_ma10), slope_pct


def rank_by_ma10_slope(account, trade_date=None):
    """
    全品种 MA10 斜率排名。

    查询 KlineData 的 ma_10 字段（预计算），按 slope_pct 降序排列，
    返回多头候选、空头候选 和 完整排名列表。

    Args:
        account: TradingAccount 实例，用于查询该账户激活的品种
        trade_date: 交易日（默认当天）

    Returns:
        (long_candidates, short_candidates, all_ranked)
        每个元素为 dict 列表: {symbol, product_code, slope_pct, rank, volume_multiple}
    """
    from django.utils import timezone
    from stock.models import KlineData, AccountContractConfig, FullContractList

    if trade_date is None:
        trade_date = timezone.now().date()

    slope_period = DEFAULTS['SLOPE_PERIOD']

    # 获取该账户激活的品种代码
    active_products = set(
        AccountContractConfig.objects.filter(
            account=account, is_active=True, allow_open=True
        ).values_list('product_code', flat=True)
    )
    if not active_products:
        return [], [], []

    # 查询这些品种的 KlineData ma_10（最新两笔）
    results = []
    for product_code in active_products:
        klines = KlineData.objects.filter(
            product_code=product_code,
            ma_10__isnull=False,
            date__lte=trade_date,
        ).order_by('-date')[:10 + slope_period]

        if len(klines) < 10 + slope_period:
            continue

        latest = klines[0]
        prev = klines[slope_period]

        if latest.ma_10 is None or prev.ma_10 is None or prev.ma_10 == 0:
            continue

        slope_pct = float((latest.ma_10 - prev.ma_10) / prev.ma_10 * 100)

        try:
            contract = FullContractList.objects.get(product_code=product_code)
            symbol = contract.symbol
            vm = contract.volume_multiple
        except FullContractList.DoesNotExist:
            symbol = product_code
            vm = 10

        results.append({
            'symbol': symbol,
            'product_code': product_code,
            'slope_pct': slope_pct,
            'volume_multiple': vm,
        })

    # 降序排列
    results.sort(key=lambda x: x['slope_pct'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    min_slope = DEFAULTS['MIN_SLOPE_THRESHOLD']
    n = DEFAULTS['RANKING_TOP_N']

    long_candidates = [
        r for r in results
        if r['slope_pct'] > min_slope
    ][:n]

    short_candidates = [
        r for r in reversed(results)
        if r['slope_pct'] < -min_slope
    ][:n]

    return long_candidates, short_candidates, results


def get_ma10_slope_for_symbol(symbol, trade_date=None, slope_period=3):
    """
    查询单个品种的当前 MA10 斜率。

    Returns:
        slope_pct (float) 或 None
    """
    from django.utils import timezone
    from stock.models import KlineData

    if trade_date is None:
        trade_date = timezone.now().date()

    klines = KlineData.objects.filter(
        symbol=symbol,
        ma_10__isnull=False,
        date__lte=trade_date,
    ).order_by('-date')[:10 + slope_period]

    if len(klines) < 10 + slope_period:
        return None

    latest = klines[0].ma_10
    prev = klines[slope_period].ma_10
    if latest is None or prev is None or prev == 0:
        return None

    return float((latest - prev) / prev * 100)


def calculate_atr_from_klines(kline_df, period=20):
    """
    从 K 线 DataFrame 计算 ATR。

    Args:
        kline_df: DataFrame，包含 high/low/close 列
        period: ATR 周期（默认 20）

    Returns:
        atr (float) 或 None
    """
    if kline_df is None or len(kline_df) < period + 1:
        return None

    high = kline_df['high'].values
    low = kline_df['low'].values
    close = kline_df['close'].values

    tr_list = []
    for i in range(1, len(kline_df)):
        hl = high[i] - low[i]
        hpc = abs(high[i] - close[i - 1])
        lpc = abs(low[i] - close[i - 1])
        tr_list.append(max(hl, hpc, lpc))

    if len(tr_list) < period:
        return None

    return float(sum(tr_list[-period:]) / period)
