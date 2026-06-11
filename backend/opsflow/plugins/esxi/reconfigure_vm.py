"""修改 ESXi 虚拟机配置 — CPU / 内存热调整"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiReconfigureVmPlugin(BasePlugin):
    name = "修改虚拟机配置"
    name_en = "Reconfigure VM"
    code = "esxi_reconfigure_vm"
    group = "ESXi"
    description = "调整 ESXi 虚拟机的 CPU 核数和内存大小（支持在线热调整）"
    description_en = "Adjust ESXi VM CPU count and memory size (hot-plug supported)"
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
                tag_code="cpu",
                type="int",
                name="CPU 核数",
                name_en="CPU Count",
                default=0,
                attrs={"min": 0, "max": 256, "placeholder": "0=不修改"},
                col=6,
            ),
            FormItem(
                tag_code="memory_mb",
                type="int",
                name="内存大小 (MB)",
                name_en="Memory (MB)",
                default=0,
                attrs={"min": 0, "max": 1048576, "placeholder": "0=不修改"},
                col=6,
            ),
        ]

    def execute(self, esxi_host: str, vm_name: str,
                cpu: int = 0, memory_mb: int = 0, **kwargs) -> dict:
        # TODO: 调用 pyVmomi ReconfigVM_Task() 修改硬件配置
        changes = []
        if cpu > 0:
            changes.append(f"cpu->{cpu}")
        if memory_mb > 0:
            changes.append(f"memory->{memory_mb}MB")

        return {
            "success": True,
            "data": {
                "vm_name": vm_name,
                "esxi_host": esxi_host,
                "changes": changes,
                "reconfigured": True,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "changes", "type": "list", "description": "变更项列表"},
            {"name": "reconfigured", "type": "bool", "description": "是否已更新"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：无（无法自动回滚硬件配置）"""
        return {"success": True, "data": {}}
