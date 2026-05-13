import traceback
import time
from datetime import date, timedelta
from typing import Optional, Any
from django.db import transaction, close_old_connections
from decimal import Decimal
from django_redis import get_redis_connection
from stock.utils.log_util import log_trade, log_error
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.core.signal_checker import check_duplicate_pending_signal

from stock.models import TradingAccount, DailyStrategySignal, PositionState, FullContractList, AccountContractConfig
from stock.infrastructure.contract_sync import sync_contract_list_from_tqsdk, sync_kline_data_from_tqsdk
from stock.infrastructure.report_sender import generate_daily_signal_report
from stock.core.indicators import calculate_indicators
from stock.core.performance import update_all_performance_metrics
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.core.config_loader import get_config

PROTECT_COST_ENABLED_RATIO = get_config('PROTECT_COST_ENABLED_RATIO')

def check_breakout_signal(symbol, product_code, trend_factor, trend_label, 
                                          breakout_info, account,trade_type):
    """
    步骤3：保存每日策略信号并更新持仓状态（检查是否需要开仓）
    
    参数：
    symbol: 合约代码
    product_code: 品种代码
    trend_factor: 趋势因子
    trend_label: 趋势标签
    breakout_info: 突破信号信息字典（来自check_breakout_signal）
    account: 交易账户对象
    
    返回：
    bool: 是否成功保存
    """
    if not breakout_info['is_breakout']:
        return False
    
    try:
        # 检查当前持仓单位数是否为0，只有无持仓时才保存突破信号
        position = PositionState.objects.filter(
            account=account,
            symbol=symbol
        ).first()
        
        # 如果存在持仓且units不为0，则不保存突破信号
        if position and position.units != 0:
            print(f"[SKIP] 跳过突破信号保存 {symbol}: 当前持仓单位数={position.units}")
            return False
        
        # 【修复1】检查是否存在未执行的开仓信号，避免跨日期重复生成
        last_entry_signal = DailyStrategySignal.objects.filter(
            account=account,
            symbol=symbol,
            trade_type='ENTRY',
            executed_status='PENDING'
        ).order_by('-trade_date').first()
        
        if last_entry_signal:
            log_trade('check_breakout_signal', f"跳过重复开仓信号 {symbol}: 存在未执行的ENTRY信号（{last_entry_signal.trade_date}）",
                      symbol=symbol, log_level='INFO')
            return False
    
        with transaction.atomic():
            DailyStrategySignal.objects.create(
                account=account,
                symbol=symbol,
                product_code=product_code,
                trade_date=date.today(),
                trend_factor=Decimal(str(trend_factor)),
                trend_label=trend_label,
                donchian_upper=Decimal(str(breakout_info['entry_high'])) if breakout_info['entry_high'] else None,
                donchian_lower=Decimal(str(breakout_info['entry_low'])) if breakout_info['entry_low'] else None,
                is_breakout=breakout_info['is_breakout'],
                signal_direction=breakout_info['signal_direction'],
                trade_type=trade_type,
                remark=breakout_info['remark'] or f"趋势状态: {trend_label} (factor={trend_factor})",
                contract_target_number=1,  # 海龟法则默认首次开仓为1单位
            )
            return True
            
    except Exception as e:
        print(f"[ERROR] 保存策略信号失败 {symbol}: {e}")
        return False


