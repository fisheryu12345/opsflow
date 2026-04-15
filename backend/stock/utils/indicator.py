import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,  DailyPerformance, DailyStrategySignal,  PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk


def update_position_tracking(symbol, current_close, direction, highest_close, lowest_close):
    """更新持仓跟踪价格（最高价、最低价）"""
    if direction > 0:
        if highest_close is None:
            highest_close = current_close
        else:
            highest_close = max(highest_close, current_close)
    elif direction < 0:
        if lowest_close is None:
            lowest_close = current_close
        else:
            lowest_close = min(lowest_close, current_close)
    
    return highest_close, lowest_close


def update_all_positions_latest_price():
    """步骤4：更新所有有持仓记录的品种的最新收盘价、最高价和最低价"""
    positions = PositionState.objects.all()
    
    if not positions:
        return
    
    updated_count = 0
    
    for position in positions:
        try:
            latest_signal = DailyStrategySignal.objects.filter(
                symbol=position.symbol
            ).order_by('-trade_date').first()
            
            if not latest_signal:
                continue
            
            api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
            
            try:
                klines = api.get_kline_serial(position.symbol, duration_seconds=24 * 60 * 60, data_length=1)
                
                if len(klines) > 0:
                    current_close = float(klines.iloc[-1]['close'])
                    
                    new_highest, new_lowest = update_position_tracking(
                        symbol=position.symbol,
                        current_close=current_close,
                        direction=position.direction,
                        highest_close=position.highest_close,
                        lowest_close=position.lowest_close
                    )
                    
                    update_fields = ['latest_close_price']
                    position.latest_close_price = Decimal(str(current_close))
                    
                    if position.direction > 0 and new_highest != position.highest_close:
                        position.highest_close = Decimal(str(new_highest))
                        update_fields.append('highest_close')
                    elif position.direction < 0 and new_lowest != position.lowest_close:
                        position.lowest_close = Decimal(str(new_lowest))
                        update_fields.append('lowest_close')
                    
                    position.save(update_fields=update_fields)
                    updated_count += 1
                    
            finally:
                api.close()
                
        except Exception:
            pass


def check_exit_signals():
    """步骤5：检查是否需要平仓"""
    positions = PositionState.objects.filter(direction__ne=0)
    
    if not positions:
        return
    
    for position in positions:
        try:
            # TODO: 实现平仓逻辑
            pass
        except Exception:
            pass


def check_rollover_needed():
    """步骤6：检查是否需要移仓"""
    positions = PositionState.objects.filter(
        direction__ne=0,
        is_rollover_enabled=True
    )
    
    if not positions:
        return
    
    for position in positions:
        try:
            # TODO: 实现移仓逻辑
            pass
        except Exception:
            pass

    """
    计算唐奇安通道突破价位
    逻辑检查：通过。iloc[-N-1:-1] 完美避开了当前K线。
    """
    if len(klines) < ENTRY_PERIOD + 2:
        return 0.0, 0.0, 0.0, 0.0
    
    try:
        # 1. 入场通道 (过去 N 天最高/低，不含当前)
        # 切片逻辑：倒数第 N+1 根 到 倒数第 2 根 (共 N 根)
        high_prior = klines["high"].iloc[-ENTRY_PERIOD - 1:-1]
        low_prior = klines["low"].iloc[-ENTRY_PERIOD - 1:-1]
        
        if len(high_prior) == 0:
            return 0.0, 0.0, 0.0, 0.0
            
        entry_high = float(high_prior.max())
        entry_low = float(low_prior.min())
        
        # 2. 离场通道 (过去 M 天最高/低，不含当前)
        exit_high_prior = klines["high"].iloc[-EXIT_PERIOD - 1:-1]
        exit_low_prior = klines["low"].iloc[-EXIT_PERIOD - 1:-1]
        
        # 如果数据不足 M 天，回退到入场通道数据（防御性编程）
        exit_high = float(exit_high_prior.max()) if len(exit_high_prior) > 0 else entry_high
        exit_low = float(exit_low_prior.min()) if len(exit_low_prior) > 0 else entry_low
        
        return entry_high, entry_low, exit_high, exit_low
        
    except Exception:
        return 0.0, 0.0, 0.0, 0.0