import time
from decimal import Decimal
from django.utils import timezone
from datetime import date
from tqsdk import TqApi, TqAuth, TargetPosTask,TqAccount , TqKq,TqSim
from django.db import transaction,close_old_connections
from django.db.models import Q, F
from stock.utils.is_trade_day import  skip_if_not_trade_day
from stock.models import TradingAccount, PositionState, DailyStrategySignal, ClosedPositionRecord, FullContractList
from stock.scheduler.calculate_unit_lots import calculate_unit_lots
from stock.scheduler.calculate_atr import calculate_atr, price_gap_protection
from stock.scheduler.send_report import send_open_report
from stock.utils.log_util import log_trade, log_error
from stock.scheduler.check_min_position_requirement import check_min_position_requirement,execute_two_step_opening
from stock.parameter_config import TIMEOUT_SECONDS, POSITION_MAX_UNITS
import time


def execute_stop_loss_exit(api, position):
    """
    使用 TargetPosTask 执行止损平仓
    
    参数：
    api: TqApi实例
    position: PositionState实例
    
    返回：
    tuple: (是否成功, 成交手数, 成交均价)
    """
    try:
        from tqsdk import TargetPosTask
        
        print(f"[INFO] 开始执行止损平仓: {position.symbol} (当前持仓={position.contract_total_position}手)")
        
        # 边界检查：如果没有持仓，直接返回成功
        if position.contract_total_position <= 0:
            return True, 0, Decimal('0')
        
        # 创建目标持仓任务
        target_pos = TargetPosTask(api, position.symbol)
        
        # 设置目标持仓为 0（全部平仓）
        target_pos.set_target_volume(0)
        
        # 等待任务完成（最多60秒）
        start_time = time.time()
        while not target_pos.is_finished():
            api.wait_update(deadline=time.time() + 1)
            
            # 超时检查
            if time.time() - start_time > 60:
                print(f"⚠️ 止损平仓超时: {position.symbol}")
                return False, 0, Decimal('0')
        
        # 任务完成，查询实际成交信息
        trades = api.get_trades()
        filled_volume = 0
        total_cost = Decimal('0')
        
        # 查找该合约最近的平仓成交记录
        for trade in reversed(trades.values()):
            if (trade.instrument_id == position.symbol and 
                trade.offset == 'CLOSE'):
                
                filled_volume += trade.volume
                total_cost += Decimal(str(trade.price)) * Decimal(str(trade.volume))
                
                # 如果累计成交量达到预期，停止搜索
                if filled_volume >= position.contract_total_position:
                    break
        
        # 计算加权平均成交价
        if filled_volume > 0:
            avg_price = total_cost / Decimal(str(filled_volume))
        else:
            # 如果没有找到成交记录，使用最新价作为近似值
            quote = api.get_quote(position.symbol)
            avg_price = Decimal(str(quote.last_price)) if quote.last_price else Decimal('0')
            filled_volume = position.contract_total_position
        
        print(f"✅ 止损平仓成功: {position.symbol} 成交量={filled_volume}, 均价={avg_price:.2f}")
        return True, filled_volume, avg_price
            
    except Exception as e:
        print(f"[ERROR] 止损平仓异常: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, Decimal('0')


def check_and_execute_stop_loss(api):
    """
    检查持仓止损并执行平仓
    
    流程：
    1. 查询所有有持仓的记录
    2. 检查是否触发止损
    3. 如果触发，先检查是否有未执行的止损信号（防重复）
    4. 创建 STOP_LOSS 信号记录
    5. 调用 execute_stop_loss_exit 执行平仓
    """
    try:
        default_account = TradingAccount.objects.filter(is_active=True).first()
        if not default_account:
            print("[WARN] 未找到活跃账户，跳过止损检查")
            return
        
        # 【优化】使用数据库层面的条件过滤，直接查询触发止损的持仓
        # 多头止损条件：direction=1 AND latest_close_price < stop_loss_price
        long_stop_loss = Q(direction=1) & Q(latest_close_price__lt=F('stop_loss_price'))
        
        # 空头止损条件：direction=-1 AND latest_close_price > stop_loss_price
        short_stop_loss = Q(direction=-1) & Q(latest_close_price__gt=F('stop_loss_price'))
        
        # 合并条件：满足任一即可，同时确保价格字段非空
        positions = PositionState.objects.filter(
            account=default_account,
            units__gt=0,
            latest_close_price__isnull=False,  # 确保最新价格存在
            stop_loss_price__isnull=False      # 确保止损价存在
        ).filter(long_stop_loss | short_stop_loss)
        
        exit_count = 0
        
        for position in positions:
            try:
                # 【简化】由于已在数据库层面过滤，此处无需再次判断止损条件
                latest_price = float(position.latest_close_price)
                stop_loss = float(position.stop_loss_price)
                
                # 构建备注信息
                if position.direction == 1:
                    remark = f"多头止损触发: 最新价{latest_price:.2f} < 止损价{stop_loss:.2f}"
                else:
                    remark = f"空头止损触发: 最新价{latest_price:.2f} > 止损价{stop_loss:.2f}"
                
                # 检查是否存在未执行的止损信号，避免跨日期重复生成
                last_stop_signal = DailyStrategySignal.objects.filter(
                    account=default_account,
                    symbol=position.symbol,
                    trade_type='STOP_LOSS',
                    executed_status='PENDING'
                ).order_by('-trade_date').first()
                
                if last_stop_signal:
                    print(f"[SKIP] 跳过重复止损信号 {position.symbol}: 存在未执行的STOP_LOSS信号（{last_stop_signal.trade_date}）")
                    log_trade('check_and_execute_stop_loss', 
                             f"[SKIP] 跳过重复止损信号 {position.symbol}: 存在未执行的STOP_LOSS信号",
                             symbol=position.symbol, log_level='INFO')
                    continue
                
                # 创建止损信号记录
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
                    executed_status='EXECUTING'
                )
                
                print(f"[EXIT] 止损信号: {position.symbol} - {remark}")
                
                # 执行平仓操作（使用 TargetPosTask）
                success, filled_volume, avg_price = execute_stop_loss_exit(api, position)
                
                if success and filled_volume > 0:
                    exit_count += 1
                    
                    with transaction.atomic():
                        # 创建平仓记录
                        ClosedPositionRecord.objects.create(
                            account=position.account,
                            symbol=position.symbol,
                            product_code=position.product_code,
                            direction=position.direction,
                            volume=filled_volume,
                            exit_price=avg_price,
                            cost_price=position.cost_price,
                            pnl=(avg_price - position.cost_price) * Decimal(str(filled_volume)),
                            trade_date=date.today(),
                            executed_at=timezone.now(),
                        )
                        
                        # 更新持仓状态为已平仓
                        PositionState.objects.filter(id=position.id).update(
                            units=0,
                            direction=0,
                            contract_total_position=0,
                            stop_loss_price=None,
                            highest_close=None,
                            lowest_close=None,
                            protect_cost_enalbed=False,
                            last_update_time=timezone.now()
                        )
                    
                    # 更新信号状态为成功
                    DailyStrategySignal.objects.filter(
                        account=default_account,
                        symbol=position.symbol,
                        trade_type='STOP_LOSS',
                        executed_status='EXECUTING'
                    ).update(executed_status='SUCCESS')
                    
                    log_trade('check_and_execute_stop_loss', 
                             f"✅ 止损平仓成功: {position.symbol} 成交量={filled_volume}, 均价={avg_price:.2f}",
                             symbol=position.symbol, log_level='SUCCESS')
                else:
                    # 更新信号状态为失败
                    DailyStrategySignal.objects.filter(
                        account=default_account,
                        symbol=position.symbol,
                        trade_type='STOP_LOSS',
                        executed_status='EXECUTING'
                    ).update(executed_status='FAILED')
                    
                    log_trade('check_and_execute_stop_loss', 
                             f"❌ 止损平仓失败: {position.symbol}",
                             symbol=position.symbol, log_level='ERROR')
                
            except Exception as pos_error:
                print(f"[ERROR] 处理 {position.symbol} 止损检查失败: {pos_error}")
                import traceback
                traceback.print_exc()
                continue
        
        if exit_count > 0:
            print(f"[SUMMARY] 今日共执行 {exit_count} 个止损平仓")
            log_trade('check_and_execute_stop_loss', 
                     f"[SUMMARY] 今日共执行 {exit_count} 个止损平仓",
                     symbol='N/A', log_level='SUCCESS')
        else:
            print(f"[INFO] 本次检查未发现触发止损的持仓")
        
    except Exception as e:
        print(f"[ERROR] 检查并执行止损失败: {e}")
        import traceback
        traceback.print_exc()


def execute_exit_before_close():
    """
    在收盘前执行平仓操作，确保所有持仓在收盘前被正确处理。
    主要步骤：
    1. 获取所有当前持仓。
    2. 对于每个持仓，检查是否满足平仓条件（如止损、止盈、时间到等）。
    3. 如果满足条件，执行平仓操作，并记录相关信息。
    4. 确保所有操作在收盘前完成。
    """
    api = None
    try:
        close_old_connections()
        log_trade('execute_exit_before_close', "开始执行收盘前平仓任务", symbol='N/A', log_level='INFO')
        
        # 创建TqApi连接
        api = TqApi(TqKq(), auth=TqAuth("yupei1986", "yupei1986"))
        
        # 第2步：检查是否为交易日
        if skip_if_not_trade_day(api=api):
            return  # 非交易日，直接返回
        
        # 检查并执行止损平仓
        check_and_execute_stop_loss(api)
        
        print("[INFO] ✅ 收盘前平仓任务完成")
        
    except Exception as e:
        log_error('execute_exit_before_close', f"收盘前平仓任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保TqApi连接被关闭
        if api:
            api.close()
            print("[INFO] TqApi连接已关闭")