"""文件上传 — 上传本地文件到远程主机（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class UploadFilePlugin(TowerBasePlugin):
    name = "文件上传"
    name_en = "File Upload"
    code = "upload_file"
    group = "Ansible"
    version = "v1.0"
    description = "上传本地文件到远程主机"
    description_en = "Upload files to remote hosts"
    risk_level = "medium"
    icon = "Upload"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="本地源文件路径",
                name_en="Source File Path",
                attrs={"placeholder": "本地源文件路径", "placeholder_en": "Local source file path"},
                validation=[ValidationRule(type="required", error_message="请输入本地源文件路径")],
            ),
            FormItem(
                tag_code="dest",
                type="input",
                name="远程目标路径",
                name_en="Remote Target Path",
                attrs={"placeholder": "远程目标路径", "placeholder_en": "Remote target path"},
                validation=[ValidationRule(type="required", error_message="请输入远程目标路径")],
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
