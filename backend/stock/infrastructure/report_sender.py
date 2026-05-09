"""
Report generation and email sending — open report and daily signal report.
"""
import traceback
from datetime import date, timedelta
from django.template.loader import render_to_string
from django.utils import timezone
from stock.tasks.send_mail import send_email_task as send_email
from stock.models import TradingAccount, DailyStrategySignal


def send_open_report(account=None, current_date=None):
    """
    发送开盘信号执行报告（基于最近24小时更新的DailyStrategySignal记录）
    """
    try:
        if account is None:
            account = TradingAccount.objects.filter(is_active=True).first()
            if not account:
                print("[WARN] 未找到活跃账户，跳过邮件发送")
                return False

        if current_date is None:
            current_date = date.today()

        now = timezone.now()
        one_day_ago = now - timedelta(hours=24)

        recent_signals = DailyStrategySignal.objects.filter(
            account=account,
            updated_at__gte=one_day_ago
        ).order_by('-updated_at', 'symbol')

        summary = {
            'total_signals': recent_signals.count(),
            'success_count': recent_signals.filter(executed_status='SUCCESS').count(),
            'failed_count': recent_signals.filter(executed_status='FAILED').count(),
            'pending_count': recent_signals.filter(executed_status='PENDING').count(),
            'cancelled_count': recent_signals.filter(executed_status='CANCELLED').count(),
        }

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

        time_range_str = f"{one_day_ago.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}"

        html_content = render_to_string('signal_execution_report.html', {
            'account_name': account.name,
            'time_range': time_range_str,
            'signals': signals_data,
            'summary': summary,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        })

        receiver_email = account.user.email if account.user.email else '312711936@qq.com'
        send_email(
            subject=f'[量化策略] 今日信号执行报告 - {now.strftime("%Y-%m-%d %H:%M")}',
            body=html_content,
            receiver_email=receiver_email,
            is_html=True
        )

        if recent_signals:
            print(f"[SUCCESS] 今日信号报告已发送: {summary['total_signals']}个信号 "
                  f"(成功:{summary['success_count']}, 失败:{summary['failed_count']}, "
                  f"待处理:{summary['pending_count']}, 取消:{summary['cancelled_count']})")
        else:
            print("[INFO] 今日信号报告已发送: 今日开盘没有需要执行的信号")
        return True

    except Exception as e:
        print(f"[ERROR] 发送今日信号报告失败: {str(e)}")
        traceback.print_exc()
        return False


def generate_daily_signal_report(account=None):
    """
    生成每日策略信号报告并发送邮件。
    """
    try:
        today = date.today()

        if account is None:
            account = TradingAccount.objects.filter(is_active=True).first()
            if not account:
                print("[WARN] 未找到活跃账户，跳过邮件发送")
                return False

        signals = DailyStrategySignal.objects.filter(
            account=account,
            trade_date=today
        ).order_by('-trade_date', 'symbol')

        # 先解析收件人邮箱，两个分支（无信号/有信号）共用
        receiver_email = account.user.email if account.user.email else '312711936@qq.com'

        if not signals:
            print(f"[INFO] {account.name} 今日无策略信号，发送通知邮件")

            html_content = render_to_string('daily_strategy_signal_report.html', {
                'report_date': today,
                'account_name': account.name,
                'signals': [],
                'summary': {
                    'total_signals': 0,
                    'open_count': 0,
                    'add_on_count': 0,
                    'stop_loss_count': 0,
                    'rollover_count': 0,
                },
                'current_time': timezone.now(),
                'no_signal_message': '今日没有产生任何策略信号',
            })

            send_email(
                subject=f'[量化策略] {account.name} 每日信号报告 - {today.strftime("%Y-%m-%d")}',
                body=html_content,
                receiver_email=receiver_email,
                is_html=True
            )

            print(f"[SUCCESS] {account.name} 无信号通知邮件已发送")
            return True

        summary = {
            'total_signals': signals.count(),
            'open_count': signals.filter(trade_type__in=['ENTRY']).count(),
            'stop_loss_count': signals.filter(trade_type='STOP_LOSS').count(),
            'rollover_count': signals.filter(trade_type='ROLLOVER').count(),
            'add_on_count': signals.filter(trade_type='ADD_ON').count(),
        }

        signals_data = []
        for signal in signals:
            signals_data.append({
                'symbol': signal.symbol,
                'trade_date': signal.trade_date,
                'trend_factor': float(signal.trend_factor) if signal.trend_factor else None,
                'trend_label': signal.trend_label,
                'donchian_upper': float(signal.donchian_upper) if signal.donchian_upper else None,
                'donchian_lower': float(signal.donchian_lower) if signal.donchian_lower else None,
                'signal_direction': signal.signal_direction,
                'is_breakout': signal.is_breakout,
                'remark': signal.remark,
                'trade_type': signal.trade_type,
            })

        html_content = render_to_string('daily_strategy_signal_report.html', {
            'report_date': today,
            'account_name': account.name,
            'signals': signals_data,
            'summary': summary,
            'current_time': timezone.now(),
        })

        send_email(
            subject=f'[量化策略] {account.name} 每日信号报告 - {today.strftime("%Y-%m-%d")}',
            body=html_content,
            receiver_email=receiver_email,
            is_html=True
        )

        print(f"[SUCCESS] {account.name} 邮件发送任务已提交: {summary['total_signals']}个信号")
        return True

    except Exception as e:
        print(f"[ERROR] 生成邮件报告失败: {e}")
        traceback.print_exc()
        return False