def check_exit_signals(account):
    """
    步骤5：检查是否需要平仓（考虑期货多空特性）

    止损逻辑：
    - 多头持仓(direction=1): 最新收盘价 < 止损价 -> 触发止损
    - 空头持仓(direction=-1): 最新收盘价 > 止损价 -> 触发止损
    """
    try:
        # 查询所有有持仓的记录（units > 0 且 direction != 0）
        positions = PositionState.objects.filter(
            account=account,
            units__gt=0
        ).exclude(direction=0)
        
        exit_count = 0
        
        for position in positions:
            # 确保有最新价格和止损价
            if not position.latest_close_price or not position.stop_loss_price:
                continue
            
            latest_price = float(position.latest_close_price)
            stop_loss = float(position.stop_loss_price)
            
            is_trigger = False
            remark = ""
            
            # 根据持仓方向判断是否触发止损
            if position.direction == 1:
                # 多头持仓：价格跌破止损价
                if latest_price < stop_loss:
                    is_trigger = True
                    remark = f"多头止损触发: 最新价{latest_price:.2f} < 止损价{stop_loss:.2f}"
            elif position.direction == -1:
                # 空头持仓：价格突破止损价
                if latest_price > stop_loss:
                    is_trigger = True
                    remark = f"空头止损触发: 最新价{latest_price:.2f} > 止损价{stop_loss:.2f}"
            
            # 如果触发止损，保存平仓信号
            if is_trigger:
                if check_duplicate_pending_signal(account, position.symbol, 'STOP_LOSS'):
                    continue

                DailyStrategySignal.objects.create(
                    account=account,
                    symbol=position.symbol,
                    product_code=position.product_code,
                    trade_date=date.today(),
                    trend_factor=Decimal(str(position.indicators.get('trend_factor', 0))) if position.indicators else Decimal('0'),
                    trend_label=position.indicators.get('trend_label', '') if position.indicators else '',
                    donchian_upper=None,
                    donchian_lower=None,
                    is_breakout=False,
                    signal_direction=0,
                    trade_type='STOP_LOSS',
                    remark=remark,
                )
                exit_count += 1
                print(f"[EXIT] 止损信号: {position.symbol} - {remark}")
        
        if exit_count > 0:
            print(f"[SUMMARY] 今日共生成 {exit_count} 个止损信号")
        
    except Exception as e:
        print(f"[ERROR] 检查平仓信号失败: {e}")


def check_rollover_signals(account):
    """
    步骤6：检查是否需要移仓（根据is_rollover_needed字段）

    逻辑：
    - 如果is_rollover_needed=True，说明主力合约发生变化且有持仓，需要移仓
    - 生成移仓信号，提醒用户进行移仓操作
    """
    try:
        # 查询所有需要移仓的记录
        rollover_positions = PositionState.objects.filter(
            account=account,
            is_rollover_needed=True,
            units__gt=0  # 只处理有持仓的记录
        )
        
        rollover_count = 0
        
        for position in rollover_positions:
            # 获取新的主力合约信息
            main_contract = FullContractList.objects.filter(
                product_code=position.product_code
            ).first()
            
            if main_contract:
                if check_duplicate_pending_signal(account, position.symbol, 'ROLLOVER'):
                    continue

                DailyStrategySignal.objects.create(
                    account=account,
                    symbol=position.symbol,
                    product_code=position.product_code,
                    trade_date=date.today(),
                    trend_factor=Decimal(str(position.indicators.get('trend_factor', 0))) if position.indicators else Decimal('0'),
                    trend_label=position.indicators.get('trend_label', '') if position.indicators else '',
                    donchian_upper=None,
                    donchian_lower=None,
                    is_breakout=False,
                    signal_direction=0,
                    trade_type='ROLLOVER',
                    remark=f"需要移仓到新主力合约 {main_contract.symbol}",
                )
                rollover_count += 1
                print(f"[ROLLOVER] 移仓信号: {position.symbol} -> {main_contract.symbol}")
        
        if rollover_count > 0:
            print(f"[SUMMARY] 今日共生成 {rollover_count} 个移仓信号")
        
    except Exception as e:
        print(f"[ERROR] 检查移仓信号失败: {e}")


