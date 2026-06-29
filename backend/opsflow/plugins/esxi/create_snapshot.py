"""创建 ESXi 虚拟机快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiCreateSnapshotPlugin(BasePlugin):
    name = "创建快照"
    name_en = "Create Snapshot"
    code = "esxi_create_snapshot"
    group = "ESXi"
    description = "为 ESXi 虚拟机创建快照（支持命名和描述备注）"
    description_en = "Create a snapshot for an ESXi virtual machine with name and description"
    risk_level = "medium"
    version = "v1.0"
    icon = "Camera"
    color = "#409EFF"

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
                attrs={"placeholder": "输入虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                name_en="Snapshot Name",
                attrs={"placeholder": "例如：升级前快照_20260612"},
                validation=[ValidationRule(type="required", error_message="请输入快照名称")],
                col=12,
            ),
            FormItem(
                tag_code="description",
                type="input",
                name="快照描述",
                name_en="Description",
                attrs={"placeholder": "可选快照说明"},
                col=12,
            ),
            FormItem(
                tag_code="memory",
                type="switch",
                name="包含内存状态",
                name_en="Include Memory State",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
            FormItem(
                tag_code="quiesce",
                type="switch",
                name="静默文件系统",
                name_en="Quiesce Filesystem",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str, snapshot_name: str,
                description: str = "", memory: bool = False,
                quiesce: bool = False, **kwargs) -> dict:
        # TODO: 调用 pyVmomi CreateSnapshot_Task()
        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "snapshot_name": snapshot_name,
                "esxi_host": esxi_host,
                "snapshot_created": True,
                "memory_snapshot": memory,
                "quiesced": quiesce,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "snapshot_name", "type": "string", "description": "快照名称"},
            {"name": "snapshot_created", "type": "bool", "description": "快照是否已创建"},
        ]
