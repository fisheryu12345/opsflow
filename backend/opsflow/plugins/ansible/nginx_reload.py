"""Nginx 重载 — 验证 Nginx 配置并执行重载（通过 Ansible Tower）"""

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem


class NginxReloadPlugin(TowerBasePlugin):
    name = "Nginx 重载"
    code = "nginx_reload"
    group = "Ansible"
    description = "验证 Nginx 配置并执行重载"
    description_en = "Reload Nginx configuration on remote hosts"
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
