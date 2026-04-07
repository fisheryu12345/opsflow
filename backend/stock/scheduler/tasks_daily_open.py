import time
from tqsdk import TqApi, TqAuth
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from stock.models import TradingAccount, PositionState, TradeExecution,RolloverLog, TrendInfo

def rollover_positions(api, pos):
    """
    执行移仓换月操作
    逻辑：平仓旧合约 -> 开仓新合约
    建议在次日开盘后由 APScheduler 触发
    """
   
    # 查询所有标记为需要移仓的持仓
    pending_rollovers = PositionState.objects.filter(
        is_rollover_needed=True
    )
    
    if not pending_rollovers.exists():
        return

    print(f"🔄 开始执行 {pending_rollovers.count()} 笔移仓任务...")

    for pos in pending_rollovers:
        old_symbol = pos.symbol
        new_symbol = pos.target_rollover_symbol
        volume = pos.volume # 移仓通常保持手数不变
        direction = pos.direction # 1多, -1空
        
        print(f"🔄 正在移仓: {old_symbol} -> {new_symbol}, 手数: {volume}")
        
        try:
            # --- 第一步：平掉旧合约 ---
            # TqApi 平仓指令
            close_order = api.insert_order(
                symbol=old_symbol,
                direction="SELL" if direction == 1 else "BUY",
                offset="CLOSE",
                volume=volume
            )
            
            # 等待成交 (实盘中建议使用 wait_update 轮询成交状态，这里简化处理)
            # 在实际 APScheduler 任务中，可能需要分步状态机来处理“等待成交”
            # 这里假设快速成交
            print(f"✅ 平仓指令已发送: {close_order}")
            
            # --- 第二步：开仓新合约 ---
            # 获取新合约的最新价用于限价单
            new_quote = api.get_quote(new_symbol)
            price = new_quote.last_price
            
            open_order = api.insert_order(
                symbol=new_symbol,
                direction="BUY" if direction == 1 else "SELL",
                offset="OPEN",
                volume=volume,
                limit_price=price
            )
            
            print(f"✅ 开仓指令已发送: {open_order}")
            
            # --- 第三步：更新数据库状态 ---
            with transaction.atomic():
                # 更新原记录指向新合约
                pos.symbol = new_symbol
                pos.is_rollover_needed = False
                pos.target_rollover_symbol = None
                # 注意：这里只是更新了 symbol，实际实盘中可能需要重新计算 ATR 和止损价
                pos.save()
                
                # 更新日志状态
                log = RolloverLog.objects.filter(
                    old_symbol=old_symbol, 
                    new_symbol=new_symbol, 
                    status='PENDING'
                ).first()
                if log:
                    log.status = 'COMPLETED'
                    log.save()
                    
        except Exception as e:
            print(f"❌ 移仓失败: {e}")
            # 失败时不要清除 is_rollover_needed，下次轮询会继续尝试
            
def execute_order_logic(api, pos, account, symbol):
    """
    执行具体的下单逻辑
    """
    print(f"🔥 准备执行: {symbol} - {'买入' if pos.pending_direction == 1 else '卖出'} - {pos.pending_contracts}手")
    try:
        # 1. 获取当前行情
        quote = api.get_quote(symbol)
        api.wait_update()  # 等待行情更新

        direction = "BUY" if pos.pending_direction == 1 else "SELL"
        offset = "OPEN"
        price = quote.ask_price1 if pos.pending_direction == 1 else quote.bid_price1

        # 2. 发送下单指令
        order = api.insert_order(
            symbol=symbol,
            direction=direction,
            offset=offset,
            volume=pos.pending_contracts,
            limit_price=price
        )
        print(f"✅ 指令已发送: OrderID={order.order_id}, 价格={price}")

        # 3. 记录交易流水
        with transaction.atomic():
            TradeExecution.objects.create(
                account=account,
                symbol=symbol,
                trade_type='ENTRY',
                direction=pos.pending_direction,
                volume=pos.pending_contracts,
                price=price,
                trade_time=timezone.now(),
                trigger_price=price
            )
        return True

    except Exception as e:
        print(f"❌ 下单失败: {e}")
        return False

def check_and_execute_pending():
    """
    查询所有 pending 状态的持仓并尝试执行
    """
    pending_positions = PositionState.objects.filter(
        ~Q(pending_direction=0)
    ).select_related('account')

    if not pending_positions.exists():
        return

    print(f"🔍 扫描到 {pending_positions.count()} 个待处理挂单...")

    # 用 with 自动管理 TqApi 连接
    with TqApi(auth=TqAuth("your_username", "your_password")) as api:
        for pos in pending_positions:
            account = pos.account
            symbol = pos.symbol

            success = execute_order_logic(api, pos, account, symbol)
            if success:
                with transaction.atomic():
                    pos.pending_direction = 0
                    pos.pending_contracts = 1
                    pos.pending_trend_factor = 0
                    pos.save()
                    print(f"🔄 状态已更新: {symbol} pending 已清除")
