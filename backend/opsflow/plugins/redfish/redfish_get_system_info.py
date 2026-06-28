"""Redfish 获取系统信息 — 通过 BMC 获取服务器硬件信息"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishGetSystemInfoPlugin(BasePlugin):
    name = "Redfish 系统信息"
    code = "redfish_get_system_info"
    group = "Redfish"
    description = "通过 BMC Redfish 接口获取服务器硬件系统信息"
    description_en = "Get server system information via Redfish API"
    risk_level = "low"

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
                tag_code="include_health",
                type="checkbox",
                name="健康状态",
                default=True,
                attrs={"options": [{"label": "获取硬件健康状态", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", include_health: bool = True,
                **kwargs) -> dict:
        # 占位实现 — 集成实际 Redfish SDK 调用
        try:
            # TODO: 使用 redfish 库调用
            # with redfish_client(bmc_host, bmc_user, bmc_password) as client:
            #     system = client.get_system()
            #     ...

            system_info = {
                "manufacturer": "Unknown",
                "model": "Unknown",
                "serial_number": "Unknown",
                "bios_version": "Unknown",
                "cpu": {"model": "Unknown", "cores": 0, "threads": 0},
                "memory_gb": 0,
                "power_state": "Unknown",
            }

            health = {}
            if include_health:
                health = {
                    "overall_status": "OK",
                    "cpu_health": "OK",
                    "memory_health": "OK",
                    "fan_health": "OK",
                    "power_supply_health": "OK",
                }

            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "system_info": system_info,
                    "health": health,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
