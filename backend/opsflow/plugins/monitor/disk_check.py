"""磁盘检查 — 检查远程主机磁盘使用率，超过阈值可触发告警"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup


class DiskCheckPlugin(BasePlugin):
    name = "磁盘检查"
    code = "disk_check"
    group = "Monitor"
    description = "检查远程主机磁盘使用率，超过阈值可触发告警"
    description_en = "Check disk space usage on target hosts"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="warning_threshold",
                type="int",
                name="告警阈值",
                default=80,
                attrs={"min": 1, "max": 100, "placeholder": "磁盘使用率告警阈值(%)"},
            ),
            FormGroup(
                name="目标设置",
                tag_code="target_settings",
                items=[
                    FormItem(
                        tag_code="mount_point",
                        type="input",
                        name="挂载点",
                        default="/",
                        attrs={"placeholder": "挂载点路径，如 / 或 /data"},
                    ),
                    FormItem(
                        tag_code="host",
                        type="async_select",
                        name="目标主机",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servers/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择服务器...",
                        },
                    ),
                ],
            ),
        ]

    def execute(self, warning_threshold: int = 80, mount_point: str = "/",
                host: str = "", **kwargs) -> dict:
        import shutil

        try:
            usage = shutil.disk_usage(mount_point)
            total_gb = round(usage.total / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            avail_gb = round(usage.free / (1024 ** 3), 2)
            usage_percent = round(usage.used / usage.total * 100, 1)

            success = usage_percent < warning_threshold

            return {
                "success": success,
                "data": {
                    "usage_percent": usage_percent,
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "avail_gb": avail_gb,
                    "mount_point": mount_point,
                    "threshold": warning_threshold,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
