"""
Contract list synchronization from TqSDK.
"""
from django.db import transaction
from decimal import Decimal
import traceback
import math
from stock.models import TradingAccount, PositionState, FullContractList, AccountContractConfig, KlineData
from stock.core.indicators import compute_batch_kline_indicators


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

                # 获取实际合约代码（带交易所前缀，如 SHFE.rb2510）
                actual_contract = instrument_id
                if '888' in instrument_id or instrument_id == f"{exchange_id}.{product_id}":
                    if quote.underlying_symbol:
                        actual_contract = quote.underlying_symbol
                        # TqSDK underlying_symbol 返回裸合约代码（如 rb2510），补上交易所前缀
                        if actual_contract and '.' not in actual_contract:
                            actual_contract = f"{exchange_id}.{actual_contract}"
                        print(f"    [INFO] 通过 underlying_symbol 解析实际合约: {instrument_id} → {actual_contract}")
                    else:
                        print(f"    [WARN] {instrument_id} 是连续合约代码，未能解析实际合约")

                # 统一确保带交易所前缀
                if actual_contract and '.' not in actual_contract:
                    actual_contract = f"{exchange_id}.{actual_contract}"
                    print(f"    [INFO] 补上交易所前缀: → {actual_contract}")

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
                            ).update(symbol=actual_contract, is_rollover_needed=False)

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

    for idx, contract in enumerate(contracts, 1):
        product_code = contract.product_code
        exchange = contract.exchange
        query_key = contract.symbol  # 使用实际合约代码（如 SHFE.rb2510），与指标计算一致

        try:
            latest = KlineData.objects.filter(symbol=query_key).order_by('-date').first()

            if latest:
                data_length = 20
                print(f"  [{idx}/{total_count}] {query_key}: 增量同步（已有数据至 {latest.date}）")
            else:
                data_length = 500
                print(f"  [{idx}/{total_count}] {query_key}: 全量同步（无历史数据，拉取 {data_length} 根）")

            klines = api.get_kline_serial(query_key, duration_seconds=86400, data_length=data_length)

            if klines is None or len(klines) == 0:
                print(f"    [SKIP] {query_key} → {query_key}: 未获取到K线数据")
                fail_count += 1
                continue

            # 查询已有日期，避免逐条 update_or_create
            existing_dates = set(
                KlineData.objects.filter(symbol=query_key)
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
                        symbol=query_key,
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
                    print(f"    [WARN] {query_key} 第{row_idx}行处理失败: {row_error}")
                    continue

            if new_records:
                KlineData.objects.bulk_create(new_records, ignore_conflicts=True)

            saved = len(new_records)

            # 报价数据 enrichment：用 get_quote() 获取结算价、涨跌停板等
            # 注意：get_quote() 返回的是当前值，仅对最新一根 K 线准确
            try:
                quote = api.get_quote(query_key)
                if quote is not None:
                    latest_bar = KlineData.objects.filter(symbol=query_key).order_by('-date').first()
                    if latest_bar:
                        update_fields = []
                        settlement = getattr(quote, 'settlement', None)
                        if settlement is not None:
                            latest_bar.settlement = Decimal(str(settlement))
                            update_fields.append('settlement')

                        pre_close = getattr(quote, 'pre_close', None)
                        if pre_close is not None:
                            latest_bar.pre_close = Decimal(str(pre_close))
                            update_fields.append('pre_close')

                        pre_settlement = getattr(quote, 'pre_settlement', None)
                        if pre_settlement is not None:
                            latest_bar.pre_settlement = Decimal(str(pre_settlement))
                            update_fields.append('pre_settlement')

                        upper_limit = getattr(quote, 'upper_limit', None)
                        if upper_limit is not None:
                            latest_bar.upper_limit = Decimal(str(upper_limit))
                            update_fields.append('upper_limit')

                        lower_limit = getattr(quote, 'lower_limit', None)
                        if lower_limit is not None:
                            latest_bar.lower_limit = Decimal(str(lower_limit))
                            update_fields.append('lower_limit')

                        average = getattr(quote, 'average', None)
                        if average is not None:
                            latest_bar.average_price = Decimal(str(average))
                            update_fields.append('average_price')

                        close_oi = getattr(quote, 'close_oi', None)
                        if close_oi is not None:
                            try:
                                latest_bar.close_oi = int(close_oi)
                                update_fields.append('close_oi')
                            except (ValueError, TypeError):
                                pass

                        turnover = getattr(quote, 'turnover', None)
                        if turnover is not None:
                            latest_bar.turnover = Decimal(str(turnover))
                            update_fields.append('turnover')

                        if update_fields:
                            latest_bar.save(update_fields=update_fields)
                            print(f"    [ENRICH] 报价数据已更新: {', '.join(update_fields)}")
            except Exception as quote_error:
                print(f"    [WARN] {query_key}: 获取报价数据失败: {quote_error}")

            # K线指标批量计算（Phase 2/3）：加载全部K线 → 计算指标 → bulk_update
            try:
                import pandas as pd
                all_klines = KlineData.objects.filter(symbol=query_key).order_by('date').values(
                    'id', 'date', 'open', 'high', 'low', 'close', 'volume',
                    'open_interest', 'upper_limit', 'lower_limit'
                )
                if len(all_klines) >= 20:
                    df = pd.DataFrame(all_klines)
                    # 数值列转 float
                    for col in ['open', 'high', 'low', 'close', 'volume', 'upper_limit', 'lower_limit']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    df2 = compute_batch_kline_indicators(df)

                    # 只更新有 id 的行
                    update_objs = []
                    indicator_fields = [
                        'atr_20', 'donchian_upper_20', 'donchian_lower_20',
                        'ma_10', 'ma_20', 'ma_40', 'trend_factor', 'trend_label', 'true_range',
                        'body_ratio', 'upper_shadow_ratio', 'lower_shadow_ratio', 'close_in_range',
                        'volume_ratio_20', 'gap_from_pre_close', 'hit_upper_limit', 'hit_lower_limit',
                    ]
                    for _, row in df2.iterrows():
                        if pd.isna(row.get('id')):
                            continue
                        obj = KlineData(id=int(row['id']))
                        for field in indicator_fields:
                            val = row.get(field)
                            if val is not None and not (isinstance(val, float) and (pd.isna(val) or pd.isinf(val))):
                                if field in ('hit_upper_limit', 'hit_lower_limit'):
                                    setattr(obj, field, bool(val))
                                elif field == 'trend_label':
                                    setattr(obj, field, str(val) if val else None)
                                else:
                                    setattr(obj, field, Decimal(str(val)))
                        update_objs.append(obj)

                    if update_objs:
                        KlineData.objects.bulk_update(
                            update_objs,
                            fields=indicator_fields,
                            batch_size=500
                        )
                        print(f"    [INDICATORS] 已更新 {len(update_objs)} 条K线指标")
            except Exception as ind_error:
                print(f"    [WARN] {query_key}: 计算K线指标失败: {ind_error}")
                traceback.print_exc()

            bar_count += saved
            success_count += 1
            print(f"    [OK] 新增 {saved} 条记录")

        except Exception as e:
            fail_count += 1
            err_msg = str(e)
            if 'non-existent instrument' in err_msg or 'contains non-existent' in err_msg:
                print(f"  [WARN] {query_key}: 无效合约代码，跳过（TqSDK 不识别此合约）")
            else:
                print(f"  [ERROR] {query_key} → {query_key}: 同步失败: {e}")
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
