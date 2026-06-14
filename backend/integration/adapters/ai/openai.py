# -*- coding: utf-8 -*-
"""OpenAI-compatible AI connector adapter

支持 OpenAI、DeepSeek、通义千问等兼容 OpenAI SDK 的 AI 服务。
通过 ConnectorInstance.config 中的 api_base 区分不同供应商。
"""

import logging
from typing import Any, Optional

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class OpenAIConnector(BaseConnector):
    """
    OpenAI 兼容 API 连接器适配器

    配置项 (config):
        api_base: API 地址 (默认 https://api.openai.com/v1)
        model: 默认模型名 (如 gpt-4o, deepseek-chat, qwen-plus)
        max_tokens: 最大输出 Token 数 (默认 4096)
        temperature: 温度参数 (默认 0.7)
        timeout: 请求超时秒数 (默认 30)

    凭证 (credential):
        api_key: API 密钥
    """

    def __init__(self, instance):
        super().__init__(instance)
        self._api_key = None

    def _load_credential(self) -> Optional[str]:
        """从凭证存储中加载 api_key"""
        if self._api_key:
            return self._api_key
        try:
            from integration.models.credential import ConnectorCredential
            cred = ConnectorCredential.objects.filter(
                instance=self.instance,
                cred_type__in=['token', 'access_key', 'custom'],
                name__in=['api_key', 'API Key', 'token', 'secret'],
            ).first()
            if cred:
                from integration.services.credential_service import decrypt_credential
                self._api_key = decrypt_credential(cred.encrypted_value)
                return self._api_key
        except Exception as e:
            logger.warning("[OpenAIConnector] Failed to load credential: %s", e)
        return None

    def health_check(self) -> HealthResult:
        """通过查询模型列表检查 API 可达性"""
        api_base = self.config.get('api_base', 'https://api.openai.com/v1').rstrip('/')
        api_key = self._load_credential()
        if not api_key:
            return HealthResult(is_healthy=False, message="No API key configured — add a credential with name 'api_key'")

        import urllib.request
        import json

        try:
            req = urllib.request.Request(
                f"{api_base}/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="GET",
            )
            timeout = self.config.get('timeout', 10)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models = data.get('data', [])
                    return HealthResult(
                        is_healthy=True,
                        message=f"Connected. {len(models)} models available. e.g. {models[0]['id'] if models else '-'}",
                    )
                else:
                    return HealthResult(is_healthy=False, message=f"HTTP {resp.status}")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self) -> Any:
        """返回 OpenAI 客户端实例"""
        api_key = self._load_credential()
        if not api_key:
            raise ValueError("No API key configured")

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            )

        timeout = self.config.get('timeout', 30)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 30
        client = OpenAI(
            api_key=api_key,
            base_url=self.config.get('api_base', 'https://api.openai.com/v1'),
            timeout=timeout,
            max_retries=2,
        )
        return client

    def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        """快捷调用聊天补全 API

        :param messages: [{"role": "user", "content": "..."}] 格式的消息列表
        :param model: 模型名，默认使用 config 中的 model
        :param kwargs: 透传给 chat.completions.create 的参数 (temperature, max_tokens, response_format 等)
        :return: API 响应 dict
        """
        client = self.get_client()
        model = model or self.config.get('model', 'gpt-4o')
        max_tokens = kwargs.pop('max_tokens', self.config.get('max_tokens', 4096))
        temperature = kwargs.pop('temperature', self.config.get('temperature', 0.7))
        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):
            max_tokens = 4096
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = 0.7
        create_kwargs = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        # 支持 response_format（如 JSON mode）、stop、top_p 等额外参数
        create_kwargs.update(kwargs)
        resp = client.chat.completions.create(**create_kwargs)
        return {
            "content": resp.choices[0].message.content,
            "model": resp.model,
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            },
        }
