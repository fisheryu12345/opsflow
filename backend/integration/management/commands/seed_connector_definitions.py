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
        'provider_class': '',
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
            },
            'required': ['webhook_url'],
        },
        'provider_class': '',
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
        'provider_class': '',
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
