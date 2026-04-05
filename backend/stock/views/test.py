from tqsdk import TqApi, TqAuth

# 创建API实例，并使用你的账号密码登录
api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))

# 订阅 rb2605 的K线数据，周期为日K
quote = api.get_quote("SHFE.rb2605")

while True:
    # 等待事件触发
    api.wait_update()
    
    # 检查是否有新的数据更新
    if api.is_changing(quote):
        print(f"rb2605 当前收盘价: {quote.last_price}")
        
        # 打印一次后退出循环
        break

# 关闭API连接
api.close()


from tqsdk import TqApi, TqAuth

# 创建API实例，并使用你的账号密码登录
api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))

# 订阅 rb2605 的日K线数据
klines = api.get_kline_serial("SHFE.rb2605", duration_seconds=24 * 60 * 60)


from tqsdk import TqApi, TqAuth

def calculate_atr(highs, lows, closes, period=20):
    tr = []
    for i in range(len(closes)):
        if i == 0:
            tr_value = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        else:
            tr_value = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr.append(tr_value)
    
    atr = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr = ((atr * (period - 1)) + tr[i]) / period
    
    return atr


# 订阅 rb2605 的日K线数据
klines = api.get_kline_serial("SHFE.rb2605", duration_seconds=24 * 60 * 60)


highs = klines['high'].tolist()
lows = klines['low'].tolist()
closes = klines['close'].tolist()
            
            # 计算 20 日 ATR
atr_20 = calculate_atr(highs, lows, closes, period=20)
            
print(f"rb2605 20 日 ATR: {atr_20}")