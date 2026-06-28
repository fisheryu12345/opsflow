"""NetApp 修改卷 — 修改 NetApp 卷属性 (扩容/改策略)"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappModifyVolumePlugin(BasePlugin):
    name = "NetApp 修改卷"
    code = "netapp_modify_volume"
    group = "NetApp"
    description = "修改 NetApp 卷属性 (扩容/改策略)"
    description_en = "Modify a NetApp storage volume"
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
                validation=[ValidationRule(type="required", error_message="请输入卷 UUID")],
            ),
            FormItem(
                tag_code="new_size_gb",
                type="int",
                name="新容量 (GB)",
                attrs={"placeholder": "新容量 (GB), 仅支持扩容"},
            ),
            FormItem(
                tag_code="new_snapshot_policy",
                type="input",
                name="新快照策略",
                attrs={"placeholder": "新快照策略 (可选)"},
            ),
        ]

    def execute(self, cluster_ip: str, volume_uuid: str, new_size_gb: int = None,
                new_snapshot_policy: str = "", **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
