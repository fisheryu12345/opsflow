"""ServiceNow CMDB 查询 — 查询 ServiceNow CMDB CI 信息"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowGetCmdbCiPlugin(BasePlugin):
    name = "ServiceNow CMDB 查询"
    code = "servicenow_get_cmdb_ci"
    group = "ServiceNow"
    description = "查询 ServiceNow CMDB 中配置项 (CI) 的详情"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="ServiceNow 连接",
                tag_code="sn_connection",
                items=[
                    FormItem(
                        tag_code="instance_url",
                        type="async_select",
                        name="实例地址",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servicenow-instances/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择 ServiceNow 实例...",
                        },
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="username",
                        type="input",
                        name="用户名",
                        attrs={"placeholder": "ServiceNow 用户名"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="password",
                        type="input",
                        name="密码",
                        attrs={"placeholder": "密码或 API Token", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormGroup(
                name="查询条件",
                tag_code="query_criteria",
                items=[
                    FormItem(
                        tag_code="ci_name",
                        type="input",
                        name="CI 名称",
                        attrs={"placeholder": "配置项名称（支持通配符）"},
                    ),
                    FormItem(
                        tag_code="ci_class",
                        type="select",
                        name="CI 类型",
                        default="cmdb_ci_server",
                        attrs={
                            "options": [
                                {"label": "服务器 (Server)", "value": "cmdb_ci_server"},
                                {"label": "网络设备 (Network)", "value": "cmdb_ci_network"},
                                {"label": "数据库 (Database)", "value": "cmdb_ci_database"},
                                {"label": "应用 (Application)", "value": "cmdb_ci_app"},
                                {"label": "存储 (Storage)", "value": "cmdb_ci_storage"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="ip_address",
                        type="input",
                        name="IP 地址",
                        attrs={"placeholder": "按 IP 查询（可选）"},
                    ),
                ],
            ),
            FormItem(
                tag_code="max_results",
                type="int",
                name="最大结果数",
                default=10,
                attrs={"min": 1, "max": 100},
            ),
        ]

    def execute(self, instance_url: str, username: str, password: str,
                ci_name: str = "", ci_class: str = "cmdb_ci_server",
                ip_address: str = "", max_results: int = 10, **kwargs) -> dict:
        # 占位实现 — 集成实际 ServiceNow API 调用
        try:
            # TODO: 使用 requests 调用 ServiceNow CMDB REST API
            # params = {"sysparm_limit": max_results, "class": ci_class}
            # if ci_name:
            #     params["name"] = ci_name
            # if ip_address:
            #     params["ip_address"] = ip_address
            # resp = requests.get(f"{instance_url}/api/now/cmdb/instance/{ci_class}", params=params, ...)

            results = [
                {
                    "sys_id": "ci001",
                    "name": ci_name or "web-server-01",
                    "class": ci_class,
                    "ip_address": ip_address or "10.0.0.1",
                    "status": "Online",
                    "operational_status": "Operational",
                },
            ]

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "ci_class": ci_class,
                    "total": len(results),
                    "results": results,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
