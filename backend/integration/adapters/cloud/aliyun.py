# -*- coding: utf-8 -*-
"""Aliyun Cloud connector adapter

阿里云 ECS 连接器 — 通过集成中心管理阿里云资产同步
"""

import logging

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class AliyunConnector(BaseConnector):
    """
    阿里云 ECS 适配器
    配置项:
    - region: 地域 (default: cn-hangzhou)
    - endpoint: API 端点
    """

    def health_check(self) -> HealthResult:
        """检查阿里云 API 可达性"""
        try:
            client = self.get_client()
            # 调用 DescribeRegions 测试连通性
            response = client.describe_regions()
            if response:
                return HealthResult(is_healthy=True, message="API 可达")
            return HealthResult(is_healthy=False, message="API 返回空响应")
        except ImportError:
            return HealthResult(is_healthy=False, message="需要安装 aliyun-python-sdk-core")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self):
        """获取阿里云 SDK 客户端"""
        if self._client:
            return self._client
        try:
            from aliyunsdkcore.client import AcsClient as AliyunAcsClient
        except ImportError:
            raise ImportError("请安装 aliyun-python-sdk-core")

        from integration.services.credential_service import decrypt_credential

        creds = {
            c.name: decrypt_credential(c.encrypted_value)
            for c in self.instance.credentials.all()
        }
        ak = creds.get("access_key_id", "")
        sk = creds.get("access_key_secret", "")
        region = self.config.get("region", "cn-hangzhou")

        self._client = AliyunAcsClient(ak, sk, region)
        return self._client
