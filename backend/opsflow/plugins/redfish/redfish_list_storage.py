"""Redfish 存储清单 — 通过 BMC 获取存储控制器信息"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class RedfishListStoragePlugin(BasePlugin):
    name = "Redfish 存储清单"
    code = "redfish_list_storage"
    group = "Redfish"
    description = "通过 BMC Redfish 接口列出存储控制器及磁盘信息"
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
                tag_code="include_drives",
                type="checkbox",
                name="包含磁盘",
                default=True,
                attrs={"options": [{"label": "同时列出物理磁盘信息", "value": True}]},
            ),
        ]

    def execute(self, bmc_host: str, bmc_user: str = "admin",
                bmc_password: str = "", include_drives: bool = True,
                **kwargs) -> dict:
        # 占位实现 — 集成实际 Redfish SDK 调用
        try:
            # TODO: 使用 redfish 库调用
            # with redfish_client(bmc_host, bmc_user, bmc_password) as client:
            #     storage = client.get_storage_controllers()
            #     ...

            controllers = [
                {
                    "id": "RAID-1",
                    "model": "Smart Array P408i-a",
                    "firmware_version": "7.10",
                    "status": "OK",
                },
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
