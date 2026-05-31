"""NetApp 存储卷快照 — 为 NetApp 存储卷创建快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappCreateSnapshotPlugin(BasePlugin):
    name = "NetApp 存储卷快照"
    code = "netapp_create_snapshot"
    group = "NetApp"
    description = "为 NetApp 存储卷创建快照（注意：这是存储设备操作，不能用于 ESXi 虚拟机快照）"
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
                tag_code="volume_uuid",
                type="input",
                name="卷 UUID",
                validation=[ValidationRule(type="required", error_message="请输入卷 UUID")],
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                validation=[ValidationRule(type="required", error_message="请输入快照名称")],
            ),
        ]

    def execute(self, cluster_ip: str, volume_uuid: str, snapshot_name: str, **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
