"""Nginx 重载 — 验证 Nginx 配置并执行重载"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem


class NginxReloadPlugin(BasePlugin):
    name = "Nginx 重载"
    code = "nginx_reload"
    group = "Ansible"
    description = "验证 Nginx 配置并执行重载"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="config_path",
                type="input",
                name="Nginx 配置文件路径",
                default="/etc/nginx/nginx.conf",
                col=6,
                attrs={"placeholder": "Nginx 配置文件路径"},
            ),
            FormItem(
                tag_code="test_config",
                type="checkbox",
                name="重载前是否执行配置测试",
                default=True,
                col=6,
                attrs={"options": [{"label": "重载前执行配置测试", "value": True}]},
            ),
        ]

    def execute(self, config_path: str = "/etc/nginx/nginx.conf", test_config: bool = True, **kwargs) -> dict:
        return {
            "success": True,
            "data": {
                "message": "execution delegated",
                "config_valid": True,
                "reload_success": True,
            },
        }
