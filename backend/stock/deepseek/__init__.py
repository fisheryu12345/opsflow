"""
DeepSeek API 集成模块

提供基于 LangChain 的 DeepSeek API 调用功能
"""

from .deepseek import DeepSeekClient, create_deepseek_client

__all__ = ['DeepSeekClient', 'create_deepseek_client']
