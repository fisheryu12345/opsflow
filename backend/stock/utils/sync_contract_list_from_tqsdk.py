from django.db import transaction
from decimal import Decimal

from stock.models import TradingAccount, PositionState, FullContractList

PRODUCT_CODES = ['rb','hc','al','ao','MA','TA','SA','FG','fu','ru','UR','m','p','CF','RM','AP','lh','AP','jd','sp','si','lc','SR']

def sync_contract_list_from_tqsdk(api=None):
    """
    使用 TqSDK 内置 API 获取所有期货合约信息并同步到 FullContractList 表
    
    💡 功能说明：
    1. 使用 api.query_cont_quotes() 获取所有主力合约列表
    2. 遍历每个主力合约，调用 api.get_quote() 获取详细信息
    3. 提取合约元数据（乘数、最小变动价位、交易时间等）写入数据库
    4. 自动识别并标记当前主力合约
    5. 检测主力合约切换，标记需要移仓的持仓记录
    
    📌 使用场景：
    - 系统初始化时批量导入所有可交易合约
    - 定期更新合约信息（如新合约上市）
    - 更新主力合约切换状态
    """
    print("[INFO] 开始同步期货合约列表...")
    try:
        print("[INFO] 查询所有主力合约...")
        cont_quotes = api.query_cont_quotes()
        
        if not cont_quotes:
            print("[WARN] 未获取到任何主力合约数据")
            return {
                'synced': 0,
                'updated': 0,
                'skipped': 0,
                'error': '未获取到主力合约数据'
            }
        
        print(f"[INFO] 共获取到 {len(cont_quotes)} 个主力合约")
       
        synced_count = 0
        updated_count = 0
        skipped_count = 0

        # 4. 遍历所有主力合约
        for cont_symbol in cont_quotes:
            try:
                print(f"\n[CHECK] 处理主力合约: {cont_symbol}")
                # 5. 获取合约详细信息
                quote = api.get_quote(cont_symbol)
                if quote.product_id not in PRODUCT_CODES:
                    print(f"  [SKIP] 排除的品种: {product_id}")
                    skipped_count += 1
                    continue
                # 6. 从 quote 对象中提取关键信息
                instrument_id = quote.instrument_id  # 完整合约代码，如 "CZCE.MA605"
                product_id = quote.product_id  # 品种代码，如 "MA"
                exchange_id = quote.exchange_id  # 交易所代码，如 "CZCE"
                instrument_name = quote.instrument_name  # 合约名称，如 "甲醇2605"
                
                # 提取合约规格
                volume_multiple = getattr(quote, 'volume_multiple', 10)
                price_tick = getattr(quote, 'price_tick', 1.0)
                
                # 验证数据有效性
                if not volume_multiple or volume_multiple <= 0:
                    volume_multiple = 10
                
                if not price_tick or price_tick <= 0:
                    price_tick = 1.0
                
                # 提取交易时间信息（用于判断是否有夜盘）
                trading_time = getattr(quote, 'trading_time', {})
                has_night = bool(trading_time.get('night', []))
                # 尝试从 categories 字段提取分类名称
                category_from_api = None
                categories_list = getattr(quote, 'categories', [])
                if categories_list and isinstance(categories_list, list) and len(categories_list) > 0:
                    # 提取第一个分类的 name 字段
                    category_from_api = categories_list[0].get('name') if isinstance(categories_list[0], dict) else None
                min_position = quote.open_min_market_order_volume
                
                print(f"  [OK] {instrument_id} | 品种: {product_id} | 乘数: {volume_multiple} | Tick: {price_tick} | 夜盘: {'有' if has_night else '无'} | 分类: {category_from_api}")
                
                # 7. 使用 update_or_create 创建或更新记录
                with transaction.atomic():
                    old_obj = FullContractList.objects.filter(
                        exchange=exchange_id, 
                        product_code=product_id
                    ).first()
                    
                    obj, created = FullContractList.objects.update_or_create(
                        exchange=exchange_id,
                        product_code=product_id,
                        defaults={
                            'symbol': instrument_id,
                            'name': instrument_name,
                            'volume_multiple': int(volume_multiple),
                            'price_tick': Decimal(str(price_tick)),
                            'min_position': min_position,
                            'category': category_from_api,
                            'night_trading': has_night,  # 根据交易时间自动设置
                        }
                    )
                    
                    if created:
                        # 新增记录时，同时创建 PositionState
                        ta = TradingAccount.objects.all().first()
                        if ta:
                            PositionState.objects.create(
                                account=ta,
                                symbol=instrument_id,
                                product_code=product_id
                            )
                        synced_count += 1
                        print(f"    [ADD] 新增记录: {instrument_id}")

                    else:
                        # 检查主力合约是否发生变化
                        if old_obj and obj.symbol != old_obj.symbol:
                            # 批量更新该品种所有有持仓的记录，标记需要移仓
                            updated_rows = PositionState.objects.filter(
                                product_code=product_id,
                                units__gt=0  # 只处理有持仓的
                            ).update(is_rollover_needed=True)

                            # 更新无持仓记录的 symbol 字段
                            PositionState.objects.filter(
                                product_code=product_id,
                                units=0
                            ).update(symbol=instrument_id)
                            
                            if updated_rows > 0:
                                print(f"    [INFO] 已标记 {updated_rows} 条持仓记录需要移仓")
                            
                            updated_count += 1
                            print(f"    [UPDATE] 主力合约变更: {old_obj.symbol} -> {instrument_id}")
                        else:
                            skipped_count += 1
                
            except Exception as e:
                print(f"  [ERROR] 处理合约 {cont_symbol} 失败: {e}")
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
        pass