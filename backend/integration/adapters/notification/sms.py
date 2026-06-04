# -*- coding: utf-8 -*-
"""SMS notification adapter

短信通知适配器 — 通过阿里云短信网关发送短信
"""

import logging

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class AliyunSmsConnector(BaseConnector):
    """
    阿里云短信适配器
    配置项:
    - sign_name: 短信签名
    - template_code: 短信模板编码
    """

    def health_check(self) -> HealthResult:
        """检查短信网关可达性"""
        try:
            client = self.get_client()
            if client:
                return HealthResult(is_healthy=True, message="短信网关配置正常")
            return HealthResult(is_healthy=False, message="客户端创建失败")
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
        cred = self.instance.credentials.first()
        ak = decrypt_credential(cred.encrypted_value) if cred else ""
        region = self.config.get('region', 'cn-hangzhou')
        self._client = AliyunAcsClient(ak, '', region)
        return self._client

    def send_sms(self, phone_numbers: str, template_params: dict = None):
        """发送短信"""
        client = self.get_client()
        sign_name = self.config.get('sign_name', '')
        template_code = self.config.get('template_code', '')

        try:
            from aliyunsdkcore.request import CommonRequest
            request = CommonRequest()
            request.set_accept_format('json')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_method('POST')
            request.set_protocol_type('https')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')
            request.add_query_param('RegionId', self.config.get('region', 'cn-hangzhou'))
            request.add_query_param('PhoneNumbers', phone_numbers)
            request.add_query_param('SignName', sign_name)
            request.add_query_param('TemplateCode', template_code)
            if template_params:
                import json
                request.add_query_param('TemplateParam', json.dumps(template_params))
            response = client.do_action_with_exception(request)
            return response
        except Exception as e:
            logger.error(f"短信发送失败 [{phone_numbers}]: {e}")
            raise
