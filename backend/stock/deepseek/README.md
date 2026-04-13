# DeepSeek API 集成（基于 LangChain）

## 📖 简介

本模块提供了基于 **LangChain** 框架的 DeepSeek API 集成，支持：
- ✅ 流式和非流式响应
- ✅ 多轮对话历史管理
- ✅ 灵活的参数配置（温度、最大token、系统提示词等）
- ✅ 两种模型支持：`deepseek-chat`（通用对话）和 `deepseek-coder`（代码生成）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install langchain langchain-openai httpx python-dotenv
```

### 2. 配置 API Key

**方式一：使用 `.env` 文件（推荐）**

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

> 获取 API Key: [https://platform.deepseek.com/](https://platform.deepseek.com/)

**方式二：直接在代码中传入**

```python
client = DeepSeekClient(api_key="your-api-key")
```

### 3. 基础使用

```python
from stock.deepseek.deepseek import DeepSeekClient

# 创建客户端
client = DeepSeekClient(
    system_prompt="你是一个专业的AI助手"
)

# 发送消息
response = client.chat("你好，请介绍一下自己")
print(response)

# 继续对话（自动维护上下文）
response = client.chat("Python 中列表和元组有什么区别？")
print(response)
```

## 💡 使用示例

### 示例1：基础对话

```python
from stock.deepseek.deepseek import DeepSeekClient

client = DeepSeekClient(
    api_key="your-api-key",
    system_prompt="你是一个友好的AI助手",
    temperature=0.7
)

# 单次对话
response = client.chat("什么是机器学习？")
print(response)

# 多轮对话（自动维护上下文）
client.chat("你好")
client.chat("今天天气怎么样？")
client.chat("能推荐一些学习资源吗？")
```

### 示例2：流式输出

```python
client = DeepSeekClient(
    api_key="your-api-key",
    enable_streaming=True
)

print("AI回复: ", end="", flush=True)
for chunk in client.chat_stream("写一个Python快速排序算法"):
    print(chunk, end="", flush=True)
print()  # 换行
```

### 示例3：代码生成（使用 deepseek-coder）

```python
coder_client = DeepSeekClient(
    api_key="your-api-key",
    model="deepseek-coder",
    system_prompt="你是一个专业的程序员，擅长编写高质量代码",
    temperature=0.3  # 代码生成需要更低的温度
)

response = coder_client.chat("""
请用 Python 实现一个线程安全的单例模式装饰器。
要求：
1. 支持多线程环境
2. 使用双重检查锁定
3. 提供完整的类型注解
""")

print(response)
```

### 示例4：动态调整参数

```python
client = DeepSeekClient(api_key="your-api-key")

# 临时覆盖温度和最大token
response = client.chat(
    "创作一首关于春天的诗",
    temperature=1.5,  # 更高的创造性
    max_tokens=500
)

print(response)
```

### 示例5：管理对话历史

```python
client = DeepSeekClient(api_key="your-api-key")

# 进行多轮对话
client.chat("你好")
client.chat("今天天气如何？")

# 查看对话历史
history = client.get_conversation_history()
for msg in history:
    print(f"[{msg['role']}] {msg['content'][:50]}...")

# 重置对话（清空历史）
client.reset_conversation()

# 重新开始对话
client.chat("我们重新开始聊天吧")
```

### 示例6：使用工厂函数

```python
from stock.deepseek.deepseek import create_deepseek_client

# 快速创建客户端
client = create_deepseek_client(
    api_key="your-api-key",
    model="deepseek-chat",
    temperature=0.7,
    system_prompt="你是一个专业的技术顾问"
)

response = client.chat("如何选择合适的前端框架？")
print(response)
```

## ⚙️ 参数说明

### DeepSeekClient 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | str | 从环境变量读取 | DeepSeek API Key |
| `base_url` | str | `https://api.deepseek.com/v1` | API 基础 URL |
| `model` | str | `deepseek-chat` | 模型名称（`deepseek-chat` 或 `deepseek-coder`） |
| `temperature` | float | `0.7` | 温度参数 (0-2)，越高越有创造性 |
| `max_tokens` | int | `2000` | 最大生成 token 数 |
| `system_prompt` | str | `None` | 系统提示词，设定 AI 角色 |
| `timeout` | int | `60` | 请求超时时间（秒） |
| `enable_streaming` | bool | `False` | 是否启用流式输出 |

