"""健康检查 — Ping + 端口检测"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule, FormGroup


class HealthCheckPlugin(BasePlugin):
    name = "健康检查"
    code = "health_check"
    group = "Monitor"
    description = "对目标主机执行 Ping 和端口连通性检查"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="host",
                type="input",
                name="目标地址",
                attrs={"placeholder": "IP 或域名"},
                validation=[ValidationRule(type="required")],
            ),
            FormGroup(
                name="检查选项",
                tag_code="check_options",
                items=[
                    FormItem(
                        tag_code="ping_count",
                        type="int",
                        name="Ping 次数",
                        default=4,
                        attrs={"min": 1, "max": 10},
                    ),
                    FormItem(
                        tag_code="check_port",
                        type="checkbox",
                        name="端口检查",
                        default=False,
                        attrs={"options": [{"label": "启用端口检查", "value": True}]},
                    ),
                    FormItem(
                        tag_code="port",
                        type="int",
                        name="目标端口",
                        default=80,
                        attrs={"min": 1, "max": 65535},
                        hidden=False,
                        events=[],
                    ),
                ],
            ),
        ]

    def execute(self, host: str, ping_count: int = 4, check_port: bool = False,
                port: int = 80, **kwargs) -> dict:
        import subprocess
        result = {
            "ping": {"success": False, "output": ""},
            "port": {"success": False, "output": ""},
        }

        # Ping 检查
        try:
            ping_cmd = ["ping", "-n" if __import__("sys").platform == "win32" else "-c",
                        str(ping_count), host]
            ping_res = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=30)
            result["ping"]["success"] = ping_res.returncode == 0
            result["ping"]["output"] = ping_res.stdout
        except Exception as e:
            result["ping"]["error"] = str(e)

        # 端口检查
        if check_port:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                code = sock.connect_ex((host, port))
                sock.close()
                result["port"]["success"] = code == 0
                result["port"]["output"] = f"端口 {port}: {'开放' if code == 0 else '未开放'}"
            except Exception as e:
                result["port"]["error"] = str(e)

        success = result["ping"]["success"]
        if check_port:
            success = success and result["port"]["success"]

        return {"success": success, "data": result}
