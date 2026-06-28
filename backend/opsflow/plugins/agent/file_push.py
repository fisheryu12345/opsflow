"""agent_file_push — 通过 Agent Agent 推送文件到目标主机

将文件从 OpsFlow 控制台分发到被管控主机的指定路径。
支持大文件分块传输、sha256 校验、断点续传。
"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentFilePushPlugin(BasePlugin):
    name = "Agent 文件推送"
    name_en = "Agent File Push"
    code = "agent_file_push"
    group = "Agent"
    description = "通过 Agent 推送文件到被管控主机"
    description_en = "Push file to managed hosts via Agent"
    risk_level = "medium"
    icon = "Upload"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_hosts",
                type="textarea",
                name="目标主机",
                name_en="Target Hosts",
                attrs={"placeholder": "主机 IP（多个用逗号分隔）", "placeholder_en": "Host IPs (comma-separated)", "rows": 2},
                default="",
            ),
            FormItem(
                tag_code="source_path",
                type="input",
                name="源文件路径",
                name_en="Source File Path",
                attrs={"placeholder": "控制台上的文件路径", "placeholder_en": "File path on the control server"},
                default="",
            ),
            FormItem(
                tag_code="target_path",
                type="input",
                name="目标路径",
                name_en="Target Path",
                attrs={"placeholder": "目标主机的完整路径，如 /data/app.tar.gz", "placeholder_en": "Full path on target host, e.g. /data/app.tar.gz"},
                default="",
            ),
        ]

    def execute(self, target_hosts: str = "", source_path: str = "",
                target_path: str = "", **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {
                "success": False,
                "error": "AGENT_SERVER_URL not configured.",
            }

        hosts = [h.strip() for h in target_hosts.split(",") if h.strip()]
        if not hosts:
            return {"success": False, "error": "No target hosts"}

        try:
            import requests
            resp = requests.post(
                f"{agent_server_url}/api/v1/files/push",
                json={
                    "hosts": hosts,
                    "source_path": source_path,
                    "target_path": target_path,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
