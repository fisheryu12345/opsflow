"""Java 部署 — 部署 Java 应用（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class JavaDeployPlugin(TowerBasePlugin):
    name = "Java 部署"
    name_en = "Java Deploy"
    code = "java_deploy"
    group = "Ansible"
    version = "v1.0"
    description = "部署 Java 应用：上传 JAR/WAR 包并重启服务"
    description_en = "Deploy Java application packages to remote hosts"
    risk_level = "high"
    icon = "CoffeeCup"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="artifact_path",
                type="input",
                name="JAR/WAR 包本地路径",
                name_en="Artifact Local Path",
                attrs={"placeholder": "JAR/WAR 包本地路径", "placeholder_en": "JAR/WAR package local path"},
                validation=[ValidationRule(type="required", error_message="请输入 JAR/WAR 包本地路径")],
            ),
            FormItem(
                tag_code="target_path",
                type="input",
                name="部署目标目录",
                name_en="Target Directory",
                default="/opt/app",
                col=6,
                attrs={"placeholder": "部署目标目录", "placeholder_en": "Deployment target directory"},
            ),
            FormItem(
                tag_code="service_name",
                type="input",
                name="服务名称(systemd unit)",
                name_en="Service Name",
                attrs={"placeholder": "服务名称(systemd unit)", "placeholder_en": "Service name (systemd unit)"},
                validation=[ValidationRule(type="required", error_message="请输入服务名称")],
            ),
            FormItem(
                tag_code="jvm_args",
                type="input",
                name="JVM 启动参数",
                name_en="JVM Arguments",
                col=6,
                attrs={"placeholder": "JVM 启动参数", "placeholder_en": "JVM startup arguments"},
            ),
        ]
