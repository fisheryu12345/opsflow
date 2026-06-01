"""Dell PowerMax 存储组管理 — 创建、查询、删除存储组"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule, FormGroup


class CreateStorageGroupPlugin(BasePlugin):
    name = "创建存储组"
    code = "pmax_create_storage_group"
    group = "Pmax"
    description = "在 Dell PowerMax 阵列上创建存储组 (Storage Group)"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="array_id",
                type="async_select",
                name="阵列 ID",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/pmax-arrays/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 PowerMax 阵列...",
                },
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormItem(
                tag_code="sg_name",
                type="input",
                name="存储组名称",
                attrs={"placeholder": "例如: Oracle_Data_SG"},
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormGroup(
                name="容量配置",
                tag_code="capacity_opts",
                items=[
                    FormItem(
                        tag_code="num_vols",
                        type="int",
                        name="卷数量",
                        default=1,
                        attrs={"min": 1, "max": 128},
                        col=6,
                    ),
                    FormItem(
                        tag_code="vol_size_gb",
                        type="int",
                        name="单卷容量 (GB)",
                        default=100,
                        attrs={"min": 1, "max": 32000},
                        col=6,
                    ),
                ],
            ),
            FormItem(
                tag_code="srp",
                type="input",
                name="SRP (Storage Resource Pool)",
                default="SRP_1",
                attrs={"placeholder": "如 SRP_1"},
                col=6,
            ),
            FormItem(
                tag_code="service_level",
                type="select",
                name="服务等级",
                default="Diamond",
                attrs={
                    "options": [
                        {"label": "Diamond", "value": "Diamond"},
                        {"label": "Platinum", "value": "Platinum"},
                        {"label": "Gold", "value": "Gold"},
                        {"label": "Silver", "value": "Silver"},
                        {"label": "Bronze", "value": "Bronze"},
                        {"label": "Optimized", "value": "Optimized"},
                    ],
                },
                col=6,
            ),
            FormItem(
                tag_code="compression",
                type="checkbox",
                name="启用压缩",
                default=True,
                attrs={"options": [{"label": "启用数据压缩", "value": True}]},
            ),
        ]

    def execute(self, array_id: str, sg_name: str, num_vols: int = 1,
                vol_size_gb: int = 100, srp: str = "SRP_1",
                service_level: str = "Diamond", compression: bool = True,
                **kwargs) -> dict:
        # TODO: 调用 Dell Unisphere REST API
        return {
            "success": True,
            "data": {
                "sg_name": sg_name,
                "array_id": array_id,
                "num_vols": num_vols,
                "total_capacity_gb": num_vols * vol_size_gb,
                "status": "创建成功",
            },
            "error": "",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "sg_name", "type": "string"},
            {"name": "num_vols", "type": "int"},
            {"name": "total_capacity_gb", "type": "int"},
        ]


class DeleteStorageGroupPlugin(BasePlugin):
    name = "删除存储组"
    code = "pmax_delete_storage_group"
    group = "Pmax"
    description = "删除 PowerMax 存储组及其关联卷"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="array_id",
                type="async_select",
                name="阵列 ID",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/pmax-arrays/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 PowerMax 阵列...",
                },
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormItem(
                tag_code="sg_name",
                type="input",
                name="存储组名称",
                attrs={"placeholder": "要删除的存储组名称"},
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormItem(
                tag_code="force",
                type="checkbox",
                name="强制删除",
                default=False,
                attrs={"options": [{"label": "强制删除（包含关联卷）", "value": True}]},
            ),
        ]

    def execute(self, array_id: str, sg_name: str, force: bool = False, **kwargs) -> dict:
        return {"success": True, "data": {"sg_name": sg_name, "status": "已删除"}, "error": ""}


class ListStorageGroupsPlugin(BasePlugin):
    name = "查询存储组列表"
    code = "pmax_list_storage_groups"
    group = "Pmax"
    description = "查询 PowerMax 阵列上的存储组列表"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="array_id",
                type="async_select",
                name="阵列 ID",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/pmax-arrays/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择 PowerMax 阵列...",
                },
                validation=[ValidationRule(type="required")],
                col=6,
            ),
            FormItem(
                tag_code="filter_name",
                type="input",
                name="名称过滤(可选)",
                attrs={"placeholder": "支持通配符"},
                col=6,
            ),
        ]

    def execute(self, array_id: str, filter_name: str = "", **kwargs) -> dict:
        return {"success": True, "data": {"storage_groups": [], "count": 0}, "error": ""}