def check_add_position_signals(account):
    """
    步骤4：检查是否需要加仓（基于海龟法则金字塔加仓逻辑）

    加仓规则：
    - 仅对持仓单位数 < 3 的持仓进行检查
    - 1单位持仓时，以 last_add_price（首次开仓价）为基准：
      - 多头：价格涨超 0.5×ATR → 加1单位；涨超 1.0×ATR → 加2单位（直接满仓）
      - 空头：价格跌超 0.5×ATR → 加1单位；跌超 1.0×ATR → 加2单位（直接满仓）
    - 2单位持仓时，以 first_open_price（首次开仓价）为基准：
      - 多头：从首次开仓价累计涨超 1.0×ATR → 加1单位
      - 空头：从首次开仓价累计跌超 1.0×ATR → 加1单位
    - 重要：无论价格变动多大，加仓后总单位数不得超过3单位

    注意：所有计算统一使用 Decimal 类型，避免精度丢失
    """
    try:
        # 查询所有有持仓且单位数 < 3 的记录
        positions = PositionState.objects.filter(
            account=account,
            units__gt=0,
            units__lt=3  # 仅检查未达到最大持仓单位数的记录
        ).exclude(direction=0)
        
        addon_count = 0
        
        for position in positions:
            # 确保必要数据存在
            if not position.latest_close_price or not position.last_add_price:
                continue
            
            if not position.indicators:
                continue
            
            try:
                # 从 indicators 获取 ATR（转换为 Decimal）
                atr_value = Decimal(str(position.indicators.get('atr_20', 0)))
                
                if atr_value <= 0:
                    continue
                
                latest_price = position.latest_close_price
                last_add_price = position.last_add_price
                first_open_price = position.first_open_price if position.first_open_price else last_add_price
                current_units = position.units
                
                add_units = 0  # 需要加仓的单位数
                price_diff = Decimal('0')  # 用于日志记录的价格变动
                
                if current_units == 1:
                    # 1单位时：以 last_add_price 为基准计算价差
                    price_diff = latest_price - last_add_price
                    
                    if position.direction == 1:
                        # 多头持仓：价格上涨才加仓
                        if price_diff > Decimal('1') * atr_value:
                            # 涨幅超过 1×ATR，直接加2单位满仓
                            add_units = 2
                        elif price_diff > Decimal('0.5') * atr_value:
                            # 涨幅超过 0.5×ATR，加仓1单位
                            add_units = 1
                    
                    elif position.direction == -1:
                        # 空头持仓：价格下跌才加仓
                        if price_diff < Decimal('-1') * atr_value:
                            # 跌幅超过 1×ATR，直接加2单位满仓
                            add_units = 2
                        elif price_diff < Decimal('-0.5') * atr_value:
                            # 跌幅超过 0.5×ATR，加仓1单位
                            add_units = 1
                
                elif current_units == 2:
                    # 2单位时：以 first_open_price 为基准判断累计波动
                    # 第3单位加仓点 = 开仓价 ± 1.0×ATR（即距离第2单位又走了0.5×ATR）
                    if position.direction == 1:
                        price_diff = latest_price - first_open_price
                        if price_diff > Decimal('1') * atr_value:
                            add_units = 1
                    elif position.direction == -1:
                        price_diff = first_open_price - latest_price
                        if price_diff > Decimal('1') * atr_value:
                            add_units = 1
              
                # 如果满足加仓条件，生成加仓信号
                if add_units > 0:
                    # 【最终安全检查】确保加仓后不超过3单位
                    new_units = current_units + add_units
                    if new_units > 3:
                        add_units = 3 - current_units
                    
                    if check_duplicate_pending_signal(account, position.symbol, 'ADD_ON'):
                        continue

                    DailyStrategySignal.objects.create(
                        account=account,
                        symbol=position.symbol,
                        product_code=position.product_code,
                        trade_date=date.today(),
                        trend_factor=Decimal(str(position.indicators.get('trend_factor', 0))),
                        trend_label=position.indicators.get('trend_label', ''),
                        donchian_upper=None,
                        donchian_lower=None,
                        is_breakout=False,
                        signal_direction=position.direction,
                        trade_type='ADD_ON',
                        contract_target_number=add_units,
                        remark=f"加仓信号: {'多头' if position.direction == 1 else '空头'} "
                               f"价格差={float(price_diff):.2f}, ATR={float(atr_value):.2f}, "
                               f"建议加仓{add_units}单位 (当前{current_units}→{current_units + add_units})"
                    )
                    addon_count += 1
            except Exception as pos_error:
                print(f"[ERROR] 处理 {position.symbol} 加仓检查失败: {pos_error}")
                continue
        
        if addon_count > 0:
            print(f"[SUMMARY] 今日共生成 {addon_count} 个加仓信号")
        
    except Exception as e:
        print(f"[ERROR] 检查加仓信号失败: {e}")



