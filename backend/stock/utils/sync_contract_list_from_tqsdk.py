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
def sync_contract_list_from_tqsdk(api=None):
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
    # TQ_ACCOUNT = "yupei1986"
    # TQ_PASSWORD = "yupei1986"
    
    # api = None
    try:
        # 1. 初始化 TqApi
        # api = TqApi(auth=TqAuth(TQ_ACCOUNT, TQ_PASSWORD))
        # print("[SUCCESS] TqApi 连接成功")
        
        # 2. 定义主要交易所和品种映射
        # 格式：{交易所代码: [品种代码列表]}
        exchange_products = {
            'SHFE': ['rb', 'hc', 'cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'ru', 'bu', 'sp', 'fu'],
            'DCE': ['i', 'j', 'jm', 'c', 'cs', 'l', 'v', 'pp', 'm', 'y', 'p', 'jd', 'eb', 'eg', 'pg', 'rr', 'b'],
            'CZCE': ['MA', 'TA', 'SR', 'CF', 'RM', 'OI', 'FG', 'SA', 'UR', 'AP', 'CJ', 'SF', 'SM', 'RS', 'RI'],
            # 'CFFEX': ['IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TS', 'TL'],
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
            # 'IF': '金融期货', 'IC': '金融期货', 'IH': '金融期货', 'IM': '金融期货',
            # 'T': '国债期货', 'TF': '国债期货', 'TS': '国债期货', 'TL': '国债期货',
            'si': '新能源', 'lc': '新能源'
        }
        
        category_mapping = {
            'rb': '螺纹类', 'hc': '热卷类', 'i': '铁矿类', 'j': '焦炭类', 'jm': '焦煤类',
            'cu': '铜类', 'al': '铝类', 'zn': '锌类', 'pb': '铅类', 'ni': '镍类', 'sn': '锡类',
            'au': '黄金类', 'ag': '白银类',
            'MA': '甲醇类', 'TA': 'PTA类', 'l': '塑料类', 'v': 'PVC类', 'pp': 'PP类',
            'eb': '苯乙烯类', 'eg': '乙二醇类', 'fu': '燃油类', 
            'c': '玉米类', 'm': '豆粕类', 'y': '豆油类', 'p': '棕榈油类',
            # 'IF': '沪深300', 'IC': '中证500', 'IH': '上证50', 'IM': '中证1000'
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
                                    
                    # 7. 使用 update_or_create 直接创建或更新记录
                    with transaction.atomic():
                        old_obj = FullContractList.objects.filter(exchange=exchange, product_code=product_code).first()
                        obj, created = FullContractList.objects.update_or_create(
                            exchange=exchange,
                            product_code=product_code,
                            defaults={
                                'symbol': main_contract,
                                'name': f"{product_code}主力合约",
                                'volume_multiple': volume_multiple,
                                'price_tick': Decimal(str(price_tick)),
                                'margin_ratio': margin_ratio,
                                'sector': sector_mapping.get(product_code, '其他'),
                                'category': category_mapping.get(product_code, '其他'),
                            }
                        )
                        
                        if created:
                            ta = TradingAccount.objects.all().first()
                            PositionState.objects.create(
                                    account=ta,
                                    symbol=main_contract,
                                    product_code=product_code
                                )
                            synced_count += 1
                            print(f"    [ADD] 新增记录: {main_contract}")

                        else:
                            # 检查主力合约是否发生变化
                            if obj.symbol != old_obj.symbol:
                                # 批量更新该品种所有有持仓的记录，标记需要移仓 
                                
                                updated_rows = PositionState.objects.filter(
                                    product_code=product_code,
                                    units__gt=0  # 只处理有持仓的
                                ).update(is_rollover_needed=True)

                                PositionState.objects.filter(
                                    product_code=product_code,
                                    units=0  # 只处理有持仓的
                                ).update(symbol=main_contract)
                                
                                if updated_rows > 0:
                                    print(f"    [INFO] 已标记 {updated_rows} 条持仓记录需要移仓")
                                
                                updated_count += 1
                                print(f"    [UPDATE] 主力合约变更: {old_obj.symbol} -> {main_contract}")
                            else:
                                skipped_count += 1
                
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
        pass
