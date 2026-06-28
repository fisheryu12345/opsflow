"""HTTP API 调用 — 发送 HTTP 请求到目标 API"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class HttpApiPlugin(BasePlugin):
    name = "HTTP API 调用"
    code = "http_api"
    group = "HTTP"
    description = "发送 HTTP 请求到指定 URL，支持 GET/POST/PUT/DELETE"
    description_en = "Call HTTP API endpoints with custom URL, method, headers and body"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="url",
                type="input",
                name="请求地址",
                attrs={"placeholder": "https://api.example.com/endpoint"},
                validation=[ValidationRule(type="required")],
                col=12,
            ),
            FormItem(
                tag_code="method",
                type="select",
                name="请求方法",
                default="GET",
                attrs={
                    "options": [
                        {"label": "GET", "value": "GET"},
                        {"label": "POST", "value": "POST"},
                        {"label": "PUT", "value": "PUT"},
                        {"label": "DELETE", "value": "DELETE"},
                    ],
                },
                col=6,
            ),
            FormItem(
                tag_code="timeout",
                type="int",
                name="超时(秒)",
                default=30,
                attrs={"min": 1, "max": 120},
                col=6,
            ),
            FormItem(
                tag_code="headers",
                type="textarea",
                name="请求头(JSON)",
                attrs={"rows": 3, "placeholder": '{"Content-Type": "application/json"}'},
            ),
            FormItem(
                tag_code="body",
                type="code_editor",
                name="请求体",
                attrs={"language": "json", "height": "150px"},
            ),
        ]

    def execute(self, url: str, method: str = "GET", timeout: int = 30,
                headers: str = "", body: str = "", **kwargs) -> dict:
        import json
        try:
            import requests
            hdrs = json.loads(headers) if headers else {}
            hdrs.setdefault("User-Agent", "OpsFlow/1.0")
            data = json.loads(body) if body and method in ("POST", "PUT") else None

            resp = requests.request(
                method=method, url=url, headers=hdrs,
                json=data, timeout=timeout,
            )
            return {
                "success": resp.ok,
                "data": {
                    "status_code": resp.status_code,
                    "response": resp.text[:10000],
                    "headers": dict(resp.headers),
                },
                "error": "" if resp.ok else f"HTTP {resp.status_code}: {resp.reason}",
            }
        except ImportError:
            return {"success": False, "data": {}, "error": "缺少 requests 库"}
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
