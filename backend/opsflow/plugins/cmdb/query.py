"""CMDB 查询插件 — 在 pipeline 执行过程中查询 CMDB 数据

支持查询模型实例、拓扑路径、关联关系，结果可被下游节点引用。
"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup


class CmdbQueryPlugin(BasePlugin):
    """CMDB 查询

    在 pipeline 执行过程中查询 CMDB 数据。
    支持任意模型类型的实例查询、拓扑路径分析、关联关系查询。
    """
    name = "CMDB 查询"
    code = "cmdb_query"
    group = "CMDB"
    version = "v1.0"
    description = "查询 CMDB 模型实例、拓扑路径或关联关系"
    risk_level = "low"
    icon = "Search"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="query_type",
                type="select",
                name="查询类型",
                attrs={
                    "options": [
                        {"label": "实例查询", "value": "instance_query"},
                        {"label": "拓扑路径", "value": "topology_path"},
                        {"label": "关联查询", "value": "neighbor_query"},
                        {"label": "影响分析", "value": "impact_analysis"},
                    ],
                },
                default="instance_query",
            ),
            FormGroup(
                type="combine",
                name="查询参数",
                tag_code="query_params",
                items=[
                    FormItem(
                        tag_code="model_code",
                        type="input",
                        name="模型编码",
                        attrs={"placeholder": "如 Host、Biz、Set"},
                    ),
                    FormItem(
                        tag_code="filters",
                        type="textarea",
                        name="过滤条件",
                        attrs={
                            "placeholder": 'JSON 格式过滤条件，如 {"status": "normal", "region": "北京"}',
                            "rows": 3,
                        },
                    ),
                    FormItem(
                        tag_code="instance_id",
                        type="input",
                        name="实例 ID",
                        attrs={"placeholder": "拓扑/关联查询时输入起始实例 ID"},
                    ),
                    FormItem(
                        tag_code="max_depth",
                        type="int",
                        name="遍历深度",
                        attrs={"min": 1, "max": 10},
                        default=3,
                    ),
                ],
            ),
            FormItem(
                tag_code="output_format",
                type="radio",
                name="输出格式",
                attrs={
                    "options": [
                        {"label": "完整数据", "value": "full"},
                        {"label": "精简摘要", "value": "summary"},
                    ],
                },
                default="summary",
            ),
        ]

    @classmethod
    def get_var_types(cls):
        return {
            "query_type": "plain",
            "model_code": "plain",
            "filters": "plain",
            "instance_id": "plain",
            "max_depth": "plain",
            "output_format": "plain",
        }

    def execute(self, **kwargs) -> dict:
        """执行 CMDB 查询"""
        from cmdb.services.node_service import NodeService
        from cmdb.services.topology_service import TopologyService
        from cmdb.services.association_service import AssociationService
        import json

        query_type = kwargs.get("query_type", "instance_query")
        model_code = kwargs.get("model_code", "Host")
        filters_raw = kwargs.get("filters", "{}")
        instance_id = kwargs.get("instance_id")
        max_depth = int(kwargs.get("max_depth", 3))
        output_format = kwargs.get("output_format", "summary")

        topo = TopologyService()
        asst = AssociationService()

        try:
            if query_type == "instance_query":
                # 实例查询
                filters = json.loads(filters_raw) if isinstance(filters_raw, str) else (filters_raw or {})
                svc = NodeService(model_code)
                result = svc.list(filters, page=1, page_size=100)

                if output_format == "summary":
                    items = [
                        {"instance_id": i.get("instance_id"),
                         "name": i.get("name") or i.get("hostname") or i.get("ip", ""),
                         "status": i.get("status", "")}
                        for i in result.get("items", [])
                    ]
                else:
                    items = result.get("items", [])

                output = {
                    "items": items,
                    "total": result.get("total", 0),
                    "model_code": model_code,
                }

            elif query_type == "topology_path":
                # 拓扑路径查询
                if not instance_id:
                    return {"success": False, "error": "拓扑查询需要 instance_id"}
                tree = topo.get_tree(instance_id, max_depth=max_depth)
                output = {
                    "root_id": instance_id,
                    "nodes": tree.get("nodes", []),
                    "total": tree.get("total", 0),
                }

            elif query_type == "neighbor_query":
                # 关联查询
                if not instance_id:
                    return {"success": False, "error": "关联查询需要 instance_id"}
                neighbors = asst.get_neighbors(instance_id, direction="both", max_depth=max_depth)
                output = {
                    "instance_id": instance_id,
                    "nodes": neighbors.get("nodes", []),
                    "edges": neighbors.get("edges", []),
                }

            elif query_type == "impact_analysis":
                # 影响分析
                if not instance_id:
                    return {"success": False, "error": "影响分析需要 instance_id"}
                impact = topo.get_impact(instance_id, direction="downstream", max_depth=max_depth)
                output = {
                    "instance_id": instance_id,
                    "impacted": impact.get("impacted", []),
                    "total": impact.get("total", 0),
                }

            else:
                return {"success": False, "error": f"不支持的查询类型: {query_type}"}

            return {"success": True, "data": output}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"过滤条件 JSON 格式错误: {e}"}
        except Exception as e:
            return {"success": False, "error": f"查询失败: {str(e)}"}
