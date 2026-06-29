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
    name_en = "CMDB Query"
    code = "cmdb_query"
    group = "CMDB"
    version = "v1.0"
    description = "查询 CMDB 模型实例、拓扑路径或关联关系"
    description_en = "Query business, cluster, module, or host information from CMDB"
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
                name_en="Query Type",
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
                name_en="Query Parameters",
                tag_code="query_params",
                items=[
                    FormItem(
                        tag_code="model_code",
                        type="input",
                        name="模型编码",
                        name_en="Model Code",
                        attrs={"placeholder": "如 Host、Biz、Set", "placeholder_en": "e.g. Host, Biz, Set"},
                    ),
                    FormItem(
                        tag_code="filters",
                        type="textarea",
                        name="过滤条件",
                        name_en="Filter Conditions",
                        attrs={
                            "placeholder": 'JSON 格式过滤条件，如 {"status": "normal", "region": "北京"}',
                            "placeholder_en": 'JSON format filter, e.g. {"status": "normal"}',
                            "rows": 3,
                        },
                    ),
                    FormItem(
                        tag_code="instance_id",
                        type="input",
                        name="实例 ID",
                        name_en="Instance ID",
                        attrs={"placeholder": "拓扑/关联查询时输入起始实例 ID", "placeholder_en": "Instance ID for topology/neighbor query"},
                    ),
                    FormItem(
                        tag_code="max_depth",
                        type="int",
                        name="遍历深度",
                        name_en="Max Depth",
                        attrs={"min": 1, "max": 10},
                        default=3,
                    ),
                ],
            ),
            FormItem(
                tag_code="output_format",
                type="radio",
                name="输出格式",
                name_en="Output Format",
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "items", "type": "array", "description": "查询结果列表（实例查询）", "description_en": "Query result items (instance query)"},
            {"name": "total", "type": "integer", "description": "结果总数", "description_en": "Total result count"},
            {"name": "model_code", "type": "string", "description": "模型编码", "description_en": "Model code"},
            {"name": "root_id", "type": "string", "description": "拓扑根节点 ID", "description_en": "Topology root node ID"},
            {"name": "nodes", "type": "array", "description": "拓扑/关联节点列表", "description_en": "Topology/neighbor node list"},
            {"name": "edges", "type": "array", "description": "关联边列表", "description_en": "Association edge list"},
            {"name": "instance_id", "type": "string", "description": "查询起始实例 ID", "description_en": "Starting instance ID"},
            {"name": "impacted", "type": "array", "description": "影响分析结果列表", "description_en": "Impact analysis result list"},
        ]

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
