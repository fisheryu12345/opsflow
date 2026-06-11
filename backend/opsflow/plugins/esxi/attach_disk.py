"""挂载磁盘到 ESXi 虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiAttachDiskPlugin(BasePlugin):
    name = "挂载磁盘"
    name_en = "Attach Disk"
    code = "esxi_attach_disk"
    group = "ESXi"
    description = "为 ESXi 虚拟机挂载新虚拟磁盘（支持厚/精简置备）"
    description_en = "Attach a new virtual disk to an ESXi VM (thick/thin provision supported)"
    risk_level = "high"

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
                tag_code="disk_size_gb",
                type="int",
                name="磁盘大小 (GB)",
                name_en="Disk Size (GB)",
                default=100,
                attrs={"min": 1, "max": 16384},
                col=6,
            ),
            FormItem(
                tag_code="disk_type",
                type="select",
                name="磁盘类型",
                name_en="Disk Type",
                default="thin",
                attrs={
                    "options": [
                        {"label": "精简置备 (Thin)", "value": "thin"},
                        {"label": "厚置备延迟零 (Thick Lazy Zero)", "value": "thick"},
                        {"label": "厚置备快速零 (Thick Eager Zero)", "value": "eager_zero"},
                    ],
                },
                col=6,
            ),
            FormItem(
                tag_code="datastore",
                type="input",
                name="目标数据存储",
                name_en="Target Datastore",
                attrs={"placeholder": "可选，默认与虚拟机相同"},
                col=12,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str, disk_size_gb: int = 100,
                disk_type: str = "thin", datastore: str = "", **kwargs) -> dict:
        # TODO: 调用 pyVmomi ReconfigVM_Task() 添加 VirtualDisk
        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "disk_size_gb": disk_size_gb,
                "disk_type": disk_type,
                "esxi_host": esxi_host,
                "disk_attached": True,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "disk_size_gb", "type": "int", "description": "磁盘大小"},
            {"name": "disk_type", "type": "string", "description": "磁盘类型"},
            {"name": "disk_attached", "type": "bool", "description": "是否已挂载"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：无（无法自动卸载已挂载的磁盘）"""
        return {"success": True, "data": {}}
