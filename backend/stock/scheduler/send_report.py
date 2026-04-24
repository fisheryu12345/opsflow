import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from django.db import transaction
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from stock.tasks.send_mail import send_email_task as send_email
from django.template.loader import render_to_string
from django.utils import timezone


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,DailyStrategySignal, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk
from stock.utils.calculate_indicators import calculate_indicators

def send_open_report(account=None, current_date=None):
    """
    发送开盘信号执行报告（基于最近一小时更新的DailyStrategySignal记录）
    
    功能说明：
    - 查询过去一小时内更新的策略信号记录
    - 统计信号的执行状态（成功/失败/待处理）
    - 生成HTML报告并发送邮件
    
    参数：
    account: TradingAccount实例，如果为None则使用第一个活跃账户
    current_date: 当前日期，如果为None则使用今天
    
    返回：
    bool: 是否发送成功
    """
    try:
        # 确定使用的账户
        if account is None:
            account = TradingAccount.objects.filter(is_active=True).first()
            if not account:
                print("[WARN] 未找到活跃账户，跳过邮件发送")
                return False
        
        # 确定当前时间
        if current_date is None:
            current_date = date.today()
        
        # 计算时间范围：过去一小时
        now = timezone.now()
        one_day_ago = now - timedelta(hours=24)
        
        # 查询过去一小时内更新的信号记录
        recent_signals = DailyStrategySignal.objects.filter(
            account=account,
            updated_at__gte=one_day_ago
        ).order_by('-updated_at', 'symbol')
        
        # 统计数据（即使没有记录也要发送邮件）
        summary = {
            'total_signals': recent_signals.count(),
            'success_count': recent_signals.filter(executed_status='SUCCESS').count(),
            'failed_count': recent_signals.filter(executed_status='FAILED').count(),
            'pending_count': recent_signals.filter(executed_status='PENDING').count(),
            'cancelled_count': recent_signals.filter(executed_status='CANCELLED').count(),
        }
        
        # 转换信号数据为字典列表
        signals_data = []
        for signal in recent_signals:
            signals_data.append({
                'symbol': signal.symbol,
                'trade_type': signal.trade_type,
                'signal_direction': signal.signal_direction,
                'executed_status': signal.executed_status or 'PENDING',
                'contract_target_number': signal.contract_target_number,
                'remark': signal.remark,
                'updated_at': signal.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        # 格式化时间范围字符串
        time_range_str = f"{one_day_ago.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}"
        
        # 渲染HTML模板
        context = {
            'account_name': account.name,
            'time_range': time_range_str,
            'signals': signals_data,
            'summary': summary,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        html_content = render_to_string('signal_execution_report.html', context)
        
        # 构建邮件主题
        subject = f'[量化策略] 今日信号执行报告 - {now.strftime("%Y-%m-%d %H:%M")}'
        
        # 异步发送邮件（即使没有信号也发送通知）
        send_email(
            subject=subject,
            body=html_content,
            receiver_email='312711936@qq.com',
            is_html=True
        )
        
        if recent_signals:
            print(f"[SUCCESS] 今日信号报告已发送: {summary['total_signals']}个信号 (成功:{summary['success_count']}, 失败:{summary['failed_count']}, 待处理:{summary['pending_count']}, 取消:{summary['cancelled_count']})")
        else:
            print(f"[INFO] 今日信号报告已发送: 今日开盘没有需要执行的信号")
        return True
        
    except Exception as e:
        print(f"[ERROR] 发送今日信号报告失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False