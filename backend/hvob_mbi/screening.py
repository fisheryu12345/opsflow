"""
盘前筛选：启动时执行，从全市场选出 6-10 个今日观察品种。
所有数据从 TqSDK 实时拉取，不依赖 KlineData 表。
"""
import time
from decimal import Decimal
import pandas as pd
from stock.models import FullContractList
from .config import ATR_PERCENT_RANK_TOP, MIN_AMPLITUDE_5D, PREFERRED_PRODUCTS, AVOID_PRODUCTS, LOW_LIQUIDITY_PRODUCTS, MAX_VOL_SCORE


def select_watchlist(api, config=None):
    """
    使用 TqSDK get_kline_serial 拉取日线数据，实时计算评分。
    返回 [{
        'symbol': str, 'product_code': str, 'score': float,
        'atr_pct': float, 'avg_amp': float, 'vol_ratio': float,
        'atr_score': float, 'amp_score': float, 'vol_score': float,
        'bonus': int, 'open_interest': float,
    }, ...] 按评分降序。
    """
    min_size = config.min_watchlist_size if config else 5
    max_pos = config.max_positions_per_day if config else 5
    contracts = FullContractList.objects.exclude(exchange='CFFEX').values('symbol', 'product_code')
    if not contracts:
        print("[HVOB] 警告: 无主力合约数据")
        return []

    scores = {}
    kline_serials = {}

    # 批量订阅日线数据
    for c in contracts:
        sym = c['symbol']
        kline_serials[sym] = api.get_kline_serial(sym, 86400, 30)

    # 等待数据到达（循环 pumping 直到超时或全部就绪）
    print("[HVOB] 等待各品种 K 线数据就绪...")
    deadline = time.time() + 60
    while time.time() < deadline:
        ready_count = 0
        for c in contracts:
            kl = kline_serials.get(c['symbol'])
            if kl is not None and len(kl) >= 25:
                ready_count += 1
        if ready_count == len(contracts):
            print(f"[HVOB] 全部 {ready_count} 个品种 K 线数据就绪")
            break
        api.wait_update(deadline=time.time() + 2)
    else:
        print(f"[HVOB] K 线数据就绪 {ready_count}/{len(contracts)}，继续计算...")

    # 计算每个品种评分
    for c in contracts:
        sym = c['symbol']
        pc = c['product_code']
        kl = kline_serials.get(sym)
        if kl is None or len(kl) < 25:
            continue

        close_list = [kl.iloc[-i]['close'] for i in range(1, 4) if not pd.isna(kl.iloc[-i]['close'])]
        if not close_list:
            continue
        latest_close = float(close_list[0])

        # 计算 ATR%
        high_low_list = []
        for i in range(1, 23):
            row = kl.iloc[-i]
            if pd.isna(row['close']):
                continue
            high_low_list.append(float(row['high'] - row['low']))
        if len(high_low_list) < 14:
            continue
        atr_20 = sum(high_low_list) / len(high_low_list)
        atr_pct = atr_20 / latest_close if latest_close > 0 else 0

        # 计算 5日平均振幅
        amp_list = []
        for i in range(1, 6):
            row = kl.iloc[-i]
            if pd.isna(row['open']) or row['open'] == 0:
                continue
            amp = float(row['high'] - row['low']) / float(row['open'])
            amp_list.append(amp)
        if len(amp_list) < 3:
            continue
        avg_amp = sum(amp_list) / len(amp_list)

        # 成交量确认
        vol_list = [float(kl.iloc[-i]['volume']) for i in range(1, 22) if not pd.isna(kl.iloc[-i]['volume'])]
        if len(vol_list) < 15:
            continue
        latest_vol = vol_list[0]
        avg_vol_20 = sum(vol_list) / len(vol_list)
        vol_ratio = latest_vol / avg_vol_20 if avg_vol_20 > 0 else 0

        # 综合评分
        score = Decimal('0')
        atr_score = Decimal(str(round(atr_pct * 100, 4))) if atr_pct >= ATR_PERCENT_RANK_TOP else Decimal('0')
        amp_score = Decimal(str(round(avg_amp * 50, 4))) if avg_amp >= MIN_AMPLITUDE_5D else Decimal('0')
        vol_raw = (vol_ratio - 1.0) * 10 if vol_ratio > 1.0 else 0
        vol_score = Decimal(str(round(min(vol_raw, MAX_VOL_SCORE), 4)))
        bonus = Decimal('3') if pc.upper() in PREFERRED_PRODUCTS else Decimal('0')
        if pc.upper() in AVOID_PRODUCTS:
            bonus -= Decimal('2')
        if pc.upper() in LOW_LIQUIDITY_PRODUCTS:
            continue  # 冷门品种直接排除，不加入评分
        score = atr_score + amp_score + vol_score + bonus

        # 持仓量过滤（低于 2 万手跳过，使用 close_oi 字段）
        latest_oi = float(kl.iloc[-1]['close_oi']) if not pd.isna(kl.iloc[-1]['close_oi']) else 0
        if latest_oi < 20000:
            continue

        scores[(sym, pc)] = {
            'symbol': sym,
            'product_code': pc,
            'score': float(score),
            'atr_pct': round(atr_pct, 4),
            'avg_amp': round(avg_amp, 4),
            'vol_ratio': round(vol_ratio, 2),
            'atr_score': round(float(atr_score), 2),
            'amp_score': round(float(amp_score), 2),
            'vol_score': round(float(vol_score), 2),
            'bonus': int(bonus),
            'open_interest': int(latest_oi),
        }

    # 按评分排序取前 min_watchlist_size
    sorted_results = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
    top_n = max(min_size, min(max_pos * 2, 10))
    result = sorted_results[:top_n]

    print(f"[HVOB] 盘前筛选完成: 共 {len(scores)} 个品种评分, 选取 {len(result)} 个")
    for r in result:
        print(f"  {r['symbol']} ({r['product_code']}) 评分: {r['score']:.2f}  "
              f"ATR%={r['atr_pct']:.3f} 振幅={r['avg_amp']:.3f} 量比={r['vol_ratio']:.2f} "
              f"ATR分={r['atr_score']} AMP分={r['amp_score']} 量分={r['vol_score']} 奖惩={r['bonus']:+d}")

    return result
