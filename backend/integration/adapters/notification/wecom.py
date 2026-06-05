# -*- coding: utf-8 -*-
"""WeCom Bot notification adapter

企业微信群机器人适配器 — 通过 Webhook 推送 Markdown/Text 消息

配置项:
  - webhook_url: 机器人 Webhook 地址

无需凭证，所有配置在 config 中
"""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class WeComBotConnector(BaseConnector):
    """
    企业微信群机器人适配器
    支持 text 和 markdown 消息类型
    """

    def get_client(self):
        """返回 webhook_url (无需 SDK，直接 HTTP POST)"""
        if self._client:
            return self._client
        self._client = self.config.get('webhook_url', '')
        return self._client

    def health_check(self) -> HealthResult:
        """通过发送空消息检查 Webhook 可达性"""
        webhook_url = self.config.get('webhook_url', '')
        if not webhook_url:
            return HealthResult(is_healthy=False, message="未配置 webhook_url")
        try:
            # Send a lightweight text message to verify
            payload = json.dumps({
                "msgtype": "text",
                "text": {"content": "【健康检查】连接测试"}
            }).encode('utf-8')
            req = Request(webhook_url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get('errcode') == 0:
                    return HealthResult(is_healthy=True, message="企业微信 Bot 连接正常")
                return HealthResult(is_healthy=False, message=f"API 异常: {result.get('errmsg', 'unknown')}")
        except URLError as e:
            return HealthResult(is_healthy=False, message=f"网络不可达: {e.reason}")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def send_text(self, content: str, mentioned_list: list[str] = None) -> dict:
        """发送文本消息

        Args:
            content: 消息内容
            mentioned_list: @ 的用户列表（@all 表示全部）
        """
        webhook_url = self.get_client()
        if not webhook_url:
            raise ValueError("webhook_url 未配置")

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
        }
        if mentioned_list:
            payload["text"]["mentioned_list"] = mentioned_list

        return self._post(payload)

    def send_markdown(self, content: str) -> dict:
        """发送 Markdown 消息

        Args:
            content: Markdown 格式内容
        """
        webhook_url = self.get_client()
        if not webhook_url:
            raise ValueError("webhook_url 未配置")

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }
        return self._post(payload)

    def _post(self, payload: dict) -> dict:
        """发送 HTTP POST 请求到 Webhook"""
        data = json.dumps(payload).encode('utf-8')
        req = Request(self._client, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        try:
            with urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get('errcode') != 0:
                    raise RuntimeError(f"企业微信 API 错误: {result.get('errmsg', 'unknown')}")
                return result
        except URLError as e:
            raise RuntimeError(f"网络错误: {e.reason}") from e

    def close(self):
        self._client = None
