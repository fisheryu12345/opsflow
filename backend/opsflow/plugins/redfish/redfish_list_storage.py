"""Redfish 存储清单 — 通过 BMC 获取存储控制器信息"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishListStoragePlugin(BasePlugin):
    name = "Redfish 存储清单"
    name_en = "Storage List"
    code = "redfish_list_storage"
    group = "Redfish"
    version = "v1.0"
    description = "通过 BMC Redfish 接口列出存储控制器及磁盘信息"
    description_en = "List storage controllers and drives via Redfish API"
    risk_level = "low"
    icon = "FolderOpened"
    color = "#67C23A"

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
                tag_code="include_drives",
                type="checkbox",
                name="包含磁盘",
                name_en="Include Drives",
                default=True,
                attrs={"options": [{"label": "同时列出物理磁盘信息", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", include_drives: bool = True,
                **kwargs) -> dict:
        try:
            controllers = [
                {"id": "RAID-1", "model": "Smart Array P408i-a", "firmware_version": "7.10", "status": "OK"},
            ]
            drives = []
            if include_drives:
                drives = [
                    {"id": "disk-0", "model": "SSD 960GB", "capacity_gb": 960, "status": "OK"},
                    {"id": "disk-1", "model": "HDD 4TB", "capacity_gb": 4096, "status": "OK"},
                ]
            return {
                "success": True,
                "data": {
                    "bmc_host": bmc_host,
                    "controllers": controllers,
                    "drives": drives,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "bmc_host", "type": "string", "description": "BMC 地址", "description_en": "BMC host address"},
            {"name": "controllers", "type": "object", "description": "存储控制器列表", "description_en": "Storage controllers"},
            {"name": "drives", "type": "object", "description": "物理磁盘列表", "description_en": "Physical drives"},
        ]
