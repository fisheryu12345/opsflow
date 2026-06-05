# -*- coding: utf-8 -*-
"""DingTalk Bot notification adapter

钉钉群机器人适配器 — 通过 Webhook 推送 Text/Markdown/Link 消息

配置项:
  - webhook_url: 机器人 Webhook 地址（含 access_token）

无需凭证，所有配置在 config 中
"""

import json
import logging
import time
import hmac
import hashlib
import base64
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class DingtalkBotConnector(BaseConnector):
    """
    钉钉群机器人适配器
    支持 text / markdown / link 消息类型
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
            payload = {
                "msgtype": "text",
                "text": {"content": "【健康检查】连接测试"}
            }
            self._post(payload)
            return HealthResult(is_healthy=True, message="钉钉 Bot 连接正常")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def send_text(self, content: str, at_mobiles: list[str] = None,
                  is_at_all: bool = False) -> dict:
        """发送文本消息

        Args:
            content: 消息内容
            at_mobiles: @ 的手机号列表
            is_at_all: 是否 @ 所有人
        """
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
        at = {}
        if at_mobiles:
            at["atMobiles"] = at_mobiles
        if is_at_all:
            at["isAtAll"] = True
        if at:
            payload["at"] = at
        return self._post(payload)

    def send_markdown(self, title: str, text: str,
                      at_mobiles: list[str] = None,
                      is_at_all: bool = False) -> dict:
        """发送 Markdown 消息

        Args:
            title: 消息标题
            text: Markdown 格式内容
            at_mobiles: @ 的手机号列表
            is_at_all: 是否 @ 所有人
        """
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title[:20],
                "text": text,
            },
        }
        at = {}
        if at_mobiles:
            at["atMobiles"] = at_mobiles
        if is_at_all:
            at["isAtAll"] = True
        if at:
            payload["at"] = at
        return self._post(payload)

    def send_link(self, title: str, text: str, message_url: str,
                  pic_url: str = '') -> dict:
        """发送链接消息

        Args:
            title: 标题
            text: 描述文本
            message_url: 点击跳转 URL
            pic_url: 图片 URL
        """
        payload = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": text,
                "messageUrl": message_url,
                "picUrl": pic_url,
            },
        }
        return self._post(payload)

    @staticmethod
    def _sign_url(webhook_url: str, secret: str) -> str:
        """加签 URL（如果配置了 secret）"""
        if not secret:
            return webhook_url
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')

        parsed = urlparse(webhook_url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query['timestamp'] = [timestamp]
        query['sign'] = [sign]
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def _post(self, payload: dict) -> dict:
        """发送 HTTP POST 请求到 Webhook"""
        webhook_url = self._client
        if not webhook_url:
            raise ValueError("webhook_url 未配置")

        # Handle signing if secret is configured
        secret = self.config.get('secret', '')
        if secret:
            webhook_url = self._sign_url(webhook_url, secret)

        data = json.dumps(payload).encode('utf-8')
        req = Request(webhook_url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        try:
            with urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get('errcode') != 0:
                    raise RuntimeError(
                        f"钉钉 API 错误: {result.get('errmsg', 'unknown')}"
                    )
                return result
        except URLError as e:
            raise RuntimeError(f"网络错误: {e.reason}") from e

    def close(self):
        self._client = None
