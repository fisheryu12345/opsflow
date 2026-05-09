"""
Signal execution — order placement functions for entry, add-on, exit, and rollover.
"""
import time
import traceback
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from tqsdk import TargetPosTask
from stock.models import TradingAccount, PositionState, DailyStrategySignal, ClosedPositionRecord, FullContractList
from stock.utils.log_util import log_trade, log_error
from stock.core.config_loader import get_config
from stock.infrastructure.tqapi import is_api_connected

TIMEOUT_SECONDS = get_config('TIMEOUT_SECONDS')
POSITION_MAX_UNITS = get_config('POSITION_MAX_UNITS')
GAP_PROTECTION_RATIO = get_config('GAP_PROTECTION_RATIO')
from stock.core.atr import price_gap_protection, calculate_atr
from stock.core.position_sizing import calculate_unit_lots
from stock.infrastructure.order_execution import (
    wait_for_target_position,
    check_min_position_requirement,
    execute_two_step_opening,
    record_and_reset_position,
)


def is_trading(api, account, signal):
    ts = api.get_trading_status(signal.symbol)
    if ts.trade_status == 'NOTRADING':
        msg = f"{signal.symbol} 不在交易时间"
        print(msg)
        log_trade('is_trading checking', msg, symbol=signal.symbol, log_level='INFO')
        return False
    return True


def execute_add_on_order(api, account, signal):
    if not is_trading(api, account, signal):
        return False

    add_units_from_signal = signal.contract_target_number
    msg = f"{signal.symbol} 从信号获取加仓单位数: {add_units_from_signal} Unit"
    print(msg)
    log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='INFO')

    position = PositionState.objects.get(
        account=account,
        symbol=signal.symbol,
    )

    projected_units = position.units + add_units_from_signal
    if projected_units > POSITION_MAX_UNITS:
        msg = (f"{signal.symbol} 加仓后将超限: 当前{position.units} Unit + 加仓 {add_units_from_signal} Unit = "
               f"{projected_units} Unit > 最大 {POSITION_MAX_UNITS} Unit")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='WARNING')
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False

    unit_lots = calculate_unit_lots(api, signal.symbol)
    order_volume = add_units_from_signal * unit_lots

    msg = f"{signal.symbol} 加仓计划: {add_units_from_signal} Unit × {unit_lots} 手/Unit = {order_volume} 手"
    print(msg)
    log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='INFO')

    min_position_check = check_min_position_requirement(signal.symbol, order_volume)

    if min_position_check['need_adjustment']:
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']
        msg = f"{signal.symbol} 采用两步开仓策略: 先开 {adjusted_volume} 手，再平 {excess_to_close} 手"
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='INFO')

        two_step_result = execute_two_step_opening(
            api=api,
            symbol=signal.symbol,
            direction=position.direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=order_volume,
            function_name='execute_add_on_order',
            account=account,
            signal=signal
        )

        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

        with transaction.atomic():
            new_units = position.units + add_units_from_signal
            new_total_lots = position.contract_total_position + order_volume

            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                last_add_price=Decimal(str(two_step_result['avg_price'])),
                latest_close_price=Decimal(str(two_step_result['avg_price'])),
                last_update_time=timezone.now()
            )

        signal.executed_status = 'SUCCESS'
        signal.save(update_fields=['executed_status', 'updated_at'])

        msg = (f"{signal.symbol} 加仓成功（两步开仓）: +{unit_lots} Unit ({order_volume}手) @ "
               f"{two_step_result['avg_price']:.2f}, 总持仓:{new_units} Unit")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='SUCCESS')
        return True

    else:
        target_pos = TargetPosTask(api, signal.symbol)
        try:
            if position.direction == 1:
                target_lots = position.contract_total_position + order_volume
            else:
                target_lots = -(position.contract_total_position + order_volume)

            msg = f"{signal.symbol} 设置目标持仓: {target_lots} 手 (当前 {position.contract_total_position} 手 + 加仓 {order_volume} 手)"
            print(msg)
            log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='INFO')

            target_pos.set_target_volume(target_lots)

            result = wait_for_target_position(
                api=api,
                target_pos=target_pos,
                symbol=signal.symbol,
                target_lots=target_lots,
                function_name='execute_add_on_order'
            )

            if not result['success']:
                msg = f"[ERROR] {signal.symbol} 加仓超时或失败"
                print(msg)
                log_error('execute_add_on_order', msg)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False

            quote = api.get_quote(signal.symbol)
            avg_price = float(quote.last_price) if quote and quote.last_price else None

            with transaction.atomic():
                new_units = position.units + add_units_from_signal
                new_total_lots = position.contract_total_position + order_volume

                PositionState.objects.filter(id=position.id).update(
                    units=new_units,
                    contract_total_position=new_total_lots,
                    last_add_price=Decimal(str(avg_price)),
                    latest_close_price=Decimal(str(avg_price)),
                    last_update_time=timezone.now()
                )

            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

            msg = f"{signal.symbol} 加仓成功: +{unit_lots} Unit({order_volume}手) @ {avg_price:.2f}, 总持仓:{new_units} Unit"
            print(msg)
            log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='SUCCESS')
            return True

        except Exception as e:
            msg = f"[ERROR] 加仓失败 {signal.symbol}: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_add_on_order', f"{msg}\n{traceback.format_exc()}")
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False
        finally:
            try:
                del target_pos
            except Exception:
                pass


