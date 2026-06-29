"""Docker 部署 — 部署 Docker 容器（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class DockerDeployPlugin(TowerBasePlugin):
    name = "Docker 部署"
    name_en = "Docker Deploy"
    code = "docker_deploy"
    group = "Ansible"
    version = "v1.0"
    description = "部署 Docker 容器：拉取镜像、创建并启动容器"
    description_en = "Deploy application as Docker containers on remote hosts"
    risk_level = "high"
    icon = "Ship"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="image",
                type="input",
                name="Docker 镜像名称:tag",
                name_en="Docker Image:Tag",
                attrs={"placeholder": "Docker 镜像名称:tag", "placeholder_en": "Docker image:tag"},
                validation=[ValidationRule(type="required", error_message="请输入 Docker 镜像名称")],
            ),
            FormItem(
                tag_code="container_name",
                type="input",
                name="容器名称",
                name_en="Container Name",
                attrs={"placeholder": "容器名称", "placeholder_en": "Container name"},
                validation=[ValidationRule(type="required", error_message="请输入容器名称")],
            ),
            FormItem(
                tag_code="ports",
                type="code_editor",
                name="端口映射",
                name_en="Port Mapping",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"host_port": container_port, "8080": 80}',
                    "placeholder_en": '{"host_port": container_port, "8080": 80}',
                },
            ),
            FormItem(
                tag_code="env_vars",
                type="code_editor",
                name="环境变量",
                name_en="Environment Variables",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"key": "value", "APP_ENV": "production"}',
                    "placeholder_en": '{"key": "value", "APP_ENV": "production"}',
                },
            ),
            FormItem(
                tag_code="volumes",
                type="code_editor",
                name="卷映射",
                name_en="Volume Mapping",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"host_path": "container_path", "/data": "/app/data"}',
                    "placeholder_en": '{"host_path": "container_path", "/data": "/app/data"}',
                },
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
