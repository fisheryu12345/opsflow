"""
【绩效计算模块 - 三层架构版】

💡 核心作用：
1. Layer 1: 从 TqSDK api.get_account() 提取实时账户数据 → DailyEquitySnapshot
2. Layer 2: 基于历史快照计算滚动窗口指标 → RollingPerformanceMetrics
3. Layer 3: 聚合全局指标生成 Dashboard 数据 → AccountPerformanceSummary

📊 数据流向：
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
from django.db.models import Avg, Count, Sum, Q, Max, Min
from django.utils import timezone

from stock.models import (
    TradingAccount, 
    DailyEquitySnapshot, 
    RollingPerformanceMetrics, 
    AccountPerformanceSummary,
    PositionState,
    ClosedPositionRecord
)
from stock.utils.log_util import log_trade, log_error


# ==================== Layer 1: 日权益快照 ====================

def save_daily_snapshot(
    account: TradingAccount,
    api_account_data: Dict[str, Any],
    trade_date: Optional[date] = None
) -> DailyEquitySnapshot:
    """
    【Layer 1: 保存日权益快照】
    
    💡 作用：将 TqSDK 原始数据保存到 DailyEquitySnapshot
    
    📥 输入：
    - account: TradingAccount 实例
    - api_account_data: api.get_account() 返回的字典
    - trade_date: 交易日期（默认为今天）
    
    📤 输出：
    - DailyEquitySnapshot 实例
    
    📊 数据来源映射：
    api.get_account()['balance']      → balance
    api.get_account()['available']    → available
    api.get_account()['float_profit'] → float_profit
    api.get_account()['margin']       → margin
    api.get_account()['risk_ratio']   → risk_ratio
    api.get_account()['commission']   → commission
    """
    if trade_date is None:
        trade_date = timezone.now().date()
    
    try:
        # Step 1: 提取 TqSDK 原始数据并转换为 Decimal
        balance = Decimal(str(api_account_data.get('balance', 0))).quantize(Decimal('0.01'))
        available = Decimal(str(api_account_data.get('available', 0))).quantize(Decimal('0.01'))
        float_profit = Decimal(str(api_account_data.get('float_profit', 0))).quantize(Decimal('0.01'))
        margin = Decimal(str(api_account_data.get('margin', 0))).quantize(Decimal('0.01'))
        risk_ratio = Decimal(str(api_account_data.get('risk_ratio', 0))).quantize(Decimal('0.0001'))
        commission = Decimal(str(api_account_data.get('commission', 0))).quantize(Decimal('0.01'))
        
        # Step 2: 计算简单指标（需要昨日数据）
        prev_snapshot = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lt=trade_date
        ).order_by('-trade_date').first()
        
        if prev_snapshot and prev_snapshot.balance > 0:
            daily_pnl = balance - prev_snapshot.balance
            daily_return = (daily_pnl / prev_snapshot.balance * 100).quantize(Decimal('0.0001'))
        else:
            # 第一天或找不到昨日数据
            daily_pnl = Decimal('0')
            daily_return = Decimal('0')
        
        # Step 3: 创建或更新快照记录
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
                'closed_pnl': closed_pnl,  # 新增：保存平仓盈亏字段
            }
        )
                
        return snapshot
        
    except Exception as e:
        import traceback
        error_msg = f"保存日权益快照失败: {str(e)}"
        log_error(
            function_name='save_daily_snapshot',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )
        raise


# ==================== Layer 2: 滚动绩效指标 ====================

def calculate_rolling_metrics(
    account: TradingAccount,
    calc_date: Optional[date] = None,
    window_days: int = 20
) -> RollingPerformanceMetrics:
    """
    【Layer 2: 计算滚动窗口绩效指标】
    
    💡 作用：基于 N 日历史快照计算统计指标
    
    📥 参数：
    - account: TradingAccount 实例
    - calc_date: 计算截止日期（默认为今天）
    - window_days: 窗口天数（默认20日，可选60、120等）
    
    📤 输出：
    - RollingPerformanceMetrics 实例
    
    📊 计算指标：
    - sharpe_ratio: 夏普比率
    - sortino_ratio: 索提诺比率
    - volatility: 年化波动率
    - win_rate: 窗口期内胜率（%）
    - profit_loss_ratio: 窗口期内盈亏比
    - total_trades: 窗口期内交易次数
    """
    if calc_date is None:
        calc_date = timezone.now().date()
    
    try:
        # Step 1: 获取窗口期内的日收益率序列
        start_date = calc_date - timedelta(days=window_days)
        snapshots = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__gte=start_date,
            trade_date__lte=calc_date
        ).exclude(daily_return=0).order_by('trade_date').values_list('daily_return', flat=True)
        
        returns = list(snapshots)
        
        # Step 2: 判断数据质量
        if len(returns) < 5:
            data_quality = 'INSUFFICIENT'
            log_trade(
                function_name='calculate_rolling_metrics',
                log_message=f"[WARN] 数据不足 - 账户:{account.name}, 窗口:{window_days}日, 有效数据:{len(returns)}条",
                symbol="N/A",
                log_level='WARNING'
            )
        elif len(returns) < window_days * 0.8:
            data_quality = 'PARTIAL'
        else:
            data_quality = 'COMPLETE'
        
        # Step 3: 计算风险调整收益指标
        if len(returns) >= 5:
            returns_array = np.array([float(r) for r in returns])
            
            # 夏普比率
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = Decimal(str((mean_return / std_return) * np.sqrt(252))).quantize(Decimal('0.0001')) if std_return > 0 else None
            
            # 索提诺比率（只考虑下行风险）
            downside_returns = returns_array[returns_array < 0]
            if len(downside_returns) > 0:
                downside_std = np.std(downside_returns)
                sortino_ratio = Decimal(str((mean_return / downside_std) * np.sqrt(252))).quantize(Decimal('0.0001')) if downside_std > 0 else None
            else:
                sortino_ratio = Decimal('999.9999')  # 没有负收益，返回极大值
            
            # 年化波动率
            volatility = Decimal(str(std_return * np.sqrt(252))).quantize(Decimal('0.0001'))
        else:
            sharpe_ratio = None
            sortino_ratio = None
            volatility = None
        
        # Step 4: 交易统计指标（从成交记录表统计）
        start_date = calc_date - timedelta(days=window_days)
        window_trades = ClosedPositionRecord.objects.filter(
            account=account,
            executed_at__date__gte=start_date,
            executed_at__date__lte=calc_date
        )
        
        total_trades = window_trades.count()
        
        if total_trades > 0:
            # 计算胜率
            winning_trades = window_trades.filter(pnl__gt=0).count()
            win_rate = Decimal(str(winning_trades / total_trades * 100)).quantize(Decimal('0.01'))
            
            # 计算盈亏比
            total_profit = window_trades.filter(pnl__gt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0')
            total_loss = abs(window_trades.filter(pnl__lt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0'))
            
            if total_loss > 0:
                profit_loss_ratio = (total_profit / total_loss).quantize(Decimal('0.01'))
            else:
                # 无亏损时，若有盈利则设为极大值，否则为 0
                profit_loss_ratio = Decimal('999.99') if total_profit > 0 else Decimal('0')
        else:
            win_rate = None
            profit_loss_ratio = None
        
        # Step 5: 创建或更新滚动指标记录
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
        print(f"计算滚动绩效指标 - 账户:{account.name}, 窗口:{window_days}日, 夏普:{sharpe_ratio}, 索提诺:{sortino_ratio}, 波动率:{volatility}, 胜率:{win_rate}, 盈亏比:{profit_loss_ratio}, 交易数:{total_trades}, 数据质量:{data_quality}")
        log_trade(
            function_name='calculate_rolling_metrics',
            log_message=f"计算滚动绩效指标 - 账户:{account.name}, 窗口:{window_days}日, 夏普:{sharpe_ratio}, 索提诺:{sortino_ratio}, 波动率:{volatility}, 胜率:{win_rate}, 盈亏比:{profit_loss_ratio}, 交易数:{total_trades}, 数据质量:{data_quality}",
            symbol="N/A",
            log_level='INFO'
        )
        return metric
        
    except Exception as e:
        import traceback
        error_msg = f"计算滚动绩效指标失败: {str(e)}"
        log_error(
            function_name='calculate_rolling_metrics',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )
        raise


# ==================== Layer 3: 账户绩效总览 ====================

def update_account_summary(
    account: TradingAccount,
    snapshot_date: Optional[date] = None
) -> AccountPerformanceSummary:
    """
    【Layer 3: 更新账户绩效总览】
    
    💡 作用：聚合各层数据，生成 Dashboard 所需的全局指标
    
    📥 参数：
    - account: TradingAccount 实例
    - snapshot_date: 快照日期（默认为今天）
    
    📤 输出：
    - AccountPerformanceSummary 实例
    
    📊 数据来源：
    - TradingAccount.initial_balance → total_return
    - DailyEquitySnapshot (全量) → max_drawdown_all_time
    - PositionState (实时) → current_long_position
    - RollingPerformanceMetrics (最新) → latest_sharpe_20d
    """
    if snapshot_date is None:
        snapshot_date = timezone.now().date()
    
    try:
        # Step 1: 获取最新日权益快照
        latest_snapshot = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lte=snapshot_date
        ).order_by('-trade_date').first()
        
        if not latest_snapshot:
            raise ValueError(f"找不到账户 {account.name} 在 {snapshot_date} 之前的权益快照")
        
        current_equity = latest_snapshot.balance
        
        # Step 2: 计算全局收益指标
        if account.initial_balance > 0:
            total_return = ((current_equity - account.initial_balance) / account.initial_balance * 100).quantize(Decimal('0.0001'))
        else:
            total_return = Decimal('0')
        
        # 计算年化收益率
        first_snapshot = DailyEquitySnapshot.objects.filter(
            account=account
        ).order_by('trade_date').first()
        
        if first_snapshot:
            days_elapsed = (snapshot_date - first_snapshot.trade_date).days
            if days_elapsed > 0:
                # 使用 250 天作为年化因子（中国期货市场标准）
                annualized_return = ((1 + float(total_return) / 100) ** (250 / days_elapsed) - 1) * 100
                annualized_return = Decimal(str(annualized_return)).quantize(Decimal('0.0001'))
            else:
                annualized_return = None
        else:
            annualized_return = None
        
        # Step 3: 计算全局回撤指标
        all_snapshots = DailyEquitySnapshot.objects.filter(
            account=account,
            trade_date__lte=snapshot_date
        ).order_by('trade_date').values_list('balance', flat=True)
        
        equity_list = [Decimal(str(e)) for e in all_snapshots]
        
        if equity_list:
            # 最大回撤
            max_drawdown = Decimal('0')
            running_peak = equity_list[0]
            max_dd_duration = 0
            current_dd_duration = 0
            
            for equity in equity_list:
                if equity > running_peak:
                    running_peak = equity
                    current_dd_duration = 0
                
                if running_peak > 0:
                    drawdown = (running_peak - equity) / running_peak * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                        max_dd_duration = current_dd_duration
                    
                    if drawdown > 0:
                        current_dd_duration += 1
                    else:
                        current_dd_duration = 0
            
            # 当前回撤
            historical_peak = max(equity_list)
            if historical_peak > 0:
                current_drawdown = ((historical_peak - current_equity) / historical_peak * 100).quantize(Decimal('0.0001'))
            else:
                current_drawdown = Decimal('0')
        else:
            max_drawdown = Decimal('0')
            current_drawdown = Decimal('0')
            max_dd_duration = 0
        
        # 卡尔玛比率
        if max_drawdown > 0 and annualized_return is not None:
            calmar_ratio = (annualized_return / max_drawdown).quantize(Decimal('0.0001'))
        else:
            calmar_ratio = None
        
        # Step 4: 获取持仓统计（实时）
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
        
        # Step 5: 引用最新的滚动指标
        latest_metric_20d = RollingPerformanceMetrics.objects.filter(
            account=account,
            window_days=20
        ).order_by('-calc_date').first()
        
        latest_sharpe_20d = latest_metric_20d.sharpe_ratio if latest_metric_20d else None
        latest_volatility_20d = latest_metric_20d.volatility if latest_metric_20d else None
        latest_sortino_20d = latest_metric_20d.sortino_ratio if latest_metric_20d else None
        
        # Step 6: 从平仓记录统计交易指标
        closed_trades = ClosedPositionRecord.objects.filter(account=account)
        
        # 总交易次数
        total_trades_all_time = closed_trades.count()
        
        if total_trades_all_time > 0:
            # 整体胜率
            winning_trades = closed_trades.filter(pnl__gt=0).count()
            overall_win_rate = Decimal(str(winning_trades / total_trades_all_time * 100)).quantize(Decimal('0.01'))
            
            # 整体盈利因子 = 总盈利 / 总亏损（绝对值）
            total_profit = closed_trades.filter(pnl__gt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0')
            total_loss = abs(closed_trades.filter(pnl__lt=0).aggregate(total=Sum('pnl'))['total'] or Decimal('0'))
            
            if total_loss > 0:
                overall_profit_factor = (total_profit / total_loss).quantize(Decimal('0.01'))
            else:
                overall_profit_factor = Decimal('999.99') if total_profit > 0 else Decimal('0')
            
            # 最佳单笔盈利
            best_single_trade = closed_trades.aggregate(max_pnl=Max('pnl'))['max_pnl']
            
            # 最差单笔亏损
            worst_single_trade = closed_trades.aggregate(min_pnl=Min('pnl'))['min_pnl']
            
            # 平均持仓天数
            avg_holding_days_result = closed_trades.aggregate(avg_days=Avg('holding_days'))
            if avg_holding_days_result['avg_days']:
                avg_holding_days = Decimal(str(avg_holding_days_result['avg_days'])).quantize(Decimal('0.01'))
            else:
                avg_holding_days = None
            
            # 最大连续盈利/亏损次数
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
                    # 盈亏为0，重置计数
                    current_wins = 0
                    current_losses = 0
            
            # 计算交易频率（日均交易次数）
            first_trade = closed_trades.order_by('executed_at').first()
            if first_trade and total_trades_all_time > 0:
                trading_days = (snapshot_date - first_trade.executed_at.date()).days
                if trading_days > 0:
                    trading_frequency = Decimal(str(total_trades_all_time / trading_days)).quantize(Decimal('0.01'))
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
        
        # Step 6.5: 计算累计平仓盈亏和手续费
        closed_profit = closed_trades.aggregate(total_pnl=Sum('pnl'))['total_pnl'] or Decimal('0')
        
        total_commission = DailyEquitySnapshot.objects.filter(
            account=account
        ).aggregate(total_commission=Sum('commission'))['total_commission'] or Decimal('0')
        
        # Step 7: 创建或更新账户总览
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
        
        # 同步更新 TradingAccount 的当前权益
        account.current_equity = current_equity
        account.save(update_fields=['current_equity', 'updated_at'])
        
        action = "创建" if created else "更新"
        log_trade(
            function_name='update_account_summary',
            log_message=f"[SUCCESS] {action}账户总览 - 累计收益:{total_return}%, 最大回撤:{max_drawdown}%, 夏普:{latest_sharpe_20d}",
            symbol="N/A",
            log_level='INFO'
        )
        
        return summary
        
    except Exception as e:
        import traceback
        error_msg = f"更新账户绩效总览失败: {str(e)}"
        log_error(
            function_name='update_account_summary',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )
        raise


# ==================== 统一入口函数 ====================

def update_all_performance_metrics(
    account: TradingAccount,
    api_account_data: Dict[str, Any],
    trade_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    【统一入口：按顺序更新三层绩效数据】
    
    💡 完整流程：
    1. Layer 1: 保存日权益快照
    2. Layer 2: 计算多个窗口的滚动指标（20/60/120日）
    3. Layer 3: 更新账户总览
    
    📥 参数：
    - account: TradingAccount 实例
    - api_account_data: api.get_account() 返回的字典
    - trade_date: 交易日期（默认为今天）
    
    📤 返回：
    {
        'snapshot': DailyEquitySnapshot 实例,
        'rolling_metrics': {20: ..., 60: ..., 120: ...},
        'summary': AccountPerformanceSummary 实例
    }
    """
    if trade_date is None:
        trade_date = timezone.now().date()
    
    try:
        log_trade(
            function_name='update_all_performance_metrics',
            log_message=f"[INFO] 开始更新三层绩效数据 - 账户:{account.name}, 日期:{trade_date}",
            symbol="N/A",
            log_level='INFO'
        )
        
        # Layer 1: 保存日权益快照
        snapshot = save_daily_snapshot(account, api_account_data, trade_date)
        
        # Layer 2: 计算多个窗口的滚动指标
        rolling_metrics = {}
        for window in [20, 60, 120, 250]:  # 支持多个窗口计算
            metric = calculate_rolling_metrics(account, trade_date, window_days=window)
            rolling_metrics[window] = metric
        
        # Layer 3: 更新账户总览
        summary = update_account_summary(account, trade_date)
        
        log_trade(
            function_name='update_all_performance_metrics',
            log_message=f"[SUCCESS] 三层绩效数据更新完成 - 权益:{snapshot.balance}, 20日夏普:{rolling_metrics[20].sharpe_ratio}",
        )
        
        return {
            'snapshot': snapshot,
            'rolling_metrics': rolling_metrics,
            'summary': summary,
        }
        
    except Exception as e:
        import traceback
        error_msg = f"更新三层绩效数据失败: {str(e)}"
        log_error(
            function_name='update_all_performance_metrics',
            error_message=f"{error_msg}\n{traceback.format_exc()}",
        )
        raise


