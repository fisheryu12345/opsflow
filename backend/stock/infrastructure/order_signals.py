"""
Signal execution — order placement functions for entry, add-on, exit, and rollover.
"""
import time
import traceback
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from tqsdk import TargetPosTask
from stock.models import TradingAccount, PositionState, DailyStrategySignal, ClosedPositionRecord, FullContractList, StrategyConfig
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
from stock.infrastructure.slippage_recorder import record_slippage


def is_trading(api, account, signal):
    ts = api.get_trading_status(signal.symbol)
    if ts.trade_status == 'NOTRADING':
        msg = f"{signal.symbol} 不在交易时间"
        print(msg)
        log_trade('is_trading checking', msg, symbol=signal.symbol, log_level='INFO', account=account)
        return False
    return True


def execute_add_on_order(api, account, signal):
    if not is_trading(api, account, signal):
        return False

    add_units_from_signal = signal.contract_target_number
    msg = f"{signal.symbol} 从信号获取加仓单位数: {add_units_from_signal} Unit"
    print(msg)
    log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='INFO', account=account)

    try:
        position = PositionState.objects.get(
            account=account,
            symbol=signal.symbol,
        )
    except PositionState.DoesNotExist:
        # 移仓后旧合约持仓已被删除，按品种查找新合约持仓
        position = PositionState.objects.filter(
            account=account,
            product_code=signal.product_code,
            units__gt=0,
        ).exclude(direction=0).first()
        if position is None:
            log_error('execute_add_on_order',
                       f"{signal.symbol}({signal.product_code}) 未找到对应持仓，无法加仓", account=account,
                       notify=True)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False
        msg = (f"{signal.symbol} 旧合约已移仓，转至新合约 {position.symbol} 加仓: "
               f"{add_units_from_signal} Unit (当前{position.units} Unit)")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=position.symbol, log_level='INFO', account=account)

    projected_units = position.units + add_units_from_signal
    if projected_units > POSITION_MAX_UNITS:
        msg = (f"{signal.symbol} 加仓后将超限: 当前{position.units} Unit + 加仓 {add_units_from_signal} Unit = "
               f"{projected_units} Unit > 最大 {POSITION_MAX_UNITS} Unit")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=signal.symbol, log_level='WARNING', account=account)
        signal.executed_status = 'CANCELLED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False

    # 使用 position.symbol（可能因移仓回退而不同于 signal.symbol）
    trade_symbol = position.symbol

    unit_lots = calculate_unit_lots(api, trade_symbol)
    order_volume = add_units_from_signal * unit_lots

    msg = f"{trade_symbol} 加仓计划: {add_units_from_signal} Unit × {unit_lots} 手/Unit = {order_volume} 手"
    print(msg)
    log_trade('execute_add_on_order', msg, symbol=trade_symbol, log_level='INFO', account=account)

    min_position_check = check_min_position_requirement(trade_symbol, order_volume)

    if min_position_check['need_adjustment']:
        min_pos = min_position_check['min_position']
        adjusted_volume = position.contract_total_position + min_pos
        excess_to_close = min_position_check['excess_to_close']
        msg = (f"{trade_symbol} 采用两步开仓策略: 当前持仓{position.contract_total_position}手, "
               f"先开 {adjusted_volume} 手 (含最小开仓限制{min_pos}手)，再平 {excess_to_close} 手")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=trade_symbol, log_level='INFO', account=account)

        two_step_result = execute_two_step_opening(
            api=api,
            symbol=trade_symbol,
            direction=position.direction,
            adjusted_volume=adjusted_volume,
            excess_to_close=excess_to_close,
            target_volume=order_volume,
            function_name='execute_add_on_order',
            account=account,
            signal=signal
        )

        if not two_step_result['success']:
            signal.remark = (
                f"加仓失败: 计划{order_volume}手 < 最小开仓{min_pos}手, "
                f"两步开仓超时 (当前持仓{position.contract_total_position}手, 目标{adjusted_volume}手, "
                f"开仓增量{adjusted_volume - position.contract_total_position}手)"
            )
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'remark', 'updated_at'])
            return False

        with transaction.atomic():
            new_units = position.units + add_units_from_signal
            new_total_lots = position.contract_total_position + order_volume

            PositionState.objects.filter(id=position.id).update(
                units=new_units,
                contract_total_position=new_total_lots,
                latest_close_price=Decimal(str(two_step_result['avg_price'])),
            )

            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

        # 记录加仓滑点（两步开仓）
        try:
            add_signal_price = (signal.donchian_upper if signal.signal_direction == 1
                                else signal.donchian_lower) or position.first_open_price
            if add_signal_price and two_step_result.get('avg_price'):
                contract = FullContractList.objects.filter(symbol=trade_symbol).first()
                price_tick = contract.price_tick if contract else Decimal('1')
                record_slippage(
                    account=account,
                    trade_type='ADD_ON',
                    symbol=trade_symbol,
                    product_code=signal.product_code,
                    position_direction=position.direction,
                    volume=order_volume,
                    signal_price=add_signal_price,
                    fill_price=Decimal(str(two_step_result['avg_price'])),
                    price_tick=price_tick,
                    signal=signal,
                )
        except Exception as slip_err:
            log_error('execute_add_on_order',
                       f"{slip_err}\n{traceback.format_exc()}", account=account,
                       )

        msg = (f"{trade_symbol} 加仓成功（两步开仓）: +{unit_lots} Unit ({order_volume}手) @ "
               f"{two_step_result['avg_price']:.2f}, 总持仓:{new_units} Unit")
        print(msg)
        log_trade('execute_add_on_order', msg, symbol=trade_symbol, log_level='SUCCESS', account=account)
        return True

    else:
        target_pos = TargetPosTask(api, trade_symbol)
        try:
            if position.direction == 1:
                target_lots = position.contract_total_position + order_volume
            else:
                target_lots = -(position.contract_total_position + order_volume)

            msg = f"{trade_symbol} 设置目标持仓: {target_lots} 手 (当前 {position.contract_total_position} 手 + 加仓 {order_volume} 手)"
            print(msg)
            log_trade('execute_add_on_order', msg, symbol=trade_symbol, log_level='INFO', account=account)

            target_pos.set_target_volume(target_lots)

            result = wait_for_target_position(
                api=api,
                target_pos=target_pos,
                symbol=trade_symbol,
                target_lots=target_lots,
                function_name='execute_add_on_order'
            )

            if not result['success']:
                signal.remark = (
                    f"加仓失败: 计划{order_volume}手, "
                    f"TargetPosTask设置目标{target_lots}手超时 "
                    f"(当前持仓{position.contract_total_position}手)"
                )
                msg = f"[ERROR] {trade_symbol} 加仓超时或失败"
                print(msg)
                log_error('execute_add_on_order', msg, notify=True)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'remark', 'updated_at'])
                return False

            quote = api.get_quote(trade_symbol)
            api.wait_update(deadline=time.time() + 2)
            avg_price = float(quote.last_price) if quote and quote.last_price else None

            with transaction.atomic():
                new_units = position.units + add_units_from_signal
                new_total_lots = position.contract_total_position + order_volume

                PositionState.objects.filter(id=position.id).update(
                    units=new_units,
                    contract_total_position=new_total_lots,
                    latest_close_price=Decimal(str(avg_price)),
                )

                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status', 'updated_at'])

            # 记录加仓滑点
            try:
                add_signal_price = (signal.donchian_upper if signal.signal_direction == 1
                                    else signal.donchian_lower) or position.first_open_price
                if add_signal_price and avg_price:
                    contract = FullContractList.objects.filter(symbol=trade_symbol).first()
                    price_tick = contract.price_tick if contract else Decimal('1')
                    record_slippage(
                        account=account,
                        trade_type='ADD_ON',
                        symbol=trade_symbol,
                        product_code=signal.product_code,
                        position_direction=position.direction,
                        volume=order_volume,
                        signal_price=add_signal_price,
                        fill_price=Decimal(str(avg_price)),
                        price_tick=price_tick,
                        signal=signal,
                    )
            except Exception as slip_err:
                log_error('execute_add_on_order',
                           f"{slip_err}\n{traceback.format_exc()}", account=account
                           )

            msg = f"{trade_symbol} 加仓成功: +{unit_lots} Unit({order_volume}手) @ {avg_price:.2f}, 总持仓:{new_units} Unit"
            print(msg)
            log_trade('execute_add_on_order', msg, symbol=trade_symbol, log_level='SUCCESS', account=account)
            return True

        except Exception as e:
            msg = f"[ERROR] 加仓失败 {trade_symbol}: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_add_on_order', f"{msg}\n{traceback.format_exc()}", notify=True)
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False


