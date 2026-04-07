import pandas as pd
import numpy as np
from datetime import date, time, datetime
from django.db import transaction
from django.db.models import Q

# 假设你的策略计算函数已经独立出来，或者在这里重新导入
from stock.utils.indicator import calculate_trend_factor, calculate_breakout_levels, calculate_atr
# 为了演示，我将在代码中保留逻辑占位符

def job_daily_open_prep():
    """
    每日开盘前准备任务 (建议时间: 08:45)
    
    核心职责：
    1. 扫描所有活跃合约。
    2. 基于昨日数据计算今日的唐奇安通道 (入场/离场价位)。
    3. 计算今日的动态止损价。
    4. 更新 PositionState 表中的 pending_... 字段，为实盘脚本提供“作战地图”。
    """
    print(f"🌅 开始每日开盘前准备任务...")
    
    # 1. 获取所有活跃的持仓状态 (即正在交易的品种)
    # 注意：这里也可以扩展为扫描一个“关注列表”，即使空仓也算，为了捕捉首次开仓信号
    positions = PositionState.objects.filter(account__is_active=True)
    
    # 模拟获取昨日行情数据
    # 在实盘中，你需要连接 TqApi 或从 InfluxDB/本地文件 读取昨日的 OHLC 数据
    # klines = api.get_kline_serial(symbol, 86400, data_length=100)
    
    for pos in positions:
        try:
            # 模拟：获取该品种昨日的 K线数据 (DataFrame)
            # klines_df = get_yesterday_klines(pos.symbol)
            # if klines_df.empty: continue
            
            print(f"   🔄 正在处理: {pos.symbol} ...")
            
            with transaction.atomic():
                # --- 步骤 1: 计算技术指标 (基于昨日数据) ---
                
                # 1.1 计算趋势因子 (TrendInfo)
                # trend_info = calculate_trend_factor(klines_df)
                # 这里我们假设 trend_factor = 0.5 (强多) 作为演示
                trend_factor = 0.5 
                trend_label = "strong_bull"
                
                # 保存趋势信息，供盘后分析
                # TrendInfo.objects.create(...)

                # 1.2 计算唐奇安通道 (Donchian Channel)
                # 对应代码: calculate_breakout_levels
                # entry_high: 过去20天最高价 (突破做多)
                # entry_low: 过去20天最低价 (跌破做空)
                # exit_high/low: 过去10天 (离场)
                
                # 模拟数据
                entry_high = 3000.0 
                entry_low = 2800.0
                atr20 = 20.0
                
                # --- 步骤 2: 计算关键风控价格 ---
                
                # 2.1 计算今日动态止损价
                # 逻辑复用: calculate_stop_price
                stop_price = 0.0
                if pos.direction == 1: # 多头
                    # 止损 = 持仓期最高价 - N * ATR
                    if pos.highest_close:
                        multiplier = 2.0 * (1.0 + trend_factor)
                        stop_price = float(pos.highest_close) - (multiplier * atr20)
                        
                elif pos.direction == -1: # 空头
                    if pos.lowest_close:
                        multiplier = 2.0 * (1.0 + trend_factor)
                        stop_price = float(pos.lowest_close) + (multiplier * atr20)

                # --- 步骤 3: 更新数据库状态 (写入“作战地图”) ---
                
                # 更新持仓状态表
                # 注意：我们只更新计算出的指标，不改变持仓方向（那是交易脚本的事）
                pos.last_update_time = datetime.now()
                
                # 将计算出的关键价位存入一个 JSON 字段或辅助表，或者直接更新 pending 字段
                # 这里为了演示，我们假设你有一个字段叫 `calculated_stop_price` (你需要加到 Model 里)
                # 或者我们可以利用 pending 字段来传递信号（如果逻辑允许）
                
                # 方案 A: 如果已有信号逻辑，这里可以预计算“如果突破就开仓”
                # 检查昨日是否已经突破 (收盘价 > 上轨)
                # last_close = klines_df['close'].iloc[-1]
                
                # if last_close > entry_high and pos.direction == 0:
                #     pos.pending_direction = 1
                #     pos.pending_contracts = calculate_units(...)
                #     print(f"   🚀 {pos.symbol} 已突破，设置待开仓状态为多")
                
                # pos.save()
                
                print(f"   ✅ {pos.symbol} 计算完成. 上轨: {entry_high}, 止损: {stop_price:.2f}")

        except Exception as e:
            print(f"   ❌ {pos.symbol} 开盘准备失败: {e}")
            import traceback
            traceback.print_exc()

    print("🏁 开盘前准备任务结束")


def job_check_pending_orders():
    """
    开盘瞬间任务 (建议时间: 09:00:05)
    
    核心职责：
    1. 检查昨晚收盘后产生的 pending 信号。
    2. 获取今早的开盘价。
    3. 判断是否触发“跳空过滤”逻辑。
    4. 如果通过过滤，保持 pending；如果未通过，清除 pending。
    
    注意：这个函数通常需要配合实时行情，或者在交易脚本的主循环开始时调用。
    这里提供一个纯数据库操作的辅助版本。
    """
    print("⏰ 检查待开仓信号 (跳空过滤)...")
    
    pending_positions = PositionState.objects.filter(pending_direction__ne=0)
    
    for pos in pending_positions:
        # 获取今早开盘价 (需要从行情源获取，这里假设为 open_price)
        # current_open = get_current_open(pos.symbol)
        current_open = 0.0 
        
        # 获取昨日收盘价 (从数据库或 K线数据)
        # last_close = get_last_close(pos.symbol)
        last_close = 0.0
        
        if current_open == 0 or last_close == 0:
            continue
            
        # 计算跳空幅度
        gap_pct = (current_open - last_close) / last_close
        
        # 获取策略配置 (跳空阈值，例如 1%)
        # config = StrategyConfig.objects.get(symbol=pos.symbol)
        threshold = 0.01 
        
        should_cancel = False
        
        # 多头：如果大幅高开 (跳空 > 1%)，放弃开仓
        if pos.pending_direction == 1 and gap_pct > threshold:
            print(f"   🚫 {pos.symbol} 多头跳空过高 ({gap_pct:.2%})，取消开仓")
            should_cancel = True
            
        # 空头：如果大幅低开 (跳空 < -1%)，放弃开仓
        elif pos.pending_direction == -1 and gap_pct < -threshold:
            print(f"   🚫 {pos.symbol} 空头跳空过高 ({gap_pct:.2%})，取消开仓")
            should_cancel = True
            
        if should_cancel:
            # 清除待开仓状态
            pos.pending_direction = 0
            pos.pending_contracts = 1
            pos.save()
            
    print("✅ 待开仓信号检查完毕")