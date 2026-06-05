# -*- coding: utf-8 -*-
"""Seed built-in monitor data: ActionPlugins, demo NotifyGroup, demo ShieldPlan

Usage:
    python manage.py seed_monitor
"""

from django.core.management.base import BaseCommand
from django.conf import settings


BUILTIN_PLUGINS = [
    {
        'plugin_type': 'notice',
        'plugin_key': 'wecom_robot',
        'name': '企业微信机器人',
        'description': '通过企业微信机器人 Webhook 发送告警通知',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'notice',
        'adapter_class': 'monitor.adapters.notify.wecom.WeComNotify',
        'config_schema': {
            'type': 'object',
            'properties': {
                'webhook_url': {'type': 'string', 'title': 'Webhook地址'},
                'mentioned_list': {'type': 'array', 'title': '@提醒用户', 'items': {'type': 'string'}},
            },
            'required': ['webhook_url'],
        },
    },
    {
        'plugin_type': 'notice',
        'plugin_key': 'dingtalk_robot',
        'name': '钉钉机器人',
        'description': '通过钉钉机器人 Webhook 发送告警通知',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'notice',
        'adapter_class': 'monitor.adapters.notify.dingtalk.DingTalkNotify',
        'config_schema': {
            'type': 'object',
            'properties': {
                'webhook_url': {'type': 'string', 'title': 'Webhook地址'},
                'secret': {'type': 'string', 'title': '加签密钥'},
            },
            'required': ['webhook_url'],
        },
    },
    {
        'plugin_type': 'notice',
        'plugin_key': 'email_smtp',
        'name': '邮件通知',
        'description': '通过 SMTP 发送邮件告警通知',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'notice',
        'adapter_class': 'monitor.adapters.notify.email.EmailNotify',
        'config_schema': {
            'type': 'object',
            'properties': {
                'smtp_host': {'type': 'string', 'title': 'SMTP服务器'},
                'smtp_port': {'type': 'integer', 'title': '端口', 'default': 465},
                'smtp_user': {'type': 'string', 'title': '用户名'},
                'smtp_password': {'type': 'string', 'title': '密码'},
                'from_addr': {'type': 'string', 'title': '发件地址'},
            },
            'required': ['smtp_host', 'smtp_user', 'smtp_password'],
        },
    },
    {
        'plugin_type': 'webhook',
        'plugin_key': 'generic_webhook',
        'name': '通用 Webhook',
        'description': 'HTTP POST 回调，向指定 URL 推送告警 JSON',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'webhook',
        'adapter_class': '',
        'config_schema': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string', 'title': '回调URL'},
                'method': {'type': 'string', 'title': '请求方法', 'default': 'POST'},
                'headers': {'type': 'object', 'title': '自定义请求头'},
            },
            'required': ['url'],
        },
    },
    {
        'plugin_type': 'opsflow',
        'plugin_key': 'opsflow_trigger',
        'name': 'OpsFlow自愈流程',
        'description': '触发 OpsFlow 流程模板执行自动化自愈',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'auto_recovery',
        'adapter_class': 'monitor.adapters.action.opsflow.OpsflowAction',
        'config_schema': {
            'type': 'object',
            'properties': {
                'template_id': {'type': 'integer', 'title': '流程模板ID'},
                'api_url': {'type': 'string', 'title': 'OpsFlow API地址'},
                'api_token': {'type': 'string', 'title': 'API Token'},
            },
            'required': ['template_id'],
        },
    },
    {
        'plugin_type': 'itsm',
        'plugin_key': 'itsm_incident',
        'name': 'ITSM事件工单',
        'description': '自动创建 ITSM 事件工单',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'ticket',
        'adapter_class': 'monitor.adapters.action.itsm.ItsmAction',
        'config_schema': {
            'type': 'object',
            'properties': {
                'title_template': {'type': 'string', 'title': '工单标题模板'},
            },
        },
    },
    {
        'plugin_type': 'awx',
        'plugin_key': 'awx_job',
        'name': 'AWX作业',
        'description': '触发 AWX/Ansible Tower 作业模板',
        'is_builtin': True,
        'plugin_source': 'builtin',
        'category': 'auto_recovery',
        'adapter_class': 'monitor.adapters.action.awx.AwxAction',
        'config_schema': {
            'type': 'object',
            'properties': {
                'awx_url': {'type': 'string', 'title': 'AWX地址'},
                'template_id': {'type': 'integer', 'title': '作业模板ID'},
                'username': {'type': 'string', 'title': '用户名'},
                'password': {'type': 'string', 'title': '密码'},
            },
            'required': ['awx_url', 'template_id'],
        },
    },
]


class Command(BaseCommand):
    help = 'Seed built-in action plugins and demo data for monitor module'

    def handle(self, *args, **options):
        self._seed_plugins()
        self.stdout.write(self.style.SUCCESS('Monitor seed data loaded successfully'))

    def _seed_plugins(self):
        from monitor.models import ActionPlugin
        created = 0
        for data in BUILTIN_PLUGINS:
            _, is_new = ActionPlugin.objects.update_or_create(
                plugin_key=data['plugin_key'],
                defaults=data,
            )
            if is_new:
                created += 1
        self.stdout.write(f"  ActionPlugins: {created} new, {len(BUILTIN_PLUGINS)} total")
