import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth

# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal,RolloverLog, PositionState, TrendInfo
from stock.utils.indicator import calculate_atr, calculate_trend_factor, calculate_breakout_levels

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

    calculate_daily_signals 是整个自动化交易系统的“大脑”或“指挥官”。
    它通常由 APScheduler 在每天盘前（如 08:45）或盘后（如 15:30）定时触发。它的核心作用是“决策”——根据历史数据计算出明天该做什么。
    它不负责下单，只负责生成计划。

    🛠️ 核心功能拆解
    这个函数主要完成了以下 4 个步骤的工作：

    1. 数据清洗与准备
       - 接收原始的 K 线数据 (klines_df)。
       - 确保数据是干净的、按时间排序的，并且截止到“昨天”（防止使用今天的收盘价来计算今天的开盘信号，即避免未来函数）。

    2. 指标计算（调用刚才讨论的函数）
       - 它调用我们刚才分析的所有底层函数来获取市场状态：
         - calculate_atr(klines_df) → 算出波动率，决定买多少手。
         - calculate_trend_factor(klines_df) → 算出是 strong_bull 还是 choppy，决定能不能买。
         - calculate_breakout_levels(klines_df) → 算出唐奇安通道的上下轨，决定具体在哪个价格买。

    3. 策略逻辑判断（核心大脑）
       - 这是该函数最重要的部分。它结合数据库中的旧状态（比如现在有没有持仓）和计算出的新指标，进行逻辑判断：
         - 场景 A：空仓 -> 开仓
           - 逻辑：如果当前没持仓，且 trend_factor 是 strong_bull，且价格即将突破 entry_high。
           - 决策：生成一个“开仓信号”。
         - 场景 B：持仓中 -> 加仓
           - 逻辑：如果持有多单，且价格涨到了 entry_high + 1ATR。
           - 决策：生成一个“加仓信号”。
         - 场景 C：持仓中 -> 止损/止盈
           - 逻辑：如果持有多单，且价格跌破了 exit_low（离场通道）。
           - 决策：生成一个“平仓信号”。

    4. 更新数据库（下达任务）
       - 函数最后不直接调用 TqApi 下单，而是将决策结果写入数据库（如 PositionState 表）：
         - 设置 pending_direction（待买/待卖方向）。
         - 设置 pending_contracts（待买手数）。
         - 设置 add_position_trigger_price（加仓触发价）。

    | 模块           | 角色         | 职责                                                                 | 对应函数/脚本                       |
    | :------------- | :----------- | :------------------------------------------------------------------- | :---------------------------------- |
    | 每日信号计算   | 大脑 (指挥官) | 分析局势，制定计划。<br>“明天如果价格到 3050，我们就买入。”           | `calculate_daily_signals`           |
    | 交易执行       | 双手 (士兵)   | 监听行情，执行计划。<br>“看到价格真的到了 3050，立即下单。”            | `check_and_execute_pending`             |
    | 加仓监控       | 观察员       | 盯着持仓，寻找加仓点。<br>“底仓有了，如果价格到 3100，通知双手加仓。” | `job_add_position_loop`                |

    这个设计的好处是职责分离，降低耦合。大脑只负责决策，不关心执行细节；双手只负责执行，不关心为什么要执行；观察员专注于监控加仓点。这种设计在复杂系统中非常常见，可以提高系统的可维护性和扩展性。
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


# ================= 全局 TqApi 实例 =================
global_api = None

def get_api():
    global global_api
    if global_api is None:
        global_api = TqApi(auth=TqAuth(account_id="YOUR_ACCOUNT_ID", password="YOUR_PASSWORD"))
    return global_api

def detect_main_contact(symbol):
    """
    检测指定品种的主力合约
    参数 symbol: 基础合约代码，如 "rb" (螺纹钢) 或 "IF" (股指)
    返回: 主力合约代码，如 "rb2410"
    """
    api = get_api()
    try:
        # 1. 获取该品种所有合约的列表
        # TqApi 提供了 get_contract_list 来获取某品种下的所有合约
        contracts = api.get_contract_list(symbol)
        
        if not contracts:
            print(f"⚠️ 未找到品种 {symbol} 的合约列表")
            return None

        # 2. 获取所有合约的行情数据 (用于获取持仓量 open_interest)
        # 我们只关心有持仓的合约
        quotes = []
        for contract in contracts:
            quote = api.get_quote(contract)
            if quote.open_interest > 0:
                quotes.append({
                    'symbol': contract,
                    'open_interest': quote.open_interest
                })
        
        if not quotes:
            return None

        # 3. 按持仓量排序，持仓量最大的即为主力合约
        df = pd.DataFrame(quotes)
        df.sort_values(by='open_interest', ascending=False, inplace=True)
        
        main_contract = df.iloc[0]['symbol']
        print(f"🔍 品种 {symbol} 当前主力合约是: {main_contract} (持仓: {df.iloc[0]['open_interest']})")
        
        return main_contract
        
    except Exception as e:
        print(f"❌ 检测主力合约失败: {e}")
        return None


def check_rollover_needed():
    """
    扫描所有持仓，标记需要移仓的记录
    通常在盘后或盘前运行
    """
    api = get_api()
    
    # 1. 获取所有有持仓的记录
    positions = PositionState.objects.filter(
        direction__ne=0,          # 有持仓
        is_rollover_enabled=True  # 开启移仓开关
    )
    
    # 按品种分组，避免重复查询主力合约
    symbols_checked = {}
    
    for pos in positions:
        # 解析品种代码 (例如从 rb2405 提取 rb)
        # 简单处理：去除数字部分
        base_symbol = ''.join([c for c in pos.symbol if c.isalpha()])
        
        if base_symbol not in symbols_checked:
            main_contract = detect_main_contact(base_symbol)
            symbols_checked[base_symbol] = main_contract
        else:
            main_contract = symbols_checked[base_symbol]
            
        if not main_contract:
            continue
            
        # 2. 判断是否需要移仓
        if pos.symbol != main_contract:
            print(f"⚠️ 发现非主力持仓: {pos.symbol} -> 需切换至 {main_contract}")
            
            # 3. 标记数据库
            with transaction.atomic():
                pos.is_rollover_needed = True
                pos.target_rollover_symbol = main_contract
                pos.save()
                
                # 记录日志
                RolloverLog.objects.create(
                    account=pos.account,
                    old_symbol=pos.symbol,
                    new_symbol=main_contract,
                    status='PENDING',
                    volume=pos.volume
                )
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