# ==================== Dashboard 数据接口 ====================

def get_dashboard_metrics(account: TradingAccount) -> Dict[str, Any]:
    """
    【获取前端 Dashboard 所需的全部指标】
    
    💡 对应 index.vue 中的所有卡片数据
    
    📥 参数：
    - account: TradingAccount 实例
    
    📤 返回格式（与 index.vue metricsData 结构完全对应）：
    {
        'currentEquity': 997978.14,
        'cumulativeReturn': 12.34,
        'annualizedReturn': 15.67,
        'maxDrawdown': 5.67,
        'sharpeRatio': 1.23,
        ...
    }
    """
    try:
        # 获取最新的账户总览
        summary = AccountPerformanceSummary.objects.filter(
            account=account
        ).order_by('-snapshot_date').first()
        
        if not summary:
            # 如果没有总览记录，返回默认值
            log_trade(
                function_name='get_dashboard_metrics',
                log_message=f"[WARN] 未找到账户 {account.name} 的绩效总览，返回默认值",
                symbol="N/A",
                log_level='WARNING'
  
            )
            return _get_default_dashboard_metrics(account)
        
        # 获取最新日权益快照（用于浮动盈亏和风险度）
        latest_snapshot = DailyEquitySnapshot.objects.filter(
            account=account
        ).order_by('-trade_date').first()
        
        # 构建返回数据（完全匹配 index.vue 的结构）
        metrics = {
            # === 资金与收益类 ===
            'currentEquity': float(summary.account.current_equity),
            'cumulativeReturn': float(summary.total_return),
            'annualizedReturn': float(summary.annualized_return) if summary.annualized_return else 0,
            'profitFactor': float(summary.overall_profit_factor) if summary.overall_profit_factor else 0,
            
            # === 风险与回撤类 ===
            'maxDrawdown': float(summary.max_drawdown_all_time),
            'riskLevel': float(latest_snapshot.risk_ratio * 100) if latest_snapshot and latest_snapshot.risk_ratio else 0,
            'volatility': float(summary.latest_volatility_20d) if summary.latest_volatility_20d else 0,
            
            # === 策略质量指标 ===
            'sharpeRatio': float(summary.latest_sharpe_20d) if summary.latest_sharpe_20d else 0,
            'calmarRatio': float(summary.calmar_ratio) if summary.calmar_ratio else 0,
            'sortinoRatio': float(summary.latest_sortino_20d) if summary.latest_sortino_20d else 0,
            'winRate': float(summary.overall_win_rate) if summary.overall_win_rate else 0,
            
            # === 持仓与交易行为 ===
            'totalPosition': summary.current_long_position + summary.current_short_position,
            'longPosition': summary.current_long_position,
            'shortPosition': summary.current_short_position,
            'avgHoldingTime': float(summary.avg_holding_days) if summary.avg_holding_days else 0,
            'tradingFrequency': {'daily': float(summary.trading_frequency) if summary.trading_frequency else 0},
            
            # === 盈亏详情 ===
            'closedProfit': float(summary.closed_profit_total),
            'unrealizedProfit': float(latest_snapshot.float_profit) if latest_snapshot else 0,
            'totalCommission': float(summary.commission_total),
            
            # === 连续表现 ===
            'consecutiveLosses': summary.consecutive_losses,
            'consecutiveWins': summary.consecutive_wins,
            'maxProfit': float(summary.best_single_trade) if summary.best_single_trade else 0,
            'maxLoss': float(summary.worst_single_trade) if summary.worst_single_trade else 0,
        }
        
        return metrics
        
    except Exception as e:
        import traceback
        log_error(
            function_name='get_dashboard_metrics',
            error_message=f"获取 Dashboard 指标失败: {str(e)}\n{traceback.format_exc()}",
        )
        raise


def _get_default_dashboard_metrics(account: TradingAccount) -> Dict[str, Any]:
    """
    【获取默认的 Dashboard 指标（当没有历史数据时）】
    """
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
