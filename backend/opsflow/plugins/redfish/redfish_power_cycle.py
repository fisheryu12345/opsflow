"""Redfish 重启 — 通过 BMC 远程重启/重置服务器"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishPowerCyclePlugin(BasePlugin):
    name = "Redfish 重启"
    code = "redfish_power_cycle"
    group = "Redfish"
    description = "通过 BMC Redfish 接口远程重启或重置服务器"
    description_en = "Power cycle server via Redfish API"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="BMC 连接",
                tag_code="bmc_connection",
                items=[
                    FormItem(
                        tag_code="bmc_host",
                        type="async_select",
                        name="BMC 地址",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servers/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择服务器...",
                        },
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="bmc_user",
                        type="input",
                        name="用户名",
                        default="admin",
                        attrs={"placeholder": "BMC 用户名"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="bmc_password",
                        type="input",
                        name="密码",
                        attrs={"placeholder": "BMC 密码", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormItem(
                tag_code="reset_type",
                type="select",
                name="重置类型",
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
        # 占位实现 — 集成实际 Redfish SDK 调用
        try:
            # TODO: 使用 redfish 库调用
            # with redfish_client(bmc_host, bmc_user, bmc_password) as client:
            #     client.reset_system(reset_type)

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
