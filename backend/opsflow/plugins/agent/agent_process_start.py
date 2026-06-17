"""agent_process_start — 通过 Agent 远程启动应用进程

支持 systemd service 和直接命令两种模式。
自动检测目标主机上是否有对应的 systemd unit。
"""

import json
import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentProcessStartPlugin(BasePlugin):
    name = "Agent 进程启动"
    name_en = "Agent Process Start"
    code = "agent_process_start"
    group = "Agent"
    description = "通过 Agent 在目标主机上启动应用进程（支持 systemd）"
    description_en = "Start application process on target host via Agent (supports systemd)"
    risk_level = "high"
    icon = "VideoPlay"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_host",
                type="input",
                name="目标主机",
                attrs={"placeholder": "目标主机 IP"},
                default="",
            ),
            FormItem(
                tag_code="service_name",
                type="input",
                name="Service 名称",
                attrs={"placeholder": "systemd unit 名（如 nginx.service）或应用名"},
                default="",
            ),
            FormItem(
                tag_code="command",
                type="input",
                name="启动命令",
                attrs={"placeholder": "无 systemd 时的启动命令（如 nohup /opt/app/start.sh &）"},
                default="",
            ),
            FormItem(
                tag_code="user",
                type="input",
                name="运行用户",
                attrs={"placeholder": "可选，以指定用户启动"},
                default="",
            ),
        ]

    def execute(self, target_host: str = "", service_name: str = "",
                command: str = "", user: str = "", **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {"success": False, "error": "AGENT_SERVER_URL not configured"}

        if not target_host or not service_name:
            return {"success": False, "error": "target_host and service_name required"}

        try:
            import requests

            # 构建启动命令：优先 systemctl
            if service_name.endswith(".service"):
                script = f"systemctl start {service_name}"
            elif command:
                script = command
                if user:
                    script = f"su - {user} -c '{command}'"
            else:
                script = service_name

            resp = requests.post(
                f"{agent_server_url}/api/v1/tasks/exec",
                json={
                    "target_host": target_host,
                    "script_content": script,
                    "script_type": "shell",
                    "timeout": 30,
                },
                timeout=40,
            )
            if resp.status_code == 200:
                data = resp.json()
                success = data.get('exit_code', 0) == 0
                return {
                    "success": success,
                    "data": {
                        "stdout": data.get('stdout', ''),
                        "stderr": data.get('stderr', ''),
                        "exit_code": data.get('exit_code', 0),
                        "service": service_name,
                        "host": target_host,
                    },
                    "error": "" if success else data.get('stderr', 'start failed'),
                }
            return {"success": False, "error": f"Agent Server HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.exception("Agent process start failed")
            return {"success": False, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "stdout", "type": "string", "description": "启动命令输出"},
            {"name": "stderr", "type": "string", "description": "启动错误输出"},
            {"name": "exit_code", "type": "integer", "description": "退出码"},
            {"name": "service", "type": "string", "description": "Service 名称"},
            {"name": "host", "type": "string", "description": "目标主机"},
        ]