### chat() 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `user_message` | str | - | 用户消息（必填） |
| `temperature` | float | `None` | 临时覆盖温度参数 |
| `max_tokens` | int | `None` | 临时覆盖最大 token 数 |
| `clear_history` | bool | `False` | 是否清空对话历史 |

### chat_stream() 方法参数

与 `chat()` 方法参数相同，但返回生成器而非字符串。

## 🎯 最佳实践

### 1. 选择合适的模型

- **`deepseek-chat`**：通用对话、问答、文本生成
- **`deepseek-coder`**：代码生成、代码解释、调试建议

### 2. 调整温度参数

- **低温度 (0.1-0.3)**：代码生成、事实性回答、需要准确性的场景
- **中温度 (0.5-0.7)**：日常对话、一般性问答
- **高温度 (1.0-1.5)**：创意写作、头脑风暴、诗歌创作

### 3. 设置系统提示词

```python
# 客服场景
client = DeepSeekClient(
    system_prompt="你是一名专业的客服代表，态度友好、耐心解答用户问题。"
)

# 编程助手
client = DeepSeekClient(
    system_prompt="你是一名资深Python工程师，擅长代码优化和架构设计。"
)

# 翻译助手
client = DeepSeekClient(
    system_prompt="你是一名专业翻译，精通中英文互译，译文要准确流畅。"
)
```

### 4. 管理对话长度

对于长对话，定期清理历史以避免超出 token 限制：

```python
# 每10轮对话后重置
if len(client.get_conversation_history()) > 20:
    client.reset_conversation()
```

## 🔧 高级用法

### 自定义回调处理

```python
from langchain.callbacks.base import BaseCallbackHandler

class MyCustomHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"收到token: {token}", end="", flush=True)

client = DeepSeekClient(
    api_key="your-api-key",
    enable_streaming=True
)

# 添加自定义回调
client.llm.callbacks = [MyCustomHandler()]
response = client.chat("你好")
```

### 批量处理

```python
questions = [
    "什么是人工智能？",
    "机器学习有哪些应用场景？",
    "深度学习与传统机器学习的区别是什么？"
]

client = DeepSeekClient(api_key="your-api-key")

for i, question in enumerate(questions, 1):
    print(f"\n问题 {i}: {question}")
    response = client.chat(question, clear_history=True)  # 每个问题独立对话
    print(f"回答: {response[:100]}...")
```

## ❓ 常见问题

### Q1: 如何获取 DeepSeek API Key？

访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册账号并创建 API Key。

### Q2: 出现 "未提供 API Key" 错误？

确保已通过以下方式之一提供 API Key：
1. 参数传入：`DeepSeekClient(api_key="your-key")`
2. 环境变量：设置 `DEEPSEEK_API_KEY`
3. `.env` 文件：`DEEPSEEK_API_KEY=your-key`

### Q3: 流式输出不工作？

确保：
1. 初始化时设置 `enable_streaming=True`
2. 使用 `chat_stream()` 方法而非 `chat()`
3. 已安装 `langchain` 和相关依赖

### Q4: 如何切换模型？

```python
# 使用代码生成模型
client = DeepSeekClient(
    api_key="your-api-key",
    model="deepseek-coder"
)
```

### Q5: 响应速度慢怎么办？

- 减小 `max_tokens` 参数
- 降低 `temperature` 参数
- 检查网络连接
- 考虑使用更快的模型（如 `deepseek-chat` 比 `deepseek-coder` 快）

## 📝 注意事项

1. **API 调用费用**：DeepSeek API 是付费服务，请注意控制调用次数和 token 用量
2. **速率限制**：注意 API 的速率限制，避免频繁调用导致被封禁
3. **错误处理**：生产环境中应添加完善的异常处理逻辑
4. **敏感信息**：不要将 API Key 硬编码在代码中，应使用环境变量或配置文件

## 🔗 相关链接

- [DeepSeek 官方网站](https://www.deepseek.com/)
- [DeepSeek 开放平台](https://platform.deepseek.com/)
- [LangChain 文档](https://python.langchain.com/)
- [OpenAI API 兼容说明](https://platform.openai.com/docs/api-reference)

## 📄 许可证

本模块遵循项目主许可证。
