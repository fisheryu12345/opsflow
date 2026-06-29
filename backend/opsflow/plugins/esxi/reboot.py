"""重启 ESXi 虚拟机 (Guest OS Reboot / Hard Reset)"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiRebootPlugin(BasePlugin):
    name = "重启虚拟机"
    name_en = "Reboot VM"
    code = "esxi_reboot"
    group = "ESXi"
    description = "重启 ESXi 虚拟机（优先发送 Guest OS 软重启，失败后回退为硬重置）"
    description_en = "Reboot ESXi virtual machine (soft reboot first, fallback to hard reset)"
    risk_level = "high"
    version = "v1.0"
    icon = "Refresh"
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
                attrs={"placeholder": "输入虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="force",
                type="switch",
                name="强制重启 (Hard Reset)",
                name_en="Force Reboot (Hard Reset)",
                default=False,
                attrs={"active_text": "强制", "inactive_text": "软重启"},
                col=6,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str, force: bool = False, **kwargs) -> dict:
        # TODO: force=False → pyVmomi RebootGuest()；force=True → ResetVM_Task()
        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "esxi_host": esxi_host,
                "reboot_type": "hard" if force else "soft",
                "reboot_requested": True,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "reboot_type", "type": "string", "description": "重启类型 (soft/hard)"},
            {"name": "reboot_requested", "type": "bool", "description": "重启请求是否已发送"},
        ]
