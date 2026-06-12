"""CMDB 计数变量 — 统计指定模型的实例数量

配置:
    value: 模型编码，如 "Host", "Biz"
"""

from opsflow.core.variable_registry import LazyVariable


class CmdbCountVariable(LazyVariable):
    """CMDB 计数变量 — 统计指定模型的实例数量"""
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
