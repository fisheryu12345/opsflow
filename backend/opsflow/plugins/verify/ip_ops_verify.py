"""IP 运维验证原子 — 用于验证 IP 选择器/资源选择/表格/级联功能"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem


class IpOpsVerifyPlugin(BasePlugin):
    name = "IP运维验证"
    code = "ip_ops_verify"
    group = "验证工具"
    description = "验证 IP 选择器/资源选择/表格/级联 四种 Tag 组件功能"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="target_ips",
                type="ip_selector",
                name="目标IP",
                attrs={
                    "modes": ["manual", "static", "dynamic"],
                    "options": [
                        {"label": "Web 服务器池", "value": "10.0.1.0/24"},
                        {"label": "DB 服务器池", "value": "10.0.2.0/24"},
                        {"label": "LB 服务器池", "value": "10.0.3.0/24"},
                    ],
                    "api_endpoint": "/api/opsflow/cmdb/ip-pools/",
                },
            ),
            FormItem(
                tag_code="ip_table",
                type="datatable",
                name="IP分配表",
                attrs={
                    "columns": [
                        {"key": "ip", "label": "IP地址", "type": "input"},
                        {"key": "hostname", "label": "主机名", "type": "input", "placeholder": "输入主机名"},
                        {
                            "key": "role",
                            "label": "角色",
                            "type": "select",
                            "options": [
                                {"label": "Web", "value": "web"},
                                {"label": "DB", "value": "db"},
                                {"label": "LB", "value": "lb"},
                                {"label": "Monitor", "value": "mon"},
                            ],
                        },
                    ]
                },
            ),
            FormItem(
                tag_code="dept_path",
                type="cascader",
                name="所属分类",
                attrs={
                    "api_endpoint": "/api/opsflow/cmdb/categories/",
                    "props": {"checkStrictly": True},
                },
            ),
        ]

    def execute(self, **kwargs) -> dict:
        """回显所有传入参数以验证各组件传值正确"""
        return {"success": True, "data": {"received": kwargs}}
