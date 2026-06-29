"""文件复制 — 复制文件或目录到远程主机（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class FileCopyPlugin(TowerBasePlugin):
    name = "文件复制"
    name_en = "File Copy"
    code = "file_copy"
    group = "Ansible"
    version = "v1.0"
    description = "复制文件或目录到远程主机"
    description_en = "Copy files between remote hosts or from local to remote"
    risk_level = "medium"
    icon = "CopyDocument"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="源路径",
                name_en="Source Path",
                attrs={"placeholder": "源路径", "placeholder_en": "Source path"},
                validation=[ValidationRule(type="required", error_message="请输入源路径")],
            ),
            FormItem(
                tag_code="dest",
                type="input",
                name="目标路径",
                name_en="Destination Path",
                attrs={"placeholder": "目标路径", "placeholder_en": "Destination path"},
                validation=[ValidationRule(type="required", error_message="请输入目标路径")],
            ),
            FormItem(
                tag_code="owner",
                type="input",
                name="文件所有者",
                name_en="Owner",
                col=6,
                attrs={"placeholder": "文件所有者", "placeholder_en": "File owner"},
            ),
            FormItem(
                tag_code="mode",
                type="input",
                name="文件权限",
                name_en="File Mode",
                default="0644",
                col=6,
                attrs={"placeholder": "文件权限", "placeholder_en": "File permissions"},
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
