"""NetApp 创建卷 — 在 NetApp ONTAP 上创建 FlexVol 存储卷"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class NetappCreateVolumePlugin(BasePlugin):
    name = "NetApp 创建卷"
    code = "netapp_create_volume"
    group = "NetApp"
    description = "在 NetApp ONTAP 上创建 FlexVol 存储卷"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="cluster_ip",
                type="input",
                name="集群 IP",
                attrs={"placeholder": "ONTAP 集群管理 IP"},
                validation=[ValidationRule(type="required", error_message="请输入集群 IP")],
            ),
            FormItem(
                tag_code="svm_name",
                type="input",
                name="SVM 名称",
                attrs={"placeholder": "SVM (Storage VM) 名称"},
                validation=[ValidationRule(type="required", error_message="请输入 SVM 名称")],
            ),
            FormItem(
                tag_code="volume_name",
                type="input",
                name="卷名称",
                validation=[ValidationRule(type="required", error_message="请输入卷名称")],
            ),
            FormItem(
                tag_code="size_gb",
                type="int",
                name="卷大小 (GB)",
                validation=[ValidationRule(type="required", error_message="请输入卷大小")],
            ),
            FormItem(
                tag_code="aggregate",
                type="input",
                name="所属 Aggregate",
                validation=[ValidationRule(type="required", error_message="请输入所属 Aggregate")],
            ),
            FormItem(
                tag_code="snapshot_policy",
                type="input",
                name="快照策略",
                default="",
                attrs={"placeholder": "快照策略 (可选)"},
            ),
        ]

    def execute(self, cluster_ip: str, svm_name: str, volume_name: str, size_gb: int,
                aggregate: str, snapshot_policy: str = "", **kwargs) -> dict:
        return {"success": True, "data": {"message": "execution delegated"}}
