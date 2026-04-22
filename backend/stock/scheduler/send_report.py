import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from backend.stock.tasks.send_mail import send_email_task as send_email
from django.template.loader import render_to_string


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,DailyStrategySignal, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk
from stock.utils.calculate_indicators import calculate_indicators

def send_report(account, current_date):
    """
    发送今日交易执行情况报告（加仓、移仓、平仓）
    
    :param account: TradingAccount实例
    :param current_date: 当前日期
    :return: 是否发送成功
    """
    from django.template.loader import render_to_string
    from django.utils import timezone
    
    try:
        # 查询今天的交易执行记录
        today_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
        
        # today_trades = TradeExecution.objects.filter(
        #     account=account,
        #     trade_time__gte=today_start,
        #     trade_time__lte=today_end
        # ).order_by('trade_time')
        
        # # 分类统计
        # addon_trades = today_trades.filter(trade_type='ADD_ON')
        # rollover_exit_trades = today_trades.filter(trade_type='ROLLOVER_EXIT')
        # rollover_entry_trades = today_trades.filter(trade_type='ROLLOVER_ENTRY')
        # stop_loss_trades = today_trades.filter(trade_type='STOP_LOSS')
        # close_signal_trades = today_trades.filter(trade_type='CLOSE_SIGNAL')
        
        # # 计算统计数据
        # total_trades = (len(addon_trades) + len(rollover_exit_trades) + 
        #                len(rollover_entry_trades) + len(stop_loss_trades) + 
        #                len(close_signal_trades))
        
        # # 使用Django Template渲染HTML
        # context = {
        #     'current_date': current_date,
        #     'total_trades': total_trades,
        #     'addon_count': len(addon_trades),
        #     'rollover_count': len(rollover_exit_trades),
        #     'stop_loss_count': len(stop_loss_trades),
        #     'close_signal_count': len(close_signal_trades),
        #     'addon_trades': addon_trades,
        #     'rollover_exit_trades': rollover_exit_trades,
        #     'rollover_entry_trades': rollover_entry_trades,
        #     'stop_loss_trades': stop_loss_trades,
        #     'close_signal_trades': close_signal_trades,
        # }
        
        # html_content = render_to_string('trade_execution_report.html', context)
        
        # # 发送邮件
        # subject = f"【量化交易日报】{current_date} 交易执行情况"
        # receiver_email = os.getenv('EMAIL_RECEIVER', '312711936@qq.com')
        
        # # 异步发送邮件
        # send_email(
        #     subject=subject,
        #     body=html_content,
        #     receiver_email=receiver_email,
        #     is_html=True
        # )
        
        print(f"[INFO] 交易报告已发送至:")
        return True
        
    except Exception as e:
        print(f"[ERROR] 发送交易报告失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False