"""
滑点记录工具

记录每笔交易的理论触发价与实际成交价的偏差 (slippage)，
供后续统计分析使用。
"""
import logging
from decimal import Decimal
from datetime import date
from typing import Optional

from stock.models import SlippageRecord, TradingAccount, DailyStrategySignal

logger = logging.getLogger(__name__)


def record_slippage(
    account: TradingAccount,
    trade_type: str,
    symbol: str,
    product_code: str,
    position_direction: int,
    volume: int,
    signal_price: Decimal,
    fill_price: Decimal,
    price_tick: Decimal = Decimal('1'),
    signal: Optional[DailyStrategySignal] = None,
    trade_date: Optional[date] = None,
) -> Optional[SlippageRecord]:
    """
    记录一笔交易的滑点。

    Args:
        account: 交易账户
        trade_type: 交易类型 (ENTRY/EXIT/STOP_LOSS/ADD_ON)
        symbol: 合约代码
        product_code: 品种代码
        position_direction: 持仓方向 (1=多头, -1=空头)
        volume: 成交手数
        signal_price: 信号触发时的理论价格
        fill_price: 实际成交均价
        price_tick: 合约最小变动价位 (用于计算滑点跳动数)
        signal: 关联的 DailyStrategySignal (可选)
        trade_date: 交易日期 (默认今天)

    Returns:
        SlippageRecord 实例，若参数无效则返回 None
    """
    if not all([account, symbol, volume > 0]):
        logger.warning('滑点记录跳过: 参数不完整')
        return None

    if signal_price is None or fill_price is None:
        logger.warning('滑点记录跳过: 价格不完整 (signal=%s, fill=%s)', signal_price, fill_price)
        return None

    signal_price = Decimal(str(signal_price))
    fill_price = Decimal(str(fill_price))
    price_tick = Decimal(str(price_tick))

    # 归一化滑点: 正值始终 = 不利成本, 负值始终 = 有利成本
    # 入场: (fill - signal) × direction   → 多头买高为正, 空头卖低为正
    # 出场: (fill - signal) × (-direction) → 多头卖低为正, 空头买高为正
    if trade_type in ('ENTRY', 'ADD_ON'):
        slippage = (fill_price - signal_price) * position_direction
    elif trade_type in ('EXIT', 'STOP_LOSS'):
        slippage = (fill_price - signal_price) * (-position_direction)
    else:
        slippage = fill_price - signal_price
    slippage_ticks = slippage / price_tick if price_tick != 0 else Decimal('0')

    # 判断滑点方向: 成交价是否优于信号价
    if trade_type in ('ENTRY', 'ADD_ON'):
        # 建仓: 多头希望买低 (fill < signal), 空头希望卖高 (fill > signal)
        if position_direction == 1:
            is_favorable = fill_price < signal_price
        else:
            is_favorable = fill_price > signal_price
    elif trade_type in ('EXIT', 'STOP_LOSS'):
        # 平仓: 多头希望卖高 (fill > signal), 空头希望买低 (fill < signal)
        if position_direction == 1:
            is_favorable = fill_price > signal_price
        else:
            is_favorable = fill_price < signal_price
    else:
        is_favorable = False

    record = SlippageRecord.objects.create(
        account=account,
        signal=signal,
        symbol=symbol,
        product_code=product_code,
        trade_type=trade_type,
        trade_date=trade_date or date.today(),
        position_direction=position_direction,
        volume=volume,
        signal_price=signal_price,
        fill_price=fill_price,
        slippage=slippage,
        slippage_ticks=slippage_ticks,
        is_favorable=is_favorable,
    )

    logger.debug(
        '滑点记录: %s %s signal=%.2f fill=%.2f slippage=%.2f (%s)',
        symbol, trade_type, signal_price, fill_price, slippage,
        '有利' if is_favorable else '不利',
    )

    return record
