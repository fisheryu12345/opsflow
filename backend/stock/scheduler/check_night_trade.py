"""
使用 TqSDK 同步期货品种夜盘交易状态

功能：
- 查询所有交易所的期货品种夜盘状态
- 批量更新 FullContractList 表的 night_trading 字段
- 提供准确的夜盘交易信息，避免人工维护静态清单

定时任务：每周一早上 8:00 执行
"""

from tqsdk import TqApi, TqAuth
from django.db import transaction
from stock.models import FullContractList


def sync_night_trading_status_from_tqsdk():
    """
    使用 TqSDK 查询所有期货品种的夜盘交易状态并更新数据库
    
    执行逻辑：
    1. 连接 TqSDK API
    2. 查询所有交易所有夜盘和无夜盘的品种
    3. 提取品种代码（product_code）
    4. 批量更新 FullContractList 表的 night_trading 字段
    5. 记录同步统计信息
    
    定时任务：每周一早上 8:00 执行
    """
    api = None
    try:
        print("[INFO] ========== 开始同步期货品种夜盘交易状态 ==========")
        
        # 第1步：创建 TqApi 连接
        api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
        print("[INFO] TqApi 连接已建立")
        
        # 第2步：查询所有交易所的期货品种
        exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "GFEX"]
        no_night_products = set()  # 无夜盘的品种代码集合
        has_night_products = set()  # 有夜盘的品种代码集合
        
        for exchange in exchanges:
            try:
                # 查询该交易所有夜盘的品种
                quotes_with_night = api.query_quotes(
                    ins_class="FUTURE", 
                    exchange_id=exchange, 
                    has_night=True
                )
                
                # 查询该交易所无夜盘的品种
                quotes_without_night = api.query_quotes(
                    ins_class="FUTURE", 
                    exchange_id=exchange, 
                    has_night=False
                )
                
                # 提取品种代码（从合约代码中提取 product_code）
                for quote in quotes_with_night:
                    # quote 格式如 "SHFE.rb2405"，提取 "rb"
                    parts = quote.split('.')
                    if len(parts) == 2:
                        symbol = parts[1]
                        # 去掉数字部分，只保留字母（处理如 MA605 -> MA）
                        product_code = ''.join([c for c in symbol if c.isalpha()])
                        has_night_products.add(product_code.upper())
                
                for quote in quotes_without_night:
                    parts = quote.split('.')
                    if len(parts) == 2:
                        symbol = parts[1]
                        product_code = ''.join([c for c in symbol if c.isalpha()])
                        no_night_products.add(product_code.upper())
                        
                print(f"[INFO] {exchange}: 有夜盘 {len(quotes_with_night)} 个合约, 无夜盘 {len(quotes_without_night)} 个合约")
                
            except Exception as e:
                print(f"[ERROR] 查询 {exchange} 交易所失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[INFO] 汇总统计: 有夜盘品种 {len(has_night_products)} 个, 无夜盘品种 {len(no_night_products)} 个")
        print(f"[INFO] 有夜盘品种列表: {sorted(has_night_products)}")
        print(f"[INFO] 无夜盘品种列表: {sorted(no_night_products)}")
        
        # 第3步：批量更新数据库
        with transaction.atomic():
            # 更新有夜盘的品种
            updated_has_night = FullContractList.objects.filter(
                product_code__in=has_night_products
            ).update(night_trading=True)
            
            # 更新无夜盘的品种
            updated_no_night = FullContractList.objects.filter(
                product_code__in=no_night_products
            ).update(night_trading=False)
            
            # 统计未匹配的品种（数据库中存在的品种但 TqSDK 未返回）
            all_db_products = set(FullContractList.objects.values_list('product_code', flat=True).distinct())
            matched_products = has_night_products | no_night_products
            unmatched_products = all_db_products - matched_products
            
            if unmatched_products:
                print(f"[WARN] 以下品种在数据库中但未从 TqSDK 获取到夜盘状态: {unmatched_products}")
                print(f"[WARN] 这些品种的 night_trading 字段保持不变")
        
        print(f"[SUCCESS] 数据库更新完成:")
        print(f"  - 更新有夜盘品种: {updated_has_night} 条记录")
        print(f"  - 更新无夜盘品种: {updated_no_night} 条记录")
        print(f"  - 未匹配品种: {len(unmatched_products)} 个")
        print("[INFO] ========== 夜盘交易状态同步完成 ==========\n")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 同步夜盘交易状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 确保 TqApi 连接被关闭
        if api:
            api.close()
            print("[INFO] TqApi 连接已关闭")
