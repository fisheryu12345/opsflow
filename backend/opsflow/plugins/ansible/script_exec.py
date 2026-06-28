"""脚本执行 — 上传脚本内容并在远程主机上执行（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ScriptExecPlugin(TowerBasePlugin):
    name = "脚本执行"
    code = "script_exec"
    group = "Ansible"
    description = "上传脚本内容并在远程主机上执行"
    description_en = "Execute scripts on remote hosts"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="script_content",
                type="input",
                name="脚本内容",
                attrs={"placeholder": "脚本内容", "type": "textarea"},
                validation=[ValidationRule(type="required", error_message="请输入脚本内容")],
            ),
            FormItem(
                tag_code="script_type",
                type="input",
                name="脚本类型",
                default="bash",
                col=6,
                attrs={"placeholder": "脚本类型: bash/python/powershell"},
            ),
            FormItem(
                tag_code="args",
                type="input",
                name="脚本参数",
                col=6,
                attrs={"placeholder": "脚本参数"},
            ),
        ]
