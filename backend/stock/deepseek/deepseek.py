"""
DeepSeek API 集成模块（基于 LangChain）

功能说明：
1. 使用 LangChain 框架调用 DeepSeek API
2. 支持流式和非流式响应
3. 支持自定义系统提示词和温度参数
4. 提供便捷的聊天接口

使用前准备：
1. 安装依赖：pip install langchain langchain-openai httpx
2. 获取 DeepSeek API Key：https://platform.deepseek.com/
3. 设置环境变量或在代码中配置 API Key
"""

import os
from typing import Optional, List, Dict, Any, Generator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# LangChain 相关导入
try:
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
except ImportError:
    raise ImportError(
        "请先安装必要依赖：pip install langchain langchain-openai httpx"
    )


class DeepSeekClient:
    """
    DeepSeek API 客户端（基于 LangChain）
    
    使用示例：
        # 基础用法
        client = DeepSeekClient(api_key="your-api-key")
        response = client.chat("你好，请介绍一下自己")
        print(response)
        
        # 带系统提示词
        client = DeepSeekClient(
            api_key="your-api-key",
            system_prompt="你是一个专业的Python程序员助手"
        )
        response = client.chat("如何优化这段代码？")
        
        # 流式输出
        for chunk in client.chat_stream("写一个快速排序算法"):
            print(chunk, end="", flush=True)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
        timeout: int = 60,
        enable_streaming: bool = False
    ):
        """
        初始化 DeepSeek 客户端
        
        Args:
            api_key: DeepSeek API Key，如果不提供则从环境变量 DEEPSEEK_API_KEY 读取
            base_url: API 基础 URL，默认 DeepSeek 官方地址
            model: 模型名称，可选 "deepseek-chat" 或 "deepseek-coder"
            temperature: 温度参数 (0-2)，控制随机性，越高越创造性
            max_tokens: 最大生成 token 数
            system_prompt: 系统提示词，设定 AI 的角色和行为
            timeout: 请求超时时间（秒）
            enable_streaming: 是否启用流式输出
        """
        # 获取 API Key
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "未提供 API Key！\n"
                "请通过以下方式之一提供：\n"
                "1. 参数传入: DeepSeekClient(api_key='your-key')\n"
                "2. 环境变量: 设置 DEEPSEEK_API_KEY\n"
                "3. .env 文件: DEEPSEEK_API_KEY=your-key"
            )
        
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.timeout = timeout
        self.enable_streaming = enable_streaming
        
        # 初始化 LangChain ChatOpenAI（兼容 OpenAI API 格式）
        self._init_llm()
        
        # 消息历史（用于多轮对话）
        self.messages: List = []
        if self.system_prompt:
            self.messages.append(SystemMessage(content=self.system_prompt))
    
    def _init_llm(self):
        """初始化语言模型"""
        callbacks = []
        if self.enable_streaming:
            callbacks.append(StreamingStdOutCallbackHandler())
        
        self.llm = ChatOpenAI(
            model=self.model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            streaming=self.enable_streaming,
            callbacks=callbacks if callbacks else None,
            model_kwargs={
                "stream": self.enable_streaming
            }
        )
    
    def chat(
        self,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        clear_history: bool = False
    ) -> str:
        """
        发送消息并获取回复（非流式）
        
        Args:
            user_message: 用户消息
            temperature: 临时覆盖温度参数
            max_tokens: 临时覆盖最大 token 数
            clear_history: 是否清空对话历史
            
        Returns:
            AI 回复文本
        """
        # 如果需要清空历史
        if clear_history:
            self.messages = []
            if self.system_prompt:
                self.messages.append(SystemMessage(content=self.system_prompt))
        
        # 添加用户消息
        self.messages.append(HumanMessage(content=user_message))
        
        # 构建调用参数
        call_kwargs = {}
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        
        # 调用模型
        try:
            response = self.llm.invoke(self.messages, **call_kwargs)
            
            # 添加 AI 回复到历史
            self.messages.append(AIMessage(content=response.content))
            
            return response.content
            
        except Exception as e:
            error_msg = f"调用 DeepSeek API 失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise
    
    def chat_stream(
        self,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        clear_history: bool = False
    ) -> Generator[str, None, None]:
        """
        发送消息并流式获取回复
        
        Args:
            user_message: 用户消息
            temperature: 临时覆盖温度参数
            max_tokens: 临时覆盖最大 token 数
            clear_history: 是否清空对话历史
            
        Yields:
            逐块生成的文本片段
        """
        # 重新初始化支持流式的 LLM
        if not self.enable_streaming:
            llm = ChatOpenAI(
                model=self.model,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                timeout=self.timeout,
                streaming=True,
                callbacks=[StreamingStdOutCallbackHandler()],
                model_kwargs={"stream": True}
            )
        else:
            llm = self.llm
        
        # 如果需要清空历史
        if clear_history:
            self.messages = []
            if self.system_prompt:
                self.messages.append(SystemMessage(content=self.system_prompt))
        
        # 添加用户消息
        self.messages.append(HumanMessage(content=user_message))
        
        # 构建调用参数
        call_kwargs = {}
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        
        # 流式调用
        full_response = ""
        try:
            for chunk in llm.stream(self.messages, **call_kwargs):
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    yield chunk.content
            
            # 添加完整回复到历史
            if full_response:
                self.messages.append(AIMessage(content=full_response))
                
        except Exception as e:
            error_msg = f"流式调用 DeepSeek API 失败: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise
    
    def reset_conversation(self):
        """重置对话历史"""
        self.messages = []
        if self.system_prompt:
            self.messages.append(SystemMessage(content=self.system_prompt))
        print("[INFO] 对话历史已重置")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Returns:
            对话历史列表，每项包含 role 和 content
        """
        history = []
        for msg in self.messages:
            if isinstance(msg, SystemMessage):
                history.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history


