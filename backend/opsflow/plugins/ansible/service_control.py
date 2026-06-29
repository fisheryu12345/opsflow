"""服务控制 — 控制系统服务的启动/停止/重启/重载状态（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ServiceControlPlugin(TowerBasePlugin):
    name = "服务控制"
    name_en = "Service Control"
    code = "service_control"
    group = "Ansible"
    version = "v1.0"
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "stdout", "type": "string", "description": "命令执行输出", "description_en": "Command execution output"},
            {"name": "stderr", "type": "string", "description": "错误输出", "description_en": "Error output"},
            {"name": "returncode", "type": "integer", "description": "返回码", "description_en": "Return code"},
            {"name": "tower_job_id", "type": "integer", "description": "Tower 作业 ID", "description_en": "Tower job ID"},
            {"name": "tower_status", "type": "string", "description": "Tower 作业状态", "description_en": "Tower job status"},
            {"name": "elapsed", "type": "float", "description": "执行耗时（秒）", "description_en": "Execution elapsed (seconds)"},
        ]
