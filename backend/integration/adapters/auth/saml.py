# -*- coding: utf-8 -*-
"""SAML Identity Provider connector adapter for Integration Hub

SAML IdP 连接器适配器 — 通过集成中心管理 SAML IdP 连接和 metadata 验证。

配置项（存储在 ConnectorInstance.config 中）:
  - entity_id: IdP Entity ID
  - metadata_url: IdP Metadata URL
  - acs_url: SP 的 ACS 回调地址（只读，由系统生成）
  - attr_username: 用户名断言属性 (default: nameId)
  - attr_name: 姓名断言属性 (default: displayName)
  - attr_email: 邮箱断言属性 (default: email)

凭证（存储在 ConnectorCredential 中）:
  - 类型 certificate: 存储 SP 的私钥证书
  - 名称约定 "sp_private_key"

注意:
  - 此适配器只负责连接测试和 metadata 验证
  - SAML ACS 端点处理和 SSO 登录在 iam/sync/ 中实现
  - python3-saml 需要 xmlsec1 库支持
"""

import logging
from typing import Optional

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class SAMLConnector(BaseConnector):
    """SAML Identity Provider 连接器适配器

    提供 IdP metadata 验证 (health_check) 和配置获取。
    实际的 Assertion Consumer Service 在 iam/sync/ 中处理。
    """

    def health_check(self) -> HealthResult:
        """验证 SAML IdP metadata — 检查 metadata URL 是否可达且签名有效

        如果配置了 metadata_url，尝试远程获取并解析。
        如果只有 entity_id（无 metadata_url），返回警告但不报错。
        """
        metadata_url = self.config.get("metadata_url", "").strip()
        entity_id = self.config.get("entity_id", "").strip()

        if not entity_id and not metadata_url:
            return HealthResult(
                is_healthy=False,
                message="未配置 entity_id 或 metadata_url",
            )

        if metadata_url:
            try:
                import requests
                resp = requests.get(metadata_url, timeout=10)
                if resp.status_code != 200:
                    return HealthResult(
                        is_healthy=False,
                        message=f"获取 metadata 失败: HTTP {resp.status_code}",
                    )

                # 检查是否为有效 XML
                import xml.etree.ElementTree as ET
                try:
                    ET.fromstring(resp.content)
                except ET.ParseError as e:
                    return HealthResult(
                        is_healthy=False,
                        message=f"metadata 不是有效 XML: {e}",
                    )

                return HealthResult(
                    is_healthy=True,
                    message=f"metadata 可访问 ({len(resp.content)} bytes)",
                )
            except requests.RequestException as e:
                return HealthResult(
                    is_healthy=False,
                    message=f"连接 metadata_url 失败: {e}",
                )

        # 仅有 entity_id，无法验证
        return HealthResult(
            is_healthy=True,
            message="已配置 entity_id（无 metadata_url，跳过验证）",
        )

    def get_client(self):
        """返回配置字典（SAML 不需要传统意义上的 client）"""
        return {
            "entity_id": self.config.get("entity_id", ""),
            "metadata_url": self.config.get("metadata_url", ""),
            "acs_url": self.config.get("acs_url", ""),
            "attr_username": self.config.get("attr_username", "nameId"),
            "attr_name": self.config.get("attr_name", "displayName"),
            "attr_email": self.config.get("attr_email", "email"),
        }

    def close(self):
        """无资源需要释放"""
        self._client = None
