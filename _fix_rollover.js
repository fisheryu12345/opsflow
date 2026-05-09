const fs = require('fs');
const content = fs.readFileSync('backend/stock/infrastructure/order_signals.py', 'utf8');

// Find the Phase 2 start and replace everything after it through the end of the function
const phase2Marker = `    # ===== Phase 2: Open new contract =====`;

// Find the old Phase 2 through end of function
const idx = content.indexOf(phase2Marker);
if (idx === -1) { console.log('ERROR: Phase 2 marker not found'); process.exit(1); }

// Find the next function definition after this point (to know where execute_rollover_order ends)
const rest = content.substring(idx);

// The function ends at the next "def " or the end of the pattern we know — let's find the next "def " after idx
const nextDefIdx = content.indexOf('\ndef ', idx);
if (nextDefIdx === -1) { console.log('ERROR: Next function not found'); process.exit(1); }

const currentEnd = nextDefIdx + 1; // +1 to keep the newline
const oldBlock = content.substring(idx, currentEnd);

const newBlock = `    # ===== Phase 2: Open new contract =====
    # 从 FullContractList 获取新主力合约代码（signal.symbol 存的是旧合约代码）
    main_contract = FullContractList.objects.filter(
        product_code=position.product_code
    ).first()
    if not main_contract:
        msg = f"[ERROR] {position.product_code} 无法获取新主力合约信息"
        print(msg)
        log_error('execute_rollover_order', msg)
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    new_symbol = main_contract.symbol

    msg = f"{new_symbol} 开始开仓新合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO')

    target_volume = position.contract_total_position
    min_position_check = check_min_position_requirement(new_symbol, target_volume)

    if min_position_check['need_adjustment']:
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']

        msg = f"{new_symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO')

        two_step_result = execute_two_step_opening(
            api=api,
            symbol=new_symbol,
            direction=position.direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=target_volume,
            function_name='execute_rollover_order',
            account=position.account,
            signal=signal
        )

        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

        entry_avg_price = two_step_result['avg_price']
        actual_filled = two_step_result['actual_filled']

        msg = f"{new_symbol} 换月开仓成功（两步开仓）: {actual_filled}手 @ {entry_avg_price:.2f}"
        print(msg)
        log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO')

    else:
        target_pos_new = TargetPosTask(api, new_symbol)
        try:
            if position.direction == 1:
                target_lots = target_volume
            else:
                target_lots = -target_volume

            msg = f"{new_symbol} 设置目标持仓: {target_lots}手"
            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO')
            target_pos_new.set_target_volume(target_lots)

            result = wait_for_target_position(
                api=api,
                target_pos=target_pos_new,
                symbol=new_symbol,
                target_lots=target_lots,
                function_name='execute_rollover_order'
            )

            pos_after = result['pos']
            if not result['success']:
                msg = f"[ERROR] {new_symbol} 移仓操作中，开仓新合约失败"
                print(msg)
                log_error('execute_rollover_order', msg)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False

            if signal.signal_direction == 1:
                entry_avg_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else None
                actual_filled = pos_after.volume_long_today
            else:
                entry_avg_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else None
                actual_filled = pos_after.volume_short_today

            msg = f"{new_symbol} 换月开仓成功: {actual_filled}手 @ {entry_avg_price:.2f}"
            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO')

        except Exception as e:
            msg = f"[ERROR] {new_symbol} 移仓操作中，开仓失败: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_rollover_order', f"{msg}\\n{traceback.format_exc()}")
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False
        finally:
            try:
                del target_pos_new
            except Exception:
                pass

    # ===== Phase 3: Update database =====
    try:
        with transaction.atomic():
            try:
                klines = api.get_kline_serial(new_symbol, duration_seconds=86400, data_length=25)
                if klines is not None and len(klines) >= 20:
                    historical_high = float(klines['close'].rolling(window=20).max().iloc[-1])
                    historical_low = float(klines['close'].rolling(window=20).min().iloc[-1])
                    atr_value = calculate_atr(api, new_symbol, period=20)

                    if position.direction == 1:
                        init_highest_close = Decimal(str(historical_high))
                        init_lowest_close = None
                        init_stop_loss = init_highest_close - Decimal('2') * Decimal(str(atr_value)) if atr_value else None
                    else:
                        init_highest_close = None
                        init_lowest_close = Decimal(str(historical_low))
                        init_stop_loss = init_lowest_close + Decimal('2') * Decimal(str(atr_value)) if atr_value else None

                    msg = (f"{new_symbol} 基于20日历史数据初始化: highest={historical_high:.2f}, "
                           f"lowest={historical_low:.2f}, ATR={atr_value:.2f}")
                    print(msg)
                    log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO')
                else:
                    msg = f"{new_symbol} 历史数据不足({len(klines) if klines else 0}根)，使用开仓价初始化"
                    print(msg)
                    log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='WARNING')
                    init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                    init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                    init_stop_loss = None
            except Exception as hist_e:
                msg = f"[WARN] {new_symbol} 计算历史数据失败: {str(hist_e)}，使用开仓价初始化"
                print(msg)
                traceback.print_exc()
                log_error('execute_rollover_order', f"{msg}\\n{traceback.format_exc()}")
                init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
                init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
                init_stop_loss = None

            PositionState.objects.update_or_create(
                account=position.account,
                symbol=new_symbol,
                defaults={
                    'product_code': signal.product_code,
                    'direction': position.direction,
                    'units': position.units,
                    'contract_total_position': actual_filled,
                    'last_add_price': Decimal(str(entry_avg_price)),
                    'highest_close': init_highest_close,
                    'lowest_close': init_lowest_close,
                    'latest_close_price': Decimal(str(entry_avg_price)),
                    'last_update_time': timezone.now(),
                    'stop_loss_price': init_stop_loss,
                    'is_rollover_needed': False,
                }
            )
            PositionState.objects.filter(id=position.id).delete()
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

        return True

    except Exception as e:
        msg = f"[ERROR] {new_symbol} 移仓操作中，数据库更新失败: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\\n{traceback.format_exc()}")
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except Exception:
            pass
        return False

`;

const newContent = content.substring(0, idx) + newBlock + content.substring(nextDefIdx + 1);
fs.writeFileSync('backend/stock/infrastructure/order_signals.py', newContent, 'utf8');
console.log('order_signals.py updated successfully');
