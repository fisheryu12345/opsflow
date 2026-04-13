# 🔧 安装依赖说明

## 问题原因

LangChain 在 **0.2 版本**后改变了模块结构，旧的导入路径已失效。

## ✅ 正确的安装命令

```bash
pip install langchain langchain-openai langchain-core httpx python-dotenv
```

### 关键依赖说明

| 包名 | 作用 | 必需 |
|------|------|------|
| `langchain` | LangChain 核心框架 | ✅ |
| `langchain-openai` | OpenAI API 兼容层（DeepSeek 使用） | ✅ |
| `langchain-core` | **核心消息类**（HumanMessage 等） | ✅ |
| `httpx` | HTTP 客户端 | ✅ |
| `python-dotenv` | 环境变量加载 | ✅ |

## 🚀 快速测试

安装完成后，运行以下代码测试：

```python
from stock.deepseek import DeepSeekClient

client = DeepSeekClient(api_key="your-api-key")
response = client.chat("你好")
print(response)
```

## ❓ 如果仍然报错

### 方法1：升级所有相关包

```bash
pip install --upgrade langchain langchain-openai langchain-core
```

### 方法2：检查版本兼容性

```bash
pip list | grep langchain
```

应该看到类似输出：
```
langchain           0.2.x
langchain-core      0.2.x
langchain-openai    0.1.x
```

### 方法3：重新安装

```bash
pip uninstall langchain langchain-openai langchain-core
pip install langchain langchain-openai langchain-core httpx python-dotenv
```

## 📝 代码已自动兼容

修复后的代码会**自动尝试两种导入方式**：

```python
try:
    # 新版 LangChain (0.2+)
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
except ImportError:
    # 旧版 LangChain (0.1.x)
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
```

所以无论使用哪个版本都能正常工作！✨
