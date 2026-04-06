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



#!/usr/bin/env python
#  -*- coding: utf-8 -*-
__author__ = 'chengzhi'

from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask

'''
如果当前价格大于10日K线的MA10且小于20日K线的MA20则开多仓
如果当前价格小于10日K线的MA10且大于20日K线的MA20则开空仓
如果当前价格在两条均线上方或下方则平仓
回测从 2018-05-01 到 2018-10-01
'''
# 在创建 api 实例时传入 TqBacktest 就会进入回测模式
api = TqApi(backtest=TqBacktest(start_dt=date(2018, 5, 1), end_dt=date(2018, 10, 1)), auth=TqAuth("yupei1986", "yupei1986"))
# 获得 m1901 日K线的引用
klines_10 = api.get_kline_serial("DCE.m1901", duration_seconds=24 * 60 * 60, data_length=20)
klines_20 = api.get_kline_serial("DCE.m1901", duration_seconds=24 * 60 * 60, data_length=20)
# 创建 m1901 的目标持仓 task，该 task 负责调整 m1901 的仓位到指定的目标仓位
target_pos = TargetPosTask(api, "DCE.m1901")

while True:
    api.wait_update()
    if api.is_changing(klines_10) and api.is_changing(klines_20):
        ma_10 = klines_10['close'].iloc[-10:].mean()
        ma_20 = klines_20['close'].iloc[-20:].mean()
        latest_price = klines_10['close'].iloc[-1]
        
        print(f"最新价: {latest_price}, 10日均线: {ma_10}, 20日均线: {ma_20}")
        
        if latest_price > ma_10 and latest_price < ma_20:
            print("最新价大于10日均线且小于20日均线: 目标多头5手")
            # 设置目标持仓为多头5手
            target_pos.set_target_volume(5)
        elif latest_price < ma_10 and latest_price > ma_20:
            print("最新价小于10日均线且大于20日均线: 目标空头5手")
            # 设置目标持仓为空头5手
            target_pos.set_target_volume(-5)
        else:
            print("最新价不在两条均线之间: 目标空仓")
            # 设置目标持仓为空仓
            target_pos.set_target_volume(0)

# 关闭API连接
api.close()




#!/usr/bin/env python
#  -*- coding: utf-8 -*-
__author__ = 'chengzhi'

from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask

def calculate_atr(klines, period=20):
    tr = []
    for i in range(len(klines)):
        if i == 0:
            tr_value = max(klines['high'][i] - klines['low'][i], abs(klines['high'][i] - klines['close'][i-1]), abs(klines['low'][i] - klines['close'][i-1]))
        else:
            tr_value = max(klines['high'][i] - klines['low'][i], abs(klines['high'][i] - klines['close'][i-1]), abs(klines['low'][i] - klines['close'][i-1]))
        tr.append(tr_value)
    
    atr = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr = ((atr * (period - 1)) + tr[i]) / period
    
    return atr

# 在创建 api 实例时传入 TqBacktest 就会进入回测模式
api = TqApi(backtest=TqBacktest(start_dt=date(2025, 12, 1), end_dt=date(2026, 4, 6)), auth=TqAuth("yupei1986", "yupei1986"))
# 获得 RU2605 日K线的引用
klines = api.get_kline_serial("SHFE.rb2605", duration_seconds=24 * 60 * 60, data_length=200)

# 创建 RU2605 的目标持仓 task，该 task 负责调整 RU2605 的仓位到指定的目标仓位
target_pos = TargetPosTask(api, "SHFE.rb2605")

entry_long_price = None
entry_short_price = None
position = 0

while True:
    api.wait_update()
    if api.is_changing(klines.iloc[-1]):
        # 计算 ATR
        atr_20 = calculate_atr(klines, period=20)
        atr_50 = calculate_atr(klines, period=50)
        atr_200 = calculate_atr(klines, period=200)
        
        # 计算入场价和平仓价
        entry_long_threshold = klines['high'].rolling(window=20).max().iloc[-1]
        exit_long_threshold = entry_long_price - 2 * atr_20 if entry_long_price else float('inf')
        
        entry_short_threshold = klines['low'].rolling(window=20).min().iloc[-1]
        exit_short_threshold = entry_short_price + 2 * atr_20 if entry_short_price else float('-inf')
        
        latest_price = klines['close'].iloc[-1]
        
        print(f"最新价: {latest_price}, 20日最高价: {entry_long_threshold}, 20日最低价: {entry_short_threshold}, 20日ATR: {atr_20}")
        
        if position == 0:
            # 开多仓条件
            if latest_price > entry_long_threshold:
                print("开多仓")
                entry_long_price = latest_price
                target_pos.set_target_volume(1)
                position = 1
            # 开空仓条件
            elif latest_price < entry_short_threshold:
                print("开空仓")
                entry_short_price = latest_price
                target_pos.set_target_volume(-1)
                position = -1
        elif position == 1:
            # 平多仓条件
            if latest_price <= exit_long_threshold:
                print("平多仓")
                entry_long_price = None
                target_pos.set_target_volume(0)
                position = 0
        elif position == -1:
            # 平空仓条件
            if latest_price >= exit_short_threshold:
                print("平空仓")
                entry_short_price = None
                target_pos.set_target_volume(0)
                position = 0

