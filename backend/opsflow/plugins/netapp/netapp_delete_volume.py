"""NetApp 删除卷 — 删除 NetApp 存储卷"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappDeleteVolumePlugin(BasePlugin):
    name = "NetApp 删除卷"
    code = "netapp_delete_volume"
    group = "NetApp"
    description = "删除 NetApp 存储卷"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="cluster_ip",
                type="async_select",
                name="集群 IP",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/netapp-clusters/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 ONTAP 集群...",
                },
                validation=[ValidationRule(type="required", error_message="请选择集群 IP")],
            ),
            FormItem(
                tag_code="volume_uuid",
                type="input",
                name="卷 UUID",
                attrs={"placeholder": "卷 UUID (优先)"},
            ),
            FormItem(
                tag_code="volume_name",
                type="input",
                name="卷名称",
                attrs={"placeholder": "卷名称 (备用)"},
            ),
        ]

    def execute(self, cluster_ip: str, volume_uuid: str = "", volume_name: str = "", **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
