# -*- coding: utf-8 -*-
"""Seed default connector definitions into the database

Usage:
    python manage.py seed_connector_definitions

This seeds the built-in connector types (cloud providers, notification channels, auth sources)
so they appear in the integration center's connector marketplace.
"""

import logging

from django.core.management.base import BaseCommand
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

DEFAULT_CONNECTORS = [
    # -- Cloud Providers --
    {
        'code': 'aliyun_ecs',
        'name': '阿里云 ECS',
        'category': 'cloud',
        'version': '1.0',
        'icon': '/static/icons/aliyun.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'region': {'type': 'string', 'title': '地域', 'default': 'cn-hangzhou'},
                'endpoint': {'type': 'string', 'title': 'API 端点'},
            },
        },
        'provider_class': 'integration.adapters.cloud.aliyun.AliyunConnector',
        'sort_order': 10,
    },
    {
        'code': 'tencent_cvm',
        'name': '腾讯云 CVM',
        'category': 'cloud',
        'version': '1.0',
        'icon': '/static/icons/tencent.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'region': {'type': 'string', 'title': '地域', 'default': 'ap-guangzhou'},
            },
        },
        'provider_class': '',
        'sort_order': 20,
    },
    {
        'code': 'huawei_ecs',
        'name': '华为云 ECS',
        'category': 'cloud',
        'version': '1.0',
        'icon': '/static/icons/huawei.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'region': {'type': 'string', 'title': '地域', 'default': 'cn-east-3'},
            },
        },
        'provider_class': '',
        'sort_order': 30,
    },
    # -- Notification Channels --
    {
        'code': 'aliyun_sms',
        'name': '阿里云短信',
        'category': 'notification',
        'version': '1.0',
        'icon': '/static/icons/sms.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'region': {'type': 'string', 'title': '地域', 'default': 'cn-hangzhou'},
                'sign_name': {'type': 'string', 'title': '短信签名'},
                'template_code': {'type': 'string', 'title': '短信模板编码'},
            },
            'required': ['sign_name', 'template_code'],
        },
        'provider_class': 'integration.adapters.notification.sms.AliyunSmsConnector',
        'sort_order': 100,
    },
    {
        'code': 'wecom_bot',
        'name': '企业微信 Bot',
        'category': 'notification',
        'version': '1.0',
        'icon': '/static/icons/wecom.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'webhook_url': {'type': 'string', 'title': 'Webhook 地址', 'format': 'uri'},
            },
            'required': ['webhook_url'],
        },
        'provider_class': 'integration.adapters.notification.wecom.WeComBotConnector',
        'sort_order': 110,
    },
    {
        'code': 'dingtalk_bot',
        'name': '钉钉 Bot',
        'category': 'notification',
        'version': '1.0',
        'icon': '/static/icons/dingtalk.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'webhook_url': {'type': 'string', 'title': 'Webhook 地址', 'format': 'uri'},
                'secret': {'type': 'string', 'title': '加签密钥(可选)'},
            },
            'required': ['webhook_url'],
        },
        'provider_class': 'integration.adapters.notification.dingtalk.DingtalkBotConnector',
        'sort_order': 120,
    },
    {
        'code': 'email_smtp',
        'name': '邮件 (SMTP)',
        'category': 'notification',
        'version': '1.0',
        'icon': '/static/icons/email.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'host': {'type': 'string', 'title': 'SMTP 服务器'},
                'port': {'type': 'integer', 'title': '端口', 'default': 465},
                'use_ssl': {'type': 'boolean', 'title': '使用 SSL', 'default': True},
                'from_address': {'type': 'string', 'title': '发件地址', 'format': 'email'},
            },
            'required': ['host', 'from_address'],
        },
        'provider_class': 'integration.adapters.notification.email_adapter.EmailSmtpConnector',
        'sort_order': 130,
    },
    # -- Auth Sources --
    {
        'code': 'ldap',
        'name': 'LDAP 认证源',
        'category': 'auth',
        'version': '1.0',
        'icon': '/static/icons/ldap.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'server_uri': {'type': 'string', 'title': 'LDAP 服务器 URI'},
                'base_dn': {'type': 'string', 'title': 'Base DN'},
                'bind_dn': {'type': 'string', 'title': 'Bind DN'},
            },
            'required': ['server_uri', 'base_dn'],
        },
        'provider_class': '',
        'sort_order': 200,
    },
    # -- AI Services --
    {
        'code': 'openai',
        'name': 'OpenAI',
        'category': 'ai',
        'version': '1.0',
        'icon': '/static/icons/openai.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'api_base': {'type': 'string', 'title': 'API 地址', 'default': 'https://api.openai.com/v1'},
                'model': {'type': 'string', 'title': '默认模型', 'default': 'gpt-4o'},
                'max_tokens': {'type': 'integer', 'title': '最大输出 Token', 'default': 4096},
                'temperature': {'type': 'number', 'title': '温度参数', 'default': 0.7, 'minimum': 0, 'maximum': 2},
                'timeout': {'type': 'integer', 'title': '超时(秒)', 'default': 30},
            },
            'required': [],
        },
        'provider_class': 'integration.adapters.ai.openai.OpenAIConnector',
        'sort_order': 300,
    },
    {
        'code': 'deepseek',
        'name': 'DeepSeek',
        'category': 'ai',
        'version': '1.0',
        'icon': '/static/icons/deepseek.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'api_base': {'type': 'string', 'title': 'API 地址', 'default': 'https://api.deepseek.com/v1'},
                'model': {'type': 'string', 'title': '默认模型', 'default': 'deepseek-chat'},
                'max_tokens': {'type': 'integer', 'title': '最大输出 Token', 'default': 4096},
                'temperature': {'type': 'number', 'title': '温度参数', 'default': 0.7, 'minimum': 0, 'maximum': 2},
                'timeout': {'type': 'integer', 'title': '超时(秒)', 'default': 30},
            },
            'required': [],
        },
        'provider_class': 'integration.adapters.ai.openai.OpenAIConnector',
        'sort_order': 310,
    },
    {
        'code': 'anthropic',
        'name': 'Anthropic Claude',
        'category': 'ai',
        'version': '1.0',
        'icon': '/static/icons/anthropic.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'api_base': {'type': 'string', 'title': 'API 地址', 'default': 'https://api.anthropic.com'},
                'model': {'type': 'string', 'title': '默认模型', 'default': 'claude-sonnet-4-20250514'},
                'max_tokens': {'type': 'integer', 'title': '最大输出 Token', 'default': 4096},
                'timeout': {'type': 'integer', 'title': '超时(秒)', 'default': 30},
            },
            'required': [],
        },
        'provider_class': 'integration.adapters.ai.anthropic.AnthropicConnector',
        'sort_order': 320,
    },
    {
        'code': 'tongyi_qwen',
        'name': '通义千问 (Qwen)',
        'category': 'ai',
        'version': '1.0',
        'icon': '/static/icons/qwen.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'api_base': {'type': 'string', 'title': 'API 地址', 'default': 'https://dashscope.aliyuncs.com/compatible-mode/v1'},
                'model': {'type': 'string', 'title': '默认模型', 'default': 'qwen-plus'},
                'max_tokens': {'type': 'integer', 'title': '最大输出 Token', 'default': 4096},
                'temperature': {'type': 'number', 'title': '温度参数', 'default': 0.7, 'minimum': 0, 'maximum': 2},
                'timeout': {'type': 'integer', 'title': '超时(秒)', 'default': 30},
            },
            'required': [],
        },
        'provider_class': 'integration.adapters.ai.openai.OpenAIConnector',
        'sort_order': 330,
    },
    {
        'code': 'local_llm',
        'name': '本地 LLM (OpenAI 兼容)',
        'category': 'ai',
        'version': '1.0',
        'icon': '/static/icons/local-llm.svg',
        'config_schema': {
            'type': 'object',
            'properties': {
                'api_base': {'type': 'string', 'title': 'API 地址', 'default': 'http://localhost:8000/v1'},
                'model': {'type': 'string', 'title': '默认模型', 'default': 'local-model'},
                'max_tokens': {'type': 'integer', 'title': '最大输出 Token', 'default': 2048},
                'temperature': {'type': 'number', 'title': '温度参数', 'default': 0.7, 'minimum': 0, 'maximum': 2},
                'timeout': {'type': 'integer', 'title': '超时(秒)', 'default': 60},
            },
            'required': ['api_base'],
        },
        'provider_class': 'integration.adapters.ai.openai.OpenAIConnector',
        'sort_order': 340,
    },
]


class Command(BaseCommand):
    help = "Seed default connector definitions into the database"

    def handle(self, *args, **options):
        from integration.models.connector import ConnectorDefinition

        created_count = 0
        for data in DEFAULT_CONNECTORS:
            _, created = ConnectorDefinition.objects.get_or_create(
                code=data['code'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {data['name']} ({data['code']})"))
            else:
                self.stdout.write(f"  [--] Already exists: {data['code']}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Created {created_count} connector definitions."))
