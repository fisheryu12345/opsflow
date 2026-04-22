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