def execute_entry_order(api, account, signal, gap_threshold_atr_multiplier=GAP_PROTECTION_RATIO):
    if not is_trading(api, account, signal):
        return False

    unit_lots = calculate_unit_lots(api, signal.symbol)
    target_units = 1
    order_volume = target_units * unit_lots
    print(f"[INFO] {signal.symbol} 开仓计划: 1个Unit × {unit_lots}手/Unit = {order_volume}手")

    can_trade = price_gap_protection(
        api=api,
        symbol=signal.symbol,
        direction=signal.signal_direction,
        gap_threshold_atr_multiplier=gap_threshold_atr_multiplier
    )
    if not can_trade:
        msg = f"{signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        log_trade('execute_entry_order', msg, signal=signal.symbol, log_level='WARNING')
        signal.executed_status = 'CANCELLED'
        signal.remark = '跳空保护'
        signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
        return False

    min_position_check = check_min_position_requirement(signal.symbol, order_volume)

    if min_position_check['need_adjustment']:
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']

        msg = f"{signal.symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='INFO')

        two_step_result = execute_two_step_opening(
            api=api,
            symbol=signal.symbol,
            direction=signal.signal_direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=order_volume,
            function_name='execute_entry_order',
            account=account,
            signal=signal
        )

        if not two_step_result['success']:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

        with transaction.atomic():
            PositionState.objects.update_or_create(
                account=account,
                symbol=signal.symbol,
                defaults={
                    'product_code': signal.product_code,
                    'direction': signal.signal_direction,
                    'units': 1,
                    'contract_total_position': two_step_result['actual_filled'],
                    'last_add_price': Decimal(str(two_step_result['avg_price'])),
                    'first_open_price': Decimal(str(two_step_result['avg_price'])),
                    'highest_close': Decimal(str(two_step_result['avg_price'])),
                    'lowest_close': Decimal(str(two_step_result['avg_price'])),
                    'latest_close_price': Decimal(str(two_step_result['avg_price'])),
                    'last_update_time': timezone.now(),
                }
            )

            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

        msg = f"{signal.symbol} 开仓成功（两步开仓）: 1 Unit({two_step_result['actual_filled']}手) @ {two_step_result['avg_price']:.2f}"
        print(msg)
        log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='SUCCESS')
        return True

    else:
        target_pos = TargetPosTask(api, signal.symbol)
        try:
            if signal.signal_direction == 1:
                target_lots = order_volume
            else:
                target_lots = -order_volume
            msg = f"{signal.symbol} 设置目标持仓: {target_lots} 手 (开仓{target_units} Unit)"
            print(msg)
            log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='INFO')
            target_pos.set_target_volume(target_lots)

            result = wait_for_target_position(
                api=api,
                target_pos=target_pos,
                symbol=signal.symbol,
                target_lots=target_lots,
                function_name='execute_entry_order'
            )

            if not result['success']:
                msg = f"[ERROR] {signal.symbol} 开仓超时或失败"
                print(msg)
                log_error('execute_entry_order', msg)
                signal.executed_status = 'FAILED'
                signal.remark = '开仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
                return False

            pos_after = result['pos']
            if pos_after is None:
                pos_after = api.get_position(signal.symbol)

            if pos_after is None:
                msg = f"[ERROR] {signal.symbol} 获取持仓信息失败"
                print(msg)
                log_error('execute_entry_order', msg)
                signal.executed_status = 'FAILED'
                signal.remark = '获取持仓信息失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
            else:
                if signal.signal_direction == 1:
                    entry_avg_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else None
                    actual_filled = pos_after.volume_long_today
                else:
                    entry_avg_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else None
                    actual_filled = pos_after.volume_short_today
                with transaction.atomic():
                    PositionState.objects.update_or_create(
                        account=account,
                        symbol=signal.symbol,
                        defaults={
                            'product_code': signal.product_code,
                            'direction': signal.signal_direction,
                            'units': 1,
                            'contract_total_position': actual_filled,
                            'last_add_price': Decimal(str(entry_avg_price)),
                            'highest_close': Decimal(str(entry_avg_price)),
                            'lowest_close': Decimal(str(entry_avg_price)),
                            'latest_close_price': Decimal(str(entry_avg_price)),
                            'last_update_time': timezone.now(),
                            'open_date': timezone.now().date(),
                            'first_open_price': Decimal(str(entry_avg_price)),
                        }
                    )

                    signal.executed_status = 'SUCCESS'
                    signal.save(update_fields=['executed_status', 'updated_at'])

                msg = f"{signal.symbol} 开仓成功: 1 Unit({actual_filled}手) @ {entry_avg_price:.2f}"
                print(msg)
                log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='SUCCESS')
                return True

        except Exception as e:
            msg = f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_entry_order', f"{msg}\n{traceback.format_exc()}")
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False
        finally:
            try:
                del target_pos
            except Exception:
                pass


