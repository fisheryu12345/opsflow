"""文件备份 — 备份远程主机上的文件或目录（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class BackupFilePlugin(TowerBasePlugin):
    name = "文件备份"
    name_en = "Backup File"
    code = "backup_file"
    group = "Ansible"
    version = "v1.0"
    description = "备份远程主机上的文件或目录"
    description_en = "Backup files or directories on remote hosts"
    risk_level = "low"
    icon = "FolderDelete"
    color = "#909399"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="需要备份的源文件路径",
                name_en="Source file path",
                attrs={"placeholder": "需要备份的源文件路径", "placeholder_en": "Source file path"},
                validation=[ValidationRule(type="required", error_message="请输入需要备份的源文件路径")],
            ),
            FormItem(
                tag_code="backup_dir",
                type="input",
                name="备份存储目录",
                name_en="Backup directory",
                default="/backup",
                col=6,
                attrs={"placeholder": "备份存储目录", "placeholder_en": "Backup directory"},
            ),
        ]
