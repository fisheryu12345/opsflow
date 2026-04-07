import pandas as pd
from tqsdk import TqApi, TqAuth
from django.db import transaction
from django.utils import timezone
import time

# 假设你的 Models
from stock.models import PositionState, TradeExecution, TradingAccount

# ================= 全局 TqApi 实例 =================
global_api = None

def get_api():
    global global_api
    if global_api is None:
        # 请在此处填入你的快期账户
        print("🔌 正在连接 TqApi (长连接模式)...")
        global_api = TqApi(auth=TqAuth(account_id="YOUR_ACCOUNT_ID", password="YOUR_PASSWORD"))
    return global_api

def execute_add_order(api, pos, symbol, price):
    """
    执行加仓下单
    """
    try:
        direction = "BUY" if pos.direction == 1 else "SELL"
        offset = "OPEN"
        
        # 使用限价单，价格设为触发价（或者根据需求使用对手价）
        order_id = api.insert_order(
            symbol=symbol,
            direction=direction,
            offset=offset,
            volume=pos.add_position_volume,
            limit_price=price
        )
        
        print(f"✅ 加仓指令已发送: {symbol} OrderID={order_id}, 价格={price}")
        
        with transaction.atomic():
            TradeExecution.objects.create(
                account=pos.account,
                symbol=symbol,
                trade_type='ADD_POSITION',
                direction=pos.direction,
                volume=pos.add_position_volume,
                price=price,
                trade_time=timezone.now()
            )
            
            # 关键步骤：加仓后必须更新触发价，防止下一次 tick 继续触发
            # 这里简单地将触发价设为 None，或者你可以计算下一个加仓层级
            pos.add_position_trigger_price = None 
            pos.save()
            print(f"🔄 {symbol} 加仓触发价已清除，防止重复加仓")
            
    except Exception as e:
        print(f"❌ 加仓失败: {e}")

def job_add_position_loop():
    """
    基于 wait_update 的长连接监听循环
    """
    api = get_api()
    print("🚀 加仓监听服务已启动，等待行情推送...")
    
    # 1. 初始化订阅列表
    # 我们不需要一开始就订阅所有，可以定期刷新，或者只订阅有持仓的品种
    # 这里为了简单，我们在循环外先获取一次，实际生产中建议定期重新扫描数据库
    # 但 wait_update 模式下，动态增删订阅比较麻烦，通常建议启动时订阅所有关注合约
    
    # 获取所有活跃且有持仓的合约
    positions = PositionState.objects.filter(
        account__is_active=True,
        direction__ne=0,
        is_add_position_enabled=True,
        add_position_trigger_price__isnull=False
    )
    
    symbols = list(set([pos.symbol for pos in positions]))
    
    if not symbols:
        print("⚠️ 当前无持仓或无加仓计划，退出监听")
        return

    # 2. 批量订阅行情
    # TqApi 会自动管理订阅，这里只是获取 quote 对象，实际上是在注册监听
    quotes = {sym: api.get_quote(sym) for sym in symbols}
    
    print(f"🔍 开始监听 {len(symbols)} 个合约的加仓信号...")

    try:
        # 3. 进入死循环，等待数据更新
        while True:
            # wait_update() 会阻塞，直到有新的行情数据包到达
            # 这是 tqsdk 最省资源、最实时的模式
            if api.wait_update(timeout=3000): # 设置超时时间，防止永久阻塞
                
                # 当有数据更新时，检查我们关心的合约
                for pos in positions:
                    symbol = pos.symbol
                    if symbol not in quotes:
                        continue
                        
                    quote = quotes[symbol]
                    current_price = quote.last_price
                    
                    if pd.isna(current_price):
                        continue

                    trigger_price = pos.add_position_trigger_price
                    if not trigger_price:
                        continue

                    should_add = False

                    # --- 逻辑判断 ---
                    if pos.direction == 1:
                        if current_price >= float(trigger_price):
                            print(f"🚀 触发多头加仓: {symbol} (现价: {current_price} >= 触发: {trigger_price})")
                            should_add = True
                            
                    elif pos.direction == -1:
                        if current_price <= float(trigger_price):
                            print(f"🚀 触发空头加仓: {symbol} (现价: {current_price} <= 触发: {trigger_price})")
                            should_add = True

                    if should_add:
                        execute_add_order(api, pos, symbol, current_price)
                        
    except KeyboardInterrupt:
        print("🛑 收到停止信号，关闭连接")
        api.close()