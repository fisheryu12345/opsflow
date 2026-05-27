"""
将 HVOB-MBI 的开/平仓信号和交易记录写入现有表。
"""
import json
from decimal import Decimal
from datetime import date
from stock.models import (
    DailyStrategySignal, ClosedPositionRecord, PositionState,
    DailyEquitySnapshot, SymbolDailyPnl, TradingAccount,
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
    or_l = Decimal(str(opening_range_l))
    or_h = Decimal(str(opening_range_h))
    or_r = Decimal(str(opening_range_r))
    stop_loss_price = or_l - Decimal('0.2') * or_r if direction == 1 else or_h + Decimal('0.2') * or_r

    signal = DailyStrategySignal.objects.create(
        account=account,
        symbol=symbol,
        product_code=product_code,
        trade_date=trade_date,
        trade_type='ENTRY',
        signal_direction=direction,
        contract_target_number=quantity,
        executed_status='SUCCESS',
        trend_factor=Decimal('0'),
        trend_label='HVOB',
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'entry_price': float(entry_price),
            'stop_loss_price': float(stop_loss_price),
            'or_h': float(opening_range_h),
            'or_l': float(opening_range_l),
            'or_r': float(opening_range_r),
            'mbi': float(mbi_value),
            'weight': position_weight,
        }, ensure_ascii=False)
    )

    # 同步持仓表
    PositionState.objects.update_or_create(
        account=account,
        symbol=symbol,
        defaults={
            'product_code': product_code,
            'units': 1,
            'direction': direction,
            'contract_total_position': quantity,
            'first_open_price': Decimal(str(entry_price)),
            'open_date': trade_date if isinstance(trade_date, date) else date.today(),
            'cost_price': Decimal(str(entry_price)),
            'stop_loss_price': Decimal(str(stop_loss_price)),
            'entry_trend_factor': Decimal('0'),
            'entry_trend_label': 'HVOB',
            'h20_price': Decimal(str(opening_range_h)),
            'l20_price': Decimal(str(opening_range_l)),
            'protect_cost_enabled': False,
            'is_rollover_needed': False,
        }
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
        trend_factor=Decimal('0'),
        trend_label='HVOB',
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'exit_reason': exit_reason,
            'exit_price': float(exit_price),
        }, ensure_ascii=False)
    )
    _create_closed_record(account, symbol, product_code, trade_date,
                          direction, exit_price, pnl, cost_price, volume)
    _reset_position_state(account, symbol)
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
        trend_factor=Decimal('0'),
        trend_label='HVOB',
        remark=json.dumps({
            'strategy': 'HVOB-MBI',
            'exit_reason': '止损',
            'exit_price': float(exit_price),
        }, ensure_ascii=False)
    )
    _create_closed_record(account, symbol, product_code, trade_date,
                          direction, exit_price, 'STOP_LOSS', pnl, cost_price, volume)
    _reset_position_state(account, symbol)
    log_trade(FSM, f"HVOB STOP_LOSS {symbol} {volume}手@{exit_price} PnL={pnl}",
              symbol=symbol, log_level='INFO', account=account)
    return stop_signal


def _reset_position_state(account, symbol):
    """平仓时删除持仓记录"""
    PositionState.objects.filter(account=account, symbol=symbol).delete()


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
        trade_date=trade_date,
        defaults={
            'balance': Decimal(str(balance)),
            'daily_pnl': Decimal(str(pnl)),
        }
    )


def record_symbol_pnl(account, trade_date, symbol, product_code, pnl):
    """写入 SymbolDailyPnl"""
    SymbolDailyPnl.objects.update_or_create(
        account=account,
        trade_date=trade_date,
        symbol=symbol,
        defaults={
            'product_code': product_code,
            'pnl': Decimal(str(pnl)),
        }
    )
