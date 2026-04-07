import pandas as pd
import numpy as np
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask  

# ================= 配置区域 =================
# InfluxDB 2.x 配置
influx_url = "http://47.103.201.230:8086"
influx_token ="wZC4_NqeQS1Qj_9OIk2vfkJ7nEh_vq_T4i0u0iuqnpRYVHEXMc252wSkki0_HRuG_4rA6PXslJ8b3qkXtYwBWg=="
influx_org = "stock"                   # 你的组织名称
influx_bucket = "stock"                # 你的存储桶名称

# TqApi 配置
symbol = "DCE.m2605"
# =============================================

# 1. 初始化 TqApi 并获取数据
api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
klines = api.get_kline_serial(symbol, 86400)

print(f"获取到 {len(klines)} 条 K线数据")

# 2. 使用 Pandas 进行数据清洗和预处理
# tq 返回的数据可能包含 NaN (例如 volume 为 0 或空)，InfluxDB 无法写入 NaN 或 inf
# 我们先将数据转换为 DataFrame (如果还不是的话)
df = pd.DataFrame(klines)

# 替换无穷大和 NaN 为 None (InfluxDB 会忽略 None 字段) 或者填充 0
# 这里选择将 NaN 替换为 None，这样该字段就不会被写入，或者你可以用 .fillna(0)
df = df.replace([np.inf, -np.inf], np.nan)

# 筛选需要的列，并准备写入
# InfluxDB 2.x 写入需要特定的格式
points = []
for _, row in df.iterrows():
    # 跳过包含 NaN 的行，或者你可以选择填充默认值
    if pd.isna(row['datetime']):
        continue
        
    # 转换时间戳: tq 的 datetime 是纳秒或毫秒级的浮点数，需转为 datetime 对象
    # tq 文档通常说明 datetime 为 纳秒 (ns)
    dt = pd.to_datetime(row['datetime'], unit='ns')
    
    point = Point("kline") \
        .tag("symbol", symbol) \
        .field("open", float(row['open'])) \
        .field("high", float(row['high'])) \
        .field("low", float(row['low'])) \
        .field("close", float(row['close'])) \
        .field("volume", float(row['volume'])) \
        .field("open_oi", float(row['open_oi'])) \
        .field("close_oi", float(row['close_oi'])) \
        .time(dt, WritePrecision.NS)
        
    points.append(point)

# 3. 写入 InfluxDB
try:

    # 初始化 InfluxDB 2.x 客户端
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    if points:
        print(f"正在写入 {len(points)} 个点到 InfluxDB...")
        write_api.write(bucket=influx_bucket, record=points)
        print("写入成功！")
    else:
        print("没有有效数据需要写入。")

except Exception as e:
    print(f"写入失败: {e}")

finally:
    # 4. 关闭连接
    client.close()
    api.close()