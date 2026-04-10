import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount, TradeExecution, DailyPerformance, DailyStrategySignal, RolloverLog, PositionState, FullContractList

def calculate_indicators_with_builtin(symbol="SHFE.rb2610", days=60):
    """
    使用Tqsdk内置函数计算技术指标
    
    参数：
    symbol: 期货合约代码
    days: 需要获取的历史K线天数
    
    返回：
    包含各项技术指标的字典
    """
    try:
        # 1. 连接天勤API
        api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
        
        # 2. 获取K线数据
        print(f"[INFO] 正在获取 {symbol} 的K线数据...")
        klines = api.get_kline_serial(symbol, duration_seconds=24 * 60 * 60, data_length=days)
        
        if len(klines) < 40:
            print(f"警告：数据长度({len(klines)})不足40天")
        
        # 3. 使用内置函数计算指标
        # 3.1 计算ATR（使用tqsdk.ta.ATR）
        atr_result = ATR(klines, 20)  # 20日ATR
        atr_20_value = float(atr_result.iloc[-1]['atr']) if len(atr_result) > 0 else None
        
        # 3.2 计算移动平均线（使用 Pandas 原生方法）
        ma_10_value = float(klines['close'].rolling(10).mean().iloc[-1]) if len(klines) >= 10 else None
        ma_20_value = float(klines['close'].rolling(20).mean().iloc[-1]) if len(klines) >= 20 else None
        ma_40_value = float(klines['close'].rolling(40).mean().iloc[-1]) if len(klines) >= 40 else None

        # 3.3 计算20日内收盘价高低点 (使用 Pandas 原生方法)
        close_high_20 = float(klines['close'].rolling(20).max().iloc[-1]) if len(klines) >= 20 else None
        close_low_20 = float(klines['close'].rolling(20).min().iloc[-1]) if len(klines) >= 20 else None
        
        # 3.4 计算唐奇安通道突破价位
        ENTRY_PERIOD = 20
            
        if len(klines) >= ENTRY_PERIOD + 2:
            high_prior = klines["high"].iloc[-ENTRY_PERIOD - 1:-1]
            low_prior = klines["low"].iloc[-ENTRY_PERIOD - 1:-1]
            
            if len(high_prior) > 0:
                entry_high = float(high_prior.max())
                entry_low = float(low_prior.min())
            else:
                entry_high = entry_low = None
        else:
            entry_high = entry_low  = None
        
        # 3.5 计算趋势因子（简化版 - 只保留5种状态）
        MA_PERIODS = [10, 20, 40]
        
        # 检查均线数据有效性
        if ma_10_value and ma_20_value and ma_40_value and not any(np.isnan(v) for v in [ma_10_value, ma_20_value, ma_40_value]):
            diff10_20 = ma_10_value - ma_20_value
            diff20_40 = ma_20_value - ma_40_value
            
            # 动态阈值：0.45% 的 MA20 价格
            threshold = 0.0045 * abs(ma_20_value)
            
            # 多头排列
            if ma_10_value > ma_20_value > ma_40_value:
                trend_factor = 0.5
                trend_label = "strong_bull"  # IF: 完全多头排列 (MA10>MA20>MA40)
            # 空头排列
            elif ma_10_value < ma_20_value < ma_40_value:
                trend_factor = -0.5
                trend_label = "strong_bear"  # ELIF-1: 完全空头排列 (MA10<MA20<MA40)
            # 震荡市（均线纠缠）
            elif abs(diff10_20) < threshold and abs(diff20_40) < threshold:
                trend_factor = -0.3
                trend_label = "choppy"  # ELIF-2: 震荡市 (均线差值都小于阈值)
            # 弱多头：至少有一条均线向上，且不是震荡
            elif (ma_10_value > ma_20_value and ma_20_value >= ma_40_value) or \
                 (ma_10_value >= ma_20_value and ma_20_value > ma_40_value):
                trend_factor = -0.15
                trend_label = "weak_bull"  # ELIF-3: 弱多头 (部分均线向上但未完全发散)
            # 弱空头：至少有一条均线向下，且不是震荡
            elif (ma_10_value < ma_20_value and ma_20_value <= ma_40_value) or \
                 (ma_10_value <= ma_20_value and ma_20_value < ma_40_value):
                trend_factor = -0.15
                trend_label = "weak_bear"  # ELIF-4: 弱空头 (部分均线向下但未完全发散)
            # 其他情况归为震荡（均线交叉或混乱）
            else:
                trend_factor = -0.3
                trend_label = "choppy"  # ELSE: 均线交叉/混乱状态
        else:
            trend_factor = 0.0
            trend_label = "neutral"  # OUTER-ELSE: 均线数据无效

        # 3.6 判断是否突破
        latest_close = float(klines.iloc[-1]['close'])
        trade_date = pd.to_datetime(klines.iloc[-1]['datetime'], unit='ns').date()
        
        is_breakout = False
        signal_direction = 0
        remark = ""
        
        # 判断突破条件：收盘价突破前20天的高低点
        if entry_high and entry_low:
            if latest_close > entry_high:
                # 向上突破
                is_breakout = True
                signal_direction = 1
                remark = f"收盘价 {latest_close:.2f} 突破唐奇安上轨 {entry_high:.2f}"
                print(f"[SIGNAL] 发现向上突破信号: {symbol} - {remark}")
            elif latest_close < entry_low:
                # 向下突破
                is_breakout = True
                signal_direction = -1
                remark = f"收盘价 {latest_close:.2f} 跌破唐奇安下轨 {entry_low:.2f}"
                print(f"[SIGNAL] 发现向下突破信号: {symbol} - {remark}")
        
        # 保存每日策略信号到数据库（每天都保存，记录完整市场状态）
        try:
            from stock.models import TradingAccount, PositionState
            
            # 尝试获取第一个活跃账户
            default_account = TradingAccount.objects.filter(is_active=True).first()
            
            if is_breakout and default_account:
                with transaction.atomic():
                    # 1. 保存/更新 DailyStrategySignal（只保存有效突破信号）
                    signal_obj, created = DailyStrategySignal.objects.update_or_create(
                        account=default_account,
                        symbol=symbol,
                        trade_date=trade_date,
                        defaults={
                            'trend_factor': Decimal(str(trend_factor)),
                            'trend_label': trend_label,
                            # 'trend_rank': trend_factor,
                            'donchian_upper': Decimal(str(entry_high)) if entry_high else None,
                            'donchian_lower': Decimal(str(entry_low)) if entry_low else None,
                            'is_breakout': is_breakout,
                            'signal_direction': signal_direction,
                            'remark': remark if remark else f"趋势状态: {trend_label} (factor={trend_factor})"
                        }
                    )
                    
                    if created:
                        print(f"[SUCCESS] 新建策略信号: {symbol} - {trade_date} - {trend_label}")
                    else:
                        print(f"[UPDATE] 更新策略信号: {symbol} - {trade_date} - {trend_label}")
                    
                    # 2. 更新 PositionState 中的趋势因子（实时状态）
                    position, pos_created = PositionState.objects.get_or_create(
                        account=default_account,
                        symbol=symbol,
                        defaults={
                            'units': 0,
                            'direction': 0,
                            'pending_trend_factor': Decimal(str(trend_factor))
                        }
                    )
                    
                    # 更新趋势因子（即使没有持仓，也记录当前趋势）
                    position.pending_trend_factor = Decimal(str(trend_factor))
                    position.save(update_fields=['pending_trend_factor'])
                    print(f"[DATA] 更新持仓状态表趋势因子: {symbol} - {trend_label} ({trend_factor})")
                    
            else:
                print(f"[WARN] 未找到活跃的交易账户，跳过保存信号: {symbol}")
                
        except Exception as db_error:
            print(f"[ERROR] 保存策略信号失败: {db_error}")
            import traceback
            traceback.print_exc()

        # 4. 整理结果
        results = {
            'symbol': symbol,
            'latest_date': trade_date.strftime('%Y-%m-%d'),
            'latest_close': latest_close,
            'atr_20': atr_20_value,
            'ma_10': ma_10_value,
            'ma_20': ma_20_value,
            'ma_40': ma_40_value,
            'close_high_20': close_high_20,
            'close_low_20': close_low_20,
            'data_points': len(klines),
            # 趋势因子相关
            'trend_factor': trend_factor,
            'trend_label': trend_label,
            # 'trend_rank': trend_rank,
            # 唐奇安通道
            'entry_high': entry_high,
            'entry_low': entry_low,
            # 'exit_high': exit_high,
            # 'exit_low': exit_low,
            # 突破信号
            'is_breakout': is_breakout,
            'signal_direction': signal_direction,
            'breakout_remark': remark,
        }
        
        # 5. 关闭API连接
        api.close()
        
        return results
        
    except Exception as e:
        print(f"计算过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    
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
    print("[INFO] 开始同步期货合约列表...")
    
    # 天勤账号配置
    TQ_ACCOUNT = "yupei1986"
    TQ_PASSWORD = "yupei1986"
    
    api = None
    try:
        # 1. 初始化 TqApi
        api = TqApi(auth=TqAuth(TQ_ACCOUNT, TQ_PASSWORD))
        print("[SUCCESS] TqApi 连接成功")
        
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
            print(f"\n[INFO] 处理交易所: {exchange}")
            
            for product_code in products:
                try:
                    # 构造 TqSDK 的品种代码格式
                    # 使用 KQ.m@ 前缀获取主力合约连续数据
                    if exchange == 'CZCE':
                        # 郑商所品种代码通常是大写字母
                        tq_main_symbol = f"KQ.m@{exchange}.{product_code}"
                    else:
                        tq_main_symbol = f"KQ.m@{exchange}.{product_code}"
                    
                    print(f"  [CHECK] 检查品种: {product_code}")
                    
                    # 5. 尝试获取主力合约行情
                    try:
                        main_quote = api.get_quote(tq_main_symbol)
                        
                        # 检查是否获取到有效数据
                        if not hasattr(main_quote, 'last_price') or pd.isna(main_quote.last_price):
                            print(f"  [WARN] {product_code}: 无法获取主力合约数据")
                            continue
                        
                        # 从主力合约代码中提取实际合约代码
                        # KQ.m@SHFE.rb 会返回类似 SHFE.rb2410 的实际合约
                        main_contract = getattr(main_quote, 'underlying_symbol', None)
                        
                        if not main_contract:
                            # 如果 underlying_symbol 为空，尝试从其他字段获取
                            # 某些版本可能直接返回合约代码在 symbol 字段
                            main_contract = getattr(main_quote, 'symbol', None)
                            
                        if not main_contract or main_contract == tq_main_symbol:
                            print(f"  [WARN] {product_code}: 无法解析主力合约代码")
                            continue
                        
                        print(f"  [OK] 主力合约: {main_contract}")
                        
                    except Exception as e:
                        print(f"  [WARN] {product_code}: 获取主力合约失败 - {e}")
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
                        print(f"  [WARN] {product_code}: 获取合约详情失败 - {e}")
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
                                print(f"    [CHANGE] 主力合约变更: {existing.symbol} -> {main_contract}")
                            
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
                                print(f"    [UPDATE] 更新记录: {main_contract}")
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
                            print(f"    [ADD] 新增记录: {main_contract}")
                
                except Exception as e:
                    print(f"  [ERROR] 处理品种 {product_code} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print(f"\n{'='*60}")
        print(f"[STATS] 同步完成统计:")
        print(f"  [ADD] 新增合约: {synced_count}")
        print(f"  [UPDATE] 更新合约: {updated_count}")
        print(f"  [SKIP] 跳过合约: {skipped_count}")
        print(f"{'='*60}")
        
        return {
            'synced': synced_count,
            'updated': updated_count,
            'skipped': skipped_count
        }
        
    except Exception as e:
        print(f"[ERROR] 同步合约列表失败: {e}")
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
                print("[INFO] TqApi 连接已关闭")
            except Exception as e:
                print(f"[WARN] 关闭 TqApi 时出错: {e}")
def update_postition_tracking(current_close, direction, highest_close, lowest_close):
    """更新持仓跟踪价格"""
    if direction > 0:
        if highest_close is None:
            highest_close = current_close
        else:
            highest_close = max(highest_close, current_close)
            print(f"   [UPDATE] 更新多头持仓最高价: {highest_close:.2f}")
    elif direction < 0:
        if lowest_close is None:
            lowest_close = current_close
        else:
            lowest_close = min(lowest_close, current_close)
            print(f"   [UPDATE] 更新空头持仓最低价: {lowest_close:.2f}")
    return highest_close, lowest_close


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
            print(f"[WARN] 发现非主力持仓: {pos.symbol} -> 需切换至 {main_contract}")
            
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
    
    执行流程：
    1. 同步期货合约列表（获取最新主力合约信息）
    2. 计算活跃品种的技术指标和策略信号
    """
    print("[TASK] 触发每日收盘计算任务...")
    print("=" * 60)
    
    # ========== 第1步：同步期货合约列表 ==========
    print("\n[STEP 1] 同步期货合约列表")
    print("-" * 60)
    try:
        sync_result = sync_contract_list_from_tqsdk()
        if sync_result:
            print(f"[SUCCESS] 合约同步完成: 新增={sync_result.get('synced', 0)}, 更新={sync_result.get('updated', 0)}")
        else:
            print("[WARN] 合约同步返回结果为空")
    except Exception as e:
        print(f"[WARN] 合约同步失败（继续执行后续任务）: {e}")
        import traceback
        traceback.print_exc()
    
    # ========== 第2步：计算活跃品种的技术指标 ==========
    print("\n[STEP 2] 计算活跃品种技术指标")
    print("-" * 60)
    
    # 获取所有激活且允许开仓的品种
    active_contracts = FullContractList.objects.filter(
        is_active=True,
        allow_open=True
    ).values_list('symbol', flat=True)
    
    if not active_contracts:
        print("[WARN] 没有激活且允许开仓的合约，跳过指标计算")
    else:
        print(f"[INFO] 找到 {len(active_contracts)} 个活跃合约")
        
        success_count = 0
        fail_count = 0
        
        for symbol in active_contracts:
            try:
                print(f"\n[PROCESS] 处理合约: {symbol}")
                result = calculate_indicators_with_builtin(symbol=symbol, days=60)
                
                if result:
                    success_count += 1
                    print(f"[SUCCESS] {symbol} 计算成功 - 趋势: {result.get('trend_label')} ({result.get('trend_factor')})")
                else:
                    fail_count += 1
                    print(f"[FAIL] {symbol} 计算失败")
                    
            except Exception as e:
                fail_count += 1
                print(f"[ERROR] {symbol} 处理异常: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n[STATS] 指标计算统计: 成功={success_count}, 失败={fail_count}")
    
