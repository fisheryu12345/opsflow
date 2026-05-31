"""NetApp 查询卷 — 查询 NetApp 存储卷详情"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappGetVolumePlugin(BasePlugin):
    name = "NetApp 查询卷"
    code = "netapp_get_volume"
    group = "NetApp"
    description = "查询 NetApp 存储卷详情"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="cluster_ip",
                type="input",
                name="集群 IP",
                validation=[ValidationRule(type="required", error_message="请输入集群 IP")],
            ),
            FormItem(
                tag_code="volume_name",
                type="input",
                name="卷名称",
                validation=[ValidationRule(type="required", error_message="请输入卷名称")],
            ),
        ]

    def execute(self, cluster_ip: str, volume_name: str, **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
