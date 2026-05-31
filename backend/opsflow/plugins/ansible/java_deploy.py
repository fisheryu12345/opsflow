"""Java 部署 — 部署 Java 应用：上传 JAR/WAR 包并重启服务"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class JavaDeployPlugin(BasePlugin):
    name = "Java 部署"
    code = "java_deploy"
    group = "Ansible"
    description = "部署 Java 应用：上传 JAR/WAR 包并重启服务"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="artifact_path",
                type="input",
                name="JAR/WAR 包本地路径",
                attrs={"placeholder": "JAR/WAR 包本地路径"},
                validation=[ValidationRule(type="required", error_message="请输入 JAR/WAR 包本地路径")],
            ),
            FormItem(
                tag_code="target_path",
                type="input",
                name="部署目标目录",
                default="/opt/app",
                col=6,
                attrs={"placeholder": "部署目标目录"},
            ),
            FormItem(
                tag_code="service_name",
                type="input",
                name="服务名称(systemd unit)",
                attrs={"placeholder": "服务名称(systemd unit)"},
                validation=[ValidationRule(type="required", error_message="请输入服务名称")],
            ),
            FormItem(
                tag_code="jvm_args",
                type="input",
                name="JVM 启动参数",
                col=6,
                attrs={"placeholder": "JVM 启动参数"},
            ),
        ]

    def execute(self, artifact_path: str = "", target_path: str = "/opt/app", service_name: str = "", jvm_args: str = "", **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "deploy_success": False,
                "service_status": "",
            },
        }
