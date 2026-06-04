# -*- coding: utf-8 -*-
"""Anthropic Claude AI connector adapter

支持 Anthropic Claude API，通过 ConnectorInstance.config 配置。
"""

import logging
from typing import Any, Optional

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class AnthropicConnector(BaseConnector):
    """
    Anthropic Claude API 连接器适配器

    配置项 (config):
        api_base: API 地址 (默认 https://api.anthropic.com)
        model: 默认模型名 (如 claude-sonnet-4-20250514, claude-opus-4-20250514)
        max_tokens: 最大输出 Token 数 (默认 4096)
        timeout: 请求超时秒数 (默认 30)

    凭证 (credential):
        api_key: Anthropic API Key
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
            logger.warning("[AnthropicConnector] Failed to load credential: %s", e)
        return None

    def health_check(self) -> HealthResult:
        """通过查询 API 版本信息检查连通性"""
        api_base = self.config.get('api_base', 'https://api.anthropic.com').rstrip('/')
        api_key = self._load_credential()
        if not api_key:
            return HealthResult(is_healthy=False, message="No API key configured")

        import urllib.request
        import json

        try:
            req = urllib.request.Request(
                f"{api_base}/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.config.get('model', 'claude-sonnet-4-20250514'),
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "ping"}],
                }).encode(),
                method="POST",
            )
            timeout = self.config.get('timeout', 10)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return HealthResult(is_healthy=True, message="Claude API connected successfully")
                else:
                    return HealthResult(is_healthy=False, message=f"HTTP {resp.status}")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self) -> Any:
        """返回 Anthropic 客户端实例"""
        api_key = self._load_credential()
        if not api_key:
            raise ValueError("No API key configured")

        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        client = Anthropic(
            api_key=api_key,
            base_url=self.config.get('api_base', 'https://api.anthropic.com'),
            timeout=self.config.get('timeout', 30),
            max_retries=2,
        )
        return client

    def chat(self, messages: list, model: str = None, **kwargs) -> dict:
        """快捷调用 Claude 消息 API

        :param messages: [{"role": "user", "content": "..."}] 格式的消息列表
        :param model: 模型名，默认使用 config 中的 model
        :return: API 响应 dict
        """
        client = self.get_client()
        model = model or self.config.get('model', 'claude-sonnet-4-20250514')
        resp = client.messages.create(
            model=model,
            max_tokens=kwargs.get('max_tokens', self.config.get('max_tokens', 4096)),
            messages=messages,
        )
        return {
            "content": resp.content[0].text if resp.content else "",
            "model": resp.model,
            "usage": {
                "input_tokens": resp.usage.input_tokens if resp.usage else 0,
                "output_tokens": resp.usage.output_tokens if resp.usage else 0,
            },
        }
