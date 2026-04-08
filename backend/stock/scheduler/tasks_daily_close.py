import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth

# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal,RolloverLog, PositionState, TrendInfo, FullContractList
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


def sync_contract_list_from_tqsdk():
    """
    使用 TqSDK 获取所有期货合约信息并同步到 FullContractList 表
    
    💡 功能说明：
    1. 连接天勤 API
    2. 遍历所有交易所的主要品种
    3. 获取每个品种的合约列表和主力合约信息
    4. 将合约元数据（乘数、最小变动价位等）写入数据库
    5. 自动识别并标记当前主力合约
    
    📌 使用场景：
    - 系统初始化时批量导入所有可交易合约
    - 定期更新合约信息（如新合约上市）
    - 更新主力合约切换状态
    """
    print("🔄 开始同步期货合约列表...")
    
    # 天勤账号配置
    TQ_ACCOUNT = "yupei1986"
    TQ_PASSWORD = "yupei1986"
    
    api = None
    try:
        # 1. 初始化 TqApi
        api = TqApi(auth=TqAuth(TQ_ACCOUNT, TQ_PASSWORD))
        print("✅ TqApi 连接成功")
        
        # 2. 定义主要交易所和品种映射
        # 格式：{交易所代码: [品种代码列表]}
        exchange_products = {
            'SHFE': ['rb', 'hc', 'cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'ru', 'bu', 'sp', 'fu'],
            'DCE': ['i', 'j', 'jm', 'c', 'cs', 'l', 'v', 'pp', 'm', 'y', 'p', 'jd', 'eb', 'eg', 'pg', 'rr', 'b'],
            'CZCE': ['MA', 'TA', 'SR', 'CF', 'RM', 'OI', 'FG', 'SA', 'UR', 'AP', 'CJ', 'SF', 'SM', 'RS', 'RI'],
            'CFFEX': ['IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TS', 'TL'],
            'GFEX': ['si', 'lc']
        }
        
        # 3. 品种板块分类映射
        sector_mapping = {
            'rb': '黑色金属', 'hc': '黑色金属', 'i': '黑色金属', 'j': '黑色金属', 'jm': '黑色金属',
            'cu': '有色金属', 'al': '有色金属', 'zn': '有色金属', 'pb': '有色金属', 'ni': '有色金属', 'sn': '有色金属',
            'au': '贵金属', 'ag': '贵金属',
            'MA': '化工', 'TA': '化工', 'l': '化工', 'v': '化工', 'pp': '化工', 'eb': '化工', 'eg': '化工',
            'fu': '能源化工', 'bu': '能源化工', 'ru': '化工', 'pg': '化工',
            'c': '农产品', 'cs': '农产品', 'm': '农产品', 'y': '农产品', 'p': '农产品', 'a': '农产品', 'b': '农产品',
            'sr': '软商品', 'cf': '软商品', 'oi': '农产品', 'fg': '建材', 'SA': '建材', 'UR': '化工',
            'IF': '金融期货', 'IC': '金融期货', 'IH': '金融期货', 'IM': '金融期货',
            'T': '国债期货', 'TF': '国债期货', 'TS': '国债期货', 'TL': '国债期货',
            'si': '新能源', 'lc': '新能源'
        }
        
        category_mapping = {
            'rb': '螺纹类', 'hc': '热卷类', 'i': '铁矿类', 'j': '焦炭类', 'jm': '焦煤类',
            'cu': '铜类', 'al': '铝类', 'zn': '锌类', 'pb': '铅类', 'ni': '镍类', 'sn': '锡类',
            'au': '黄金类', 'ag': '白银类',
            'MA': '甲醇类', 'TA': 'PTA类', 'l': '塑料类', 'v': 'PVC类', 'pp': 'PP类',
            'eb': '苯乙烯类', 'eg': '乙二醇类', 'fu': '燃油类', 
            'c': '玉米类', 'm': '豆粕类', 'y': '豆油类', 'p': '棕榈油类',
            'IF': '沪深300', 'IC': '中证500', 'IH': '上证50', 'IM': '中证1000'
        }
        
        synced_count = 0
        updated_count = 0
        skipped_count = 0
        
        # 4. 遍历所有品种
        for exchange, products in exchange_products.items():
            print(f"\n📊 处理交易所: {exchange}")
            
            for product_code in products:
                try:
                    # 构造 TqSDK 的品种代码格式
                    # 使用 KQ.m@ 前缀获取主力合约连续数据
                    if exchange == 'CZCE':
                        # 郑商所品种代码通常是大写字母
                        tq_main_symbol = f"KQ.m@{exchange}.{product_code}"
                    else:
                        tq_main_symbol = f"KQ.m@{exchange}.{product_code}"
                    
                    print(f"  🔍 检查品种: {product_code}")
                    
                    # 5. 尝试获取主力合约行情
                    try:
                        main_quote = api.get_quote(tq_main_symbol)
                        
                        # 检查是否获取到有效数据
                        if not hasattr(main_quote, 'last_price') or pd.isna(main_quote.last_price):
                            print(f"  ⚠️  {product_code}: 无法获取主力合约数据")
                            continue
                        
                        # 从主力合约代码中提取实际合约代码
                        # KQ.m@SHFE.rb 会返回类似 SHFE.rb2410 的实际合约
                        main_contract = getattr(main_quote, 'underlying_symbol', None)
                        
                        if not main_contract:
                            # 如果 underlying_symbol 为空，尝试从其他字段获取
                            # 某些版本可能直接返回合约代码在 symbol 字段
                            main_contract = getattr(main_quote, 'symbol', None)
                            
                        if not main_contract or main_contract == tq_main_symbol:
                            print(f"  ⚠️  {product_code}: 无法解析主力合约代码")
                            continue
                        
                        print(f"  ✅ 主力合约: {main_contract}")
                        
                    except Exception as e:
                        print(f"  ⚠️  {product_code}: 获取主力合约失败 - {e}")
                        continue
                    
                    # 6. 获取具体合约的详细信息
                    try:
                        contract_quote = api.get_quote(main_contract)
                        
                        # 提取合约乘数和最小变动价位
                        volume_multiple = getattr(contract_quote, 'volume_multiple', 10)
                        price_tick = getattr(contract_quote, 'price_tick', 1.0)
                        
                        # 验证数据有效性
                        if not volume_multiple or volume_multiple <= 0:
                            volume_multiple = 10  # 默认值
                        
                        if not price_tick or price_tick <= 0:
                            price_tick = 1.0  # 默认值
                            
                    except Exception as e:
                        print(f"  ⚠️  {product_code}: 获取合约详情失败 - {e}")
                        # 使用默认值继续
                        volume_multiple = 10
                        price_tick = 1.0
                    
                    # 估算保证金比例（默认10%，实际需要从交易所获取或配置）
                    margin_ratio = Decimal('0.1')
                    
                    # 判断是否需要移仓换月（股指期货通常不需要频繁换月）
                    need_rollover = product_code not in ['IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TS', 'TL']
                    
                    # 7. 检查数据库中是否已存在该品种记录
                    existing = FullContractList.objects.filter(
                        exchange=exchange,
                        product_code=product_code
                    ).first()
                    
                    # 8. 创建或更新记录
                    with transaction.atomic():
                        if existing:
                            # 更新现有记录
                            update_fields = []
                            
                            # 只在主力合约变化时更新 symbol
                            if existing.symbol != main_contract:
                                existing.symbol = main_contract
                                update_fields.append('symbol')
                                print(f"    🔄 主力合约变更: {existing.symbol} -> {main_contract}")
                            
                            # 更新其他元数据
                            if existing.volume_multiple != volume_multiple:
                                existing.volume_multiple = volume_multiple
                                update_fields.append('volume_multiple')
                            
                            if float(existing.price_tick) != float(price_tick):
                                existing.price_tick = Decimal(str(price_tick))
                                update_fields.append('price_tick')
                            
                            if update_fields:
                                existing.save(update_fields=update_fields)
                                updated_count += 1
                                print(f"    ✏️  更新记录: {main_contract}")
                            else:
                                skipped_count += 1
                        else:
                            # 创建新记录
                            FullContractList.objects.create(
                                exchange=exchange,
                                product_code=product_code,
                                symbol=main_contract,
                                name=f"{product_code}主力合约",
                                is_active=False,  # 默认不激活，需要手动开启
                                allow_open=True,
                                volume_multiple=volume_multiple,
                                price_tick=Decimal(str(price_tick)),
                                margin_ratio=margin_ratio,
                                sector=sector_mapping.get(product_code, '其他'),
                                category=category_mapping.get(product_code, '其他'),
                                need_rollover=need_rollover
                            )
                            synced_count += 1
                            print(f"    ➕ 新增记录: {main_contract}")
                
                except Exception as e:
                    print(f"  ❌ 处理品种 {product_code} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print(f"\n{'='*60}")
        print(f"📈 同步完成统计:")
        print(f"  ✅ 新增合约: {synced_count}")
        print(f"  ✏️  更新合约: {updated_count}")
        print(f"  ⏭️  跳过合约: {skipped_count}")
        print(f"{'='*60}")
        
        return {
            'synced': synced_count,
            'updated': updated_count,
            'skipped': skipped_count
        }
        
    except Exception as e:
        print(f"❌ 同步合约列表失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'synced': 0,
            'updated': 0,
            'skipped': 0,
            'error': str(e)
        }
    
    finally:
        # 确保关闭 API 连接
        if api:
            try:
                api.close()
                print("🔒 TqApi 连接已关闭")
            except Exception as e:
                print(f"⚠️ 关闭 TqApi 时出错: {e}")


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
    
    💡 实现原理：
    使用 TqSDK 的 KQ.m@ 主力合约连续数据，直接获取当前主力合约
    """
    api = get_api()
    try:
        # 1. 构造主力合约连续代码
        # 首先判断交易所
        exchange = None
        if symbol in ['rb', 'hc', 'cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'ru', 'bu', 'sp', 'fu',]:
            exchange = 'SHFE'
        elif symbol in ['i', 'j', 'jm', 'c', 'cs', 'l', 'v', 'pp', 'm', 'y', 'p', 'jd', 'eb', 'eg', 'pg', 'rr', 'b']:
            exchange = 'DCE'
        elif symbol in ['MA', 'TA', 'SR', 'CF', 'RM', 'OI', 'FG', 'SA', 'UR', 'AP', 'CJ', 'SF', 'SM', 'RS', 'RI']:
            exchange = 'CZCE'
        elif symbol in ['IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TS', 'TL']:
            exchange = 'CFFEX'
        elif symbol in ['si', 'lc']:
            exchange = 'GFEX'
        
        if not exchange:
            print(f"⚠️ 未知品种: {symbol}")
            return None
        
        # 2. 使用 KQ.m@ 获取主力合约连续数据
        main_symbol_code = f"KQ.m@{exchange}.{symbol}"
        
        # 3. 获取主力合约行情
        quote = api.get_quote(main_symbol_code)
        
        # 4. 从行情中提取实际的主力合约代码
        # underlying_symbol 字段包含实际的合约代码（如 SHFE.rb2410）
        actual_contract = getattr(quote, 'underlying_symbol', None)
        
        if not actual_contract or actual_contract == main_symbol_code:
            # 某些版本可能在 symbol 字段
            actual_contract = getattr(quote, 'symbol', None)
        
        if not actual_contract:
            print(f"⚠️ 无法获取 {symbol} 的主力合约信息")
            return None
        
        print(f"🔍 品种 {symbol} 当前主力合约是: {actual_contract}")
        return actual_contract
        
    except Exception as e:
        print(f"❌ 检测主力合约失败: {e}")
        import traceback
        traceback.print_exc()
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