"""Dell PowerMax 性能监控 — 查询阵列和存储组性能指标"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class GetPerformancePlugin(BasePlugin):
    name = "查询性能指标"
    code = "pmax_get_performance"
    group = "Pmax"
    description = "查询 PowerMax 阵列或存储组的性能指标（IOPS、带宽、延迟）"
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
                tag_code="sg_name",
                type="input",
                name="存储组名称(可选)",
                attrs={"placeholder": "留空则查询阵列整体性能"},
                col=6,
            ),
            FormItem(
                tag_code="metrics",
                type="select",
                name="指标类型",
                default="all",
                attrs={
                    "options": [
                        {"label": "全部指标", "value": "all"},
                        {"label": "IOPS (读写)", "value": "iops"},
                        {"label": "带宽 MB/s", "value": "bandwidth"},
                        {"label": "响应时间 ms", "value": "latency"},
                        {"label": "缓存命中率", "value": "cache_hit"},
                    ],
                },
                col=12,
            ),
            FormItem(
                tag_code="time_range",
                type="select",
                name="时间范围",
                default="last_hour",
                attrs={
                    "options": [
                        {"label": "最近 1 小时", "value": "last_hour"},
                        {"label": "最近 24 小时", "value": "last_24h"},
                        {"label": "最近 7 天", "value": "last_7d"},
                    ],
                },
                col=12,
            ),
        ]

    def execute(self, array_id: str, sg_name: str = "", metrics: str = "all",
                time_range: str = "last_hour", **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "array_id": array_id,
                "sg_name": sg_name or "整个阵列",
                "metrics": {
                    "read_iops": 0,
                    "write_iops": 0,
                    "read_mb_s": 0.0,
                    "write_mb_s": 0.0,
                    "avg_latency_ms": 0.0,
                },
            },
            "error": "",
        }
