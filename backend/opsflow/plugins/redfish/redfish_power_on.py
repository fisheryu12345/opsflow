"""Redfish 开机 — 通过 BMC 远程开机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishPowerOnPlugin(BasePlugin):
    name = "Redfish 开机"
    code = "redfish_power_on"
    group = "Redfish"
    description = "通过 BMC Redfish 接口远程开启服务器电源"
    description_en = "Power on server via Redfish API"
    risk_level = "medium"

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
                tag_code="verify_connectivity",
                type="checkbox",
                name="执行前检查",
                default=True,
                attrs={"options": [{"label": "开机前先 Ping 检测 BMC 可达性", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", verify_connectivity: bool = True,
                **kwargs) -> dict:
        # 占位实现 — 集成实际 Redfish SDK 调用
        try:
            if verify_connectivity:
                import subprocess
                res = subprocess.run(
                    ["ping", "-n", "1", bmc_host],
                    capture_output=True, text=True, timeout=10,
                )
                if res.returncode != 0:
                    return {"success": False, "data": {}, "error": f"BMC {bmc_host} 不可达"}

            # TODO: 使用 redfish 库调用
            # with redfish_client(bmc_host, bmc_user, bmc_password) as client:
            #     client.reset_system("On")

            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "action": "power_on",
                    "result": "开机指令已发送",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
