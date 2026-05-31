"""文件备份 — 备份远程主机上的文件或目录"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class BackupFilePlugin(BasePlugin):
    name = "文件备份"
    code = "backup_file"
    group = "Ansible"
    description = "备份远程主机上的文件或目录"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="需要备份的源文件路径",
                attrs={"placeholder": "需要备份的源文件路径"},
                validation=[ValidationRule(type="required", error_message="请输入需要备份的源文件路径")],
            ),
            FormItem(
                tag_code="backup_dir",
                type="input",
                name="备份存储目录",
                default="/backup",
                col=6,
                attrs={"placeholder": "备份存储目录"},
            ),
        ]

    def execute(self, src: str = "", backup_dir: str = "/backup", **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "backup_path": "",
                "size_bytes": 0,
            },
        }
