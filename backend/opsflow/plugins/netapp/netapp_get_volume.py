"""NetApp 查询卷 — 查询 NetApp 存储卷详情"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappGetVolumePlugin(BasePlugin):
    name = "NetApp 查询卷"
    name_en = "NetApp Get Volume"
    code = "netapp_get_volume"
    group = "NetApp"
    version = "v1.0"
    description = "查询 NetApp 存储卷详情"
    description_en = "Get NetApp storage volume information"
    risk_level = "low"
    icon = "Search"
    color = "#409EFF"

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
                tag_code="volume_name",
                type="input",
                name="卷名称",
                name_en="Volume Name",
                validation=[ValidationRule(type="required", error_message="请输入卷名称")],
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "message", "type": "string", "description_en": "Execution result message"},
        ]

    def execute(self, cluster_ip: str, volume_name: str, **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
