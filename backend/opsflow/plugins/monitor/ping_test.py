"""Ping 测试 — 测试目标主机的网络连通性"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class PingTestPlugin(BasePlugin):
    name = "Ping 测试"
    code = "ping_test"
    group = "Monitor"
    description = "测试目标主机的网络连通性"
    description_en = "Test network connectivity via ICMP ping"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_host",
                type="async_select",
                name="目标地址",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/servers/",
                    "value_key": "value",
                    "label_key": "label",
                    "searchable": True,
                    "placeholder": "从 CMDB 选择服务器...",
                },
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="count",
                type="int",
                name="Ping 次数",
                default=4,
                attrs={"min": 1, "max": 10, "placeholder": "4"},
            ),
        ]

    def execute(self, target_host: str, count: int = 4, **kwargs) -> dict:
        import subprocess
        import sys

        try:
            flag = "-n" if sys.platform == "win32" else "-c"
            res = subprocess.run(
                ["ping", flag, str(count), target_host],
                capture_output=True, text=True, timeout=30,
            )
            success = res.returncode == 0

            # 简单解析丢包率和延迟
            packet_loss = 0.0
            latency_ms = 0.0
            if success:
                for line in res.stdout.splitlines():
                    if "loss" in line.lower() or "丢失" in line:
                        import re
                        nums = re.findall(r"(\d+)%", line)
                        if nums:
                            packet_loss = float(nums[0])
                    if "time" in line.lower() or "平均" in line:
                        import re
                        nums = re.findall(r"(\d+\.?\d*)\s*ms", line, re.IGNORECASE)
                        if nums:
                            nums = [float(x) for x in nums]
                            latency_ms = sum(nums) / len(nums)

            return {
                "success": success,
                "data": {
                    "packet_loss": packet_loss,
                    "latency_ms": latency_ms,
                    "output": res.stdout,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