def update_all_positions_high_low_price(account):
    """
    计算持仓后出现的历史收盘最高价和最低价

    逻辑：
    - 对于每个持仓记录，查询该合约的历史收盘价
    - 更新持仓记录的最高收盘价和最低收盘价字段
    """
    try:
        positions = PositionState.objects.filter(
            account=account,
            units__gt=0  # 只处理有持仓的记录
        )
        
        updated_count = 0
        
        for position in positions:
            try:
                # 查询该合约的历史收盘价
                # 开仓日期之前的收盘价不考虑
                # 开仓的时候以开仓价格为初始最高价和最低价，需要再开仓的时候填入。然后每日收盘后更新一次，计算开仓以来的最高价和最低价。
                # 无论多空，同时跟踪最高价和最低价
                # 多头：highest_close 上移跟踪浮盈，lowest_close 下移提供 MAE
                # 空头：lowest_close 下移跟踪浮盈，highest_close 上移提供 MAE
                if position.highest_close is not None and position.latest_close_price > position.highest_close:
                    PositionState.objects.filter(id=position.id).update(highest_close=position.latest_close_price)
                if position.lowest_close is not None and position.latest_close_price < position.lowest_close:
                    PositionState.objects.filter(id=position.id).update(lowest_close=position.latest_close_price)
                updated_count += 1
                
            except Exception as pos_error:
                print(f"[ERROR] 更新 {position.symbol} 最高最低价失败: {pos_error}")
                traceback.print_exc()
                continue

        print(f"[SUCCESS] 已更新 {updated_count}/{positions.count()} 个持仓的最高最低价格")

    except Exception as e:
        print(f"[ERROR] 更新最高最低价格失败: {e}")
        traceback.print_exc()
