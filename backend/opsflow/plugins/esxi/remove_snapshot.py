"""删除 ESXi 虚拟机快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiRemoveSnapshotPlugin(BasePlugin):
    name = "删除快照"
    name_en = "Remove Snapshot"
    code = "esxi_remove_snapshot"
    group = "ESXi"
    description = "删除 ESXi 虚拟机指定快照（支持删除所有快照）"
    description_en = "Remove a specified snapshot from an ESXi VM (or remove all snapshots)"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="esxi_host",
                type="async_select",
                name="ESXi 主机",
                name_en="ESXi Host",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/esxi-hosts/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 ESXi 主机...",
                },
                validation=[ValidationRule(type="required", error_message="请选择 ESXi 主机")],
                col=12,
            ),
            FormItem(
                tag_code="vm_name",
                type="input",
                name="虚拟机名称",
                name_en="VM Name",
                attrs={"placeholder": "输入虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                name_en="Snapshot Name",
                attrs={"placeholder": "输入快照名称，留空表示删除所有快照"},
                col=12,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str,
                snapshot_name: str = "", **kwargs) -> dict:
        # TODO: 调用 pyVmomi RemoveSnapshot_Task() 或 RemoveAllSnapshots_Task()
        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "snapshot_name": snapshot_name or "(all)",
                "esxi_host": esxi_host,
                "removed": True,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "snapshot_name", "type": "string", "description": "已删除的快照名称"},
            {"name": "removed", "type": "bool", "description": "是否已删除"},
        ]
