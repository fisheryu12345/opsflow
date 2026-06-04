"""CMDB 变量类型 — 运行时动态查询 CMDB 数据

这些变量在 pipeline 执行时动态计算，返回 CMDB 中的实例数据。
"""

import json

from opsflow.core.variable_registry import LazyVariable


class CmdbQueryVariable(LazyVariable):
    """CMDB 实例查询变量 — 按条件查询 CMDB 模型实例

    配置:
        value: JSON 字符串，包含 model_code + filters
        如: {"model_code": "Host", "filters": {"status": "normal"}, "limit": 10}
    """
    code = "cmdb_query"
    name = "CMDB 查询"
    type = "dynamic"
    tag = "cmdb.cmdb_query"
    description = "按条件查询 CMDB 模型实例，返回实例列表"

    def get_value(self):
        from cmdb.services.node_service import NodeService

        config = self.value
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except (json.JSONDecodeError, TypeError):
                return {"error": "配置格式错误，请使用 JSON 格式"}

        model_code = config.get("model_code", "Host") if isinstance(config, dict) else "Host"
        filters = config.get("filters", {}) if isinstance(config, dict) else {}
        limit = config.get("limit", 20) if isinstance(config, dict) else 20

        try:
            svc = NodeService(model_code)
            result = svc.list(filters, page=1, page_size=limit)
            return {
                "items": result.get("items", []),
                "total": result.get("total", 0),
                "model_code": model_code,
            }
        except Exception as e:
            return {"error": str(e), "model_code": model_code}


class CmdbTopologyVariable(LazyVariable):
    """CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径

    配置:
        value: JSON 字符串，包含 instance_id + direction + max_depth
        如: {"instance_id": "xxx", "direction": "downstream", "max_depth": 3}
    """
    code = "cmdb_topology"
    name = "CMDB 拓扑路径"
    type = "dynamic"
    tag = "cmdb.cmdb_topology"
    description = "查询实例的拓扑路径或影响范围"

    def get_value(self):
        from cmdb.services.topology_service import TopologyService

        config = self.value
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except (json.JSONDecodeError, TypeError):
                return {"error": "配置格式错误，请使用 JSON 格式"}

        instance_id = config.get("instance_id") if isinstance(config, dict) else None
        if not instance_id:
            return {"error": "缺少 instance_id"}

        direction = config.get("direction", "downstream") if isinstance(config, dict) else "downstream"
        max_depth = config.get("max_depth", 3) if isinstance(config, dict) else 3

        try:
            topo = TopologyService()
            impact = topo.get_impact(instance_id, direction=direction, max_depth=max_depth)
            return impact
        except Exception as e:
            return {"error": str(e)}


class CmdbCountVariable(LazyVariable):
    """CMDB 计数变量 — 统计指定模型的实例数量

    配置:
        value: 模型编码，如 "Host", "Biz"
    """
    code = "cmdb_count"
    name = "CMDB 实例计数"
    type = "dynamic"
    tag = "cmdb.cmdb_count"
    description = "统计 CMDB 指定模型的实例数量"

    def get_value(self):
        from cmdb.services.node_service import NodeService

        model_code = str(self.value) if self.value else "Host"

        try:
            svc = NodeService(model_code)
            result = svc.list(page=1, page_size=0)
            return {
                "model_code": model_code,
                "count": result.get("total", 0),
            }
        except Exception as e:
            return {"error": str(e), "model_code": model_code}