# 关闭API连接
api.close()



#!/usr/bin/env python
#  -*- coding: utf-8 -*-
__author__ = 'chaos'

from tqsdk import TqApi, TqAuth

api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))

# 全部主连合约对应的标的合约
ls = api.query_cont_quotes()
print(ls)

# 大商所主连合约对应的标的合约
ls = api.query_cont_quotes(exchange_id="DCE")
print(ls)

# jd 品种主连合约对应的标的合约
ls = api.query_cont_quotes(product_id="jd")
print(ls)

# 关闭api,释放相应资源
api.close()

# 预期输出如下
# ['SHFE.cu2503', 'SHFE.ni2503', 'CFFEX.TS2503', 'SHFE.br2503', 'CZCE.OI505', 'DCE.c2505', 'GFEX.lc2505', 'INE.bc2503', 'CZCE.CJ505', 'CFFEX.TF2503', 'SHFE.hc2505', 'SHFE.ru2505', 'DCE.lg2507', 'DCE.a2505', 'DCE.b2505', 'GFEX.ps2506', 'SHFE.ss2505', 'CZCE.CF505', 'DCE.m2505', 'CFFEX.T2503', 'DCE.pg2503', 'CZCE.SR505', 'CZCE.PF504', 'SHFE.pb2503', 'CZCE.UR505', 'CZCE.MA505', 'CZCE.PX505', 'SHFE.sn2503', 'GFEX.si2505', 'CZCE.FG505', 'CFFEX.IM2503', 'CZCE.ZC505', 'CFFEX.IC2503', 'INE.nr2504', 'INE.lu2505', 'DCE.fb2505', 'CZCE.RM505', 'CFFEX.TL2503', 'CZCE.SA505', 'CZCE.AP505', 'CZCE.PK505', 'CZCE.SF505', 'SHFE.ao2505', 'CZCE.TA505', 'SHFE.bu2504', 'SHFE.zn2503', 'DCE.jm2505', 'DCE.jd2505', 'INE.sc2504', 'INE.ec2504', 'CZCE.PM505', 'DCE.lh2505', 'CZCE.WH505', 'CZCE.RI505', 'DCE.l2505', 'CZCE.PR503', 'CZCE.CY505', 'DCE.eg2505', 'DCE.pp2505', 'SHFE.fu2505', 'DCE.v2505', 'DCE.p2505', 'SHFE.rb2505', 'CZCE.JR505', 'SHFE.sp2505', 'CZCE.SM505', 'CFFEX.IF2503', 'DCE.rr2503', 'SHFE.au2504', 'DCE.bb2509', 'SHFE.ag2504', 'SHFE.al2504', 'DCE.j2505', 'CZCE.RS507', 'DCE.y2505', 'DCE.i2505', 'CZCE.SH505', 'CZCE.LR505', 'DCE.cs2503', 'SHFE.wr2505', 'CFFEX.IH2503', 'DCE.eb2503']
# ['DCE.c2505', 'DCE.lg2507', 'DCE.a2505', 'DCE.b2505', 'DCE.m2505', 'DCE.pg2503', 'DCE.fb2505', 'DCE.jm2505', 'DCE.jd2505', 'DCE.lh2505', 'DCE.l2505', 'DCE.eg2505', 'DCE.pp2505', 'DCE.v2505', 'DCE.p2505', 'DCE.rr2503', 'DCE.bb2509', 'DCE.j2505', 'DCE.y2505', 'DCE.i2505', 'DCE.cs2503', 'DCE.eb2503']
# ['DCE.jd2505']


#!/usr/bin/env python
#  -*- coding: utf-8 -*-
__author__ = "Ringo"

from tqsdk import TqApi, TqAuth

api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))

# 订阅螺纹钢主连
quote = api.get_quote("KQ.m@SHFE.rb")
# 打印现在螺纹钢主连的标的合约
print(quote.underlying_symbol)

api.close()