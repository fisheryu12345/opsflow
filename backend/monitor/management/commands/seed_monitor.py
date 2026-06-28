"""Seed monitor ActionPlugins"""

from django.core.management.base import BaseCommand
from monitor.models import ActionPlugin

class Command(BaseCommand):
    help = "Seed monitor ActionPlugins"

    def handle(self, *args, **options):
        self._seed_monitor_plugins()
        self.stdout.write(self.style.SUCCESS("Seed complete!"))

    def _seed_monitor_plugins(self):
        from monitor.models import ActionPlugin
        plugins = [
            {"plugin_type": "notice", "plugin_key": "wecom_robot", "name": "企业微信机器人",
             "config_schema": {"webhook_url": {"type": "string"}}},
            {"plugin_type": "notice", "plugin_key": "dingtalk_robot", "name": "钉钉机器人",
             "config_schema": {"access_token": {"type": "string"}}},
            {"plugin_type": "notice", "plugin_key": "email_smtp", "name": "邮件通知",
             "config_schema": {"smtp_server": {"type": "string"}, "smtp_port": {"type": "integer"}}},
            {"plugin_type": "webhook", "plugin_key": "generic_webhook", "name": "通用 Webhook",
             "config_schema": {"url": {"type": "string"}, "method": {"type": "string"}}},
            {"plugin_type": "opsflow", "plugin_key": "opsflow_trigger", "name": "OpsFlow自愈流程",
             "config_schema": {"template_id": {"type": "integer"}}},
            {"plugin_type": "itsm", "plugin_key": "itsm_incident", "name": "ITSM事件工单",
             "config_schema": {"urgency": {"type": "string"}, "impact": {"type": "string"}}},
            {"plugin_type": "awx", "plugin_key": "awx_job", "name": "AWX作业",
             "config_schema": {"job_template_id": {"type": "integer"}, "inventory_id": {"type": "integer"}}},
        ]
        for data in plugins:
            ActionPlugin.objects.update_or_create(plugin_key=data["plugin_key"], defaults=data)
        self.stdout.write(f">>> Monitor Plugins: {len(plugins)} seeded")

    # ── 6. Connector Definitions ──
