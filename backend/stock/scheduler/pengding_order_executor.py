import time
import datetime
from tqsdk import TqApi, TqAuth
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

# 假设 models 路径
from stock.models import TradingAccount, PositionState, TradeExecution

def execute_order_logic(api, pos, account, symbol):
    """
    执行具体的下单逻辑
    """
    print(f"🔥 准备执行: {symbol} - {'买入' if pos.pending_direction == 1 else '卖出'} - {pos.pending_contracts}手")
    
    try:
        # 1. 获取当前行情 (用于确认价格和发送指令)
        quote = api.get_quote(symbol)
        
        # 2. 构建交易指令
        # 注意：这里使用限价单（Limit Order）还是市价单（Market Order）取决于你的策略偏好
        # 既然已经确认突破，通常为了成交使用“对手价”或者“市价”
        
        direction = "BUY" if pos.pending_direction == 1 else "SELL"
        # 期货通常使用 OPEN (开仓)
        offset = "OPEN" 
        
        # 使用对手价确保快速成交
        price = quote.ask_price1 if pos.pending_direction == 1 else quote.bid_price1
        
        # 3. 发送指令
        # insert_order 会立即返回，但成交是异步的
        order_id = api.insert_order(
            symbol=symbol, 
            direction=direction, 
            offset=offset, 
            volume=pos.pending_contracts, 
            limit_price=price # 限价单
        )
        
        print(f"✅ 指令已发送: OrderID={order_id}, 价格={price}")
        
        # 4. 记录交易流水 (TradeExecution)
        with transaction.atomic():
            TradeExecution.objects.create(
                account=account,
                symbol=symbol,
                trade_type='ENTRY', # 这里假设 pending 都是开仓，如果是平仓逻辑需调整
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
    核心轮询函数：
    1. 查询所有 pending 状态的持仓
    2. 尝试执行
    3. 执行成功后清除 pending 状态
    """
    # 1. 查询数据库：找出所有有待办任务的持仓
    # 只要 pending_direction 不为 0，就代表需要处理
    pending_positions = PositionState.objects.filter(
        pending_direction__ne=0
    ).select_related('account') # 优化查询，一次性获取账户信息
    
    if not pending_positions.exists():
        # 调试模式下可以注释掉这行，避免日志太多
        # print("🔍 扫描完毕：当前无待处理挂单")
        pass
        return

    print(f"🔍 扫描到 {pending_positions.count()} 个待处理挂单...")

    # 初始化 TqApi (建议每次循环重新初始化或保持单例，这里为了简单在函数内初始化)
    # 注意：频繁初始化 TqApi 可能会慢，生产环境建议将 api 作为全局变量或单例管理
    # 但为了 APScheduler 的独立性，这里假设 api 是全局的或者在这里创建
    # 如果 api 是全局的，请确保它已经连接
    pass 

    # 这里的 api 应该是一个全局连接对象，或者在外部传入
    # 为了演示，我们假设有一个全局的 api 对象在 job_trade_loop 中管理
    # 但由于 APScheduler 的特性，我们最好在这里通过某种方式获取 api
    # *修正*：为了保持连接稳定，建议 api 在全局初始化，或者使用单例模式。
    # 下面的代码假设 `global_api` 已经在外部定义并连接。
    global global_api
    if not global_api:
         print("⚠️ TqApi 尚未连接，跳过本次轮询")
         return

    for pos in pending_positions:
        account = pos.account
        symbol = pos.symbol
        
        # 执行下单
        success = execute_order_logic(global_api, pos, account, symbol)
        
        if success:
            # 5. 更新数据库状态：清除 pending 标记
            # 这一步非常关键，防止重复下单
            with transaction.atomic():
                pos.pending_direction = 0
                pos.pending_contracts = 1 # 重置为默认值
                pos.pending_trend_factor = 0
                pos.save()
                print(f"🔄 状态已更新: {symbol} pending 已清除")