"""
Contract list synchronization from TqSDK.
"""
from django.db import transaction
from decimal import Decimal
import traceback
from stock.models import TradingAccount, PositionState, FullContractList, AccountContractConfig


def _ensure_position_states(symbol, product_code):
    """
    为所有已激活该品种的账户创建/更新 PositionState。
    多用户场景下，每个激活了此品种的账户都需要有对应的持仓状态记录。
    """
    configs = AccountContractConfig.objects.filter(
        product_code=product_code, is_active=True
    ).select_related('account')
    for cfg in configs:
        PositionState.objects.get_or_create(
            account=cfg.account,
            symbol=symbol,
            defaults={'product_code': product_code}
        )


def sync_contract_list_from_tqsdk(api=None):
    """
    使用 TqSDK 获取所有期货合约信息并同步到 FullContractList 表。
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

        for cont_symbol in cont_quotes:
            try:
                print(f"\n[CHECK] 处理主力合约: {cont_symbol}")
                quote = api.get_quote(cont_symbol)
                instrument_id = quote.instrument_id
                product_id = quote.product_id
                exchange_id = quote.exchange_id
                instrument_name = quote.instrument_name

                volume_multiple = getattr(quote, 'volume_multiple', 10)
                price_tick = getattr(quote, 'price_tick', 1.0)

                if not volume_multiple or volume_multiple <= 0:
                    volume_multiple = 10
                if not price_tick or price_tick <= 0:
                    price_tick = 1.0

                trading_time = getattr(quote, 'trading_time', {})
                has_night = bool(trading_time.get('night', []))
                categories_list = getattr(quote, 'categories', [])
                category_from_api = None
                if categories_list and isinstance(categories_list, list) and len(categories_list) > 0:
                    category_from_api = categories_list[0].get('name') if isinstance(categories_list[0], dict) else None
                min_position = quote.open_min_market_order_volume

                print(f"  [OK] {instrument_id} | 品种: {product_id} | 乘数: {volume_multiple} | Tick: {price_tick} | 夜盘: {'有' if has_night else '无'} | 分类: {category_from_api}")

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
                            'night_trading': has_night,
                        }
                    )

                    if created:
                        _ensure_position_states(instrument_id, product_id)
                        synced_count += 1
                        print(f"    [ADD] 新增记录: {instrument_id}")
                    else:
                        if old_obj and obj.symbol != old_obj.symbol:
                            updated_rows = PositionState.objects.filter(
                                product_code=product_id,
                                units__gt=0
                            ).update(is_rollover_needed=True)

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
        traceback.print_exc()
        return {
            'synced': 0,
            'updated': 0,
            'skipped': 0,
            'error': str(e)
        }
