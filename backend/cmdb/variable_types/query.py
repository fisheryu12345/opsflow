"""CMDB 实例查询变量 — 按条件查询 CMDB 模型实例

配置:
    value: JSON 字符串，包含 model_code + filters
    如: {"model_code": "Host", "filters": {"status": "normal"}, "limit": 10}
"""

import json

from opsflow.core.variable_registry import LazyVariable


class CmdbQueryVariable(LazyVariable):
    """CMDB 实例查询变量 — 按条件查询 CMDB 模型实例"""
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
