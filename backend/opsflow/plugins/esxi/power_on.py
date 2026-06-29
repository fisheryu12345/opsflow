"""启动 ESXi 虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiPowerOnPlugin(BasePlugin):
    name = "启动虚拟机"
    name_en = "Power On VM"
    code = "esxi_power_on"
    group = "ESXi"
    description = "启动 ESXi 虚拟机"
    description_en = "Power on a virtual machine on VMware ESXi"
    risk_level = "medium"
    version = "v1.0"
    icon = "VideoPlay"
    color = "#67C23A"
    show_loop_config = False

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
        # TODO: 调用 pyVmomi / REST API 启动虚拟机
        return {
            "success": True,
            "data": {
                "power_state": "poweredOn",
                "vm_name": vm_name,
                "esxi_host": esxi_host,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "power_state", "type": "string", "description": "电源状态"},
        ]