def execute_entry_order(api, account, signal, gap_threshold_atr_multiplier=GAP_PROTECTION_RATIO):
    if not is_trading(api, account, signal):
        return False

    # ---- 跳过震荡行情开仓 ----
    try:
        config = account.strategyconfig
        if config.skip_choppy_entry and signal.trend_label in ('choppy', 'neutral'):
            msg = f"{signal.symbol} 趋势为{signal.trend_label}，跳过开仓（震荡行情不入场）"
            print(msg)
            log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='INFO', account=account)
            signal.executed_status = 'CANCELLED'
            signal.remark = '震荡行情不入场'
            signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
            return False
    except StrategyConfig.DoesNotExist:
        pass

    # 预计算 ATR，避免 price_gap_protection 和 calculate_unit_lots 重复计算
    atr_20 = calculate_atr(api, signal.symbol, period=20)

    unit_lots = calculate_unit_lots(api, signal.symbol, atr=atr_20)
    target_units = 1
    order_volume = target_units * unit_lots
    print(f"[INFO] {signal.symbol} 开仓计划: 1个Unit × {unit_lots}手/Unit = {order_volume}手")

    can_trade = price_gap_protection(
        api=api,
        symbol=signal.symbol,
        direction=signal.signal_direction,
        gap_threshold_atr_multiplier=gap_threshold_atr_multiplier,
        atr=atr_20
    )
    if not can_trade:
        msg = f"{signal.symbol} 跳空幅度过大，禁止开仓"
        print(msg)
        log_trade('execute_entry_order', msg, signal=signal.symbol, log_level='WARNING', account=account)
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
        log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='INFO', account=account)

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
                    'first_open_price': Decimal(str(two_step_result['avg_price'])),
                    'highest_close': Decimal(str(two_step_result['avg_price'])),
                    'lowest_close': Decimal(str(two_step_result['avg_price'])),
                    'latest_close_price': Decimal(str(two_step_result['avg_price'])),
                    'open_date': timezone.now().date(),
                    # 入场趋势快照
                    'entry_trend_factor': signal.trend_factor,
                    'entry_trend_label': signal.trend_label,
                    'entry_atr': Decimal(str(atr_20)) if atr_20 is not None else None,
                }
            )

            signal.executed_status = 'SUCCESS'
            signal.save(update_fields=['executed_status', 'updated_at'])

        # 记录滑点（两步开仓）
        try:
            signal_price = (signal.donchian_upper if signal.signal_direction == 1
                            else signal.donchian_lower)
            if signal_price and two_step_result.get('avg_price'):
                contract = FullContractList.objects.filter(symbol=signal.symbol).first()
                price_tick = contract.price_tick if contract else Decimal('1')
                record_slippage(
                    account=account,
                    trade_type='ENTRY',
                    symbol=signal.symbol,
                    product_code=signal.product_code,
                    position_direction=signal.signal_direction,
                    volume=two_step_result.get('actual_filled') or 0,
                    signal_price=signal_price,
                    fill_price=Decimal(str(two_step_result['avg_price'])),
                    price_tick=price_tick,
                    signal=signal,
                )
        except Exception as slip_err:
            log_error(
                function_name='execute_entry_order',
                error_message=f"记录滑点异常: {slip_err}",
                account=account
            )

        msg = f"{signal.symbol} 开仓成功（两步开仓）: 1 Unit({two_step_result['actual_filled']}手) @ {two_step_result['avg_price']:.2f}"
        print(msg)
        log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='SUCCESS', account=account)
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
            log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='INFO', account=account)
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
                log_error('execute_entry_order', msg, notify=True)
                signal.executed_status = 'FAILED'
                signal.remark = '开仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
                return False

            pos_after = result['pos']
            if signal.signal_direction == 1:
                entry_avg_price = float(pos_after.open_price_long) if pos_after.open_price_long else None
                actual_filled = pos_after.volume_long_today
            else:
                entry_avg_price = float(pos_after.open_price_short) if pos_after.open_price_short else None
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
                        'highest_close': Decimal(str(entry_avg_price)),
                        'lowest_close': Decimal(str(entry_avg_price)),
                        'latest_close_price': Decimal(str(entry_avg_price)),
                        'open_date': timezone.now().date(),
                        'first_open_price': Decimal(str(entry_avg_price)),
                        # 入场趋势快照
                        'entry_trend_factor': signal.trend_factor,
                        'entry_trend_label': signal.trend_label,
                        'entry_atr': Decimal(str(atr_20)) if atr_20 is not None else None,
                    }
                )

                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status', 'updated_at'])

            # 记录滑点
            try:
                signal_price = (signal.donchian_upper if signal.signal_direction == 1
                                else signal.donchian_lower)
                if signal_price and entry_avg_price:
                    contract = FullContractList.objects.filter(symbol=signal.symbol).first()
                    price_tick = contract.price_tick if contract else Decimal('1')
                    record_slippage(
                        account=account,
                        trade_type='ENTRY',
                        symbol=signal.symbol,
                        product_code=signal.product_code,
                        position_direction=signal.signal_direction,
                        volume=actual_filled or 0,
                        signal_price=signal_price,
                        fill_price=Decimal(str(entry_avg_price)),
                        price_tick=price_tick,
                        signal=signal,
                    )
            except Exception as slip_err:
                log_error(
                    function_name='execute_entry_order',
                    error_message=f"记录滑点异常: {slip_err}",
                    account=account
                )

            msg = f"{signal.symbol} 开仓成功: 1 Unit({actual_filled}手) @ {entry_avg_price:.2f}"
            print(msg)
            log_trade('execute_entry_order', msg, symbol=signal.symbol, log_level='SUCCESS', account=account)
            return True

        except Exception as e:
            msg = f"[ERROR] 开仓失败 {signal.symbol}: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_entry_order', f"{msg}\n{traceback.format_exc()}", notify=True)
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False


