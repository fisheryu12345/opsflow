"""克隆 ESXi 虚拟机 — 从源虚拟机克隆为新虚拟机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class EsxiCloneVmPlugin(BasePlugin):
    name = "克隆虚拟机"
    name_en = "Clone VM"
    code = "esxi_clone_vm"
    group = "ESXi"
    description = "从源 ESXi 虚拟机克隆为新虚拟机（支持自定义名称和数据存储）"
    description_en = "Clone an ESXi virtual machine to a new VM (custom name and datastore supported)"
    risk_level = "medium"

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
                tag_code="source_vm",
                type="input",
                name="源虚拟机名称",
                name_en="Source VM Name",
                attrs={"placeholder": "输入源虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入源虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="new_vm_name",
                type="input",
                name="新虚拟机名称",
                name_en="New VM Name",
                attrs={"placeholder": "输入新虚拟机名称"},
                validation=[ValidationRule(type="required", error_message="请输入新虚拟机名称")],
                col=12,
            ),
            FormItem(
                tag_code="datastore",
                type="input",
                name="目标数据存储",
                name_en="Target Datastore",
                attrs={"placeholder": "可选，默认与源相同"},
                col=6,
            ),
            FormItem(
                tag_code="power_on",
                type="switch",
                name="克隆后开机",
                name_en="Power On After Clone",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, esxi_host: str, source_vm: str, new_vm_name: str,
                datastore: str = "", power_on: bool = False, **kwargs) -> dict:
        # TODO: 调用 pyVmomi CloneVM_Task()
        return {
            "success": True,
            "data": {
                "source_vm": source_vm,
                "new_vm_name": new_vm_name,
                "esxi_host": esxi_host,
                "clone_completed": True,
                "powered_on": power_on,
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "source_vm", "type": "string", "description": "源虚拟机名称"},
            {"name": "new_vm_name", "type": "string", "description": "新虚拟机名称"},
            {"name": "clone_completed", "type": "bool", "description": "克隆是否完成"},
            {"name": "powered_on", "type": "bool", "description": "克隆后是否已开机"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：删除克隆出的虚拟机"""
        new_vm = context.get("new_vm_name", "")
        if new_vm:
            return {"success": True, "data": {"action": "delete_clone", "vm_name": new_vm}}
        return {"success": True, "data": {}}
