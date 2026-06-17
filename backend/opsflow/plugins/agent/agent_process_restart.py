"""agent_process_restart — 通过 Agent 远程重启应用进程"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentProcessRestartPlugin(BasePlugin):
    name = "Agent 进程重启"
    name_en = "Agent Process Restart"
    code = "agent_process_restart"
    group = "Agent"
    description = "通过 Agent 在目标主机上重启应用进程（支持 systemctl restart）"
    description_en = "Restart application process on target host via Agent"
    risk_level = "high"
    icon = "Refresh"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(tag_code="target_host", type="input", name="目标主机",
                     attrs={"placeholder": "目标主机 IP"}, default=""),
            FormItem(tag_code="service_name", type="input", name="Service 名称",
                     attrs={"placeholder": "systemd unit 名（如 nginx.service）"}, default=""),
        ]

    def execute(self, target_host: str = "", service_name: str = "", **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {"success": False, "error": "AGENT_SERVER_URL not configured"}
        if not target_host or not service_name:
            return {"success": False, "error": "target_host and service_name required"}

        try:
            import requests
            if service_name.endswith(".service"):
                script = f"systemctl restart {service_name}"
            else:
                script = f"systemctl restart {service_name} 2>/dev/null || (pkill -f {service_name}; sleep 1; nohup {service_name} &)"

            resp = requests.post(
                f"{agent_server_url}/api/v1/tasks/exec",
                json={"target_host": target_host, "script_content": script,
                       "script_type": "shell", "timeout": 60}, timeout=70,
            )
            if resp.status_code == 200:
                data = resp.json()
                success = data.get('exit_code', 0) == 0
                return {"success": success, "data": {"stdout": data.get('stdout',''), "stderr": data.get('stderr',''), "exit_code": data.get('exit_code', 0), "service": service_name, "host": target_host}}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.exception("Agent process restart failed")
            return {"success": False, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [{"name": "stdout", "type": "string"}, {"name": "stderr", "type": "string"},
                {"name": "exit_code", "type": "integer"}, {"name": "service", "type": "string"}]
