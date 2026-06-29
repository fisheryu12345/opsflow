"""Dell PowerMax 快照管理 — 创建、查看、删除快照"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class CreateSnapshotPlugin(BasePlugin):
    name = "创建快照"
    name_en = "Create Snapshot"
    code = "pmax_create_snapshot"
    group = "Pmax"
    version = "v1.0"
    description = "为 PowerMax 存储组创建时间点快照"
    description_en = "Create a PowerMax storage snapshot"
    risk_level = "medium"
    icon = "CopyDocument"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="array_id",
                type="async_select",
                name="阵列 ID",
                name_en="Array ID",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/pmax-arrays/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 PowerMax 阵列...",
                    "placeholder_en": "Select PowerMax array from CMDB...",
                },
                validation=[ValidationRule(type="required")],
                col=6,
            ),
            FormItem(
                tag_code="sg_name",
                type="input",
                name="源存储组名称",
                name_en="Source Storage Group Name",
                validation=[ValidationRule(type="required")],
                attrs={"placeholder": "要快照的存储组", "placeholder_en": "Storage group to snapshot"},
                col=6,
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                name_en="Snapshot Name",
                attrs={"placeholder": "例如: DailyBackup_20260531", "placeholder_en": "e.g. DailyBackup_20260531"},
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormItem(
                tag_code="ttl_hours",
                type="int",
                name="保留时间(小时)",
                name_en="Retention Time (Hours)",
                default=24,
                attrs={"min": 1, "max": 8760},
                col=6,
            ),
            FormItem(
                tag_code="generate_host",
                type="checkbox",
                name="生成主机可见",
                name_en="Make Visible to Host",
                default=True,
                attrs={"options": [{"label": "快照对主机可见", "value": True}]},
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "snapshot_name", "type": "string", "description_en": "Snapshot name"},
            {"name": "source_sg", "type": "string", "description_en": "Source storage group"},
            {"name": "ttl_hours", "type": "int", "description_en": "Retention time (hours)"},
            {"name": "status", "type": "string", "description_en": "Operation status"},
        ]

    def execute(self, array_id: str, sg_name: str, snapshot_name: str,
                ttl_hours: int = 24, generate_host: bool = True, **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "snapshot_name": snapshot_name,
                "source_sg": sg_name,
                "ttl_hours": ttl_hours,
                "status": "创建成功",
            },
            "error": "",
        }


class DeleteSnapshotPlugin(BasePlugin):
    name = "删除快照"
    name_en = "Delete Snapshot"
    code = "pmax_delete_snapshot"
    group = "Pmax"
    version = "v1.0"
    description = "删除 PowerMax 存储组的快照"
    description_en = "Delete a PowerMax storage snapshot"
    risk_level = "high"
    icon = "Delete"
    color = "#F56C6C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="array_id",
                type="async_select",
                name="阵列 ID",
                name_en="Array ID",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/pmax-arrays/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 PowerMax 阵列...",
                    "placeholder_en": "Select PowerMax array from CMDB...",
                },
                validation=[ValidationRule(type="required")],
                col=6,
            ),
            FormItem(
                tag_code="snapshot_name",
                type="input",
                name="快照名称",
                name_en="Snapshot Name",
                validation=[ValidationRule(type="required")],
                col=6,
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "snapshot_name", "type": "string", "description_en": "Snapshot name"},
            {"name": "status", "type": "string", "description_en": "Operation status"},
        ]

    def execute(self, array_id: str, snapshot_name: str, **kwargs) -> dict:
        return {"success": True, "data": {"snapshot_name": snapshot_name, "status": "已删除"}, "error": ""}
