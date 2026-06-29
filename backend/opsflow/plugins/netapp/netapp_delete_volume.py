"""NetApp 删除卷 — 删除 NetApp 存储卷"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappDeleteVolumePlugin(BasePlugin):
    name = "NetApp 删除卷"
    name_en = "NetApp Delete Volume"
    code = "netapp_delete_volume"
    group = "NetApp"
    version = "v1.0"
    description = "删除 NetApp 存储卷"
    description_en = "Delete a NetApp storage volume"
    risk_level = "high"
    icon = "Delete"
    color = "#F56C6C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="cluster_ip",
                type="async_select",
                name="集群 IP",
                name_en="Cluster IP",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/netapp-clusters/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 ONTAP 集群...",
                    "placeholder_en": "Select ONTAP cluster from CMDB...",
                },
                validation=[ValidationRule(type="required", error_message="请选择集群 IP")],
            ),
            FormItem(
                tag_code="volume_uuid",
                type="input",
                name="卷 UUID",
                name_en="Volume UUID",
                attrs={"placeholder": "卷 UUID (优先)", "placeholder_en": "Volume UUID (preferred)"},
            ),
            FormItem(
                tag_code="volume_name",
                type="input",
                name="卷名称",
                name_en="Volume Name",
                attrs={"placeholder": "卷名称 (备用)", "placeholder_en": "Volume name (fallback)"},
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "message", "type": "string", "description_en": "Execution result message"},
        ]

    def execute(self, cluster_ip: str, volume_uuid: str = "", volume_name: str = "", **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
