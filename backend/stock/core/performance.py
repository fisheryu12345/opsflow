"""
【绩效计算模块 - 三层架构版】

数据流向：
TqSDK get_account()
    ↓ save_daily_snapshot()
DailyEquitySnapshot (日权益快照)
    ↓ calculate_rolling_metrics()
RollingPerformanceMetrics (滚动绩效指标)
    ↓ update_account_summary()
AccountPerformanceSummary (账户总览)
    ↓ get_dashboard_metrics()
前端 Dashboard 展示数据
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Dict, Any, Optional, List
import numpy as np
import traceback
from django.db.models import Avg, Count, Sum, Q, Max, Min
from django.utils import timezone

from stock.models import (
    TradingAccount,
    DailyEquitySnapshot,
    RollingPerformanceMetrics,
    AccountPerformanceSummary,
    SymbolDailyPnl,
    PositionState,
    ClosedPositionRecord,
    FullContractList,
)
from stock.utils.log_util import log_trade, log_error
from stock.scheduler.tasks_daily_commission import update_trading_account_total_commission


# ==================== Layer 1: 日权益快照 ====================

def save_daily_snapshot(
    account: TradingAccount,
    api_account_data: Dict[str, Any],
    trade_date: Optional[date] = None
) -> DailyEquitySnapshot:
    if trade_date is None:
        trade_date = timezone.now().date()

    try:
        balance = Decimal(str(api_account_data.get('balance', 0))).quantize(Decimal('0.01'))
        available = Decimal(str(api_account_data.get('available', 0))).quantize(Decimal('0.01'))
        float_profit = Decimal(str(api_account_data.get('float_profit', 0))).quantize(Decimal('0.01'))
        margin = Decimal(str(api_account_data.get('margin', 0))).quantize(Decimal('0.01'))
        risk_ratio = Decimal(str(api_account_data.get('risk_ratio', 0))).quantize(Decimal('0.0001'))
        commission = Decimal(str(api_account_data.get('commission', 0))).quantize(Decimal('0.01'))
        closed_pnl = Decimal(str(api_account_data.get('close_profit', 0))).quantize(Decimal('0.01'))

        # 【修复】通用 0 值保护：TqSDK 若返回 0 但 DB 已有正值，保留原值
        raw_values = {
            'balance': balance,
            'float_profit': float_profit,
            'margin': margin,
            'commission': commission,
            'closed_pnl': closed_pnl,
        }
        existing = DailyEquitySnapshot.objects.filter(
            account=account, trade_date=trade_date
        ).first()
        for field, val in raw_values.items():
            if val == 0 and existing and getattr(existing, field, 0) > 0:
                raw_values[field] = getattr(existing, field)
        balance = raw_values['balance']
        float_profit = raw_values['float_profit']
        margin = raw_values['margin']
        commission = raw_values['commission']
        closed_pnl = raw_values['closed_pnl']

        prev_snapshot = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lt=trade_date
        ).order_by('-trade_date').first()

        if prev_snapshot and prev_snapshot.balance > 0:
            daily_pnl = balance - prev_snapshot.balance
            daily_return = (daily_pnl / prev_snapshot.balance * 100).quantize(Decimal('0.0001'))
        else:
            daily_pnl = Decimal('0')
            daily_return = Decimal('0')

        snapshot, created = DailyEquitySnapshot.objects.update_or_create(
            account=account,
            trade_date=trade_date,
            defaults={
                'balance': balance,
                'available': available,
                'float_profit': float_profit,
                'margin': margin,
                'risk_ratio': risk_ratio,
                'commission': commission,
                'daily_pnl': daily_pnl,
                'daily_return': daily_return,
                'closed_pnl': closed_pnl,
            }
        )

        return snapshot

    except Exception as e:
        error_msg = f"保存日权益快照失败: {str(e)}"
        log_error(
            function_name='save_daily_snapshot',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        account=account)
        raise


# ==================== Layer 2: 滚动绩效指标 ====================

def calculate_rolling_metrics(
    account: TradingAccount,
    calc_date: Optional[date] = None,
    window_days: int = 20
) -> RollingPerformanceMetrics:
    if calc_date is None:
        calc_date = timezone.now().date()

    try:
        start_date = calc_date - timedelta(days=window_days)
        snapshots = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__gte=start_date,
            trade_date__lte=calc_date
        ).exclude(daily_return=0).order_by('trade_date').values_list('daily_return', flat=True)

        returns = list(snapshots)

        if len(returns) < 5:
            data_quality = 'INSUFFICIENT'
            log_trade(
                function_name='calculate_rolling_metrics',
                log_message=f"[WARN] 数据不足 - 账户:{account.name}, 窗口:{window_days}日, 有效数据:{len(returns)}条",
                symbol="N/A",
                log_level='WARNING'
            , account=account)
        elif len(returns) < window_days * 0.8:
            data_quality = 'PARTIAL'
        else:
            data_quality = 'COMPLETE'

        if len(returns) >= 5:
            returns_array = np.array([float(r) for r in returns])

            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = Decimal(str((mean_return / std_return) * np.sqrt(252))).quantize(Decimal('0.0001')) if std_return > 0 else None

            downside_returns = returns_array[returns_array < 0]
            if len(downside_returns) > 0:
                downside_std = np.std(downside_returns)
                sortino_ratio = Decimal(str((mean_return / downside_std) * np.sqrt(252))).quantize(Decimal('0.0001')) if downside_std > 0 else None
            else:
                sortino_ratio = None

            volatility = Decimal(str(std_return * np.sqrt(252))).quantize(Decimal('0.0001'))
        else:
            sharpe_ratio = None
            sortino_ratio = None
            volatility = None

        start_date = calc_date - timedelta(days=window_days)
        window_trades = ClosedPositionRecord.objects.filter(
            account=account,
            executed_at__date__gte=start_date,
            executed_at__date__lte=calc_date
        )

        total_trades = window_trades.count()

        if total_trades > 0:
            winning_trades = window_trades.filter(pnl__gt=0).count()
            win_rate = Decimal(str(winning_trades / total_trades * 100)).quantize(Decimal('0.01'))

            total_profit = window_trades.filter(pnl__gt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0')
            total_loss = abs(window_trades.filter(pnl__lt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0'))

            if total_loss > 0:
                profit_loss_ratio = (total_profit / total_loss).quantize(Decimal('0.01'))
            else:
                profit_loss_ratio = None
        else:
            win_rate = None
            profit_loss_ratio = None

        metric, created = RollingPerformanceMetrics.objects.update_or_create(
            account=account,
            calc_date=calc_date,
            window_days=window_days,
            defaults={
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'volatility': volatility,
                'win_rate': win_rate,
                'profit_loss_ratio': profit_loss_ratio,
                'total_trades': total_trades,
                'data_quality': data_quality,
            }
        )
        log_trade(
            function_name='calculate_rolling_metrics',
            log_message=f"计算滚动绩效指标 - 账户:{account.name}, 窗口:{window_days}日, 夏普:{sharpe_ratio}, 索提诺:{sortino_ratio}, 波动率:{volatility}, 胜率:{win_rate}, 盈亏比:{profit_loss_ratio}, 交易数:{total_trades}, 数据质量:{data_quality}",
            symbol="N/A",
            log_level='INFO', account=account)
        return metric

    except Exception as e:
        error_msg = f"计算滚动绩效指标失败: {str(e)}"
        log_error(
            function_name='calculate_rolling_metrics',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
            account=account)
        raise


# ==================== Layer 3: 账户绩效总览 ====================

def update_account_summary(
    account: TradingAccount,
    snapshot_date: Optional[date] = None
) -> AccountPerformanceSummary:
    if snapshot_date is None:
        snapshot_date = timezone.now().date()

    try:
        latest_snapshot = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lte=snapshot_date
        ).order_by('-trade_date').first()

        if not latest_snapshot:
            raise ValueError(f"找不到账户 {account.name} 在 {snapshot_date} 之前的权益快照")

        current_equity = latest_snapshot.balance

        if account.initial_balance > 0:
            total_return = ((current_equity - account.initial_balance) / account.initial_balance * 100).quantize(Decimal('0.0001'))
        else:
            total_return = Decimal('0')

        first_snapshot = DailyEquitySnapshot.objects.filter(
            account=account
        ).order_by('trade_date').first()

        if first_snapshot:
            days_elapsed = (snapshot_date - first_snapshot.trade_date).days
            if days_elapsed > 0:
                annualized_return = ((1 + float(total_return) / 100) ** (250 / days_elapsed) - 1) * 100
                annualized_return = Decimal(str(annualized_return)).quantize(Decimal('0.0001'))
            else:
                annualized_return = None
        else:
            annualized_return = None

        all_snapshots = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lte=snapshot_date
        ).order_by('trade_date').values_list('trade_date', 'balance')

        equity_list = [(d, Decimal(str(b))) for d, b in all_snapshots]

        if equity_list:
            max_drawdown = Decimal('0')
            running_peak = equity_list[0][1]
            max_dd_duration = 0
            peak_date = equity_list[0][0]
            drawdown_start_date = None

            for trade_date, equity in equity_list:
                if equity > running_peak:
                    # 到达新高：记录上一个回撤段的持续时间
                    if drawdown_start_date is not None:
                        recovery_days = (trade_date - drawdown_start_date).days
                        if recovery_days > max_dd_duration:
                            max_dd_duration = recovery_days
                        drawdown_start_date = None
                    running_peak = equity
                    peak_date = trade_date

                if running_peak > 0:
                    drawdown = (running_peak - equity) / running_peak * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                    if drawdown > 0:
                        # 处于回撤中
                        if drawdown_start_date is None:
                            drawdown_start_date = trade_date
                    else:
                        # 已恢复
                        if drawdown_start_date is not None:
                            recovery_days = (trade_date - drawdown_start_date).days
                            if recovery_days > max_dd_duration:
                                max_dd_duration = recovery_days
                            drawdown_start_date = None

            # 如果当前仍处于回撤中，计算到截止日期的持续时间
            if drawdown_start_date is not None:
                ongoing_days = (snapshot_date - drawdown_start_date).days
                if ongoing_days > max_dd_duration:
                    max_dd_duration = ongoing_days

            historical_peak = max(b for _, b in equity_list)
            if historical_peak > 0:
                current_drawdown = ((historical_peak - current_equity) / historical_peak * 100).quantize(Decimal('0.0001'))
            else:
                current_drawdown = Decimal('0')
        else:
            max_drawdown = Decimal('0')
            current_drawdown = Decimal('0')
            max_dd_duration = 0

        if max_drawdown > 0 and annualized_return is not None:
            calmar_ratio = (annualized_return / max_drawdown).quantize(Decimal('0.0001'))
        else:
            calmar_ratio = None

        long_positions = PositionState.objects.filter(
            account=account,
            direction=1,
            units__gt=0
        ).aggregate(total=Sum('contract_total_position'))['total'] or 0

        short_positions = PositionState.objects.filter(
            account=account,
            direction=-1,
            units__gt=0
        ).aggregate(total=Sum('contract_total_position'))['total'] or 0

        latest_metric_20d = RollingPerformanceMetrics.objects.filter(
            account=account,
            window_days=20
        ).order_by('-calc_date').first()

        latest_sharpe_20d = latest_metric_20d.sharpe_ratio if latest_metric_20d else None
        latest_volatility_20d = latest_metric_20d.volatility if latest_metric_20d else None
        latest_sortino_20d = latest_metric_20d.sortino_ratio if latest_metric_20d else None

        closed_trades = ClosedPositionRecord.objects.filter(account=account)
        total_trades_all_time = closed_trades.count()

        if total_trades_all_time > 0:
            winning_trades = closed_trades.filter(pnl__gt=0).count()
            overall_win_rate = Decimal(str(winning_trades / total_trades_all_time * 100)).quantize(Decimal('0.01'))

            total_profit = closed_trades.filter(pnl__gt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0')
            total_loss = abs(closed_trades.filter(pnl__lt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0'))

            if total_loss > 0:
                overall_profit_factor = (total_profit / total_loss).quantize(Decimal('0.01'))
            else:
                overall_profit_factor = Decimal('999.99') if total_profit > 0 else Decimal('0')

            best_single_trade = closed_trades.aggregate(max_pnl=Max('pnl'))['max_pnl']
            worst_single_trade = closed_trades.aggregate(min_pnl=Min('pnl'))['min_pnl']

            avg_holding_days_result = closed_trades.aggregate(avg_days=Avg('holding_days'))
            if avg_holding_days_result['avg_days']:
                avg_holding_days = Decimal(str(avg_holding_days_result['avg_days'])).quantize(Decimal('0.01'))
            else:
                avg_holding_days = None

            trades_ordered = closed_trades.order_by('executed_at').values_list('pnl', flat=True)
            consecutive_wins = 0
            consecutive_losses = 0
            current_wins = 0
            current_losses = 0

            for pnl in trades_ordered:
                if pnl > 0:
                    current_wins += 1
                    current_losses = 0
                    consecutive_wins = max(consecutive_wins, current_wins)
                elif pnl < 0:
                    current_losses += 1
                    current_wins = 0
                    consecutive_losses = max(consecutive_losses, current_losses)
                else:
                    current_wins = 0
                    current_losses = 0

            first_trade = closed_trades.order_by('executed_at').first()
            if first_trade and total_trades_all_time > 0:
                trading_days = (snapshot_date - first_trade.executed_at.date()).days
                if trading_days > 0:
                    trading_frequency = Decimal(str(total_trades_all_time / trading_days)).quantize(Decimal('0.001'))
                else:
                    trading_frequency = Decimal(str(total_trades_all_time))
            else:
                trading_frequency = Decimal('0')
        else:
            overall_win_rate = None
            overall_profit_factor = None
            best_single_trade = None
            worst_single_trade = None
            avg_holding_days = None
            consecutive_wins = 0
            consecutive_losses = 0
            trading_frequency = Decimal('0')

        closed_profit = closed_trades.aggregate(total_pnl=Sum('pnl'))['total_pnl'] or Decimal('0')

        # 直接从 TradingAccount 读取累计手续费（由 14:58 定时任务或收盘任务维护）
        total_commission = account.total_commission

        summary, created = AccountPerformanceSummary.objects.update_or_create(
            account=account,
            defaults={
                'snapshot_date': snapshot_date,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'max_drawdown_all_time': max_drawdown,
                'current_drawdown': current_drawdown,
                'max_drawdown_duration': max_dd_duration,
                'calmar_ratio': calmar_ratio,
                'total_trades_all_time': total_trades_all_time,
                'overall_win_rate': overall_win_rate,
                'overall_profit_factor': overall_profit_factor,
                'best_single_trade': best_single_trade,
                'worst_single_trade': worst_single_trade,
                'consecutive_wins': consecutive_wins,
                'consecutive_losses': consecutive_losses,
                'current_long_position': long_positions,
                'current_short_position': short_positions,
                'avg_holding_days': avg_holding_days,
                'latest_sharpe_20d': latest_sharpe_20d,
                'latest_volatility_20d': latest_volatility_20d,
                'latest_sortino_20d': latest_sortino_20d,
                'trading_frequency': trading_frequency,
                'closed_profit_total': closed_profit,
                'commission_total': total_commission,
            }
        )

        account.current_equity = current_equity
        account.total_commission = total_commission
        account.save(update_fields=['current_equity', 'total_commission', 'updated_at'])

        action = "创建" if created else "更新"
        log_trade(
            function_name='update_account_summary',
            log_message=f"[SUCCESS] {action}账户总览 - 累计收益:{total_return}%, 最大回撤:{max_drawdown}%, 夏普:{latest_sharpe_20d}",
            symbol="N/A",
            log_level='INFO'
        , account=account)

        return summary

    except Exception as e:
        error_msg = f"更新账户绩效总览失败: {str(e)}"
        log_error(
            function_name='update_account_summary',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        account=account)
        raise


# ==================== 品种日盈亏分解 ====================

def save_symbol_daily_pnl(
    account: TradingAccount,
    trade_date: date,
) -> List[SymbolDailyPnl]:
    """
    计算并保存当日每个持仓品种的盈亏分解。

    数据来源：
    - realized_pnl: 从 ClosedPositionRecord 按 symbol 聚合当日已平仓盈亏
    - float_pnl: 从 PositionState 按市值计价计算浮动盈亏
    - volume: 从 PositionState 获取收盘持仓手数

    合约乘数从 FullContractList 按 product_code 批量查询（缓存避免 N+1）。
    """
    log_trade(
        function_name='save_symbol_daily_pnl',
        log_message=f"[INFO] 开始计算品种日盈亏 - 账户:{account.name}, 日期:{trade_date}",
        symbol="N/A",
        log_level='INFO'
    , account=account)

    # 1. 预加载合约乘数（按 product_code 缓存）
    multipliers = {}
    for fc in FullContractList.objects.values('product_code', 'volume_multiple').distinct():
        multipliers[fc['product_code']] = fc['volume_multiple']

    # 2. 已实现盈亏：从 ClosedPositionRecord 按 symbol 聚合
    realized_data = {}
    closed_qs = ClosedPositionRecord.objects.filter(
        account=account,
        trade_date=trade_date,
    ).values('symbol', 'product_code').annotate(
        total_realized=Sum('pnl')
    )
    for item in closed_qs:
        realized_data[item['symbol']] = {
            'product_code': item['product_code'],
            'realized_pnl': item['total_realized'] or Decimal('0'),
        }

    # 3. 浮动盈亏 + 持仓手数：从 PositionState 计算
    float_data = {}
    positions = PositionState.objects.filter(
        account=account,
        units__gt=0,
    ).exclude(direction=0)

    for pos in positions:
        symbol = pos.symbol
        volume = pos.contract_total_position or 0
        fpnl = Decimal('0')

        if (pos.latest_close_price is not None
                and pos.cost_price is not None
                and pos.cost_price != 0
                and volume > 0):
            multiplier = multipliers.get(pos.product_code, 10)
            price_diff = pos.latest_close_price - pos.cost_price
            # float_pnl = direction × (latest_close - cost_price) × lots × multiplier
            fpnl = price_diff * volume * multiplier * pos.direction

        float_data[symbol] = {
            'product_code': pos.product_code or '',
            'float_pnl': fpnl,
            'volume': volume,
        }

    # 4. 合并写入：先处理有平仓记录的品种，再处理仅有持仓的品种
    created_records = []
    all_symbols = set(realized_data.keys()) | set(float_data.keys())

    for symbol in all_symbols:
        r = realized_data.get(symbol, {'realized_pnl': Decimal('0')})
        f = float_data.get(symbol, {'float_pnl': Decimal('0'), 'volume': 0})
        product_code = realized_data[symbol]['product_code'] if symbol in realized_data else float_data[symbol]['product_code']

        record, _ = SymbolDailyPnl.objects.update_or_create(
            account=account,
            trade_date=trade_date,
            symbol=symbol,
            defaults={
                'product_code': product_code,
                'realized_pnl': r['realized_pnl'],
                'float_pnl': f['float_pnl'],
                'volume': f['volume'],
            }
        )
        created_records.append(record)

    log_trade(
        function_name='save_symbol_daily_pnl',
        log_message=f"[SUCCESS] 品种日盈亏保存完成 - {len(created_records)}个品种",
        symbol="N/A",
        log_level='INFO'
    , account=account)

    return created_records


# ==================== 统一入口函数 ====================

def update_all_performance_metrics(
    account: TradingAccount,
    api_account_data: Dict[str, Any],
    trade_date: Optional[date] = None
) -> Dict[str, Any]:
    if trade_date is None:
        trade_date = timezone.now().date()

    try:
        log_trade(
            function_name='update_all_performance_metrics',
            log_message=f"[INFO] 开始更新三层绩效数据 - 账户:{account.name}, 日期:{trade_date}",
            symbol="N/A",
            log_level='INFO'
        , account=account)

        snapshot = save_daily_snapshot(account, api_account_data, trade_date)

        rolling_metrics = {}
        for window in [20, 60, 120, 250]:
            metric = calculate_rolling_metrics(account, trade_date, window_days=window)
            rolling_metrics[window] = metric

        # 同步累计手续费（供 update_account_summary 直接读取 account.total_commission）
        update_trading_account_total_commission(account)

        summary = update_account_summary(account, trade_date)

        # 品种日盈亏分解
        symbol_pnls = save_symbol_daily_pnl(account, trade_date)

        log_trade(
            function_name='update_all_performance_metrics',
            log_message=f"[SUCCESS] 三层绩效数据更新完成 - 权益:{snapshot.balance}, 20日夏普:{rolling_metrics[20].sharpe_ratio}",
        account=account)

        return {
            'snapshot': snapshot,
            'rolling_metrics': rolling_metrics,
            'summary': summary,
            'symbol_pnls': symbol_pnls,
        }

    except Exception as e:
        error_msg = f"更新三层绩效数据失败: {str(e)}"
        log_error(
            function_name='update_all_performance_metrics',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        account=account)
        raise


# ==================== Dashboard 数据接口 ====================

def get_dashboard_metrics(account: TradingAccount) -> Dict[str, Any]:
    try:
        summary = AccountPerformanceSummary.objects.filter(
            account=account
        ).order_by('-snapshot_date').first()

        if not summary:
            log_trade(
                function_name='get_dashboard_metrics',
                log_message=f"[WARN] 未找到账户 {account.name} 的绩效总览，返回默认值",
                symbol="N/A",
                log_level='WARNING'
            , account=account)
            return _get_default_dashboard_metrics(account)

        latest_snapshot = DailyEquitySnapshot.objects.filter(
            account=account
        ).order_by('-trade_date').first()

        metrics = {
            'currentEquity': float(summary.account.current_equity),
            'cumulativeReturn': float(summary.total_return),
            'annualizedReturn': float(summary.annualized_return) if summary.annualized_return else 0,
            'profitFactor': float(summary.overall_profit_factor) if summary.overall_profit_factor else 0,
            'maxDrawdown': float(summary.max_drawdown_all_time),
            'riskLevel': float(latest_snapshot.risk_ratio * 100) if latest_snapshot and latest_snapshot.risk_ratio else 0,
            'volatility': float(summary.latest_volatility_20d) if summary.latest_volatility_20d else 0,
            'sharpeRatio': float(summary.latest_sharpe_20d) if summary.latest_sharpe_20d else 0,
            'calmarRatio': float(summary.calmar_ratio) if summary.calmar_ratio else 0,
            'sortinoRatio': float(summary.latest_sortino_20d) if summary.latest_sortino_20d else 0,
            'winRate': float(summary.overall_win_rate) if summary.overall_win_rate else 0,
            'totalPosition': summary.current_long_position + summary.current_short_position,
            'longPosition': summary.current_long_position,
            'shortPosition': summary.current_short_position,
            'avgHoldingTime': float(summary.avg_holding_days) if summary.avg_holding_days else 0,
            'tradingFrequency': {'daily': float(summary.trading_frequency) if summary.trading_frequency else 0},
            'closedProfit': float(summary.closed_profit_total),
            'unrealizedProfit': float(latest_snapshot.float_profit) if latest_snapshot else 0,
            'totalCommission': float(summary.commission_total),
            'consecutiveLosses': summary.consecutive_losses,
            'consecutiveWins': summary.consecutive_wins,
            'maxProfit': float(summary.best_single_trade) if summary.best_single_trade else 0,
            'maxLoss': float(summary.worst_single_trade) if summary.worst_single_trade else 0,
        }

        return metrics

    except Exception as e:
        log_error(
            function_name='get_dashboard_metrics',
            error_message=f"获取 Dashboard 指标失败: {str(e)}\n{traceback.format_exc()}",
        account=account)
        raise


def _get_default_dashboard_metrics(account: TradingAccount) -> Dict[str, Any]:
    return {
        'currentEquity': float(account.current_equity),
        'cumulativeReturn': 0,
        'annualizedReturn': 0,
        'maxDrawdown': 0,
        'sharpeRatio': 0,
        'calmarRatio': 0,
        'sortinoRatio': 0,
        'winRate': 0,
        'profitFactor': 0,
        'volatility': 0,
        'riskLevel': 0,
        'totalPosition': 0,
        'longPosition': 0,
        'shortPosition': 0,
        'avgHoldingTime': 0,
        'tradingFrequency': {'daily': 0},
        'closedProfit': 0,
        'unrealizedProfit': 0,
        'totalCommission': 0,
        'consecutiveLosses': 0,
        'consecutiveWins': 0,
        'maxProfit': 0,
        'maxLoss': 0,
    }
