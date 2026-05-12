"""
Order execution infrastructure — TargetPosTask management, two-step opening, position recording.
"""
import time
import traceback
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from tqsdk import TargetPosTask
from stock.utils.log_util import log_trade, log_error
from stock.core.config_loader import get_config

TIMEOUT_SECONDS = get_config('TIMEOUT_SECONDS')


def wait_for_target_position(api, target_pos, symbol, target_lots, function_name, timeout=TIMEOUT_SECONDS):
    """
    通用持仓目标等待与资源释放函数。
    等待持仓达到目标手数，无论成功与否都释放 TargetPosTask 资源。
    """
    start_time = time.time()
    pos_current = None

    while time.time() - start_time < timeout:
        remaining = timeout - (time.time() - start_time)
        if remaining <= 0:
            break
        api.wait_update(deadline=time.time() + min(1, remaining))
        pos_current = api.get_position(symbol)
        if pos_current and pos_current.pos == target_lots:
            msg = f"{symbol} 任务完成: 当前持仓 {target_lots} 手"
            print(msg)
            log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
            break

    try:
        target_pos.cancel()
        while not target_pos.is_finished():
            api.wait_update()
    except Exception as e:
        log_error(function_name, f"{symbol} 释放 TargetPosTask 资源时出错: {str(e)}")

    return {'success': pos_current is not None and pos_current.pos == target_lots, 'pos': pos_current}


def check_min_position_requirement(symbol, planned_volume):
    """
    检查交易所最小开仓手数限制，返回是否需要两步开仓策略。
    """
    result = {
        'need_adjustment': False,
        'min_position': planned_volume,
        'original_volume': planned_volume,
        'adjusted_volume': planned_volume,
        'excess_to_close': 0
    }

    try:
        from stock.models import FullContractList
        import re
        product_code = re.match(r'^[A-Za-z]+', symbol.split('.')[-1])
        product_code = product_code.group(0) if product_code else symbol[:2]

        contract_info = FullContractList.objects.filter(
            product_code=product_code
        ).first()

        if contract_info and contract_info.min_position > 1:
            min_pos = contract_info.min_position
            result['min_position'] = min_pos

            if planned_volume < min_pos:
                print(f"[INFO] {symbol} 检测到最小开仓限制: {min_pos}手")
                print(f"[WARN] {symbol} 计划开仓{planned_volume}手 < 最小限制{min_pos}手，将采用两步开仓策略")

                result['need_adjustment'] = True
                result['original_volume'] = planned_volume
                result['adjusted_volume'] = min_pos
                result['excess_to_close'] = min_pos - planned_volume
            else:
                print(f"[INFO] {symbol} 计划开仓{planned_volume}手 >= 最小限制{min_pos}手，直接开仓")
        else:
            print(f"[INFO] {symbol} 无最小开仓限制或限制为1手，直接开仓")

    except Exception as e:
        print(f"[WARN] {symbol} 检查最小开仓限制失败: {str(e)}，继续正常开仓流程")
        traceback.print_exc()

    return result


def execute_two_step_opening(api, symbol, direction, adjusted_volume, excess_to_close, target_volume, function_name, account=None, signal=None):
    """
    执行两步开仓策略（应对交易所最小开仓限制）。
    """
    result = {
        'success': False,
        'actual_filled': 0,
        'avg_price': None
    }

    target_pos = TargetPosTask(api, symbol, support_open_min_volume=True)

    try:
        # 第1步：开立等于最小开仓手数的仓位
        if direction == 1:
            step1_target = adjusted_volume
        else:
            step1_target = -adjusted_volume

        msg = f"{symbol} 第1步：设置目标持仓 {step1_target}手 (最小开仓{adjusted_volume}手)"
        print(msg)
        log_trade(function_name, msg, symbol=symbol, log_level='INFO')

        target_pos.set_target_volume(step1_target)
        start_time = time.time()
        step1_completed = False
        pos_current = None
        while time.time() - start_time < TIMEOUT_SECONDS:
            api.wait_update()
            pos_current = api.get_position(symbol)
            if pos_current and pos_current.pos == step1_target:
                msg = f"{symbol} 第1步完成: 已开{step1_target}手"
                print(msg)
                log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
                step1_completed = True
                break

        target_pos.cancel()
        while not target_pos.is_finished():
            api.wait_update()

        if not step1_completed:
            msg = f"[ERROR] {symbol} 第1步开仓超时或失败"
            print(msg)
            log_error(function_name, msg)
            return result

        # 第2步：平仓多余部分
        target_pos = TargetPosTask(api, symbol, support_open_min_volume=True)
        if direction == 1:
            step2_target = adjusted_volume - excess_to_close
        else:
            step2_target = -(adjusted_volume - excess_to_close)

        msg = f"{symbol} 第2步：平仓{excess_to_close}手，目标持仓 {step2_target}手"
        print(msg)
        log_trade(function_name, msg, symbol=symbol, log_level='INFO')

        target_pos.set_target_volume(step2_target)

        start_time = time.time()
        step2_completed = False
        pos_current = None

        while time.time() - start_time < TIMEOUT_SECONDS:
            api.wait_update()
            pos_current = api.get_position(symbol)
            if pos_current and pos_current.pos == step2_target:
                msg = f"{symbol} 第2步完成: 最终持仓{step2_target}手"
                print(msg)
                log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
                step2_completed = True
                break

        target_pos.cancel()
        while not target_pos.is_finished():
            api.wait_update()

        if not step2_completed:
            msg = f"[ERROR] {symbol} 第2步平仓超时或失败"
            print(msg)
            log_error(function_name, msg)
            return result

        pos_after = api.get_position(symbol)
        if pos_after is None:
            msg = f"[ERROR] {symbol} 无法获取持仓信息"
            print(msg)
            log_error(function_name, msg)
            return result

        quote = api.get_quote(symbol)
        avg_price = float(quote.last_price) if quote and quote.last_price else None

        if direction == 1:
            actual_final_filled = pos_after.volume_long
        else:
            actual_final_filled = pos_after.volume_short

        result['success'] = True
        result['actual_filled'] = actual_final_filled
        result['avg_price'] = avg_price

        msg = f"两步开仓成功: {actual_final_filled}手 @ {avg_price:.2f}"
        print(msg)
        log_trade(function_name, msg, symbol=symbol, log_level='SUCCESS')
        return result

    except Exception as e:
        msg = f"[ERROR] {symbol} 两步开仓失败: {str(e)}"
        print(msg)
        traceback.print_exc()
        log_error(function_name, f"{msg}\n{traceback.format_exc()}")
        return result
    finally:
        try:
            del target_pos
        except Exception:
            pass


