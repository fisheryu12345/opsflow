"""
MBI（市场宽度指数）：让观察池品种集体表态。
使用 TqSDK Quote 实时数据计算。
"""
from decimal import Decimal


def calculate_mbi(api, watchlist, opening_ranges):
    """
    三个投票维度：
    1. 隔夜跳空：开盘价 vs 昨日收盘
    2. 区间重心：开盘区间中点 vs 昨日收盘
    3. 突破方向：开盘区间后最先突破哪边
    返回 (mbi_value, mbi_label)
    """
    total_score = 0
    valid_count = 0

    for item in watchlist:
        symbol = item['symbol'] if isinstance(item, dict) else item[0]
        quote = api.get_quote(symbol)
        or_data = opening_ranges.get(symbol)
        if or_data is None or or_data.get('R') is None:
            continue

        product_code = item['product_code'] if isinstance(item, dict) else ''
        pre_close = float(getattr(quote, 'pre_close', 0) or 0)
        open_price = float(getattr(quote, 'open', 0) or 0)
        last_price = float(getattr(quote, 'last_price', 0) or 0)
        or_h = float(or_data['H'])
        or_l = float(or_data['L'])

        if pre_close <= 0 or open_price <= 0:
            continue

        score = score_for_symbol(
            product_code, open_price, pre_close,
            or_h, or_l, last_price
        )
        total_score += score
        valid_count += 1

    if valid_count == 0:
        return Decimal('0.5'), '中性'

    # 总分映射到 [0, 1]
    max_possible = valid_count * 3  # 每个品种最高 +3
    min_possible = valid_count * -3  # 每个品种最低 -3
    if max_possible == min_possible:
        return Decimal('0.5'), '中性'

    mbi_value = Decimal(str(total_score - min_possible)) / Decimal(str(max_possible - min_possible))
    label = mbi_to_label(mbi_value)

    print(f"[HVOB] MBI 计算完成: {mbi_value:.4f} ({label}), 参与品种: {valid_count}/{len(watchlist)}")
    return mbi_value, label


def score_for_symbol(product_code, open_price, pre_close, or_h, or_l, last_price):
    """
    单品种打分：-3 到 +3
    三个维度各 ±1:
    - 隔夜跳空: open 在 pre_close 之上(+1)或之下(-1)
    - 区间重心: OR中点 在 pre_close 之上(+1)或之下(-1)
    - 突破方向: last_price 在 OR范围之上(+1)或之下(-1)
    """
    score = 0

    # 1. 隔夜跳空
    gap_pct = (open_price - pre_close) / pre_close
    if abs(gap_pct) < 0.0005:  # 基本平开
        pass
    elif gap_pct > 0:
        score += 1
    else:
        score -= 1

    # 2. 区间重心
    or_mid = (or_h + or_l) / 2
    if or_mid > pre_close:
        score += 1
    elif or_mid < pre_close:
        score -= 1

    # 3. 突破方向（当前价格相对开盘区间的位置）
    if last_price > or_h:
        score += 1
    elif last_price < or_l:
        score -= 1

    return score


def mbi_to_label(mbi_value):
    """mbi [0,1] → 标签"""
    if mbi_value > Decimal('0.75'):
        return '极强多头'
    elif mbi_value > Decimal('0.65'):
        return '多头'
    elif mbi_value > Decimal('0.45'):
        return '中性'
    elif mbi_value > Decimal('0.35'):
        return '空头'
    else:
        return '极强空头'


def get_trading_permission(mbi_value, direction):
    """
    根据 MBI 和方向返回仓位权重 [0, 0.5, 1]。
    direction: 1=多, -1=空
    """
    if direction == 1:
        if mbi_value > Decimal('0.75'):
            return 1.0    # 极强多头 → 正常做多
        elif mbi_value > Decimal('0.65'):
            return 1.0    # 多头 → 正常做多
        elif mbi_value >= Decimal('0.45'):
            return 1.0    # 震荡 → 正常
        elif mbi_value >= Decimal('0.35'):
            return 0.5    # 空头 → 半仓
        else:
            return 0.0    # 极强空头 → 禁止做多
    else:
        if mbi_value > Decimal('0.75'):
            return 0.0    # 极强多头 → 禁止做空
        elif mbi_value > Decimal('0.65'):
            return 0.5    # 多头 → 半仓
        elif mbi_value >= Decimal('0.45'):
            return 1.0    # 震荡 → 正常
        elif mbi_value >= Decimal('0.35'):
            return 1.0    # 空头 → 正常做空
        else:
            return 1.0    # 极强空头 → 正常做空
