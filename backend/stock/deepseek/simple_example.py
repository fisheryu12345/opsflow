"""
DeepSeek API 极简示例
"""

import os
from stock.deepseek import DeepSeekClient
from datetime import datetime

# 从环境变量读取 API Key（推荐方式），如果不存在则使用默认值（仅用于开发/测试）
api_key = os.getenv("DEEPSEEK_API_KEY", "sk-217d89e0760c4e6eab307e87383f34b5")

# 创建客户端
client = DeepSeekClient(api_key=api_key)
date = datetime.now().strftime("%Y-%m-%d")

# 发送消息 - 注意：JSON 中的花括号需要转义（使用双花括号 {{ }}）以避免 format() 报错
prompt = """
请告诉我当前{date}国内期货哪些品种有开仓最小数量限制?请直接返回一个JSON数据,返回的数据格式请严格遵守JSON数据格式。具体的返回数据格式参考如下：
{{
    "data": [
        {{
            "合约代码": "RB2610",
            "开仓最小数量限制": "100"
        }},
        {{
            "合约代码": "MA2605",
            "开仓最小数量限制": "50"
        }}
    ]
}}
"""

try:
    response = client.chat(prompt.format(date=date))
    print(response)
except Exception as e:
    print(f"请求失败: {str(e)}")

