# 🚀 DeepSeek API 快速开始指南

## 5分钟上手教程

### 第1步：安装依赖

```bash
cd c:\Users\dell\Desktop\Vue\backend
pip install langchain langchain-openai httpx python-dotenv
```

### 第2步：配置 API Key

在项目根目录创建 `.env` 文件：

```bash
# .env 文件内容
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

> 💡 获取 API Key: [https://platform.deepseek.com/](https://platform.deepseek.com/)

### 第3步：运行测试

```bash
cd backend/stock/deepseek
python deepseek.py
```

如果看到输出，说明配置成功！🎉

---

## 💻 代码示例

### 示例1：最简单的调用

```python
from stock.deepseek import DeepSeekClient

# 创建客户端（自动从 .env 读取 API Key）
client = DeepSeekClient()

# 发送消息
response = client.chat("你好")
print(response)
```

### 示例2：多轮对话

```python
from stock.deepseek import DeepSeekClient

client = DeepSeekClient(
    system_prompt="你是一个专业的Python程序员助手"
)

# 第一轮对话
response = client.chat("什么是装饰器？")
print(response)

# 第二轮对话（自动记住上下文）
response = client.chat("能给我一个实际应用的例子吗？")
print(response)
```

### 示例3：流式输出

```python
from stock.deepseek import DeepSeekClient

client = DeepSeekClient(enable_streaming=True)

print("AI正在思考...", end="", flush=True)
for chunk in client.chat_stream("写一个Python的快速排序算法"):
    print(chunk, end="", flush=True)
print()  # 换行
```

### 示例4：代码生成

```python
from stock.deepseek import create_deepseek_client

# 使用专门的代码生成模型
coder = create_deepseek_client(
    model="deepseek-coder",
    temperature=0.3,  # 低温度保证准确性
    system_prompt="你是一个资深软件工程师"
)

code = coder.chat("""
请用 Python 实现一个线程安全的单例模式。
要求：
1. 使用双重检查锁定
2. 添加完整的类型注解
3. 包含详细的注释
""")

print(code)
```

---

## 📊 完整项目结构

```
backend/stock/deepseek/
├── __init__.py              # 模块初始化
├── deepseek.py              # 核心实现（DeepSeekClient类）
├── test_deepseek.py         # 单元测试
├── README.md                # 详细文档
└── QUICKSTART.md            # 本文件（快速开始）
```

---

## 🔧 常用配置

### 调整创造性（temperature）

```python
# 低创造性（事实性回答、代码生成）
client = DeepSeekClient(temperature=0.2)

# 中等创造性（日常对话）
client = DeepSeekClient(temperature=0.7)

# 高创造性（创意写作、头脑风暴）
client = DeepSeekClient(temperature=1.5)
```

### 限制回复长度

```python
# 短回复
response = client.chat("总结一下", max_tokens=100)

# 长回复
response = client.chat("详细解释", max_tokens=3000)
```

### 清空对话历史

```python
client.chat("问题1")
client.chat("问题2")

# 重置，开始新话题
client.reset_conversation()
client.chat("全新的问题")
```

---

## ❓ 常见问题

### Q: 出现 "ModuleNotFoundError"？

**A:** 确保已安装依赖：
```bash
pip install langchain langchain-openai httpx python-dotenv
```

### Q: 出现 "未提供 API Key" 错误？

**A:** 检查以下三点：
1. `.env` 文件是否存在于项目根目录
2. `.env` 文件中是否有 `DEEPSEEK_API_KEY=your-key`
3. 是否重启了 Python 环境

### Q: 如何查看完整的对话历史？

**A:** 
```python
history = client.get_conversation_history()
for msg in history:
    print(f"[{msg['role']}] {msg['content']}")
```

### Q: 流式输出为什么不工作？

**A:** 确保：
1. 初始化时设置 `enable_streaming=True`
2. 使用 `chat_stream()` 而非 `chat()`
3. 已正确安装所有依赖

---

## 📚 下一步

- 📖 阅读 [README.md](README.md) 了解高级用法
- 🧪 运行 `test_deepseek.py` 查看测试用例
- 🔗 访问 [DeepSeek 官方文档](https://platform.deepseek.com/docs)

---

## 💡 提示

1. **生产环境**：务必添加异常处理逻辑
2. **成本控制**：监控 token 使用量，避免超额消费
3. **性能优化**：对于批量请求，考虑使用异步调用
4. **安全注意**：不要将 API Key 提交到版本控制系统

---

祝你使用愉快！🎊
