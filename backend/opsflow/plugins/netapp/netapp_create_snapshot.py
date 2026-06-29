"""NetApp 存储卷快照 — 为 NetApp 存储卷创建快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappCreateSnapshotPlugin(BasePlugin):
    name = "NetApp 存储卷快照"
    name_en = "NetApp Create Snapshot"
    code = "netapp_create_snapshot"
    group = "NetApp"
    version = "v1.0"
    description = "为 NetApp 存储卷创建快照（注意：这是存储设备操作，不能用于 ESXi 虚拟机快照）"
    description_en = "Create a NetApp storage volume snapshot"
    risk_level = "low"
    icon = "CopyDocument"
    color = "#67C23A"

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
                validation=[ValidationRule(type="required", error_message="请输入卷 UUID")],
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                name_en="Snapshot Name",
                validation=[ValidationRule(type="required", error_message="请输入快照名称")],
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "message", "type": "string", "description_en": "Execution result message"},
        ]

    def execute(self, cluster_ip: str, volume_uuid: str, snapshot_name: str, **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
