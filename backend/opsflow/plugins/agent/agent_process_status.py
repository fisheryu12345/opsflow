"""agent_process_status — 通过 Agent 查询应用进程状态"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentProcessStatusPlugin(BasePlugin):
    name = "Agent 进程状态"
    name_en = "Agent Process Status"
    code = "agent_process_status"
    group = "Agent"
    description = "通过 Agent 查询目标主机上应用进程的运行状态"
    description_en = "Query application process status on target host via Agent"
    risk_level = "low"
    icon = "Monitor"
    color = "#909399"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(tag_code="target_host", type="input", name="目标主机",
                     name_en="Target Host",
                     attrs={"placeholder": "目标主机 IP", "placeholder_en": "Target host IP"}, default=""),
            FormItem(tag_code="service_name", type="input", name="Service 名称",
                     name_en="Service Name",
                     attrs={"placeholder": "systemd unit 名或进程名", "placeholder_en": "systemd unit name or process name"}, default=""),
        ]

    @classmethod
    def get_var_types(cls):
        return {"service_name": "splice"}

    def execute(self, target_host: str = "", service_name: str = "", **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {"success": False, "error": "AGENT_SERVER_URL not configured"}
        if not target_host or not service_name:
            return {"success": False, "error": "target_host and service_name required"}

        try:
            import requests
            script = f"systemctl is-active {service_name} 2>/dev/null || ps -C {service_name} -o pid,stat --no-headers 2>/dev/null || echo 'not_found'"
            resp = requests.post(
                f"{agent_server_url}/api/v1/tasks/exec",
                json={"target_host": target_host, "script_content": script,
                       "script_type": "shell", "timeout": 15}, timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                stdout = (data.get('stdout') or '').strip()
                is_running = stdout in ('active', 'activating') or 'running' in stdout.lower()
                return {
                    "success": True,
                    "data": {
                        "status": "running" if is_running else "stopped",
                        "raw": stdout,
                        "service": service_name,
                        "host": target_host,
                    },
                }
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.exception("Agent process status failed")
            return {"success": False, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "status", "type": "string", "description": "running/stopped"},
            {"name": "raw", "type": "string", "description": "原始命令输出"},
            {"name": "service", "type": "string"},
            {"name": "host", "type": "string"},
        ]