def execute_exit_order(api, position, signal):
    if not is_trading(api, position.account, signal):
        return False
    total_volume = position.contract_total_position
    target_pos = TargetPosTask(api, position.symbol)
    try:
        msg = f"{position.symbol} 设置目标持仓: 0手 (平仓{total_volume} 手)"
        print(msg)
        log_trade('execute_exit_order', msg, symbol=position.symbol, log_level='INFO')
        target_pos.set_target_volume(0)

        result = wait_for_target_position(
            api=api,
            target_pos=target_pos,
            symbol=position.symbol,
            target_lots=0,
            function_name='execute_exit_order'
        )

        if not result['success']:
            msg = f"[ERROR] {position.symbol} 平仓超时或失败"
            print(msg)
            log_error('execute_exit_order', msg)
            if signal:
                signal.executed_status = 'FAILED'
                signal.remark = '平仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
            return False

        quote = api.get_quote(position.symbol)
        exit_price = float(quote.last_price) if quote and quote.last_price else None

        record_and_reset_position(api, position, signal, total_volume, exit_price)

        if signal:
            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

        msg = f"{position.symbol} 平仓成功"
        print(msg)
        log_trade('execute_exit_order', msg, symbol=position.symbol, log_level='SUCCESS')
        return True

    except Exception as e:
        msg = f"[ERROR] 平仓失败 {position.symbol}: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_exit_order', f"{msg}\n{traceback.format_exc()}")
        if signal:
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
        return False
    finally:
        try:
            del target_pos
        except Exception:
            pass


def execute_rollover_order(api, position, signal):
    if not is_trading(api, position.account, signal):
        return False

    # ===== Phase 1: Close old contract =====
    msg = f"{position.symbol} 开始平仓旧合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO')

    target_pos_old = TargetPosTask(api, position.symbol)
    try:
        target_pos_old.set_target_volume(0)
        result = wait_for_target_position(
            api=api,
            target_pos=target_pos_old,
            symbol=position.symbol,
            target_lots=0,
            function_name='execute_rollover_order'
        )

        if not result['success']:
            msg = f"[ERROR] {position.symbol} 移仓操作中，平仓旧合约失败"
            print(msg)
            log_error('execute_rollover_order', msg)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

    except Exception as e:
        msg = f"[ERROR] {position.symbol} 平仓失败: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    finally:
        try:
            del target_pos_old
        except Exception:
            pass

    # ===== Phase 2: Open new contract =====
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
            log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
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
                log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
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
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}")
        try:
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
        except Exception:
            pass
        return False

