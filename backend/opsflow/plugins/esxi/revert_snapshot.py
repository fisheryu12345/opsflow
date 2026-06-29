"""恢复 ESXi 虚拟机快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiRevertSnapshotPlugin(BasePlugin):
    name = "恢复快照"
    name_en = "Revert to Snapshot"
    code = "esxi_revert_snapshot"
    group = "ESXi"
    description = "将 ESXi 虚拟机恢复到指定快照"
    description_en = "Revert an ESXi virtual machine to a specified snapshot"
    risk_level = "high"
    version = "v1.0"
    icon = "RefreshLeft"
    color = "#E6A23C"

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
                    "placeholder_en": "Select ESXi host from CMDB...",
                validation=[ValidationRule(type="required", error_message="请选择 ESXi 主机")],
                col=12,
            ),
            FormItem(
                tag_code="vm_name",
                type="input",
                name="虚拟机名称",
                name_en="VM Name",
                attrs={"placeholder": "输入虚拟机名称", "placeholder_en": "Enter VM name"},
                validation=[ValidationRule(type="required", error_message="请输入虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="目标快照名称",
                name_en="Target Snapshot Name",
                attrs={"placeholder": "输入要恢复到的快照名称", "placeholder_en": "Enter target snapshot name"},
                validation=[ValidationRule(type="required", error_message="请输入快照名称")],
                col=12,
            ),
            FormItem(
                tag_code="power_on",
                type="switch",
                name="恢复后开机",
                name_en="Power On After Revert",
                default=True,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str, snapshot_name: str,
                power_on: bool = True, **kwargs) -> dict:
        # TODO: 调用 pyVmomi RevertToSnapshot_Task()
        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "snapshot_name": snapshot_name,
                "esxi_host": esxi_host,
                "reverted": True,
                "powered_on": power_on,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "snapshot_name", "type": "string", "description": "已恢复的快照名称"},
            {"name": "reverted", "type": "bool", "description": "是否已恢复"},
        ]
