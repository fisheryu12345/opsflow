import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal

# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal

def calculate_daily_performance(account, trade_date):
    """
    核心计算函数：计算指定账户在指定日期的所有绩效指标
    并在 DailyPerformance 表中创建或更新记录。
    """
    print(f"🔍 开始计算 {account.name} 在 {trade_date} 的绩效...")

    # 1. 获取历史净值序列 (用于计算回撤和波动率)
    # 我们至少需要过去 60 天的数据来计算稳定的指标
    history_qs = DailyPerformance.objects.filter(
        account=account, 
        trade_date__lt=trade_date
    ).order_by('trade_date')

    # 将历史数据转为 DataFrame
    df = pd.DataFrame(list(history_qs.values('trade_date', 'daily_equity')))
    
    # 获取当日权益 (从 TradingAccount 表读取，这是交易脚本每天收盘后更新的)
    current_equity = account.current_equity
    
    # 将当日数据加入 DataFrame 以便计算
    # 注意：这里我们只是临时拼接用于计算，稍后保存
    df = df.append({'trade_date': trade_date, 'daily_equity': float(current_equity)}, ignore_index=True)
    
    if df.empty or len(df) < 2:
        print("⚠️ 数据不足，跳过计算")
        return

    df.set_index('trade_date', inplace=True)
    df['daily_equity'] = df['daily_equity'].astype(float)

    # --- 2. 计算基础收益指标 ---
    
    # 当日盈亏 (今日权益 - 昨日权益)
    # fillna(0) 处理第一天的数据
    daily_pnl = float(current_equity) - float(df['daily_equity'].shift(1).fillna(current_equity).iloc[-1]) if len(df) > 1 else 0
    
    # 当日收益率 (今日/昨日 - 1)
    df['daily_return'] = df['daily_equity'].pct_change()
    current_daily_return = df['daily_return'].iloc[-1] if not pd.isna(df['daily_return'].iloc[-1]) else 0

    # 累计收益率 (当前权益 / 初始资金 - 1)
    cumulative_return = (float(current_equity) / float(account.initial_balance) - 1) * 100

    # --- 3. 计算回撤指标 ---
    
    # 历史最高净值 (截止到今天)
    df['cum_max'] = df['daily_equity'].cummax()
    # 当前回撤 = (最高 - 当前) / 最高
    current_drawdown = (df['cum_max'].iloc[-1] - df['daily_equity'].iloc[-1]) / df['cum_max'].iloc[-1]
    
    # 历史最大回撤
    df['drawdown'] = (df['cum_max'] - df['daily_equity']) / df['cum_max']
    max_drawdown = df['drawdown'].max()

    # 计算最大回撤持续天数 (简单的逻辑：统计连续低于最高点的天数)
    # 这里为了简化，只计算当前的持续天数，历史最大值建议由更复杂的算法维护
    # 简单实现：找到上一次创新高的时间
    last_peak_idx = df['cum_max'].iloc[:-1][df['cum_max'].iloc[:-1] < df['cum_max'].iloc[-1]].last_valid_index()
    if last_peak_idx is None:
        max_drawdown_duration = (df.index[-1] - df.index[0]).days
    else:
        max_drawdown_duration = (df.index[-1] - last_peak_idx).days

    # --- 4. 计算风险调整指标 (需要足够的历史数据) ---
    
    sharpe_ratio = None
    sortino_ratio = None
    calmar_ratio = None
    volatility = None
    
    # 去除空值，只取过去的收益率序列（不含今天，或者含今天均可，通常用过去20日）
    returns = df['daily_return'].dropna()
    
    if len(returns) >= 20: # 至少20天数据才计算
        # 无风险利率 (假设年化3%)
        risk_free_rate = 0.03 / 252
        
        # 年化波动率
        vol_daily = returns.std()
        volatility = vol_daily * np.sqrt(252)
        
        # 年化收益率 (简单用最近20天的均值估算，或者用总年化)
        # 这里使用滚动窗口计算更准确，但为了展示，我们计算当前的年化收益
        # 简单算法：(1+日均收益)^252 - 1
        annual_return = (1 + returns.mean()) ** 252 - 1
        
        # 夏普比率
        if volatility > 0:
            sharpe_ratio = (annual_return - 0.03) / volatility
            
        # 索提诺比率 (只考虑下行波动)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            if downside_std > 0:
                sortino_ratio = (annual_return - 0.03) / downside_std

        # 卡尔玛比率 (年化收益 / 最大回撤)
        if max_drawdown > 0:
            calmar_ratio = annual_return / max_drawdown

    # --- 5. 计算交易统计 (基于 TradeExecution 表) ---
    # 统计过去 20 天的交易
    start_date = trade_date - timedelta(days=20)
    trades = TradeExecution.objects.filter(
        account=account, 
        trade_time__gte=start_date,
        trade_time__lte=trade_date
    )
    
    win_count = 0
    loss_count = 0
    total_profit = 0
    total_loss = 0
    
    # 注意：这里需要复杂的逻辑来配对开仓和平仓计算单笔盈亏
    # 为了简化，这里仅做占位符，实际需要根据 trade_type 配对计算
    # 或者简单地统计平仓单
    # 这里简化为：假设我们有一个方法能算出每笔平仓的盈亏
    # 实际代码中建议直接查询 TradeLog 或解析 TradeExecution 的配对
    
    # 简化版：假设我们只统计交易次数
    trade_count = trades.filter(trade_type__in=['CLOSE_SIGNAL', 'STOP_LOSS']).count()
    
    # 胜率与盈亏比计算比较复杂，通常需要遍历交易记录配对开平
    # 这里暂时留空或设为0，建议单独写一个函数处理配对
    
    # --- 6. 保存到数据库 ---
    
    with transaction.atomic():
        perf, created = DailyPerformance.objects.update_or_create(
            account=account,
            trade_date=trade_date,
            defaults={
                'daily_equity': current_equity,
                'daily_pnl': round(daily_pnl, 2),
                'daily_return': round(current_daily_return * 100, 4), # 存百分比
                'cumulative_return': round(cumulative_return, 4),
                'current_drawdown': round(current_drawdown * 100, 4),
                'max_drawdown': round(max_drawdown * 100, 4),
                'max_drawdown_duration': max_drawdown_duration,
                'sharpe_ratio': round(sharpe_ratio, 4) if sharpe_ratio else None,
                'sortino_ratio': round(sortino_ratio, 4) if sortino_ratio else None,
                'calmar_ratio': round(calmar_ratio, 4) if calmar_ratio else None,
                'volatility': round(volatility * 100, 4) if volatility else None,
                'trade_count': trade_count,
                # 'win_rate': ..., 
                # 'profit_loss_ratio': ...
            }
        )
        print(f"✅ 绩效已更新: 净值={current_equity}, 夏普={sharpe_ratio}, 回撤={max_drawdown*100:.2f}%")

