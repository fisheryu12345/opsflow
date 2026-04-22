import pandas as pd
import numpy as np
from datetime import date, timedelta
from django.db import transaction
from decimal import Decimal
from tqsdk import TqApi, TqAuth
from stock.tasks.send_mail import send_email_task as send_email
from django.template.loader import render_to_string


# 假设你的 models 在 myapp.models 中
from stock.models import TradingAccount,DailyStrategySignal, PositionState, FullContractList
from stock.utils.sync_contract_list_from_tqsdk import sync_contract_list_from_tqsdk
from stock.utils.calculate_indicators import calculate_indicators

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
    
        with transaction.atomic():
            DailyStrategySignal.objects.update_or_create(
                account=account,
                symbol=symbol,
                product_code=product_code,
                trade_date=date.today(),
                defaults={
                    'trend_factor': Decimal(str(trend_factor)),
                    'trend_label': trend_label,

                    'donchian_upper': Decimal(str(breakout_info['entry_high'])) if breakout_info['entry_high'] else None,
                    'donchian_lower': Decimal(str(breakout_info['entry_low'])) if breakout_info['entry_low'] else None,
                    'is_breakout': breakout_info['is_breakout'],
                    'signal_direction': breakout_info['signal_direction'],
                    'trade_type': trade_type,
                    'remark': breakout_info['remark'] or f"趋势状态: {trend_label} (factor={trend_factor})"
                }
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
                DailyStrategySignal.objects.update_or_create(
                    account=default_account,
                    symbol=position.symbol,
                    product_code=position.product_code,
                    trade_date=date.today(),
                    defaults={
                        'trend_factor': position.indicators.get('trend_factor', 0) if position.indicators else 0,
                        'trend_label': position.indicators.get('trend_label', '') if position.indicators else '',
                        'donchian_upper': None,
                        'donchian_lower': None,
                        'is_breakout': False,
                        'signal_direction': 0,
                        'trade_type': 'STOP_LOSS',
                        'remark': remark
                    }
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
                DailyStrategySignal.objects.update_or_create(
                    account=default_account,
                    symbol=position.symbol,
                    product_code=position.product_code,
                    trade_date=date.today(),
                    defaults={
                        'trend_factor': position.indicators.get('trend_factor', 0) if position.indicators else 0,
                        'trend_label': position.indicators.get('trend_label', '') if position.indicators else '',
                        'donchian_upper': None,
                        'donchian_lower': None,
                        'is_breakout': False,
                        'signal_direction': 0,
                        'trade_type': 'ROLLOVER',
                        'remark': f"需要移仓到新主力合约 {main_contract.symbol}"
                    }
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
    - 多头：今日收盘价 - 上次加仓价 > 0.5×ATR → 加仓1单位
    - 多头：今日收盘价 - 上次加仓价 > 1.0×ATR 且 当前持仓=1单位 → 加仓2单位
    - 空头：上次加仓价 - 今日收盘价 > 0.5×ATR → 加仓1单位
    - 空头：上次加仓价 - 今日收盘价 > 1.0×ATR 且 当前持仓=1单位 → 加仓2单位
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
                current_units = position.units  # ← 当前策略单位数（1或2）
                
                # 计算价格差
                price_diff = latest_price - last_add_price
                
                add_units = 0  # 需要加仓的单位数
                
                if position.direction == 1:
                    # 多头持仓：价格上涨才加仓
                    if price_diff > Decimal('1') * atr_value:
                        # 涨幅超过 1×ATR
                        # 只有当前持仓为1单位时，才能加2单位（1+2=3）
                        # 如果当前持仓为2单位，只能加1单位（2+1=3）
                        if current_units == 1:
                            add_units = 2
                        else:  # current_units == 2
                            add_units = 1
                    elif price_diff > Decimal('0.5') * atr_value:
                        # 涨幅超过 0.5×ATR，加仓1单位
                        add_units = 1
                
                elif position.direction == -1:
                    # 空头持仓：价格下跌才加仓
                    # 对于空头，price_diff 为负值表示价格下跌
                    if price_diff < Decimal('-1') * atr_value:
                        # 跌幅超过 1×ATR
                        # 只有当前持仓为1单位时，才能加2单位（1+2=3）
                        # 如果当前持仓为2单位，只能加1单位（2+1=3）
                        if current_units == 1:
                            add_units = 2
                        else:  # current_units == 2
                            add_units = 1
                    elif price_diff < Decimal('-0.5') * atr_value:
                        # 跌幅超过 0.5×ATR，加仓1单位
                        add_units = 1
                
                # 如果满足加仓条件，生成加仓信号
                if add_units > 0:
                    # 【最终安全检查】确保加仓后不超过3单位
                    new_units = current_units + add_units
                    if new_units > 3:
                        add_units = 3 - current_units  # 调整为最多只能加到3单位
                    
                    DailyStrategySignal.objects.update_or_create(
                        account=default_account,
                        symbol=position.symbol,
                        product_code=position.product_code,
                        trade_date=date.today(),
                        defaults={
                            'trend_factor': position.indicators.get('trend_factor', 0),
                            'trend_label': position.indicators.get('trend_label', ''),
                            'donchian_upper': None,
                            'donchian_lower': None,
                            'is_breakout': False,
                            'signal_direction': position.direction,
                            'trade_type': 'ADD_ON',
                            'contract_target_number': add_units,  # ← 新增：直接存储目标加仓单位数
                            'remark': f"加仓信号: {'多头' if position.direction == 1 else '空头'} "
                                     f"价格差={float(price_diff):.2f}, ATR={float(atr_value):.2f}, "
                                     f"建议加仓{add_units}单位 (当前{current_units}→{current_units + add_units})"
                        }
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
        
        from celery import current_app
        print("Broker URL:", current_app.conf.broker_url)
        print("Backend URL:", current_app.conf.result_backend)
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
                        PositionState.objects.filter(id=position.id).update(highest_close=position.latest_close_price)
                if position.direction == -1:
                    if position.latest_close_price < position.lowest_close:
                        PositionState.objects.filter(id=position.id).update(lowest_close=position.latest_close_price)
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
def update_all_positions_stop_loss_price():
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
                
                # 根据持仓方向选择基准价格和计算止损价
                if position.direction == 1:
                    # 多头持仓：使用最高价作为基准
                    if not position.highest_close:
                        print(f"[SKIP] {position.symbol}: 缺少最高价数据")
                        continue
                    
                    # 多头止损价 = 最高价 - 2(1+factor) * ATR
                    new_stop_loss = position.highest_close - Decimal('2') * (Decimal('1') + factor) * atr_value
                    
                    print(f"[UPDATE] {position.symbol} 多头止损: 最高价={position.highest_close}, ATR={atr_value}, factor={factor}, 止损价={new_stop_loss}")
                    
                elif position.direction == -1:
                    # 空头持仓：使用最低价作为基准
                    if not position.lowest_close:
                        print(f"[SKIP] {position.symbol}: 缺少最低价数据")
                        continue
                    
                    # 空头止损价 = 最低价 + 2(1+factor) * ATR
                    new_stop_loss = position.lowest_close + Decimal('2') * (Decimal('1') + factor) * atr_value
                    
                    print(f"[UPDATE] {position.symbol} 空头止损: 最低价={position.lowest_close}, ATR={atr_value}, factor={factor}, 止损价={new_stop_loss}")
                else:
                    continue
                
                # 更新止损价格（保持 Decimal 类型）
                PositionState.objects.filter(id=position.id).update(
                    stop_loss_price=new_stop_loss,
                    trend_info=f'{atr_value:.2f},  {factor:.2f}'
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
    2. 同步期货合约列表（获取最新主力合约信息）
    3. 计算活跃品种的技术指标和策略信号
    4. 检查是否需要开仓
    5. 更新持仓跟踪价格
    6. 检查是否需要平仓
    7. 检查是否需要移仓
    8. 邮件通知今日持仓、信号和操作建议
    9. 关闭TqApi连接
    """
    api = None
    try:
        # 第1步：创建TqApi连接
        api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
        print("[INFO] TqApi连接已建立")
        
        # 第2步：同步期货合约列表
        sync_contract_list_from_tqsdk(api=api)
        
        # 第3步：计算活跃品种的技术指标
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
        
        # 第4步：检查是否需要开仓（保存信号到数据库）
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
    
        # 第5步：计算持仓后出现的历史收盘最高低价格
        update_all_positions_high_low_price()
        
        # 第6步：止损价格计算
        update_all_positions_stop_loss_price()
        
        # 第7步：检查是否需要平仓
        check_exit_signals()

        # 第8步：检查加仓信号
        check_add_position_signals()
        
        # 第9步：检查是否需要移仓
        check_rollover_signals()
        
        # 第10步：生成并发送每日策略信号报告邮件
        generate_daily_signal_report()
        
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
