"""
DeepSeek API 极简示例
"""

from stock.deepseek import DeepSeekClient
from datetime import datetime

# 创建客户端（替换为你的 API Key）
client = DeepSeekClient(api_key="sk-217d89e0760c4e6eab307e87383f34b5")
date = datetime.now().strftime("%Y-%m-%d")
# 发送消息
response = client.chat(f"请告诉我今天晚上{date}国内期货夜盘进行交易吗？请直接返回一个JSON数据,只需要包含以下字段：\n\"is_trading_night\": true/false" )
print(response)


response = client.chat(f"请告诉我哪些国内期货品种没有夜盘？请直接返回一个JSON数据,只需要包含以下字段：\n\"product_code\": true/false" )
print(response)

