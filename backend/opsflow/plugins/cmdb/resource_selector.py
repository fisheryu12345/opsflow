"""CMDB 资源选择器 — 在工作流节点中选择 CMDB 资产作为执行目标

用户通过 resource_selector 表单组件选择业务/集群/模块/主机，
execute() 时从 Neo4j 查询并返回选中实例的详细信息。
"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup


class CmdbResourceSelector(BasePlugin):
    """CMDB 资源选择器

    在 pipeline 节点中嵌入 CMDB 资源选择界面。
    支持按业务拓扑路径选择主机，或按条件筛选。
    输出可被下游节点通过 ${node_id.ip} 引用。
    """
    name = "CMDB 资源选择"
    name_en = "CMDB Resource Selector"
    code = "cmdb_resource_selector"
    group = "CMDB"
    version = "v1.0"
    description = "从 CMDB 选择业务/集群/模块下的主机作为执行目标"
    description_en = "Select business resources from CMDB as execution targets"
    risk_level = "low"
    icon = "FolderOpened"
    color = "#409EFF"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                type="combine",
                name="资源筛选",
                name_en="Resource Filter",
                tag_code="resource_group",
                items=[
                    FormItem(
                        tag_code="biz_filter",
                        type="cascader",
                        name="业务路径",
                        name_en="Business Path",
                        attrs={
                            "api_endpoint": "/api/cmdb/topology/tree/",
                            "props": {
                                "value": "instance_id",
                                "label": "label",
                                "multiple": False,
                                "checkStrictly": True,
                            },
                            "placeholder": "按业务/集群/模块路径选择",
                            "placeholder_en": "Select by business/cluster/module path",
                        },
                    ),
                    FormItem(
                        tag_code="host_filter",
                        type="input",
                        name="主机过滤",
                        name_en="Host Filter",
                        attrs={
                            "placeholder": "可输入 IP/主机名筛选，支持逗号分隔",
                            "placeholder_en": "Filter by IP/hostname, comma-separated",
                        },
                    ),
                    FormItem(
                        tag_code="include_relations",
                        type="select",
                        name="关联资源",
                        name_en="Related Resources",
                        attrs={
                            "options": [
                                {"label": "仅主机", "value": "host_only"},
                                {"label": "含进程", "value": "include_processes"},
                                {"label": "含上下游", "value": "include_neighbors"},
                            ],
                            "placeholder": "选择关联资源范围",
                            "placeholder_en": "Select related resource scope",
                        },
                        default="host_only",
                    ),
                ],
            ),
            FormItem(
                tag_code="output_mode",
                type="radio",
                name="输出模式",
                name_en="Output Mode",
                attrs={
                    "options": [
                        {"label": "IP 列表", "value": "ip_list"},
                        {"label": "完整信息", "value": "full"},
                    ],
                },
                default="ip_list",
            ),
        ]

    @classmethod
    def get_var_types(cls):
        return {
            "biz_filter": "plain",
            "host_filter": "plain",
            "include_relations": "plain",
            "output_mode": "plain",
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "hosts", "type": "array", "description": "主机详情列表", "description_en": "Host detail list"},
            {"name": "ip_list", "type": "array", "description": "IP 地址列表", "description_en": "IP address list"},
            {"name": "count", "type": "integer", "description": "主机数量", "description_en": "Host count"},
        ]

    def execute(self, **kwargs) -> dict:
        """执行资源选择

        根据前端配置，从 CMDB 查询并返回选中资源列表。

        Returns:
            success: True/False
            data: {
                "hosts": [...],       # 主机列表
                "ip_list": [...],     # IP 地址列表（供下游引用）
                "count": N,
            }
        """
        from cmdb.services.association_service import AssociationService
        from cmdb.services.node_service import NodeService
        from cmdb.services.topology_service import TopologyService

        biz_filter = kwargs.get("biz_filter", "")
        host_filter = kwargs.get("host_filter", "")
        include_relations = kwargs.get("include_relations", "host_only")
        output_mode = kwargs.get("output_mode", "ip_list")

        result_hosts = []
        topo = TopologyService()

        try:
            if biz_filter:
                # 通过拓扑树获取下游所有主机
                tree = topo.get_tree(biz_filter, rel_types=["CONTAINS"], max_depth=5)
                # 从树节点中提取 Host 类型
                host_ids = [
                    n["instance_id"] for n in tree.get("nodes", [])
                    if n.get("__model_code") == "Host"
                ]
            else:
                # 无筛选时查询所有主机
                svc = NodeService("Host")
                result = svc.list(page=1, page_size=1000)
                host_ids = [h["instance_id"] for h in result.get("items", [])]

            # 获取主机详情
            host_svc = NodeService("Host")
            for hid in host_ids:
                host = host_svc.retrieve(hid)
                if host:
                    # 主机过滤
                    if host_filter:
                        q = host_filter.lower()
                        ip_match = q in (host.get("ip") or "").lower()
                        hostname_match = q in (host.get("hostname") or "").lower()
                        if not ip_match and not hostname_match:
                            continue

                    host_entry = {
                        "instance_id": host.get("instance_id"),
                        "ip": host.get("ip"),
                        "hostname": host.get("hostname"),
                        "os_type": host.get("os_type"),
                        "status": host.get("status"),
                        "region": host.get("region"),
                    }

                    # 关联资源
                    if include_relations == "include_processes":
                        try:
                            nb = AssociationService().get_neighbors(
                                hid, direction="out", asst_types=["RUNS"]
                            )
                            host_entry["processes"] = nb.get("nodes", [])
                        except Exception:
                            host_entry["processes"] = []
                    elif include_relations == "include_neighbors":
                        try:
                            nb = AssociationService().get_neighbors(
                                hid, direction="both", max_depth=2
                            )
                            host_entry["neighbors"] = nb.get("nodes", [])
                            host_entry["edges"] = nb.get("edges", [])
                        except Exception:
                            host_entry["neighbors"] = []

                    result_hosts.append(host_entry)

            ip_list = [h.get("ip") for h in result_hosts if h.get("ip")]

            if output_mode == "ip_list":
                output = {"ip_list": ip_list, "count": len(ip_list)}
            else:
                output = {
                    "hosts": result_hosts,
                    "ip_list": ip_list,
                    "count": len(result_hosts),
                }

            return {"success": True, "data": output}

        except Exception as e:
            return {"success": False, "data": {"error": str(e)}, "error": str(e)}