def update_all_positions_stop_loss_price(api, account):
    """
    更新所有持仓的止损价格

    止损价计算逻辑（考虑期货多空特性）：
    - 多头持仓 (direction=1)：止损价 = 最高价 - 2(1+factor) * ATR
      当价格跌破止损价时触发平仓
    - 空头持仓 (direction=-1)：止损价 = 最低价 + 2(1+factor) * ATR
      当价格突破止损价时触发平仓

    注意：所有计算统一使用 Decimal 类型，避免精度丢失
    """
    try:
        positions = PositionState.objects.filter(
            account=account,
            units__gt=0  # 只处理有持仓的记录
        ).exclude(direction=0)

        updated_count = 0

        # 先统一订阅所有持仓，再一次性 wait_update 填充数据
        tq_positions = {}
        if positions.exists():
            for position in positions:
                try:
                    tq_positions[position.symbol] = api.get_position(position.symbol)
                except Exception:
                    pass
            # 注意：必须有 deadline，收盘后无新行情时 wait_update() 不会自动返回
            api.wait_update(deadline=time.time() + 5)

        for position in positions:
            try:
                # 检查必要数据是否存在
                if not position.indicators:
                    print(f"[SKIP] {position.symbol}: indicators字段为空")
                    continue

                atr_value = Decimal(str(position.indicators.get('atr_20', 0)))
                factor = Decimal(str(position.indicators.get('trend_factor', 0)))
                trend_label = position.indicators.get('trend_label', '')
                tick_contract = FullContractList.objects.filter(symbol=position.symbol).first()
                tick = tick_contract.price_tick if tick_contract else Decimal('0.01')

                # 从已加载的 TqSDK 代理读取成本价（数据已在 wait_update 中填充）
                cost_price = None
                tq_pos = tq_positions.get(position.symbol)
                if position.direction == 1:
                    # 多头持仓：使用最高价作为基准
                    if tq_pos is not None and tq_pos.open_price_long:
                        cost_price = Decimal(str(tq_pos.open_price_long)).quantize(Decimal('0.01'))
                    else:
                        cost_price = position.cost_price
                        if cost_price is None:
                            log_error('update_all_positions_stop_loss_price',
                                       f"{position.symbol} 数据库和API均无成本价，跳过止损更新")
                            continue
                    if not position.highest_close:
                        print(f"[SKIP] {position.symbol}: 缺少最高价数据")
                        continue

                    # 多头止损价 = 最高价 - 2(1+factor) * ATR
                    dynamic_stop_loss = position.highest_close - Decimal('2') * (Decimal('1') + factor) * atr_value

                    print(f"[UPDATE] {position.symbol} 多头止损: 最高价={position.highest_close}, ATR={atr_value}, factor={factor}, 动态止损价={dynamic_stop_loss}")

                elif position.direction == -1:
                    # 空头持仓：使用最低价作为基准
                    if tq_pos is not None and tq_pos.open_price_short:
                        cost_price = Decimal(str(tq_pos.open_price_short)).quantize(Decimal('0.01'))
                    else:
                        cost_price = position.cost_price
                        if cost_price is None:
                            log_error('update_all_positions_stop_loss_price',
                                       f"{position.symbol} 数据库和API均无成本价，跳过止损更新")
                            continue
                    if not position.lowest_close:
                        print(f"[SKIP] {position.symbol}: 缺少最低价数据")
                        continue

                    # 空头止损价 = 最低价 + 2(1+factor) * ATR
                    dynamic_stop_loss = position.lowest_close + Decimal('2') * (Decimal('1') + factor) * atr_value

                    print(f"[UPDATE] {position.symbol} 空头止损: 最低价={position.lowest_close}, ATR={atr_value}, factor={factor}, 动态止损价={dynamic_stop_loss}")
                else:
                    continue
                
                # === 保本功能检查 ===
                protect_cost_enabled = position.protect_cost_enabled  # 当前保本状态
                # 计算保本价（基于成本价）
                protect_price = None
                if cost_price:
                    if position.direction == 1:
                        protect_price = Decimal(str(cost_price)) + tick * Decimal('2')
                    elif position.direction == -1:
                        protect_price = Decimal(str(cost_price)) - tick * Decimal('2')
                
                # 首次检查是否满足保本条件（仅持仓达到3个单位才激活）
                if not protect_cost_enabled and cost_price and position.latest_close_price and position.units >= 3:
                    if position.direction == 1:
                        # 多头：收盘价 - 成本价 > 2×ATR 时启用保本
                        profit_diff = position.latest_close_price - Decimal(str(cost_price))
                        if profit_diff > PROTECT_COST_ENABLED_RATIO * float(atr_value):
                            protect_cost_enabled = True
                            print(f"[PROTECT] {position.symbol} 多头启用保本: 盈利={float(profit_diff):.2f} > {PROTECT_COST_ENABLED_RATIO}×ATR={float(PROTECT_COST_ENABLED_RATIO*float(atr_value)):.2f}, 保本价={protect_price}")
                            log_trade('update_all_positions_stop_loss_price', f"[PROTECT] {position.symbol} 多头启用保本: 盈利={float(profit_diff):.2f} > {PROTECT_COST_ENABLED_RATIO}×ATR={float(PROTECT_COST_ENABLED_RATIO*float(atr_value)):.2f}, 保本价={protect_price}",
                                    symbol=position.symbol, log_level='INFO') 
                    elif position.direction == -1:
                        # 空头：成本价 - 收盘价 > 2×ATR 时启用保本
                        profit_diff = Decimal(str(cost_price)) - position.latest_close_price
                        if profit_diff > PROTECT_COST_ENABLED_RATIO * float(atr_value):
                            protect_cost_enabled = True
                            print(f"[PROTECT] {position.symbol} 空头启用保本: 盈利={float(profit_diff):.2f} > {PROTECT_COST_ENABLED_RATIO}×ATR={float(PROTECT_COST_ENABLED_RATIO*float(atr_value)):.2f}, 保本价={protect_price}")
                            log_trade('update_all_positions_stop_loss_price', f"[PROTECT] {position.symbol} 空头启用保本: 盈利={float(profit_diff):.2f} > {PROTECT_COST_ENABLED_RATIO}×ATR={float(PROTECT_COST_ENABLED_RATIO    *float(atr_value)):.2f}, 保本价={protect_price}",
                                      symbol=position.symbol, log_level='INFO')
                
                # 如果启用保本，确保止损价不劣于保本价（保本只是底线，动态跟踪继续生效）
                if protect_cost_enabled and protect_price is not None:
                    if position.direction == 1:
                        # 多头：止损价不能低于保本价（取较大者）
                        if dynamic_stop_loss < protect_price:
                            dynamic_stop_loss = protect_price
                            print(f"[PROTECT] {position.symbol} 多头保本兜底: 动态止损 < 保本价={float(protect_price):.2f}, 采用保本价")
                            log_trade('update_all_positions_stop_loss_price', f"[PROTECT] {position.symbol} 多头保本兜底: 动态止损 < 保本价={float(protect_price):.2f}, 采用保本价",
                                      symbol=position.symbol, log_level='INFO')
                    elif position.direction == -1:
                        # 空头：止损价不能高于保本价（取较小者）
                        if dynamic_stop_loss > protect_price:
                            dynamic_stop_loss = protect_price
                            print(f"[PROTECT] {position.symbol} 空头保本兜底: 动态止损 > 保本价={float(protect_price):.2f}, 采用保本价")
                            log_trade('update_all_positions_stop_loss_price', f"[PROTECT] {position.symbol} 空头保本兜底: 动态止损 > 保本价={float(protect_price):.2f}, 采用保本价",
                                      symbol=position.symbol, log_level='INFO')
                # 更新持仓止损价和保本状态（成本价由 tasks_update_float_profit 统一同步）
                PositionState.objects.filter(id=position.id).update(
                    stop_loss_price=dynamic_stop_loss,
                    trend_info=f'{atr_value:.2f},  {factor:.2f} , {trend_label}',
                    protect_cost_enabled=protect_cost_enabled,
                )
                updated_count += 1
                
            except Exception as pos_error:
                print(f"[ERROR] 更新 {position.symbol} 止损价失败: {pos_error}")
                traceback.print_exc()
                continue

        print(f"[SUCCESS] 已更新 {updated_count}/{positions.count()} 个持仓的止损价格")

    except Exception as e:
        print(f"[ERROR] 更新止损价格失败: {e}")
        traceback.print_exc()
