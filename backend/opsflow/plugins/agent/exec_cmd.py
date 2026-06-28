"""agent_exec_cmd — 通过 Agent 远程执行命令/脚本

支持 shell、python、bat、powershell 等多种脚本类型。
自动选择有在线 Agent 的目标主机，通过 Agent Server 下发执行并收集结果。
"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentExecCmdPlugin(BasePlugin):
    name = "Agent 远程执行"
    name_en = "Agent Remote Execute"
    code = "agent_exec_cmd"
    group = "Agent"
    description = "通过 Agent 在被管控主机上执行命令或脚本（替代 SSH）"
    description_en = "Execute commands/scripts on managed hosts via Agent"
    risk_level = "medium"
    icon = "Monitor"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_hosts",
                type="textarea",
                name="目标主机",
                name_en="Target Hosts",
                attrs={
                    "placeholder": "主机 IP（多个用逗号分隔，或从 CMDB 变量传入）",
                    "placeholder_en": "Host IPs (comma-separated, or from CMDB variable)",
                    "rows": 2,
                },
                default="",
            ),
            FormItem(
                tag_code="script_type",
                type="select",
                name="脚本类型",
                name_en="Script Type",
                default="shell",
                attrs={
                    "options": [
                        {"label": "Shell (Linux/AIX)", "value": "shell"},
                        {"label": "Python", "value": "python"},
                        {"label": "BAT (Windows)", "value": "bat"},
                        {"label": "PowerShell (Windows)", "value": "powershell"},
                    ]
                },
            ),
            FormItem(
                tag_code="script_content",
                type="textarea",
                name="脚本内容",
                name_en="Script Content",
                attrs={"placeholder": "输入要执行的命令或脚本内容", "placeholder_en": "Enter the command or script to execute", "rows": 8},
                default="",
            ),
            FormItem(
                tag_code="timeout",
                type="input",
                name="超时秒数",
                name_en="Timeout (s)",
                default="3600",
                attrs={"placeholder": "命令执行超时时间（秒）", "placeholder_en": "Command execution timeout in seconds"},
            ),
            FormItem(
                tag_code="work_dir",
                type="input",
                name="工作目录",
                name_en="Work Directory",
                default="",
                attrs={"placeholder": "可选，命令执行的工作目录", "placeholder_en": "Optional working directory"},
            ),
        ]

    def execute(self, target_hosts: str = "", script_type: str = "shell",
                script_content: str = "", timeout: str = "3600",
                work_dir: str = "", **kwargs) -> dict:
        """通过 Agent Server 在目标主机上执行命令"""
        # XXX: actual implement: call Agent Server REST API
        # If AGENT_SERVER_URL is configured, use it; otherwise return a tip
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {
                "success": False,
                "error": "AGENT_SERVER_URL not configured. "
                         "Set env var or check Agent Server deployment.",
            }

        hosts = [h.strip() for h in target_hosts.split(",") if h.strip()]
        if not hosts:
            return {"success": False, "error": "No target hosts specified"}

        try:
            import requests
            from django.utils import timezone

            results = {}
            all_success = True

            for host in hosts:
                resp = requests.post(
                    f"{agent_server_url}/api/v1/tasks/exec",
                    json={
                        "target_host": host,
                        "script_content": script_content,
                        "script_type": script_type,
                        "timeout": int(timeout),
                        "work_dir": work_dir or None,
                    },
                    timeout=int(timeout) + 10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results[host] = data
                else:
                    results[host] = {
                        "error": f"HTTP {resp.status_code}: {resp.text}",
                        "exit_code": -1,
                    }
                    all_success = False

            return {
                "success": all_success,
                "data": {
                    "results": results,
                    "host_count": len(hosts),
                    "finish_time": timezone.now().isoformat(),
                },
            }

        except ImportError:
            return {"success": False, "error": "requests library not installed"}
        except Exception as e:
            logger.exception("Agent exec failed")
            return {"success": False, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "results", "type": "dict", "description": "各主机的执行结果"},
            {"name": "host_count", "type": "integer", "description": "目标主机数量"},
            {"name": "finish_time", "type": "string", "description": "完成时间"},
        ]
