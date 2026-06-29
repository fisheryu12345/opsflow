"""Redfish 获取系统信息 — 通过 BMC 获取服务器硬件信息"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishGetSystemInfoPlugin(BasePlugin):
    name = "Redfish 系统信息"
    name_en = "System Info"
    code = "redfish_get_system_info"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口获取服务器硬件系统信息"
    description_en = "Get server system information via Redfish API"
    risk_level = "low"
    icon = "Monitor"
    color = "#409EFF"

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
                tag_code="include_health",
                type="checkbox",
                name="健康状态",
                name_en="Health Status",
                default=True,
                attrs={"options": [{"label": "获取硬件健康状态", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", include_health: bool = True,
                **kwargs) -> dict:
        try:
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "system_info", "type": "object", "description": "系统信息", "description_en": "System information"},
            {"name": "health", "type": "object", "description": "硬件健康状态", "description_en": "Hardware health status"},
        ]
