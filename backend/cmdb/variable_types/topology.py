"""CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径

配置:
    value: JSON 字符串，包含 instance_id + direction + max_depth
    如: {"instance_id": "xxx", "direction": "downstream", "max_depth": 3}
"""

import json

from opsflow.core.variable_registry import LazyVariable


class CmdbTopologyVariable(LazyVariable):
    """CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径"""
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
