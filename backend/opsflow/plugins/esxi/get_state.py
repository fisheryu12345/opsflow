"""查询 ESXi 虚拟机状态"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiGetStatePlugin(BasePlugin):
    name = "查询虚拟机状态"
    code = "esxi_get_state"
    group = "ESXi"
    description = "查询 ESXi 虚拟机状态"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="esxi_host",
                type="input",
                name="ESXi 主机",
                attrs={"placeholder": "ESXi 主机 IP 或 vCenter FQDN"},
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
        # TODO: 调用 pyVmomi / REST API 查询虚拟机状态
        return {
            "success": True,
            "data": {
                "exists": True,
                "power_state": "poweredOn",
                "guest_ip": "192.168.1.100",
                "cpu": 2,
                "memory_mb": 4096,
                "vm_name": vm_name,
                "esxi_host": esxi_host,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "exists", "type": "bool", "description": "虚拟机是否存在"},
            {"name": "power_state", "type": "string", "description": "电源状态"},
            {"name": "guest_ip", "type": "string", "description": "客户机 IP"},
            {"name": "cpu", "type": "int", "description": "CPU 核数"},
            {"name": "memory_mb", "type": "int", "description": "内存大小 (MB)"},
        ]
