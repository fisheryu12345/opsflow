"""
DeepSeek API 极简客户端（基于 LangChain）

使用示例：
    from stock.deepseek import DeepSeekClient
    
    client = DeepSeekClient(api_key="your-api-key")
    response = client.chat("你好")
    print(response)
"""

import os
from typing import Optional, List

# LangChain 导入（兼容新旧版本）
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
except ImportError:
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage, AIMessage
    except ImportError:
        raise ImportError("请安装依赖: pip install langchain langchain-openai langchain-core")


class DeepSeekClient:
    """DeepSeek API 客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 20000,
        system_prompt: Optional[str] = None
    ):
        """
        初始化客户端
        
        Args:
            api_key: API Key，不提供则从环境变量 DEEPSEEK_API_KEY 读取
            model: 模型名称（deepseek-chat 或 deepseek-coder）
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成 token 数
            system_prompt: 系统提示词
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未提供 API Key！请通过参数传入或设置环境变量 DEEPSEEK_API_KEY")
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=self.api_key,
            openai_api_base="https://api.deepseek.com/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60
        )
        
        # 消息历史
        self.messages: List = []
        if system_prompt:
            self.messages.append(SystemMessage(content=system_prompt))
    
    def chat(self, user_message: str, clear_history: bool = False) -> str:
        """
        发送消息并获取回复
        
        Args:
            user_message: 用户消息
            clear_history: 是否清空对话历史
            
        Returns:
            AI 回复文本
        """
        # 清空历史
        if clear_history:
            self.messages = self.messages[:1] if self.messages and isinstance(self.messages[0], SystemMessage) else []
        
        # 添加用户消息
        self.messages.append(HumanMessage(content=user_message))
        
        # 调用模型
        response = self.llm.invoke(self.messages)
        
        # 保存回复到历史
        self.messages.append(AIMessage(content=response.content))
        
        return response.content
    
    def reset(self):
        """重置对话历史"""
        self.messages = []
