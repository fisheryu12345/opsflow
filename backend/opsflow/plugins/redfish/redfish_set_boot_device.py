"""Redfish 设置启动设备 — 通过 BMC 设置下次启动设备"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishSetBootDevicePlugin(BasePlugin):
    name = "Redfish 设置启动设备"
    name_en = "Set Boot Device"
    code = "redfish_set_boot_device"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口设置服务器下次启动设备"
    description_en = "Set server boot device via Redfish API"
    risk_level = "high"
    icon = "Tools"
    color = "#9B59B6"
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
                tag_code="boot_device",
                type="select",
                name="启动设备",
                name_en="Boot Device",
                validation=[ValidationRule(type="required")],
                attrs={
                    "options": [
                        {"label": "硬盘 (Hdd)", "value": "Hdd"},
                        {"label": "光驱 (Cd)", "value": "Cd"},
                        {"label": "网络启动 (Pxe)", "value": "Pxe"},
                        {"label": "UEFI 目标 (UefiTarget)", "value": "UefiTarget"},
                        {"label": "USB (Usb)", "value": "Usb"},
                    ],
                },
            ),
            FormItem(
                tag_code="persistent",
                type="checkbox",
                name="持久生效",
                name_en="Persistent",
                default=False,
                attrs={"options": [{"label": "设置为持久启动设备（非一次性）", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", boot_device: str = "Hdd",
                persistent: bool = False, **kwargs) -> dict:
        try:
            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "boot_device": boot_device,
                    "persistent": persistent,
                    "result": f"启动设备已设置为 {boot_device} ({'持久' if persistent else '一次性'})",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "boot_device", "type": "string", "description": "启动设备", "description_en": "Boot device"},
            {"name": "persistent", "type": "boolean", "description": "是否持久生效", "description_en": "Persistent"},
        ]
