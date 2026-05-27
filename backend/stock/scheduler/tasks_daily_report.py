"""
Daily consolidated trading report — sent at 15:40 after market close.

Covers all 4 trading accounts (Turtle/V2/V3/HVOB) with:
  - Today's trade signals and explanations (from DailyStrategySignal.remark)
  - Current open positions
  - HVOB closed P&L detail
  - Cross-account equity comparison
"""
import json
import traceback
from datetime import date
from django.template.loader import render_to_string
from django.utils import timezone
from django_redis import get_redis_connection
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.tasks.send_mail import send_email_task
from stock.models import (
    TradingAccount, DailyStrategySignal, PositionState,
    ClosedPositionRecord, DailyEquitySnapshot, AccountPerformanceSummary,
    ErrorLog,
)
from stock.utils.log_util import log_trade, log_error

FSM = 'job_daily_consolidated_report'

# The 4 production account IDs (skip ID 4 which is admin/test)
REPORT_ACCOUNT_IDS = [1, 5, 6, 10]

STRATEGY_LABELS = {
    'V2': '海龟增强V2',
    'V3': '海龟增强V3',
    'TURTLE': '原版海龟',
    'HVOB': 'HVOB-MBI',
}


def get_strategy_label(account):
    """Map account's StrategyConfig.strategy_type to a Chinese label."""
    try:
        st = account.strategyconfig.strategy_type
        return STRATEGY_LABELS.get(st, st)
    except Exception:
        return '未知策略'


def query_turtle_signals(account, today):
    """Today's signals for Turtle/V2/V3 accounts (excludes HVOB signals)."""
    signals = DailyStrategySignal.objects.filter(
        account=account, trade_date=today
    ).exclude(trend_label='HVOB').order_by('symbol', 'trade_type')
    return [
        {
            'trade_type': s.trade_type,
            'symbol': s.symbol,
            'signal_direction': s.signal_direction,
            'contract_target_number': s.contract_target_number,
            'executed_status': s.executed_status or 'PENDING',
            'remark': s.remark or '',
            'is_breakout': s.is_breakout,
            'trend_label': s.trend_label or '',
            'trend_factor': float(s.trend_factor) if s.trend_factor else None,
        }
        for s in signals
    ]


def query_hvob_signals(account, today):
    """Today's HVOB signals — parse JSON remark for entry/exit detail."""
    signals = DailyStrategySignal.objects.filter(
        account=account, trade_date=today, trend_label='HVOB'
    ).order_by('symbol', 'trade_type')

    result = []
    for s in signals:
        remark_data = {}
        if s.remark:
            try:
                remark_data = json.loads(s.remark)
            except (json.JSONDecodeError, TypeError):
                remark_data = {'raw': s.remark}

        result.append({
            'trade_type': s.trade_type,
            'symbol': s.symbol,
            'signal_direction': s.signal_direction,
            'contract_target_number': s.contract_target_number,
            'executed_status': s.executed_status or 'PENDING',
            'entry_price': remark_data.get('entry_price'),
            'exit_price': remark_data.get('exit_price'),
            'exit_reason': remark_data.get('exit_reason'),
            'stop_loss_price': remark_data.get('stop_loss_price'),
            'mbi': remark_data.get('mbi'),
            'remark': s.remark or '',
        })
    return result


def query_current_positions(account):
    """Current open positions."""
    positions = PositionState.objects.filter(
        account=account, units__gt=0
    ).exclude(direction=0).order_by('symbol')
    return [
        {
            'symbol': p.symbol,
            'direction': p.direction,
            'units': p.units,
            'contract_total_position': p.contract_total_position,
            'cost_price': float(p.cost_price) if p.cost_price else None,
            'stop_loss_price': float(p.stop_loss_price) if p.stop_loss_price else None,
            'latest_close_price': float(p.latest_close_price) if p.latest_close_price else None,
            'open_date': p.open_date,
        }
        for p in positions
    ]


def query_hvob_closed_pnl(account, today):
    """Today's closed P&L detail for HVOB."""
    closed = ClosedPositionRecord.objects.filter(
        account=account, trade_date=today
    ).order_by('symbol')
    trades = [
        {
            'symbol': c.symbol,
            'direction': c.direction,
            'volume': c.volume,
            'exit_price': float(c.exit_price),
            'cost_price': float(c.cost_price),
            'pnl': float(c.pnl),
        }
        for c in closed
    ]
    return {
        'total_pnl': sum(t['pnl'] for t in trades),
        'trades': trades,
        'count': len(trades),
    }


