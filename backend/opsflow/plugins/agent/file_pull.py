"""agent_file_pull — 通过 Agent Agent 从目标主机拉取文件

从被管控主机拉取文件到 OpsFlow 控制台。
"""

import logging
import os

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem

logger = logging.getLogger(__name__)


class AgentFilePullPlugin(BasePlugin):
    name = "Agent 文件拉取"
    name_en = "Agent File Pull"
    code = "agent_file_pull"
    group = "Agent"
    version = "v1.0"
    description = "通过 Agent Agent 从被管控主机拉取文件到控制台"
    description_en = "Pull file from managed host to control server via Agent"
    risk_level = "medium"
    icon = "Download"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_host",
                type="input",
                name="目标主机",
                name_en="Target Host",
                attrs={"placeholder": "主机 IP", "placeholder_en": "Host IP"},
                default="",
            ),
            FormItem(
                tag_code="source_path",
                type="input",
                name="源文件路径",
                name_en="Source File Path",
                attrs={"placeholder": "目标主机上的文件路径", "placeholder_en": "File path on target host"},
                default="",
            ),
            FormItem(
                tag_code="target_path",
                type="input",
                name="保存路径",
                name_en="Save Path",
                attrs={"placeholder": "控制台上的保存路径", "placeholder_en": "Save path on control server"},
                default="",
            ),
        ]

    def execute(self, target_host: str = "", source_path: str = "",
                target_path: str = "", **kwargs) -> dict:
        agent_server_url = os.environ.get("AGENT_SERVER_URL", None)
        if not agent_server_url:
            return {
                "success": False,
                "error": "AGENT_SERVER_URL not configured.",
            }
        if not target_host:
            return {"success": False, "error": "No target host"}

        try:
            import requests
            resp = requests.post(
                f"{agent_server_url}/api/v1/files/pull",
                json={
                    "host": target_host,
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "results", "type": "object", "description": "拉取操作结果", "description_en": "Pull operation result"},
        ]
