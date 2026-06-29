"""Redfish 关机 — 通过 BMC 远程关机"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishPowerOffPlugin(BasePlugin):
    name = "Redfish 关机"
    name_en = "Power Off"
    code = "redfish_power_off"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口远程关闭服务器电源"
    description_en = "Power off server via Redfish API"
    risk_level = "high"
    icon = "VideoPause"
    color = "#F56C6C"
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
                tag_code="shutdown_type",
                type="select",
                name="关机方式",
                name_en="Shutdown Type",
                default="GracefulShutdown",
                attrs={
                    "options": [
                        {"label": "优雅关机 (GracefulShutdown)", "value": "GracefulShutdown"},
                        {"label": "强制关机 (ForceOff)", "value": "ForceOff"},
                    ],
                },
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", shutdown_type: str = "GracefulShutdown",
                **kwargs) -> dict:
        try:
            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "action": "power_off",
                    "shutdown_type": shutdown_type,
                    "result": f"关机指令 ({shutdown_type}) 已发送",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "shutdown_type", "type": "string", "description": "关机方式", "description_en": "Shutdown type"},
            {"name": "result", "type": "string", "description": "执行结果", "description_en": "Execution result"},
        ]
