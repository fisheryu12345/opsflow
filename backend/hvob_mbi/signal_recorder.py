"""
将 HVOB-MBI 的开/平仓信号和交易记录写入现有表。
"""
import json
from decimal import Decimal
from datetime import date
from stock.models import (
    DailyStrategySignal, ClosedPositionRecord,
    DailyEquitySnapshot, SymbolDailyPnl,
)
from stock.utils.log_util import log_trade

FSM = 'hvob_mbi.signal_recorder'


def record_entry_signal(account, symbol, product_code, trade_date, direction, quantity,
                        entry_price, opening_range_h, opening_range_l, opening_range_r,
                        mbi_value, position_weight):
    """
    写入 DailyStrategySignal:
      trade_type='ENTRY'
    """
    signal = DailyStrategySignal.objects.create(
        account=account,
        symbol=symbol,
        product_code=product_code,
        trade_date=trade_date,
        trade_type='ENTRY',
        signal_direction=direction,
        contract_target_number=quantity,
        entry_price=Decimal(str(entry_price)),
        stop_loss_price=Decimal(str(opening_range_l - Decimal('0.2') * opening_range_r if direction == 1
                                   else opening_range_h + Decimal('0.2') * opening_range_r)),
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'or_h': float(opening_range_h),
            'or_l': float(opening_range_l),
            'or_r': float(opening_range_r),
            'mbi': float(mbi_value),
            'weight': position_weight,
        }, ensure_ascii=False)
    )
    log_trade(FSM, f"HVOB ENTRY {symbol} {'多' if direction > 0 else '空'} {quantity}手@{entry_price}",
              symbol=symbol, log_level='INFO', account=account)
    return signal


def record_exit_signal(account, symbol, product_code, trade_date, direction,
                       exit_price, exit_reason, pnl, cost_price, volume):
    """
    写入 DailyStrategySignal (trade_type='EXIT') + ClosedPositionRecord。
    用于止盈/保本/强制平仓。
    """
    exit_signal = DailyStrategySignal.objects.create(
        account=account,
        symbol=symbol,
        product_code=product_code,
        trade_date=trade_date,
        trade_type='EXIT',
        signal_direction=direction,
        contract_target_number=volume,
        exit_price=Decimal(str(exit_price)),
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'exit_reason': exit_reason,
        }, ensure_ascii=False)
    )
    _create_closed_record(account, symbol, product_code, trade_date,
                          direction, exit_price, pnl, cost_price, volume)
    log_trade(FSM, f"HVOB EXIT {symbol} {exit_reason} {volume}手@{exit_price} PnL={pnl}",
              symbol=symbol, log_level='INFO', account=account)
    return exit_signal


def record_stop_loss_signal(account, symbol, product_code, trade_date, direction,
                            exit_price, pnl, cost_price, volume):
    """
    写入 DailyStrategySignal (trade_type='STOP_LOSS') + ClosedPositionRecord。
    """
    stop_signal = DailyStrategySignal.objects.create(
        account=account,
        symbol=symbol,
        product_code=product_code,
        trade_date=trade_date,
        trade_type='STOP_LOSS',
        signal_direction=direction,
        contract_target_number=volume,
        exit_price=Decimal(str(exit_price)),
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'exit_reason': '止损',
        }, ensure_ascii=False)
    )
    _create_closed_record(account, symbol, product_code, trade_date,
                          direction, exit_price, 'STOP_LOSS', pnl, cost_price, volume)
    log_trade(FSM, f"HVOB STOP_LOSS {symbol} {volume}手@{exit_price} PnL={pnl}",
              symbol=symbol, log_level='INFO', account=account)
    return stop_signal


def _create_closed_record(account, symbol, product_code, trade_date,
                          direction, exit_price, pnl, cost_price, volume):
    """写入 ClosedPositionRecord"""
    ClosedPositionRecord.objects.create(
        account=account,
        symbol=symbol,
        product_code=product_code,
        trade_date=trade_date,
        direction=direction,
        volume=volume or 0,
        cost_price=Decimal(str(cost_price)) if cost_price else Decimal('0'),
        exit_price=Decimal(str(exit_price)),
        pnl=Decimal(str(pnl)) if pnl else Decimal('0'),
    )


def record_daily_equity(account, trade_date, balance, pnl):
    """写入 DailyEquitySnapshot"""
    DailyEquitySnapshot.objects.update_or_create(
        account=account,
        date=trade_date,
        defaults={
            'balance': Decimal(str(balance)),
            'daily_pnl': Decimal(str(pnl)),
        }
    )


def record_symbol_pnl(account, trade_date, symbol, product_code, pnl):
    """写入 SymbolDailyPnl"""
    SymbolDailyPnl.objects.update_or_create(
        account=account,
        date=trade_date,
        symbol=symbol,
        defaults={
            'product_code': product_code,
            'pnl': Decimal(str(pnl)),
        }
    )
