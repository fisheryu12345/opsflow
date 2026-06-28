"""在 ESXi/vCenter 上创建虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiCreateVmPlugin(BasePlugin):
    name = "创建虚拟机"
    code = "esxi_create_vm"
    group = "ESXi"
    description = "在 ESXi/vCenter 上创建虚拟机"
    description_en = "Create a new virtual machine on VMware ESXi"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="esxi_host",
                type="async_select",
                name="ESXi 主机",
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
                attrs={"placeholder": "输入虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="cpu",
                type="int",
                name="CPU 核数",
                default=2,
                attrs={"min": 1, "max": 128},
                col=6,
            ),
            FormItem(
                tag_code="memory_mb",
                type="int",
                name="内存大小 (MB)",
                default=4096,
                attrs={"min": 512, "max": 524288},
                col=6,
            ),
            FormItem(
                tag_code="disk_gb",
                type="int",
                name="系统盘大小 (GB)",
                default=50,
                attrs={"min": 10, "max": 4096},
                col=6,
            ),
            FormItem(
                tag_code="datastore",
                type="input",
                name="数据存储",
                attrs={"placeholder": "数据存储名称"},
                validation=[ValidationRule(type="required", error_message="请输入数据存储名称")],
                col=12,
            ),
            FormItem(
                tag_code="network",
                type="input",
                name="网络名称",
                default="VM Network",
                attrs={"placeholder": "虚拟机网络"},
                col=12,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str, datastore: str,
                cpu: int = 2, memory_mb: int = 4096, disk_gb: int = 50,
                network: str = "VM Network", **kwargs) -> dict:
        # TODO: 调用 pyVmomi / REST API 创建虚拟机
        return {
            "success": True,
            "data": {
                "vm_id": "placeholder-vm-moid",
                "vm_name": vm_name,
                "power_state": "poweredOn",
                "esxi_host": esxi_host,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "vm_id", "type": "string", "description": "VM 实例 MoID"},
            {"name": "vm_name", "type": "string", "description": "VM 名称"},
            {"name": "power_state", "type": "string", "description": "电源状态"},
        ]
