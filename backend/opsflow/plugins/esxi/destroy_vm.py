"""删除 ESXi 上的虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiDestroyVmPlugin(BasePlugin):
    name = "删除虚拟机"
    code = "esxi_destroy_vm"
    group = "ESXi"
    description = "删除 ESXi 上的虚拟机"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="esxi_host",
                type="input",
                name="ESXi 主机",
                attrs={"placeholder": "ESXi 主机 IP"},
                validation=[ValidationRule(type="required", error_message="请输入 ESXi 主机")],
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
        ]

    def execute(self, esxi_host: str, vm_name: str, **kwargs) -> dict:
        # TODO: 调用 pyVmomi / REST API 删除虚拟机
        return {
            "success": True,
            "data": {
                "status": "deleted",
                "vm_name": vm_name,
                "esxi_host": esxi_host,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "status", "type": "string", "description": "操作结果"},
        ]
