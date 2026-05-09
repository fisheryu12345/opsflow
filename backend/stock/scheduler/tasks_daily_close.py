import pandas as pd
import numpy as np
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction,close_old_connections
from decimal import Decimal
from tqsdk import TqApi, TqAuth,TqKq
from stock.utils.log_util import log_trade, log_error
from stock.tasks.send_mail import send_email_task as send_email
from django.template.loader import render_to_string
from stock.utils.is_trade_day import  skip_if_not_trade_day


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,DailyStrategySignal, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk
from stock.utils.calculate_indicators import calculate_indicators
from stock.scheduler.performance_cal import update_all_performance_metrics
from stock.parameter_config import PROTECT_COST_ENABLED_RATIO

def check_breakout_singal(symbol, product_code, trend_factor, trend_label, 
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
            print(f"[SKIP] 跳过重复开仓信号 {symbol}: 存在未执行的ENTRY信号（{last_entry_signal.trade_date}）")
            log_trade('check_breakout_singal', f"[SKIP] 跳过重复开仓信号 {symbol}: 存在未执行的ENTRY信号（{last_entry_signal.trade_date}）",
                      symbol=symbol,log_level='INFO')
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


def check_exit_signals():
    """
    步骤5：检查是否需要平仓（考虑期货多空特性）
    
    止损逻辑：
    - 多头持仓(direction=1): 最新收盘价 < 止损价 -> 触发止损
    - 空头持仓(direction=-1): 最新收盘价 > 止损价 -> 触发止损
    """
    try:
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            return
        
        # 查询所有有持仓的记录（units > 0 且 direction != 0）
        positions = PositionState.objects.filter(
            account=default_account,
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
                # 【修复】检查是否存在未执行的止损信号，避免跨日期重复生成
                last_stop_signal = DailyStrategySignal.objects.filter(
                    account=default_account,
                    symbol=position.symbol,
                    trade_type='STOP_LOSS',
                    executed_status='PENDING'
                ).order_by('-trade_date').first()
                
                if last_stop_signal:
                    print(f"[SKIP] 跳过重复止损信号 {position.symbol}: 存在未执行的STOP_LOSS信号（{last_stop_signal.trade_date}）")
                    log_trade('check_exit_signals', f"[SKIP] 跳过重复止损信号 {position.symbol}: 存在未执行的STOP_LOSS信号（{last_stop_signal.trade_date}）",
                              symbol=position.symbol,log_level='INFO')
                    continue
                
                DailyStrategySignal.objects.create(
                    account=default_account,
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


def check_rollover_signals():
    """
    步骤6：检查是否需要移仓（根据is_rollover_needed字段）
    
    逻辑：
    - 如果is_rollover_needed=True，说明主力合约发生变化且有持仓，需要移仓
    - 生成移仓信号，提醒用户进行移仓操作
    """
    try:
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            return
        
        # 查询所有需要移仓的记录
        rollover_positions = PositionState.objects.filter(
            account=default_account,
            is_rollover_needed=True,
            units__gt=0  # 只处理有持仓的记录
        )
        
        rollover_count = 0
        
        for position in rollover_positions:
            # 获取新的主力合约信息
            main_contract = FullContractList.objects.filter(
                product_code=position.product_code,
                is_active=True
            ).first()
            
            if main_contract:
                # 【修复】检查是否存在未执行的移仓信号，避免跨日期重复生成
                last_rollover_signal = DailyStrategySignal.objects.filter(
                    account=default_account,
                    symbol=position.symbol,
                    trade_type='ROLLOVER',
                    executed_status='PENDING'
                ).order_by('-trade_date').first()
                
                if last_rollover_signal:
                    print(f"[SKIP] 跳过重复移仓信号 {position.symbol}: 存在未执行的ROLLOVER信号（{last_rollover_signal.trade_date}）")
                    log_trade('check_rollover_signals', f"[SKIP] 跳过重复移仓信号 {position.symbol}: 存在未执行的ROLLOVER信号（{last_rollover_signal.trade_date}）",
                              symbol=position.symbol,log_level='INFO')
                    continue
                
                DailyStrategySignal.objects.create(
                    account=default_account,
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


def check_add_position_signals():
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
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            return
        
        # 查询所有有持仓且单位数 < 3 的记录
        positions = PositionState.objects.filter(
            account=default_account,
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
                    
                    # 【修复】检查是否存在未执行的加仓信号，避免跨日期重复生成
                    last_add_signal = DailyStrategySignal.objects.filter(
                        account=default_account,
                        symbol=position.symbol,
                        trade_type='ADD_ON',
                        executed_status='PENDING'
                    ).order_by('-trade_date').first()
                    
                    if last_add_signal:
                        print(f"[SKIP] {position.symbol}: 存在未执行的加仓信号（{last_add_signal.trade_date}），跳过重复生成")
                        log_trade('check_add_position_signals', f"[SKIP] {position.symbol}: 存在未执行的加仓信号（{last_add_signal.trade_date}），跳过重复生成",
                                  symbol=position.symbol, log_level='INFO')
                        continue
                    
                    DailyStrategySignal.objects.create(
                        account=default_account,
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



def generate_daily_signal_report():
    """
    步骤7：生成每日策略信号报告并发送邮件
    
    返回：
    bool: 是否成功发送
    """
    try:
        # 获取今日的所有信号
        today = date.today()
        default_account = TradingAccount.objects.filter(is_active=True).first()
        
        if not default_account:
            print("[WARN] 未找到活跃账户，跳过邮件发送")
            return False
        
        # 查询今日信号
        signals = DailyStrategySignal.objects.filter(
            account=default_account,
            trade_date=today
        ).order_by('-trade_date', 'symbol')
        
        if not signals:
            print("[INFO] 今日无策略信号，发送通知邮件")
            
            # 渲染无信号的HTML模板
            context = {
                'report_date': today,
                'account_name': default_account.name,
                'signals': [],
                'summary': {
                    'total_signals': 0,
                    'open_count': 0,
                    'add_on_count': 0,
                    'stop_loss_count': 0,
                    'rollover_count': 0,
                },
                'current_time': pd.Timestamp.now(),
                'no_signal_message': '今日没有产生任何策略信号',
            }
            
            html_content = render_to_string('daily_strategy_signal_report.html', context)
            
            # 异步发送邮件
            send_email(
                subject=f'[量化策略] 每日信号报告 - {today.strftime("%Y-%m-%d")}',
                body=html_content,
                receiver_email='312711936@qq.com',
                is_html=True
            )
            
            print(f"[SUCCESS] 无信号通知邮件已发送")
            return True
        
        # 统计数据
        summary = {
            'total_signals': signals.count(),
            'open_count': signals.filter(trade_type__in=['ENTRY']).count(),
            'stop_loss_count': signals.filter(trade_type='STOP_LOSS').count(),
            'rollover_count': signals.filter(trade_type='ROLLOVER').count(),
            'add_on_count': signals.filter(trade_type='ADD_ON').count(),
        }
        
        # 转换信号数据为字典列表
        signals_data = []
        for signal in signals:
            signals_data.append({
                'symbol': signal.symbol,
                'trade_date': signal.trade_date,
                'trend_factor': float(signal.trend_factor) if signal.trend_factor else None,
                'trend_label': signal.trend_label,
                'donchian_upper': float(signal.donchian_upper) if signal.donchian_upper else None,
                'donchian_lower': float(signal.donchian_lower) if signal.donchian_lower else None,
                'signal_direction': signal.signal_direction,
                'is_breakout': signal.is_breakout,
                'remark': signal.remark,
                'trade_type': signal.trade_type,
            })
        
        # 渲染HTML模板
        context = {
            'report_date': today,
            'account_name': default_account.name,
            'signals': signals_data,
            'summary': summary,
            'current_time': pd.Timestamp.now(),
        }
        
        html_content = render_to_string('daily_strategy_signal_report.html', context)
        
        # 异步发送邮件
        send_email(
            subject=f'[量化策略] 每日信号报告 - {today.strftime("%Y-%m-%d")}',
            body=html_content,
            receiver_email='312711936@qq.com',
            is_html=True
        )
        
        print(f"[SUCCESS] 邮件发送任务已提交: {summary['total_signals']}个信号")
        return True
        
    except Exception as e:
        print(f"[ERROR] 生成邮件报告失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_all_positions_high_low_price():
    """
    计算持仓后出现的历史收盘最高价和最低价
    
    逻辑：
    - 对于每个持仓记录，查询该合约的历史收盘价
    - 更新持仓记录的最高收盘价和最低收盘价字段
    """
    try:
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            print("[WARN] 未找到活跃账户，跳过最高最低价更新")
            return
        
        positions = PositionState.objects.filter(
            account=default_account,
            units__gt=0  # 只处理有持仓的记录
        )
        
        updated_count = 0
        
        for position in positions:
            try:
                # 查询该合约的历史收盘价
                # 开仓日期之前的收盘价不考虑
                # 开仓的时候以开仓价格为初始最高价和最低价，需要再开仓的时候填入。然后每日收盘后更新一次，计算开仓以来的最高价和最低价。
                if position.direction == 1:
                    if position.latest_close_price > position.highest_close:
                        PositionState.objects.filter(id=position.id).update(highest_close=position.latest_close_price,last_update_time=timezone.now())
                if position.direction == -1:
                    if position.latest_close_price < position.lowest_close:
                        PositionState.objects.filter(id=position.id).update(lowest_close=position.latest_close_price,last_update_time=timezone.now())
                updated_count += 1
                
            except Exception as pos_error:
                print(f"[ERROR] 更新 {position.symbol} 最高最低价失败: {pos_error}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[SUCCESS] 已更新 {updated_count}/{positions.count()} 个持仓的最高最低价格")
        
    except Exception as e:
        print(f"[ERROR] 更新最高最低价格失败: {e}")
        import traceback
        traceback.print_exc()
def update_all_positions_stop_loss_price(api):
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
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            print("[WARN] 未找到活跃账户，跳过止损价格更新")
            return
        
        positions = PositionState.objects.filter(
            account=default_account,
            units__gt=0  # 只处理有持仓的记录
        ).exclude(direction=0)
        
        updated_count = 0
        
        for position in positions:
            try:
                # 检查必要数据是否存在
                if not position.indicators:
                    print(f"[SKIP] {position.symbol}: indicators字段为空")
                    continue
                # {"symbol": "SHFE.sp2605", "product_code": "sp", "latest_date": "2026-04-12", "latest_close": 4976.0, "atr_20": 86.0, "ma_10": 5062.2, "ma_20": 5111.5, "ma_40": 5186.6, "close_high_20": 5308.0, "close_low_20": 4978.0, "trend_factor": 0.5, "trend_label": "strong_bear"}
                # 从 indicators 获取 ATR 和 factor（统一转换为 Decimal）
                atr_value = Decimal(str(position.indicators.get('atr_20', 0)))
                factor = Decimal(str(position.indicators.get('trend_factor', 0)))
                trend_label = position.indicators.get('trend_label', '')
                tick = FullContractList.objects.filter(symbol=position.symbol).first().price_tick if FullContractList.objects.filter(symbol=position.symbol).exists() else Decimal('0.01')

                # 获取持仓成本（开仓价或加仓加权均价）
                cost_price = None
                # 根据持仓方向选择基准价格和计算止损价
                if position.direction == 1:
                    # 多头持仓：使用最高价作为基准
                    try:
                        tq_pos = api.get_position(position.symbol)
                        cost_price = tq_pos.open_price_long
                    except Exception as e:
                        log_trade('update_all_positions_stop_loss_price',
                                   f"API获取{position.symbol}多头成本价失败({e})，使用数据库记录",
                                   symbol=position.symbol, log_level='WARNING')
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
                    try:
                        tq_pos = api.get_position(position.symbol)
                        cost_price = tq_pos.open_price_short
                    except Exception as e:
                        log_trade('update_all_positions_stop_loss_price',
                                   f"API获取{position.symbol}空头成本价失败({e})，使用数据库记录",
                                   symbol=position.symbol, log_level='WARNING')
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
                protect_cost_enabled = position.protect_cost_enalbed  # 当前保本状态
                # 计算保本价（基于成本价）
                protect_price = None
                if cost_price:
                    if position.direction == 1:
                        protect_price = Decimal(str(cost_price)) + tick * Decimal('2')
                    elif position.direction == -1:
                        protect_price = Decimal(str(cost_price)) - tick * Decimal('2')
                
                # 首次检查是否满足保本条件
                if not protect_cost_enabled and cost_price and position.latest_close_price:
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
                # 更新持仓仓位成本价格
                PositionState.objects.filter(id=position.id).update(
                    stop_loss_price=dynamic_stop_loss,
                    cost_price=cost_price,
                    last_update_time=timezone.now(),  # 【修复】手动更新最后更新时间
                    trend_info=f'{atr_value:.2f},  {factor:.2f} , {trend_label}',
                    protect_cost_enalbed=protect_cost_enabled,  # 【新增】更新保本状态

                )
                updated_count += 1
                
            except Exception as pos_error:
                print(f"[ERROR] 更新 {position.symbol} 止损价失败: {pos_error}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[SUCCESS] 已更新 {updated_count}/{positions.count()} 个持仓的止损价格")
        
    except Exception as e:
        print(f"[ERROR] 更新止损价格失败: {e}")
        import traceback
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
    try:
        close_old_connections()
        
        # 第1步：创建TqApi连接
        api = TqApi(TqKq(), auth=TqAuth("yupei1986", "yupei1986"))
        # api = TqApi(TqAccount("Y银河期货_CTP七席", "0210003762", "012613"), auth=TqAuth("yupei1986", "yupei1986"))
        print("[INFO] TqApi连接已建立")
        # 第2步：检查是否为交易日
        if skip_if_not_trade_day(api=api): 
            # 如果不是交易日期，直接返回
            return 
         
        # 第3步：同步期货合约列表
        sync_contract_list_from_tqsdk(api=api)
        
        # 第4步：计算活跃品种的技术指标
        contracts = PositionState.objects.all().values('symbol', 'product_code','units')
        for contract in contracts:
            if FullContractList.objects.filter(symbol=contract['symbol'], is_active=True).exists():
                contract['is_active'] = True
        active_contracts = [contract for contract in contracts if contract.get('is_active')]
        
        indicator_results = []
        
        if active_contracts:
            success_count = 0
            fail_count = 0
            
            for contract in active_contracts:
                try:
                    # 传入api实例，避免重复创建连接
                    result = calculate_indicators(
                        api=api,  # ← 传入统一的api实例
                        symbol=contract['symbol'], 
                        product_code=contract['product_code'], 
                        days=60
                    )
                    
                    if result:
                        indicators = result.copy()
                        del indicators['breakout_info']  # 不需要把突破信息存到 indicators 字段里
                        del indicators['data_points']  # 不需要存储数据点数量
                        
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
                        
                except Exception as e:
                    fail_count += 1
                    print(f"[ERROR] 计算指标失败 {contract['symbol']}: {e}")
            
            print(f"[INFO] 指标计算完成: 成功{success_count}个, 失败{fail_count}个")
        
        # 第5步：检查是否需要开仓（保存信号到数据库）
        default_account = TradingAccount.objects.filter(is_active=True).first()
        
        if default_account and indicator_results:
            open_count = 0
            
            for result in indicator_results:
                breakout_info = result.get('breakout_info', {})
                if breakout_info.get('is_breakout'):
                    success = check_breakout_singal(
                        symbol=result['symbol'],
                        product_code=result['product_code'],
                        trend_factor=result['trend_factor'],
                        trend_label=result['trend_label'],
                        breakout_info=breakout_info,
                        account=default_account,
                        trade_type='ENTRY'
                    )
                    
                    if success:
                        open_count += 1
            
            print(f"[INFO] 开仓信号生成: {open_count}个")
    
        # 第6步：计算持仓后出现的历史收盘最高低价格
        update_all_positions_high_low_price()
        
        # 第7步：止损价格计算
        update_all_positions_stop_loss_price(api=api)
        
        # 第8步：检查是否需要平仓
        check_exit_signals()

        # 第9步：检查加仓信号
        check_add_position_signals()
        
        # 第10步：检查是否需要移仓
        check_rollover_signals()
        
        # 第11步：生成并发送每日策略信号报告邮件
        generate_daily_signal_report()
        
        # 第12步：更新三层绩效指标（日权益快照、滚动指标、账户总览）
        if default_account and api:
            try:
                # 从 TqSDK 获取账户数据
                api_account = api.get_account()
                
                # 转换为字典格式（update_all_performance_metrics 需要的格式）
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
                
                # 调用统一更新函数
                result = update_all_performance_metrics(
                    account=default_account,
                    api_account_data=api_account_data,
                    trade_date=date.today()
                )
                
                print(f"[SUCCESS] ✅ 三层绩效数据已更新")
                print(f"  - 日权益快照: balance={result['snapshot'].balance}")
                print(f"  - 滚动指标: sharpe_20d={result['rolling_metrics'][20].sharpe_ratio}")
                print(f"  - 账户总览: total_return={result['summary'].total_return}%")
                
            except Exception as perf_error:
                print(f"[ERROR] 更新绩效指标失败: {perf_error}")
                import traceback
                traceback.print_exc()
        
        print("[INFO] ✅ 今日收盘计算任务完成")

    except Exception as e:
        print(f"[ERROR] 收盘计算任务失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保TqApi连接被关闭
        if api:
            api.close()
            print("[INFO] TqApi连接已关闭")
