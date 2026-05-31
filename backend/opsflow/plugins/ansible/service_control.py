"""服务控制 — 控制系统服务的启动/停止/重启/重载状态"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ServiceControlPlugin(BasePlugin):
    name = "服务控制"
    code = "service_control"
    group = "Ansible"
    description = "控制系统服务的启动/停止/重启/重载状态"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="service",
                type="input",
                name="服务名称",
                attrs={"placeholder": "服务名称"},
                validation=[ValidationRule(type="required", error_message="请输入服务名称")],
            ),
            FormItem(
                tag_code="action",
                type="select",
                name="操作",
                default="status",
                col=6,
                attrs={
                    "placeholder": "操作: start/stop/restart/reload/status",
                    "options": [
                        {"label": "启动", "value": "start"},
                        {"label": "停止", "value": "stop"},
                        {"label": "重启", "value": "restart"},
                        {"label": "重载", "value": "reload"},
                        {"label": "状态", "value": "status"},
                    ],
                },
            ),
            FormItem(
                tag_code="enabled",
                type="checkbox",
                name="是否设置开机自启",
                default=False,
                col=6,
                attrs={"options": [{"label": "设置开机自启", "value": True}]},
            ),
        ]

    def execute(self, service: str = "", action: str = "status", enabled: bool = False, **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "changed": False,
                "status": action,
            },
        }
