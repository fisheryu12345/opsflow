"""agent_process_stop — 通过 Agent 远程停止应用进程"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentProcessStopPlugin(BasePlugin):
    name = "Agent 进程停止"
    name_en = "Agent Process Stop"
    code = "agent_process_stop"
    group = "Agent"
    description = "通过 Agent 在目标主机上停止应用进程（支持 systemd 和强制 Kill）"
    description_en = "Stop application process on target host via Agent"
    risk_level = "high"
    icon = "VideoPause"
    color = "#F56C6C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(tag_code="target_host", type="input", name="目标主机",
                     attrs={"placeholder": "目标主机 IP"}, default=""),
            FormItem(tag_code="service_name", type="input", name="Service 名称",
                     attrs={"placeholder": "systemd unit 名（如 nginx.service）"}, default=""),
            FormItem(tag_code="force", type="checkbox", name="强制停止",
                     default=False, attrs={"options": [{"label": "kill -9 强制终止", "value": True}]}),
        ]

    def execute(self, target_host: str = "", service_name: str = "",
                force: bool = False, **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {"success": False, "error": "AGENT_SERVER_URL not configured"}
        if not target_host or not service_name:
            return {"success": False, "error": "target_host and service_name required"}

        try:
            import requests
            if service_name.endswith(".service"):
                if force:
                    script = f"systemctl kill --signal=SIGKILL {service_name}"
                else:
                    script = f"systemctl stop {service_name}"
            else:
                script = f"pkill -{'9' if force else '15'} {service_name}" if force else f"pkill {service_name}"

            resp = requests.post(
                f"{agent_server_url}/api/v1/tasks/exec",
                json={"target_host": target_host, "script_content": script,
                       "script_type": "shell", "timeout": 30}, timeout=40,
            )
            if resp.status_code == 200:
                data = resp.json()
                success = data.get('exit_code', 0) == 0
                return {"success": success, "data": {"stdout": data.get('stdout',''), "stderr": data.get('stderr',''), "exit_code": data.get('exit_code', 0), "service": service_name, "host": target_host}}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.exception("Agent process stop failed")
            return {"success": False, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [{"name": "stdout", "type": "string"}, {"name": "stderr", "type": "string"},
                {"name": "exit_code", "type": "integer"}, {"name": "service", "type": "string"}]