def query_equity_snapshot(account, today):
    """Today's equity snapshot."""
    try:
        snap = DailyEquitySnapshot.objects.get(account=account, trade_date=today)
        return {
            'balance': float(snap.balance),
            'daily_pnl': float(snap.daily_pnl),
            'daily_return': float(snap.daily_return),
            'closed_pnl': float(snap.closed_pnl),
            'commission': float(snap.commission),
            'risk_ratio': float(snap.risk_ratio),
            'margin': float(snap.margin),
            'available': float(snap.available),
        }
    except DailyEquitySnapshot.DoesNotExist:
        return None


def query_performance_summary(account):
    """Latest AccountPerformanceSummary."""
    try:
        s = AccountPerformanceSummary.objects.get(account=account)
        return {
            'total_return': float(s.total_return),
            'max_drawdown': float(s.max_drawdown_all_time),
            'win_rate': float(s.overall_win_rate) if s.overall_win_rate else None,
            'profit_factor': float(s.overall_profit_factor) if s.overall_profit_factor else None,
            'total_trades': s.total_trades_all_time,
        }
    except AccountPerformanceSummary.DoesNotExist:
        return None


def query_error_log_summary(today):
    """Query today's ErrorLog entries grouped by function_name."""
    errors = ErrorLog.objects.filter(timestamp__date=today).order_by('-timestamp')
    total_count = errors.count()
    if total_count == 0:
        return {'total_count': 0, 'groups': []}

    from collections import Counter
    func_counts = Counter(errors.values_list('function_name', flat=True))
    # Get latest error per function group
    seen_funcs = set()
    groups = []
    for e in errors:
        if e.function_name in seen_funcs:
            continue
        seen_funcs.add(e.function_name)
        groups.append({
            'function_name': e.function_name,
            'count': func_counts[e.function_name],
            'account_name': e.account.name if e.account else '系统',
            'latest_message': (e.error_message[:200] + '…') if e.error_message and len(e.error_message) > 200 else (e.error_message or ''),
        })
    return {'total_count': total_count, 'groups': groups}


def _build_account_section(account, today):
    """Build the full data section for one account."""
    label = get_strategy_label(account)
    is_hvob = (label == 'HVOB-MBI')

    signals = query_hvob_signals(account, today) if is_hvob \
              else query_turtle_signals(account, today)

    signal_summary = {}
    for sig in signals:
        st = sig['trade_type']
        signal_summary[st] = signal_summary.get(st, 0) + 1
    signal_summary['total'] = len(signals)

    positions = query_current_positions(account)

    return {
        'account_id': account.id,
        'account_name': account.name,
        'strategy_label': label,
        'is_hvob': is_hvob,
        'signals': signals,
        'signal_summary': signal_summary,
        'positions': positions,
        'position_count': len(positions),
        'equity': query_equity_snapshot(account, today),
        'hvob_pnl': query_hvob_closed_pnl(account, today) if is_hvob else None,
        'perf': query_performance_summary(account),
    }


def job_daily_consolidated_report():
    """
    APScheduler entry point — generates and emails the daily consolidated report.

    Schedule: Mon-Fri 15:40 (after close calc at 15:32 + reconciliation at 15:35).
    """
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:daily_consolidated_report'):
            if skip_if_not_trade_day():
                log_trade(FSM, '非交易日，跳过日报', symbol='N/A', log_level='INFO')
                return

            today = date.today()
            accounts = TradingAccount.objects.filter(
                id__in=REPORT_ACCOUNT_IDS, is_active=True
            )

            account_sections = []
            summary_rows = []

            for account in accounts:
                try:
                    section = _build_account_section(account, today)
                    account_sections.append(section)

                    summary_rows.append({
                        'account_name': section['account_name'],
                        'strategy_label': section['strategy_label'],
                        'equity': section['equity'],
                        'perf': section['perf'],
                        'position_count': section['position_count'],
                        'signal_count': section['signal_summary']['total'],
                    })
                except Exception as e:
                    log_error(FSM, f'处理账户 {account.name} 失败: {e}')
                    traceback.print_exc()
                    continue

            html_content = render_to_string('daily_consolidated_report.html', {
                'report_date': today,
                'report_date_cn': today.strftime('%Y年%m月%d日'),
                'current_time': timezone.now(),
                'account_sections': account_sections,
                'summary_rows': summary_rows,
                'total_accounts': len(account_sections),
                'error_log': query_error_log_summary(today),
            })

            success = send_email_task(
                subject=f'[量化策略] 每日综合交易日报 - {today.strftime("%Y-%m-%d")}',
                body=html_content,
                receiver_email='312711936@qq.com',
                is_html=True,
            )

            if success:
                log_trade(FSM, f'综合日报发送成功: {today}', symbol='N/A', log_level='INFO')
            else:
                log_error(FSM, '综合日报发送失败')

    except LockAcquisitionError:
        log_trade(FSM, '任务正在其他实例执行，跳过', symbol='N/A', log_level='INFO')
    except Exception as e:
        log_error(FSM, f'综合日报生成失败: {e}')
        traceback.print_exc()
