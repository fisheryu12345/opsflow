"""删除 ESXi 上的虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiDestroyVmPlugin(BasePlugin):
    name = "删除虚拟机"
    name_en = "Delete VM"
    code = "esxi_destroy_vm"
    group = "ESXi"
    version = "v1.0"
    description = "删除 ESXi 上的虚拟机"
    description_en = "Delete a virtual machine from VMware ESXi"
    risk_level = "high"
    icon = "Delete"
    color = "#F56C6C"

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
                },
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