# ==================== APScheduler 任务入口 ====================

def job_daily_close_calculation():
    """
    每日收盘后定时任务入口
    
    执行流程：
    1. 创建TqApi连接（统一管理）
    2. 检查是否为交易日（非交易日直接返回）
    3. 同步期货合约列表（获取最新主力合约信息）
    4. 计算活跃品种的技术指标和策略信号
    5. 检查是否需要开仓
    6. 更新持仓跟踪价格
    7. 检查是否需要平仓
    8. 检查是否需要移仓
    9. 邮件通知今日持仓、信号和操作建议
    10. 关闭TqApi连接
    """
    api = None
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:daily_close'):
            close_old_connections()

            # 第1步：创建TqApi连接
            api = create_tqapi()
            print("[INFO] TqApi连接已建立")
            # 第2步：检查是否为交易日
            if skip_if_not_trade_day(api=api):
                # 如果不是交易日期，直接返回
                return

            # 第3步：同步期货合约列表
            sync_contract_list_from_tqsdk(api=api)

            # 第4步：同步所有合约的K线数据
            print("[INFO] 开始同步K线数据...")
            sync_kline_data_from_tqsdk(api=api)
            print("[INFO] K线数据同步完成")

            # 第5步：计算品种技术指标（基于 AccountContractConfig + 持仓品种）
            active_product_codes = AccountContractConfig.objects.filter(
                is_active=True,
                account__is_active=True
            ).values_list('product_code', flat=True).distinct()
            # 同时计入有持仓的品种（即使已停用，仍需更新指标维持止损跟踪）
            position_product_codes = PositionState.objects.filter(
                units__gt=0
            ).values_list('product_code', flat=True).distinct()
            all_product_codes = set(active_product_codes) | set(position_product_codes)
            active_contracts = FullContractList.objects.filter(
                product_code__in=all_product_codes
            ).values('symbol', 'product_code')

            indicator_results = []

            if active_contracts:
                success_count = 0
                fail_count = 0

                for contract in active_contracts:
                    try:
                        # 传入api实例，避免重复创建连接
                        result = calculate_indicators(
                            api=api,
                            symbol=contract['symbol'],
                            product_code=contract['product_code'],
                            days=60
                        )

                        if result:
                            indicators = result.copy()
                            del indicators['breakout_info']
                            del indicators['data_points']

                            PositionState.objects.filter(symbol=contract['symbol']).update(
                                indicators=indicators,
                                latest_close_price=result['latest_close'],
                                h20_price=result['h_20'],
                                l20_price=result['l_20'],
                            )

                            indicator_results.append(result)
                            success_count += 1
                        else:
                            fail_count += 1
                            log_trade('job_daily_close_calculation',
                                      f"{contract['symbol']} 指标计算返回空，跳过",
                                      symbol=contract['symbol'], log_level='WARNING')

                    except Exception as e:
                        fail_count += 1
                        msg = f"计算指标失败 {contract['symbol']}: {e}"
                        print(f"[ERROR] {msg}")
                        log_trade('job_daily_close_calculation', msg,
                                  symbol=contract['symbol'], log_level='ERROR')

                print(f"[INFO] 指标计算完成: 成功{success_count}个, 失败{fail_count}个")

            # 第6-13步：遍历所有活跃账户，执行账户级操作
            accounts = TradingAccount.objects.filter(is_active=True)

            for account in accounts:
                # 每个账户独立创建 TqApi 连接（实盘用 TqAccount，模拟盘用各自的 TqKq）
                account_api = None
                try:
                    account_api = create_tqapi(account)

                    account_product_codes = set(
                        AccountContractConfig.objects.filter(
                            account=account, is_active=True
                        ).values_list('product_code', flat=True)
                    )
                    account_results = [
                        r for r in indicator_results
                        if r['product_code'] in account_product_codes
                    ]

                    if account_results:
                        open_count = 0
                        for result in account_results:
                            breakout_info = result.get('breakout_info', {})
                            if breakout_info.get('is_breakout'):
                                success = check_breakout_signal(
                                    symbol=result['symbol'],
                                    product_code=result['product_code'],
                                    trend_factor=result['trend_factor'],
                                    trend_label=result['trend_label'],
                                    breakout_info=breakout_info,
                                    account=account,
                                    trade_type='ENTRY'
                                )
                                if success:
                                    open_count += 1
                        print(f"[INFO] {account.name} 开仓信号生成: {open_count}个")

                    update_all_positions_high_low_price(account)
                    print(f"[INFO] {account.name} 更新持仓高低价完成")
                    update_all_positions_stop_loss_price(api=account_api, account=account)
                    print(f"[INFO] {account.name} 更新持仓止损价完成")
                    check_exit_signals(account)
                    print(f"[INFO] {account.name} 持仓退出信号生成完成")
                    check_add_position_signals(account)
                    print(f"[INFO] {account.name} 持仓加仓信号生成完成")
                    check_rollover_signals(account)
                    print(f"[INFO] {account.name} 持仓轮换信号生成完成")
                    generate_daily_signal_report(account)
                    print(  f"[INFO] {account.name} 日报生成完成")

                    if account_api:
                        try:
                            # 账户数据在前序操作中已到达，轻量等待确保最新
                            account_api.wait_update(deadline=time.time() + 2)

                            api_account = account_api.get_account()
                            print(f"[INFO] {account.name} 更新数据")
                            api_account_data = {
                                'balance': float(api_account.balance),
                                'static_balance': float(api_account.static_balance),
                                'available': float(api_account.available),
                                'margin': float(api_account.margin),
                                'float_profit': float(api_account.float_profit),
                                'close_profit': float(api_account.close_profit),
                                'commission': float(api_account.commission),
                                'risk_ratio': float(api_account.risk_ratio),
                                'pre_balance': float(api_account.pre_balance),
                            }
                            result = update_all_performance_metrics(
                                account=account,
                                api_account_data=api_account_data,
                                trade_date=date.today()
                            )
                            print(f"[SUCCESS] {account.name} ✅ 三层绩效数据已更新")
                            print(f"  - 日权益快照: balance={result['snapshot'].balance}")
                            print(f"  - 滚动指标: sharpe_20d={result['rolling_metrics'][20].sharpe_ratio}")
                            print(f"  - 账户总览: total_return={result['summary'].total_return}%")
                        except Exception as perf_error:
                            print(f"[ERROR] {account.name} 更新绩效指标失败: {perf_error}")
                            traceback.print_exc()

                except Exception as account_error:
                    print(f"[ERROR] 处理账户 {account.name} 任务失败: {account_error}")
                    traceback.print_exc()
                finally:
                    if account_api:
                        safe_close_api(account_api)

            print("[INFO] ✅ 今日收盘计算任务完成")

    except LockAcquisitionError:
        print("[INFO] 收盘计算任务正在执行中，跳过本次调度")
    except Exception as e:
        print(f"[ERROR] 收盘计算任务失败: {e}")
        traceback.print_exc()
    finally:
        safe_close_api(api)