def execute_exit_order(api, position, signal):
    if not is_trading(api, position.account, signal):
        return False
    total_volume = position.contract_total_position
    target_pos = TargetPosTask(api, position.symbol)
    try:
        msg = f"{position.symbol} 设置目标持仓: 0手 (平仓{total_volume} 手)"
        print(msg)
        log_trade('execute_exit_order', msg, symbol=position.symbol, log_level='INFO', account=position.account)
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
            log_error('execute_exit_order', msg, notify=True)
            if signal:
                signal.executed_status = 'FAILED'
                signal.remark = '平仓超时或失败'
                signal.save(update_fields=['executed_status', 'updated_at', 'remark'])
            return False

        # 从实际成交回报计算均价，而非用 quote.last_price
        trades = api.get_trades()
        filled_vol = 0
        total_cost = Decimal('0')
        for trade in reversed(trades.values()):
            if (trade.instrument_id == position.symbol
                    and trade.offset in ('CLOSE', 'CLOSETODAY')):
                filled_vol += trade.volume
                total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                if filled_vol >= total_volume:
                    break
        if filled_vol > 0:
            exit_price = float(total_cost / Decimal(str(filled_vol)))
        else:
            quote = api.get_quote(position.symbol)
            api.wait_update(deadline=time.time() + 2)
            exit_price = float(quote.last_price) if quote and quote.last_price else None

        with transaction.atomic():
            record_and_reset_position(api, position, signal, total_volume, exit_price)

            if signal:
                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status', 'updated_at'])

        # 记录平仓滑点
        try:
            if position.stop_loss_price and exit_price:
                contract = FullContractList.objects.filter(symbol=position.symbol).first()
                price_tick = contract.price_tick if contract else Decimal('1')
                record_slippage(
                    account=position.account,
                    trade_type='EXIT',
                    symbol=position.symbol,
                    product_code=position.product_code or '',
                    position_direction=position.direction,
                    volume=total_volume,
                    signal_price=position.stop_loss_price,
                    fill_price=Decimal(str(exit_price)),
                    price_tick=price_tick,
                    signal=signal,
                )
        except Exception as slip_err:
            logger.warning('记录平仓滑点失败: %s', slip_err)

        msg = f"{position.symbol} 平仓成功"
        print(msg)
        log_trade('execute_exit_order', msg, symbol=position.symbol, log_level='SUCCESS', account=position.account)
        return True

    except Exception as e:
        msg = f"[ERROR] 平仓失败 {position.symbol}: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_exit_order', f"{msg}\n{traceback.format_exc()}", notify=True)
        if signal:
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
        return False


