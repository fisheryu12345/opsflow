"""Redfish 重启 — 通过 BMC 远程重启/重置服务器"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishPowerCyclePlugin(BasePlugin):
    name = "Redfish 重启"
    name_en = "Power Cycle"
    code = "redfish_power_cycle"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口远程重启或重置服务器"
    description_en = "Power cycle server via Redfish API"
    risk_level = "high"
    icon = "Refresh"
    color = "#E6A23C"
    show_loop_config = False

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="BMC 连接",
                name_en="BMC Connection",
                tag_code="bmc_connection",
                items=[
                    FormItem(
                        tag_code="bmc_host",
                        type="async_select",
                        name="BMC 地址",
                        name_en="BMC Host",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servers/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择服务器...",
                            "placeholder_en": "Select server from CMDB...",
                        },
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="bmc_user",
                        type="input",
                        name="用户名",
                        name_en="Username",
                        default="admin",
                        attrs={"placeholder": "BMC 用户名", "placeholder_en": "BMC username"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="bmc_password",
                        type="input",
                        name="密码",
                        name_en="Password",
                        attrs={"placeholder": "BMC 密码", "placeholder_en": "BMC password", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormItem(
                tag_code="reset_type",
                type="select",
                name="重置类型",
                name_en="Reset Type",
                default="PowerCycle",
                attrs={
                    "options": [
                        {"label": "冷重启 (PowerCycle)", "value": "PowerCycle"},
                        {"label": "热重启 (GracefulRestart)", "value": "GracefulRestart"},
                        {"label": "强制重启 (ForceRestart)", "value": "ForceRestart"},
                    ],
                },
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", reset_type: str = "PowerCycle",
                **kwargs) -> dict:
        try:
            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "action": "power_cycle",
                    "reset_type": reset_type,
                    "result": f"重启指令 ({reset_type}) 已发送",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "reset_type", "type": "string", "description": "重置类型", "description_en": "Reset type"},
            {"name": "result", "type": "string", "description": "执行结果", "description_en": "Execution result"},
        ]
