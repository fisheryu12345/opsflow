"""ServiceNow CMDB CI 查询"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServiceNowGetCmbdCiPlugin(BasePlugin):
    name = "ServiceNow CMDB 查询"
    name_en = "ServiceNow CMDB Query"
    code = "servicenow_get_cmdb_ci"
    group = "ServiceNow"
    version = "v1.0"
    description = "通过 REST API 查询 ServiceNow CMDB 配置项（CI）"
    description_en = "Query ServiceNow CMDB configuration items via REST API"
    risk_level = "medium"
    icon = "Search"
    color = "#1890FF"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="ServiceNow 连接",
                name_en="ServiceNow Connection",
                tag_code="sn_connection",
                items=[
                    FormItem(
                        tag_code="instance_url",
                        type="input",
                        name="实例地址",
                        name_en="Instance URL",
                        attrs={"placeholder": "https://your-instance.service-now.com", "placeholder_en": "https://your-instance.service-now.com"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="username",
                        type="input",
                        name="用户名",
                        name_en="Username",
                        attrs={"placeholder": "admin", "placeholder_en": "admin"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="password",
                        type="input",
                        name="密码",
                        name_en="Password",
                        attrs={"placeholder": "********", "placeholder_en": "********", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormGroup(
                name="查询条件",
                name_en="Query Conditions",
                tag_code="query_conditions",
                items=[
                    FormItem(
                        tag_code="ci_class",
                        type="select",
                        name="CI 类型",
                        name_en="CI Class",
                        attrs={
                            "options": [
                                {"label": "服务器 (cmdb_ci_server)", "value": "cmdb_ci_server"},
                                {"label": "网络设备 (cmdb_ci_network)", "value": "cmdb_ci_network"},
                                {"label": "存储设备 (cmdb_ci_storage)", "value": "cmdb_ci_storage"},
                                {"label": "数据库 (cmdb_ci_database)", "value": "cmdb_ci_database"},
                                {"label": "应用 (cmdb_ci_app)", "value": "cmdb_ci_app"},
                                {"label": "虚拟机 (cmdb_ci_vm)", "value": "cmdb_ci_vm"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="query_filter",
                        type="input",
                        name="过滤条件",
                        name_en="Query Filter",
                        attrs={"placeholder": "nameLIKEweb^status=1", "placeholder_en": "nameLIKEweb^status=1"},
                    ),
                    FormItem(
                        tag_code="limit",
                        type="int",
                        name="返回数量",
                        name_en="Limit",
                        default=10,
                        attrs={"min": 1, "max": 100},
                    ),
                ],
            ),
        ]

    def execute(self, instance_url: str, username: str, password: str,
                ci_class: str = "", query_filter: str = "", limit: int = 10,
                **kwargs) -> dict:
        try:
            import requests
            from requests.auth import HTTPBasicAuth

            url = f"{instance_url.rstrip('/')}/api/now/table/{ci_class or 'cmdb_ci'}"
            headers = {"Accept": "application/json"}
            params = {
                "sysparm_limit": min(max(limit, 1), 100),
                "sysparm_display_value": "true",
            }
            if query_filter:
                params["sysparm_query"] = query_filter

            resp = requests.get(url, auth=HTTPBasicAuth(username, password),
                                headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "ci_class": ci_class or "cmdb_ci",
                    "total": len(data.get("result", [])),
                    "results": data.get("result", []),
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_url", "type": "string", "description": "实例地址", "description_en": "ServiceNow instance URL"},
            {"name": "ci_class", "type": "string", "description": "CI 类型", "description_en": "CI class"},
            {"name": "total", "type": "int", "description": "结果总数", "description_en": "Total result count"},
            {"name": "results", "type": "array", "description": "CI 列表", "description_en": "List of configuration items"},
        ]