def execute_rollover_order(api, position, signal):
    if not is_trading(api, position.account, signal):
        return False

    # ===== Phase 1: Close old contract =====
    msg = f"{position.symbol} 开始平仓旧合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO', account=position.account)

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
            log_error('execute_rollover_order', msg, notify=True)
            signal.executed_status = 'FAILED'
            signal.save(update_fields=['executed_status', 'updated_at'])
            return False

        # ===== Record closed position for rollover =====
        # TargetPosTask 完成后，等待成交回报到达（超时等待替代固定次数更新）
        filled_volume = 0
        total_cost = Decimal('0')
        confirm_start = time.time()
        CONFIRM_TIMEOUT = 10  # 最多等待10秒等待成交回报

        while time.time() - confirm_start < CONFIRM_TIMEOUT:
            api.wait_update(deadline=time.time() + 1)
            trades = api.get_trades()
            filled_volume = 0
            total_cost = Decimal('0')
            for trade in reversed(trades.values()):
                if (trade.instrument_id == position.symbol and
                        trade.offset in ('CLOSE', 'CLOSETODAY')):
                    filled_volume += trade.volume
                    total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                    if filled_volume >= position.contract_total_position:
                        break
            if filled_volume >= position.contract_total_position:
                msg = f"{position.symbol} 全部成交回报已接收: {filled_volume}手"
                print(msg)
                log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='SUCCESS', account=position.account)
                break

        if filled_volume > 0:
            rollover_exit_price = total_cost / Decimal(str(filled_volume))
        else:
            quote = api.get_quote(position.symbol)
            api.wait_update(deadline=time.time() + 2)
            rollover_exit_price = Decimal(str(quote.last_price)) if quote.last_price else Decimal('0')
            filled_volume = position.contract_total_position

        try:
            contract_info = FullContractList.objects.get(symbol=position.symbol)
            volume_multiple = contract_info.volume_multiple
        except FullContractList.DoesNotExist:
            log_error('execute_rollover_order', f"合约 {position.symbol} 未找到，乘数默认10", notify=True)
            volume_multiple = 10

        cost_price = position.cost_price if position.cost_price else None
        if position.direction == 1:
            rollover_pnl = (rollover_exit_price - cost_price) * Decimal(str(filled_volume)) * Decimal(str(volume_multiple))
        else:
            rollover_pnl = (cost_price - rollover_exit_price) * Decimal(str(filled_volume)) * Decimal(str(volume_multiple))

        holding_days = None
        if position.open_date:
            holding_days = (timezone.now().date() - position.open_date).days

        # --- 计算出场趋势快照 ---
        exit_trend_factor = signal.trend_factor if signal else None
        exit_trend_label = signal.trend_label if signal else None

        # 计算出场 ATR
        try:
            exit_atr_raw = calculate_atr(api, position.symbol)
            exit_atr_roll = Decimal(str(exit_atr_raw)) if exit_atr_raw is not None else None
        except Exception:
            exit_atr_roll = None

        # 计算 MFE/MAE
        mfe = None
        mae = None
        if cost_price is not None and position.highest_close is not None and position.lowest_close is not None:
            if position.direction == 1:
                mfe = position.highest_close - cost_price
                mae = cost_price - position.lowest_close
            elif position.direction == -1:
                mfe = cost_price - position.lowest_close
                mae = position.highest_close - cost_price

        ClosedPositionRecord.objects.create(
            account=position.account,
            symbol=position.symbol,
            product_code=position.product_code,
            direction=position.direction,
            volume=filled_volume,
            exit_price=rollover_exit_price,
            cost_price=cost_price,
            pnl=rollover_pnl,
            trade_date=timezone.now().date(),
            executed_at=timezone.now(),
            holding_days=Decimal(str(holding_days)) if holding_days is not None else None,
            # 入场趋势快照
            entry_trend_factor=position.entry_trend_factor,
            entry_trend_label=position.entry_trend_label,
            entry_atr=position.entry_atr,
            # 出场趋势快照
            exit_trend_factor=exit_trend_factor,
            exit_trend_label=exit_trend_label,
            exit_atr=exit_atr_roll,
            # 极值分析
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
        )

        msg = f"{position.symbol} 移仓平仓记录已创建: {filled_volume}手 @ {rollover_exit_price:.2f}, PnL={rollover_pnl:.2f}"
        print(msg)
        log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='SUCCESS', account=position.account)

    except Exception as e:
        msg = f"[ERROR] {position.symbol} 平仓失败: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", notify=True)
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False

    # ===== Phase 2: Open new contract =====
    # 从 FullContractList 获取新主力合约代码（signal.symbol 存的是旧合约代码）
    main_contract = FullContractList.objects.filter(
        product_code=position.product_code
    ).first()
    if not main_contract:
        msg = f"[ERROR] {position.product_code} 无法获取新主力合约信息"
        print(msg)
        log_error('execute_rollover_order', msg, notify=True)
        signal.executed_status = 'FAILED'
        signal.save(update_fields=['executed_status', 'updated_at'])
        return False
    new_symbol = main_contract.symbol

    msg = f"{new_symbol} 开始开仓新合约..."
    print(msg)
    log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO', account=position.account)

    target_volume = position.contract_total_position
    min_position_check = check_min_position_requirement(new_symbol, target_volume)

    if min_position_check['need_adjustment']:
        adjusted_volume = min_position_check['adjusted_volume']
        excess_to_close = min_position_check['excess_to_close']

        msg = f"{new_symbol} 采用两步开仓策略: 先开{adjusted_volume}手，再平{excess_to_close}手"
        print(msg)
        log_trade('execute_rollover_order', msg, symbol=position.symbol, log_level='INFO', account=position.account)

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
        log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO', account=position.account)

    else:
        target_pos_new = TargetPosTask(api, new_symbol)
        try:
            if position.direction == 1:
                target_lots = target_volume
            else:
                target_lots = -target_volume

            msg = f"{new_symbol} 设置目标持仓: {target_lots}手"
            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO', account=position.account)
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
                log_error('execute_rollover_order', msg, notify=True)
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
                return False

            if position.direction == 1:
                entry_avg_price = float(pos_after.open_price_long) if pos_after and pos_after.open_price_long else None
                actual_filled = pos_after.volume_long_today
            else:
                entry_avg_price = float(pos_after.open_price_short) if pos_after and pos_after.open_price_short else None
                actual_filled = pos_after.volume_short_today

            msg = f"{new_symbol} 换月开仓成功: {actual_filled}手 @ {entry_avg_price:.2f}"
            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO', account=position.account)

        except Exception as e:
            msg = f"[ERROR] {new_symbol} 移仓操作中，开仓失败: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", notify=True)
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False

    # ===== Phase 3: Update database =====
    try:
        # 计算新合约初始数据 + init_stop_loss（合并，只需一次get_kline_serial）
        old_profit = abs(rollover_exit_price - cost_price) if (cost_price and rollover_exit_price) else None
        holding_days = (timezone.now().date() - position.open_date).days if position.open_date else 0
        data_length = max(25, (holding_days or 0) + 10)
        klines = api.get_kline_serial(new_symbol, duration_seconds=86400, data_length=data_length)

        if klines is not None and len(klines) >= 20:
            # 完整历史 → H_full/L_full
            H_full = float(klines['close'].max())
            L_full = float(klines['close'].min())

            # 跟踪止损参考值（直接用完整历史最高/最低）
            if position.direction == 1:
                init_highest_close = Decimal(str(H_full))
                init_lowest_close = None
            else:
                init_highest_close = None
                init_lowest_close = Decimal(str(L_full))

            # ATR + stop_distance
            atr_val = calculate_atr(api, new_symbol, period=20)
            # trend_factor 来自老合约信号，同品种均线类同偏差可忽略
            # 且收盘任务会按新合约的 ATR+自身指标重新计算，此处只需一个合理初始值
            tf_val = float(signal.trend_factor) if (signal and signal.trend_factor) else 0
            stop_dist = Decimal(str(2 * (1 + tf_val) * atr_val))

            # 新公式：init_stop_loss = max(H_full - stop_dist, entry - old_profit)
            entry_dec = Decimal(str(entry_avg_price))
            if position.direction == 1:
                loss_budget = entry_dec - old_profit
                init_stop_loss = max(Decimal(str(H_full)) - stop_dist, loss_budget)
            else:
                loss_budget = entry_dec + old_profit
                init_stop_loss = min(Decimal(str(L_full)) + stop_dist, loss_budget)
            msg = f"{new_symbol} 移仓初始化: stop={init_stop_loss}, budget={loss_budget}, H_full={H_full:.2f}"

            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='INFO', account=position.account)
        else:
            msg = f"{new_symbol} 历史数据不足({len(klines) if klines else 0}根)，使用开仓价初始化"
            print(msg)
            log_trade('execute_rollover_order', msg, symbol=new_symbol, log_level='WARNING', account=position.account)
            init_highest_close = Decimal(str(entry_avg_price)) if position.direction == 1 else None
            init_lowest_close = Decimal(str(entry_avg_price)) if position.direction == -1 else None
            init_stop_loss = None

        try:
            with transaction.atomic():
                # 移仓换月 — 直接创建新合约持仓（目标合约不可能有持仓）
                PositionState.objects.create(
                    account=position.account,
                    symbol=new_symbol,
                    product_code=signal.product_code,
                    direction=position.direction,
                    units=position.units,
                    contract_total_position=actual_filled,
                    first_open_price=Decimal(str(entry_avg_price)),
                    highest_close=init_highest_close,
                    lowest_close=init_lowest_close,
                    latest_close_price=Decimal(str(entry_avg_price)),
                    open_date=timezone.now().date(),
                    stop_loss_price=init_stop_loss,
                    protect_cost_enabled=position.protect_cost_enabled,
                    is_rollover_needed=False,
                )
                PositionState.objects.filter(id=position.id).delete()
                signal.executed_status = 'SUCCESS'
                signal.save(update_fields=['executed_status', 'updated_at'])

                return True

        except Exception as e:
            msg = f"[ERROR] {new_symbol} 移仓数据库更新失败: {str(e)}"
            print(msg)
            traceback.print_exc()
            log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", notify=True)
            try:
                signal.executed_status = 'FAILED'
                signal.save(update_fields=['executed_status', 'updated_at'])
            except Exception:
                pass
            return False

    except Exception as e:
        msg = f"[ERROR] {new_symbol} 移仓操作中，数据库更新失败: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error('execute_rollover_order', f"{msg}\n{traceback.format_exc()}", notify=True)
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
                   f"API连接已断开，跳过{trade_type}处理", notify=True)
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
                    account=account,
                    executed_status='PENDING'
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