def record_and_reset_position(api, position, signal, filled_volume, avg_price):
    """
    创建平仓记录并重置持仓状态。
    被 execute_exit_order 和 execute_stop_loss_exit 共享。
    """
    from stock.models import ClosedPositionRecord, PositionState, FullContractList
    from stock.core.atr import calculate_atr

    with transaction.atomic():
        quote = api.get_quote(position.symbol)
        exit_price = avg_price if avg_price else (float(quote.last_price) if quote and quote.last_price else None)
        cost_price = position.cost_price if position.cost_price else None
        volume = filled_volume
        direction = position.direction

        holding_days = None
        if position.open_date:
            holding_days = (timezone.now().date() - position.open_date).days

        try:
            contract_info = FullContractList.objects.get(symbol=position.symbol)
            volume_multiple = contract_info.volume_multiple
        except FullContractList.DoesNotExist:
            log_error('record_and_reset_position', f"合约 {position.symbol} 未找到，乘数默认10")
            volume_multiple = 10

        if direction == 1:
            pnl = (Decimal(str(exit_price)) - cost_price) * Decimal(str(volume)) * Decimal(str(volume_multiple))
        else:
            pnl = (cost_price - Decimal(str(exit_price))) * Decimal(str(volume)) * Decimal(str(volume_multiple))

        # --- 计算出场趋势快照 ---
        if signal is not None:
            exit_trend_factor = signal.trend_factor
            exit_trend_label = signal.trend_label
        elif position.indicators:
            exit_trend_factor = Decimal(str(position.indicators.get('trend_factor', 0)))
            exit_trend_label = position.indicators.get('trend_label', '')
        else:
            exit_trend_factor = None
            exit_trend_label = None

        # 计算出场 ATR
        try:
            exit_atr_raw = calculate_atr(api, position.symbol)
            exit_atr_val = Decimal(str(exit_atr_raw)) if exit_atr_raw is not None else None
        except Exception:
            exit_atr_val = None

        # 计算 MFE/MAE
        mfe = None
        mae = None
        if cost_price is not None and position.highest_close is not None and position.lowest_close is not None:
            if direction == 1:
                # 多头：MFE=最高价-成本价，MAE=成本价-最低价
                mfe = position.highest_close - cost_price
                mae = cost_price - position.lowest_close
            elif direction == -1:
                # 空头：MFE=成本价-最低价，MAE=最高价-成本价
                mfe = cost_price - position.lowest_close
                mae = position.highest_close - cost_price

        ClosedPositionRecord.objects.create(
            account=position.account,
            symbol=position.symbol,
            product_code=position.product_code,
            direction=direction,
            volume=volume,
            exit_price=Decimal(str(exit_price)),
            cost_price=cost_price,
            pnl=pnl,
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
            exit_atr=exit_atr_val,
            # 极值分析
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
        )

        update_fields = {
            'units': 0,
            'contract_total_position': 0,
            'direction': 0,
            'last_add_price': None,
            'highest_close': None,
            'lowest_close': None,
            'stop_loss_price': None,
            'protect_cost_enabled': False,
            'open_date': None,
            'last_update_time': timezone.now(),
        }
        PositionState.objects.filter(id=position.id).update(**update_fields)
