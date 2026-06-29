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
