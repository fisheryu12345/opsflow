"""Shell 执行 — 在目标主机上执行 Shell 命令（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ShellPlugin(TowerBasePlugin):
    name = "Shell 执行"
    code = "shell"
    group = "Ansible"
    description = "在目标主机上执行 Shell 命令"
    description_en = "Execute shell commands on remote hosts"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="command",
                type="code_editor",
                name="执行命令",
                attrs={"language": "shell", "height": "200px", "placeholder": "#!/bin/bash\n"},
                validation=[ValidationRule(type="required", error_message="请输入命令")],
            ),
            FormItem(
                tag_code="timeout",
                type="int",
                name="超时时间(秒)",
                default=60,
                attrs={"min": 5, "max": 600},
            ),
            FormItem(
                tag_code="ignore_error",
                type="checkbox",
                name="忽略错误",
                default=False,
                attrs={"options": [{"label": "命令失败时继续执行", "value": True}]},
            ),
        ]
