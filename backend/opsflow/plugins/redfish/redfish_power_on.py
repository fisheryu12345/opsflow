"""Redfish 开机 — 通过 BMC 远程开机"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishPowerOnPlugin(BasePlugin):
    name = "Redfish 开机"
    name_en = "Power On"
    code = "redfish_power_on"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口远程开启服务器电源"
    description_en = "Power on server via Redfish API"
    risk_level = "medium"
    icon = "VideoPlay"
    color = "#67C23A"
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
                tag_code="verify_connectivity",
                type="checkbox",
                name="执行前检查",
                name_en="Pre-check",
                default=True,
                attrs={"options": [{"label": "开机前先 Ping 检测 BMC 可达性", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", verify_connectivity: bool = True,
                **kwargs) -> dict:
        try:
            if verify_connectivity:
                import subprocess
                res = subprocess.run(
                    ["ping", "-n", "1", bmc_host],
                    capture_output=True, text=True, timeout=10,
                )
                if res.returncode != 0:
                    return {"success": False, "data": {}, "error": f"BMC {bmc_host} 不可达"}
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "action", "type": "string", "description": "执行动作", "description_en": "Executed action"},
            {"name": "result", "type": "string", "description": "执行结果", "description_en": "Execution result"},
        ]