def create_deepseek_client(
    api_key: Optional[str] = None,
    model: str = "deepseek-chat",
    **kwargs
) -> DeepSeekClient:
    """
    工厂函数：创建 DeepSeek 客户端
    
    Args:
        api_key: API Key
        model: 模型名称
        **kwargs: 其他参数传递给 DeepSeekClient
        
    Returns:
        DeepSeekClient 实例
    """
    return DeepSeekClient(api_key=api_key, model=model, **kwargs)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek API 测试（基于 LangChain）")
    print("=" * 60)
    
    # 示例1：基础对话
    print("\n【示例1】基础对话")
    print("-" * 60)
    try:
        client = DeepSeekClient(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            system_prompt="你是一个友好的AI助手，擅长解答各种问题。"
        )
        
        response = client.chat("你好，请简单介绍一下你自己")
        print(f"AI回复: {response}\n")
        
        response = client.chat("Python 中列表和元组有什么区别？")
        print(f"AI回复: {response}\n")
        
    except Exception as e:
        print(f"错误: {e}\n")
    
    # 示例2：流式输出
    print("\n【示例2】流式输出")
    print("-" * 60)
    try:
        client = DeepSeekClient(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            enable_streaming=True
        )
        
        print("AI回复: ", end="", flush=True)
        for chunk in client.chat_stream("用 Python 写一个斐波那契数列生成器"):
            pass  # 内容已在回调中打印
        print("\n")
        
    except Exception as e:
        print(f"错误: {e}\n")
    
    # 示例3：代码生成（使用 deepseek-coder 模型）
    print("\n【示例3】代码生成（deepseek-coder）")
    print("-" * 60)
    try:
        coder_client = DeepSeekClient(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            model="deepseek-coder",
            system_prompt="你是一个专业的程序员，擅长编写高质量、高效的代码。",
            temperature=0.3  # 代码生成需要更低的温度以保证准确性
        )
        
        response = coder_client.chat("""
请用 Python 实现一个线程安全的单例模式装饰器。
要求：
1. 支持多线程环境
2. 使用双重检查锁定
3. 提供完整的类型注解
""")
        print(f"AI回复:\n{response}\n")
        
    except Exception as e:
        print(f"错误: {e}\n")
    
    # 示例4：查看对话历史
    print("\n【示例4】查看对话历史")
    print("-" * 60)
    try:
        history = client.get_conversation_history()
        print(f"对话历史共 {len(history)} 条消息:")
        for i, msg in enumerate(history, 1):
            role_map = {"system": "系统", "user": "用户", "assistant": "AI"}
            role = role_map.get(msg["role"], msg["role"])
            content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            print(f"  {i}. [{role}] {content_preview}")
        
    except Exception as e:
        print(f"错误: {e}\n")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
