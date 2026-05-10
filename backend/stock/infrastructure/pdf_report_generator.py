"""
绩效报告 PDF 生成器

根据三层绩效数据（DailyEquitySnapshot、RollingPerformanceMetrics、AccountPerformanceSummary）
生成 HTML 报告并转换为 PDF，供邮件附件发送。

依赖: weasyprint (pip install weasyprint)
如未安装 weasyprint，则回退为仅返回 HTML 字符串。
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from django.template.loader import render_to_string
from django.db.models import Q

from stock.models import (
    TradingAccount,
    DailyEquitySnapshot,
    RollingPerformanceMetrics,
    AccountPerformanceSummary,
    ClosedPositionRecord,
)

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    logger.warning('weasyprint 未安装，PDF 生成将降级为 HTML 格式。安装: pip install weasyprint')


def _get_account_email(account):
    """获取账户关联的邮箱地址"""
    try:
        email = account.user.email if account.user and account.user.email else None
    except Exception:
        email = None
    return email or '312711936@qq.com'


def _query_snapshots(account_id, start_date, end_date):
    """查询指定日期范围的日权益快照"""
    return DailyEquitySnapshot.objects.filter(
        account_id=account_id,
        trade_date__gte=start_date,
        trade_date__lte=end_date,
    ).order_by('trade_date')


def _query_closed_positions(account_id, start_date, end_date):
    """查询指定日期范围的平仓记录"""
    return ClosedPositionRecord.objects.filter(
        account_id=account_id,
        trade_date__gte=start_date,
        trade_date__lte=end_date,
    ).order_by('trade_date')


def _query_rolling_metrics(account_id, end_date, window_days=120):
    """查询截至日期的指定窗口滚动指标"""
    return RollingPerformanceMetrics.objects.filter(
        account_id=account_id,
        calc_date__lte=end_date,
        window_days=window_days,
    ).order_by('-calc_date').first()


def _get_summary(account_id):
    """获取账户绩效总览"""
    try:
        return AccountPerformanceSummary.objects.get(account_id=account_id)
    except AccountPerformanceSummary.DoesNotExist:
        return None


def _calc_monthly_returns(snapshots):
    """从日权益快照计算月度收益率"""
    monthly = defaultdict(list)
    for snap in snapshots:
        month_key = snap.trade_date.strftime('%Y-%m')
        monthly[month_key].append(float(snap.daily_return or 0))

    result = []
    for month_key, returns in sorted(monthly.items()):
        total_return = sum(returns)
        # 月度收益率 = 当月日收益率的累乘
        compound = 1.0
        for r in returns:
            compound *= (1 + r / 100)
        monthly_return = (compound - 1) * 100
        result.append({
            'month': month_key,
            'days': len(returns),
            'monthly_return': round(monthly_return, 2),
            'positive_days': sum(1 for r in returns if r > 0),
            'negative_days': sum(1 for r in returns if r < 0),
        })
    return result


def _calc_symbol_pnl(positions):
    """从平仓记录计算品种盈亏"""
    symbol_stats = defaultdict(lambda: {'trades': 0, 'pnl': Decimal('0'), 'wins': 0, 'losses': 0})
    for pos in positions:
        stats = symbol_stats[pos.product_code or pos.symbol]
        stats['trades'] += 1
        stats['pnl'] += pos.pnl
        if pos.pnl > 0:
            stats['wins'] += 1
        elif pos.pnl < 0:
            stats['losses'] += 1

    result = []
    for code, stats in sorted(symbol_stats.items()):
        win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        result.append({
            'symbol': code,
            'trades': stats['trades'],
            'pnl': float(stats['pnl']),
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': round(win_rate, 1),
        })
    return sorted(result, key=lambda x: x['pnl'], reverse=True)


def _calc_drawdown(snapshots):
    """从权益序列计算回撤"""
    peak = Decimal('0')
    max_drawdown = Decimal('0')
    max_drawdown_pct = Decimal('0')
    current_drawdown = Decimal('0')

    for snap in snapshots:
        equity = snap.balance
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak * 100
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd
                max_drawdown = peak - equity

    if snapshots:
        last_equity = snapshots.last().balance
        if peak > 0:
            current_drawdown = (peak - last_equity) / peak * 100 if last_equity < peak else Decimal('0')

    return {
        'max_drawdown': round(float(max_drawdown), 2),
        'max_drawdown_pct': round(float(max_drawdown_pct), 2),
        'current_drawdown_pct': round(float(current_drawdown), 2),
    }


def generate_report_pdf(account_id, report_type, year, month=None, quarter=None):
    """
    生成绩效报告 PDF

    Args:
        account_id: TradingAccount ID
        report_type: 'monthly', 'quarterly', 'annual'
        year: 年份
        month: 月份（月度报告）
        quarter: 季度（季度报告，1-4）

    Returns:
        bytes: PDF 字节数据（weasyprint 可用时），否则返回 HTML 字节数据
    """
    try:
        account = TradingAccount.objects.get(id=account_id)
    except TradingAccount.DoesNotExist:
        logger.error('账户不存在: id=%s', account_id)
        return None

    # 计算日期范围
    if report_type == 'monthly':
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        period_label = f'{year}年{month}月'
    elif report_type == 'quarterly':
        start_date = date(year, quarter * 3 - 2, 1)
        if quarter == 4:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, quarter * 3 + 1, 1) - timedelta(days=1)
        period_label = f'{year}年 第{quarter}季度'
    else:  # annual
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        period_label = f'{year}年度'

    # 查询数据
    snapshots = _query_snapshots(account_id, start_date, end_date)
    closed_positions = _query_closed_positions(account_id, start_date, end_date)
    summary = _get_summary(account_id)
    rolling_120 = _query_rolling_metrics(account_id, end_date, 120)

    # 计算指标
    monthly_returns = _calc_monthly_returns(snapshots)
    symbol_pnl = _calc_symbol_pnl(closed_positions)
    drawdown_info = _calc_drawdown(snapshots)

    # 计算汇总统计
    total_trades = len(closed_positions)
    total_pnl = sum(float(p.pnl) for p in closed_positions)
    wins = sum(1 for p in closed_positions if p.pnl > 0)
    losses = sum(1 for p in closed_positions if p.pnl < 0)
    win_rate = round(wins / total_trades * 100, 1) if total_trades > 0 else 0

    # 计算期初期末权益
    start_equity = float(snapshots.first().balance) if snapshots else 0
    end_equity = float(snapshots.last().balance) if snapshots else 0

    context = {
        'account_name': account.name,
        'period_label': period_label,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': date.today().isoformat(),

        # 汇总
        'total_trades': total_trades,
        'total_pnl': round(total_pnl, 2),
        'win_rate': win_rate,
        'wins': wins,
        'losses': losses,
        'start_equity': round(start_equity, 2),
        'end_equity': round(end_equity, 2),
        'equity_change': round(end_equity - start_equity, 2),
        'equity_change_pct': round((end_equity - start_equity) / start_equity * 100, 2) if start_equity else 0,
        'trading_days': len(snapshots),

        # 详细数据
        'monthly_returns': monthly_returns,
        'symbol_pnl': symbol_pnl,
        'drawdown': drawdown_info,
        'report_type': report_type,

        # 三层绩效
        'summary': summary,
        'rolling_120': rolling_120,
    }

    # 渲染 HTML
    html_str = render_to_string('performance_report.html', context)

    # 尝试生成 PDF
    if HAS_WEASYPRINT:
        try:
            pdf_bytes = HTML(string=html_str).write_pdf()
            logger.info('PDF 报告生成成功: %s - %s', period_label, account.name)
            return pdf_bytes
        except Exception as e:
            logger.error('PDF 生成失败，降级为 HTML: %s', str(e))

    # 降级：返回 HTML
    logger.info('HTML 报告生成成功: %s - %s', period_label, account.name)
    return html_str.encode('utf-8')
