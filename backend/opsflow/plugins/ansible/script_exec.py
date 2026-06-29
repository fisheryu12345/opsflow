"""脚本执行 — 上传脚本内容并在远程主机上执行（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ScriptExecPlugin(TowerBasePlugin):
    name = "脚本执行"
    name_en = "Script Execute"
    code = "script_exec"
    group = "Ansible"
    version = "v1.0"
    description = "上传脚本内容并在远程主机上执行"
    description_en = "Execute scripts on remote hosts"
    risk_level = "medium"
    icon = "Cpu"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="script_content",
                type="input",
                name="脚本内容",
                name_en="Script Content",
                attrs={"placeholder": "脚本内容", "placeholder_en": "Script content", "type": "textarea"},
                validation=[ValidationRule(type="required", error_message="请输入脚本内容")],
            ),
            FormItem(
                tag_code="script_type",
                type="input",
                name="脚本类型",
                name_en="Script Type",
                default="bash",
                col=6,
                attrs={"placeholder": "脚本类型: bash/python/powershell", "placeholder_en": "Script type: bash/python/powershell"},
            ),
            FormItem(
                tag_code="args",
                type="input",
                name="脚本参数",
                name_en="Script Arguments",
                col=6,
                attrs={"placeholder": "脚本参数", "placeholder_en": "Script arguments"},
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
