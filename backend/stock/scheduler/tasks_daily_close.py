import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR, SMA,MA
from tqsdk.tafunc import hhv, llv
# from stock.utils.send_mail import send_email
from stock.tasks.celery_test import send_email_task as send_email


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal, RolloverLog, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk
from stock.utils.calculate_indicators import calculate_indicators

def save_daily_signal_and_update_position(symbol, product_code, trend_factor, trend_label, 
                                          breakout_info, account,trade_type):
    """
    步骤3：保存每日策略信号并更新持仓状态（检查是否需要开仓）
    
    参数：
    symbol: 合约代码
    product_code: 品种代码
    trend_factor: 趋势因子
    trend_label: 趋势标签
    breakout_info: 突破信号信息字典（来自check_breakout_signal）
    account: 交易账户对象
    
    返回：
    bool: 是否成功保存
    """
    if not breakout_info['is_breakout']:
        return False
    try:
        with transaction.atomic():
            DailyStrategySignal.objects.update_or_create(
                account=account,
                symbol=symbol,
                trade_date=breakout_info['trade_date'],
                defaults={
                    'trend_factor': Decimal(str(trend_factor)),
                    'trend_label': trend_label,
                    'donchian_upper': Decimal(str(breakout_info['entry_high'])) if breakout_info['entry_high'] else None,
                    'donchian_lower': Decimal(str(breakout_info['entry_low'])) if breakout_info['entry_low'] else None,
                    'is_breakout': breakout_info['is_breakout'],
                    'signal_direction': breakout_info['signal_direction'],
                    'trade_type': trade_type,
                    'remark': breakout_info['remark'] or f"趋势状态: {trend_label} (factor={trend_factor})"
                }
            )
            return True
            
    except Exception as e:
        print(f"[ERROR] 保存策略信号失败 {symbol}: {e}")
        return False

# ==================== APScheduler 任务入口 ====================

def job_daily_close_calculation():
    """
    每日收盘后定时任务入口
    
    执行流程：
    1. 同步期货合约列表（获取最新主力合约信息）
    2. 计算活跃品种的技术指标和策略信号
    3. 检查是否需要开仓
    4. 更新持仓跟踪价格
    5. 检查是否需要平仓
    6. 检查是否需要移仓
    7. 邮件通知今日持仓、信号和操作建议（TODO）
    """
    try:
        # 第1步：同步期货合约列表
        sync_contract_list_from_tqsdk()
        
        # 第2步：计算活跃品种的技术指标
        contracts = PositionState.objects.all().values('symbol', 'product_code')
        for contract in contracts:
            if FullContractList.objects.filter(symbol=contract['symbol'], is_active=True).exists():
                contract['is_active'] = True
        active_contracts = [contract for contract in contracts if contract.get('is_active')]
        print(active_contracts)
        indicator_results = []
        
        if active_contracts:
            success_count = 0
            fail_count = 0
            
            for contract in active_contracts:
                try:
                    result = calculate_indicators(
                        symbol=contract['symbol'], 
                        product_code=contract['product_code'], 
                        days=60
                    )
                    indicators = result.copy()
                    del indicators['breakout_info']  # 不需要把突破信息存到 indicators 字段里
                    del indicators['data_points']  # 不需要存储数据点数量
                    PositionState.objects.filter(symbol=contract['symbol']).update(indicators=indicators,latest_close_price=result['latest_close'])
                    
                    if result:
                        # print(result)
                        indicator_results.append(result)
                        success_count += 1
                    else:
                        fail_count += 1
                        
                except Exception as e:
                    fail_count += 1
                    print(str(e))

        # print(indicator_results)        
        # 第3步：检查是否需要开仓（保存信号到数据库）
        default_account = TradingAccount.objects.filter(is_active=True).first()
        
        if default_account and indicator_results:
            open_count = 0
            
            for result in indicator_results:
                breakout_info = result.get('breakout_info', {})
                
                if breakout_info.get('is_breakout'):
                    success = save_daily_signal_and_update_position(
                        symbol=result['symbol'],
                        product_code=result['product_code'],
                        trend_factor=result['trend_factor'],
                        trend_label=result['trend_label'],
                        breakout_info=breakout_info,
                        account=default_account,
                        trade_type='OPEN'
                    )
                    
                    if success:
                        open_count += 1
        
        # 第4步：更新持仓跟踪价格
        # update_all_positions_latest_price()
        
        # 第5步：检查是否需要平仓
        # check_exit_signals()
        
        # 第6步：检查是否需要移仓
        # check_rollover_needed()
        # 第7步：邮件通知今日持仓、信号和操作建议（TODO）
        send_email(
            subject='收盘计算',
            body="今日收盘指标已经计算完毕，请查看邮件。",
            receiver_email='312711936@qq.com',
            is_html=True  # 默认就是True，可以省略
        ).delay()  # 使用 Celery 异步发送邮件

        
    except Exception as e:
        import traceback
        traceback.print_exc()
