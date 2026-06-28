"""关闭 ESXi 虚拟机 (强制关机)"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiPowerOffPlugin(BasePlugin):
    name = "关闭虚拟机"
    code = "esxi_power_off"
    group = "ESXi"
    description = "关闭 ESXi 虚拟机 (强制关机)"
    description_en = "Power off a virtual machine on VMware ESXi"
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
        ]

    def execute(self, esxi_host: str, vm_name: str, **kwargs) -> dict:
        # TODO: 调用 pyVmomi / REST API 关闭虚拟机
        return {
            "success": True,
            "data": {
                "power_state": "poweredOff",
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

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：启动虚拟机"""
        return {"success": True, "data": {}}
