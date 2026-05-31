"""Docker 部署 — 部署 Docker 容器：拉取镜像、创建并启动容器"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class DockerDeployPlugin(BasePlugin):
    name = "Docker 部署"
    code = "docker_deploy"
    group = "Ansible"
    description = "部署 Docker 容器：拉取镜像、创建并启动容器"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="image",
                type="input",
                name="Docker 镜像名称:tag",
                attrs={"placeholder": "Docker 镜像名称:tag"},
                validation=[ValidationRule(type="required", error_message="请输入 Docker 镜像名称")],
            ),
            FormItem(
                tag_code="container_name",
                type="input",
                name="容器名称",
                attrs={"placeholder": "容器名称"},
                validation=[ValidationRule(type="required", error_message="请输入容器名称")],
            ),
            FormItem(
                tag_code="ports",
                type="code_editor",
                name="端口映射",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"host_port": container_port, "8080": 80}',
                },
            ),
            FormItem(
                tag_code="env_vars",
                type="code_editor",
                name="环境变量",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"key": "value", "APP_ENV": "production"}',
                },
            ),
            FormItem(
                tag_code="volumes",
                type="code_editor",
                name="卷映射",
                default={},
                col=12,
                attrs={
                    "language": "json",
                    "height": "100px",
                    "placeholder": '{"host_path": "container_path", "/data": "/app/data"}',
                },
            ),
        ]

    def execute(self, image: str = "", container_name: str = "", ports: dict = None,
                env_vars: dict = None, volumes: dict = None, **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "container_id": "",
                "deploy_success": False,
            },
        }
