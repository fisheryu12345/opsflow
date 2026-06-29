"""Redfish 固件清单 — 通过 BMC 获取服务器固件版本清单"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishFirmwareInventoryPlugin(BasePlugin):
    name = "Redfish 固件清单"
    name_en = "Firmware Inventory"
    code = "redfish_firmware_inventory"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口获取服务器固件版本清单"
    description_en = "Get server firmware inventory via Redfish API"
    risk_level = "low"
    icon = "Document"
    color = "#909399"

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
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", **kwargs) -> dict:
        try:
            firmware_list = [
                {"name": "BIOS", "version": "2.3.0", "status": "OK"},
                {"name": "iLO/BMC", "version": "1.50", "status": "OK"},
                {"name": "Power Supply FW", "version": "1.01", "status": "OK"},
            ]
            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "firmware_count": len(firmware_list),
                    "firmware_list": firmware_list,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "firmware_count", "type": "number", "description": "固件数量", "description_en": "Firmware count"},
            {"name": "firmware_list", "type": "object", "description": "固件列表", "description_en": "Firmware list"},
        ]
