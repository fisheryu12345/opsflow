"""文件复制 — 复制文件或目录到远程主机"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class FileCopyPlugin(BasePlugin):
    name = "文件复制"
    code = "file_copy"
    group = "Ansible"
    description = "复制文件或目录到远程主机"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="源路径",
                attrs={"placeholder": "源路径"},
                validation=[ValidationRule(type="required", error_message="请输入源路径")],
            ),
            FormItem(
                tag_code="dest",
                type="input",
                name="目标路径",
                attrs={"placeholder": "目标路径"},
                validation=[ValidationRule(type="required", error_message="请输入目标路径")],
            ),
            FormItem(
                tag_code="owner",
                type="input",
                name="文件所有者",
                col=6,
                attrs={"placeholder": "文件所有者"},
            ),
            FormItem(
                tag_code="mode",
                type="input",
                name="文件权限",
                default="0644",
                col=6,
                attrs={"placeholder": "文件权限"},
            ),
        ]

    def execute(self, src: str = "", dest: str = "", owner: str = "", mode: str = "0644", **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "changed": False,
                "dest_path": dest,
            },
        }
