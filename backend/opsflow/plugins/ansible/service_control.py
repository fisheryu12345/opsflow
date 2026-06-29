"""服务控制 — 控制系统服务的启动/停止/重启/重载状态（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ServiceControlPlugin(TowerBasePlugin):
    name = "服务控制"
    name_en = "Service Control"
    code = "service_control"
    group = "Ansible"
    description = "控制系统服务的启动/停止/重启/重载状态"
    description_en = "Start, stop, or restart services on remote hosts"
    risk_level = "high"
    icon = "Switch"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="service",
                type="input",
                name="服务名称",
                name_en="Service Name",
                attrs={"placeholder": "服务名称", "placeholder_en": "Service name"},
                validation=[ValidationRule(type="required", error_message="请输入服务名称")],
            ),
            FormItem(
                tag_code="action",
                type="select",
                name="操作",
                name_en="Action",
                default="status",
                col=6,
                attrs={
                    "placeholder": "操作: start/stop/restart/reload/status",
                    "placeholder_en": "Action: start/stop/restart/reload/status",
                    "options": [
                        {"label": "start", "value": "start"},
                        {"label": "stop", "value": "stop"},
                        {"label": "restart", "value": "restart"},
                        {"label": "reload", "value": "reload"},
                        {"label": "status", "value": "status"},
                    ],
                },
            ),
            FormItem(
                tag_code="enabled",
                type="checkbox",
                name="是否设置开机自启",
                name_en="Enable on Boot",
                default=False,
                col=6,
                attrs={"options": [{"label": "设置开机自启", "value": True}]},
            ),
        ]