def process_signals_by_type(api, account, trade_type):
    from django.db.models import Q

    type_config = {
        'ENTRY': {
            'query_filter': Q(trade_type='ENTRY'),
            'executor': execute_entry_order,
            'executor_args': ['api', 'account', 'signal'],
            'success_msg': lambda signal: f"✅ 开仓成功: {signal.symbol}",
            'fail_msg': lambda signal: f"❌ 开仓失败: {signal.symbol}",
            'need_position': False
        },
        'STOP_LOSS': {
            'query_filter': Q(trade_type='STOP_LOSS'),
            'executor': execute_exit_order,
            'executor_args': ['api', 'position', 'signal'],
            'success_msg': lambda position: f"✅ 平仓成功: {position.symbol}",
            'fail_msg': lambda position: f"❌ 平仓失败: {position.symbol}",
            'need_position': True,
            'position_filter': lambda account: PositionState.objects.filter(account=account, units__gt=0)
        },
        'ROLLOVER': {
            'query_filter': Q(trade_type='ROLLOVER'),
            'executor': execute_rollover_order,
            'executor_args': ['api', 'position', 'signal'],
            'success_msg': lambda position, signal: f"✅ 移仓成功: {position.symbol} -> {signal.symbol}",
            'fail_msg': lambda position, signal: f"❌ 移仓失败: {position.symbol} -> {signal.symbol}",
            'need_position': True,
            'position_filter': lambda account, symbol: PositionState.objects.get(account=account, symbol=symbol, units__gt=0)
        },
        'ADD_ON': {
            'query_filter': Q(trade_type='ADD_ON'),
            'executor': execute_add_on_order,
            'executor_args': ['api', 'account', 'signal'],
            'success_msg': lambda signal: f"✅ 加仓成功: {signal.symbol}",
            'fail_msg': lambda signal: f"❌ 加仓失败: {signal.symbol}",
            'need_position': False
        }
    }

    config = type_config.get(trade_type)
    if not config:
        print(f"[ERROR] 不支持的交易类型: {trade_type}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    # API 连接检查：如果连接已断开，跳过本批次处理并记录日志
    if not is_api_connected(api):
        log_error('process_signals_by_type',
                   f"API连接已断开，跳过{trade_type}处理")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    signals = DailyStrategySignal.objects.filter(
        config['query_filter'], account=account, executed_status='PENDING'
    )

    success_count = 0
    failed_count = 0
    skipped_count = 0

    if config['need_position']:
        if trade_type == 'STOP_LOSS':
            positions = config['position_filter'](account)
            for position in positions:
                exit_signals = DailyStrategySignal.objects.filter(
                    Q(symbol=position.symbol) & config['query_filter'],
                    account=account
                )
                for signal in exit_signals:
                    try:
                        success = config['executor'](api, position, signal)
                        if success:
                            print(config['success_msg'](position))
                            success_count += 1
                        else:
                            print(config['fail_msg'](position))
                            failed_count += 1
                    except Exception as e:
                        print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                        failed_count += 1

        elif trade_type == 'ROLLOVER':
            for signal in signals:
                try:
                    position = config['position_filter'](account, signal.symbol)
                    success = config['executor'](api, position, signal)
                    if success:
                        print(config['success_msg'](position, signal))
                        success_count += 1
                    else:
                        print(config['fail_msg'](position, signal))
                        failed_count += 1
                except PositionState.DoesNotExist:
                    print(f"⚠️ 移仓信号未找到对应持仓: {signal.symbol}")
                    skipped_count += 1
                except Exception as e:
                    print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                    failed_count += 1
    else:
        for signal in signals:
            try:
                success = config['executor'](api, account, signal)
                if success:
                    print(config['success_msg'](signal))
                    success_count += 1
                else:
                    print(config['fail_msg'](signal))
                    failed_count += 1
            except Exception as e:
                print(f"[ERROR] 处理{trade_type}信号异常: {str(e)}")
                failed_count += 1

    return {'success': success_count, 'failed': failed_count, 'skipped': skipped_count}
