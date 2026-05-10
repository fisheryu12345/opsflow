"""
Contract list synchronization from TqSDK.
"""
from django.db import transaction
from decimal import Decimal
import traceback
import math
from stock.models import TradingAccount, PositionState, FullContractList, AccountContractConfig, KlineData


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

                # 尝试获取实际主力合约代码（而非连续合约代码）
                actual_contract = instrument_id
                if '888' in instrument_id or instrument_id == f"{exchange_id}.{product_id}":
                    if quote.underlying_symbol:
                        actual_contract = quote.underlying_symbol
                        print(f"    [INFO] 通过 underlying_symbol 解析实际合约: {instrument_id} → {actual_contract}")
                    else:
                        print(f"    [WARN] {instrument_id} 是连续合约代码，未能解析实际合约")

                # 去掉交易所前缀，只保留合约代码（如 CFFEX.IC2606 → IC2606）
                # TqSDK 可能返回带交易所前缀的代码（如 CFFEX.IC2606），去掉前缀只保留合约代码
                if actual_contract and '.' in actual_contract:
                    actual_contract = actual_contract.split('.', 1)[1]

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

                print(f"  [OK] {actual_contract} | 品种: {product_id} | 乘数: {volume_multiple} | Tick: {price_tick} | 夜盘: {'有' if has_night else '无'} | 分类: {category_from_api}")

                with transaction.atomic():
                    old_obj = FullContractList.objects.filter(
                        exchange=exchange_id,
                        product_code=product_id
                    ).first()

                    obj, created = FullContractList.objects.update_or_create(
                        exchange=exchange_id,
                        product_code=product_id,
                        defaults={
                            'symbol': actual_contract,
                            'name': instrument_name,
                            'volume_multiple': int(volume_multiple),
                            'price_tick': Decimal(str(price_tick)),
                            'min_position': min_position,
                            'category': category_from_api,
                            'night_trading': has_night,
                        }
                    )

                    if created:
                        _ensure_position_states(actual_contract, product_id)
                        synced_count += 1
                        print(f"    [ADD] 新增记录: {actual_contract}")
                    else:
                        if old_obj and obj.symbol != old_obj.symbol:
                            updated_rows = PositionState.objects.filter(
                                product_code=product_id,
                                units__gt=0
                            ).update(is_rollover_needed=True)

                            PositionState.objects.filter(
                                product_code=product_id,
                                units=0
                            ).update(symbol=actual_contract)

                            if updated_rows > 0:
                                print(f"    [INFO] 已标记 {updated_rows} 条持仓记录需要移仓")

                            updated_count += 1
                            print(f"    [UPDATE] 主力合约变更: {old_obj.symbol} -> {actual_contract}")
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


def sync_kline_data_from_tqsdk(api, product_codes=None):
    """
    使用 TqSDK 获取日K线数据并同步到 KlineData 表。

    TqSDK 连续合约 K 线使用 KQ.m@{exchange}.{product_code} 查询。
    instrument_id 可能是连续合约代码（如 rb888）或直接可用的合约代码。
    """
    import pandas as pd

    print("[INFO] 开始同步K线数据...")

    contracts = FullContractList.objects.all()
    if product_codes:
        contracts = contracts.filter(product_code__in=product_codes)

    total_count = contracts.count()
    success_count = 0
    fail_count = 0
    bar_count = 0

    print(f"[INFO] 共 {total_count} 个合约需要同步K线")

    # 直接用 FullContractList 的 exchange+product_code 构造 KQ.m@ 格式查询标识
    # 这是 TqSDK 标准连续合约 K 线查询方式，无需依赖 query_cont_quotes

    for idx, contract in enumerate(contracts, 1):
        product_code = contract.product_code
        exchange = contract.exchange
        contract_symbol = contract.symbol  # 数据库已无污染数据，symbol 不带交易所前缀

        # TqSDK 查询使用连续合约标识
        query_key = f"KQ.m@{exchange}.{product_code}"
        # 数据库存储使用实际合约代码
        store_symbol = contract_symbol

        try:
            latest = KlineData.objects.filter(symbol=store_symbol).order_by('-date').first()

            if latest:
                data_length = 20
                print(f"  [{idx}/{total_count}] {store_symbol}: 增量同步（已有数据至 {latest.date}）")
            else:
                data_length = 500
                print(f"  [{idx}/{total_count}] {store_symbol}: 全量同步（无历史数据，拉取 {data_length} 根）")

            klines = api.get_kline_serial(query_key, duration_seconds=86400, data_length=data_length)

            if klines is None or len(klines) == 0:
                print(f"    [SKIP] {query_key} → {store_symbol}: 未获取到K线数据")
                fail_count += 1
                continue

            # 查询已有日期，避免逐条 update_or_create
            existing_dates = set(
                KlineData.objects.filter(symbol=store_symbol)
                .values_list('date', flat=True)
            )

            new_records = []
            for row_idx, kline in klines.iterrows():
                try:
                    dt = kline.get('datetime')
                    if dt is None:
                        continue

                    # 纳秒时间戳 → date
                    kline_date = pd.Timestamp(dt).date()

                    if kline_date in existing_dates:
                        continue

                    open_val = float(kline.get('open', 0))
                    high_val = float(kline.get('high', 0))
                    low_val = float(kline.get('low', 0))
                    close_val = float(kline.get('close', 0))
                    volume_val = int(kline.get('volume', 0))

                    # 跳过包含 NaN 的行（不活跃合约或无交易日期）
                    if math.isnan(open_val) or math.isnan(high_val) or math.isnan(low_val) or math.isnan(close_val):
                        continue

                    oi_val = kline.get('open_interest')
                    if oi_val is not None:
                        oi_val = int(oi_val)

                    new_records.append(KlineData(
                        symbol=store_symbol,
                        product_code=product_code,
                        exchange=exchange,
                        date=kline_date,
                        open=Decimal(str(open_val)),
                        high=Decimal(str(high_val)),
                        low=Decimal(str(low_val)),
                        close=Decimal(str(close_val)),
                        volume=volume_val,
                        open_interest=oi_val,
                    ))
                except Exception as row_error:
                    print(f"    [WARN] {store_symbol} 第{row_idx}行处理失败: {row_error}")
                    continue

            if new_records:
                KlineData.objects.bulk_create(new_records, ignore_conflicts=True)

            saved = len(new_records)

            bar_count += saved
            success_count += 1
            print(f"    [OK] 新增 {saved} 条记录")

        except Exception as e:
            fail_count += 1
            err_msg = str(e)
            if 'non-existent instrument' in err_msg or 'contains non-existent' in err_msg:
                print(f"  [WARN] {query_key}: 无效合约代码，跳过（TqSDK 不识别此合约）")
            else:
                print(f"  [ERROR] {query_key} → {store_symbol}: 同步失败: {e}")
                traceback.print_exc()
            continue

    print(f"\n{'='*60}")
    print(f"[STATS] K线同步完成统计:")
    print(f"  [OK] 成功合约: {success_count}")
    print(f"  [FAIL] 失败合约: {fail_count}")
    print(f"  [BARS] 新增K线: {bar_count}")
    print(f"{'='*60}")

    return {
        'success': success_count,
        'failed': fail_count,
        'bars': bar_count,
    }