def calculate_daily_signals(account, symbol, trade_date, klines_df):
    """
    辅助函数：计算每日策略信号 (TrendInfo 和 DailyStrategySignal)
    这个函数通常在获取到 K线数据后调用，不依赖数据库，只写数据库。
    
    :param klines_df: 包含最新 K线数据的 Pandas DataFrame
    """
    # 这里调用你策略里的 calculate_trend_factor 和 calculate_breakout_levels
    # 因为这两个函数是纯计算逻辑，不依赖 TqApi 对象
    
    # 模拟调用
    # trend_info = calculate_trend_factor(klines_df)
    # entry_high, entry_low, _, _ = calculate_breakout_levels(klines_df)
    
    # 保存 TrendInfo
    # TrendInfo.objects.create(...)
    
    # 保存 DailyStrategySignal
    # DailyStrategySignal.objects.create(...)
    pass

# ==================== APScheduler 任务入口 ====================

def job_daily_close_calculation():
    """
    每日收盘后定时任务入口
    """
    print("🕒 触发每日收盘计算任务...")
    
    # 1. 获取所有活跃账户
    accounts = TradingAccount.objects.filter(is_active=True)
    
    today = date.today()
    
    for account in accounts:
        try:
            # 2. 计算绩效
            calculate_daily_performance(account, today)
            
            # 3. (可选) 如果有实时行情源，可以在这里重新计算明日的信号
            # 但通常信号计算是在交易脚本运行时完成的
            
        except Exception as e:
            print(f"❌ 账户 {account.name} 计算失败: {e}")
            import traceback
            traceback.print_exc()

    print("🏁 每日计算任务结束")