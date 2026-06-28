"""文件上传 — 上传本地文件到远程主机（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class UploadFilePlugin(TowerBasePlugin):
    name = "文件上传"
    code = "upload_file"
    group = "Ansible"
    description = "上传本地文件到远程主机"
    description_en = "Upload files to remote hosts"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="src",
                type="input",
                name="本地源文件路径",
                attrs={"placeholder": "本地源文件路径"},
                validation=[ValidationRule(type="required", error_message="请输入本地源文件路径")],
            ),
            FormItem(
                tag_code="dest",
                type="input",
                name="远程目标路径",
                attrs={"placeholder": "远程目标路径"},
                validation=[ValidationRule(type="required", error_message="请输入远程目标路径")],
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
