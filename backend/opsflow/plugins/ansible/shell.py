"""Shell 执行 — 在目标主机上执行 Shell 命令（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ShellPlugin(TowerBasePlugin):
    name = "Shell 执行"
    name_en = "Shell Execute"
    code = "shell"
    group = "Ansible"
    version = "v1.0"
    description = "在目标主机上执行 Shell 命令"
    description_en = "Execute shell commands on remote hosts"
    risk_level = "medium"
    icon = "Terminal"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="command",
                type="code_editor",
                name="执行命令",
                name_en="Command",
                attrs={"language": "shell", "height": "200px", "placeholder": "#!/bin/bash\n", "placeholder_en": "#!/bin/bash\n"},
                validation=[ValidationRule(type="required", error_message="请输入命令")],
            ),
            FormItem(
                tag_code="timeout",
                type="int",
                name="超时时间(秒)",
                name_en="Timeout (s)",
                default=60,
                attrs={"min": 5, "max": 600},
            ),
            FormItem(
                tag_code="ignore_error",
                type="checkbox",
                name="忽略错误",
                name_en="Ignore Error",
                default=False,
                attrs={"options": [{"label": "命令失败时继续执行", "value": True}]},
            ),
        ]

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "stdout", "type": "string", "description": "命令执行输出", "description_en": "Command execution output"},
            {"name": "stderr", "type": "string", "description": "错误输出", "description_en": "Error output"},
            {"name": "returncode", "type": "integer", "description": "返回码", "description_en": "Return code"},
            {"name": "tower_job_id", "type": "integer", "description": "Tower 作业 ID", "description_en": "Tower job ID"},
            {"name": "tower_status", "type": "string", "description": "Tower 作业状态", "description_en": "Tower job status"},
            {"name": "elapsed", "type": "float", "description": "执行耗时（秒）", "description_en": "Execution elapsed (seconds)"},
        ]
