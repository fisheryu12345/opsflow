"""HTTP RESTful API 通用执行器 — 调用任意 HTTP API

executor_type: "http"
底层技术: requests (HTTP REST)

设计思路:
  与 ESXi/NetApp/Redfish 等专用执行器不同, HTTP 执行器是"万能适配器"。
  适用于对接没有专用执行器的第三方系统:
    - 监控系统 (Prometheus/Grafana API)
    - 告警平台 (飞书/钉钉/企微机器人 Webhook)
    - 内部自研平台
    - 云平台 API (AWS/GCP/Azure 无 SDK 时)

  注意事项:
    - 对用户暴露此执行器意味着任意 HTTP 请求能力, 需要权限控制
    - 建议将 executor_type=http 标记为高危, 并限制 target_hosts
    - credentials 走 Vault 而非 os.getenv
"""

import json
import logging
import os

import requests
from requests.auth import HTTPBasicAuth

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class HttpExecutor(BaseExecutor):
    """通用 HTTP RESTful API 执行器

    支持认证方式:
      - none: 无认证
      - basic: HTTP Basic Auth (从环境变量读取)
      - bearer: Bearer Token (从环境变量读取)
      - header: 自定义 Header (从 inputs 传入)
    """

    executor_type = "http"

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行 HTTP 请求

        必填参数:
          - method: GET/POST/PUT/PATCH/DELETE
          - url: 请求 URL

        可选参数:
          - headers: dict, 自定义请求头
          - body: dict, JSON body (GET/DELETE 忽略)
          - timeout: int, 超时秒数 (默认 30)
          - expected_status: list[int], 期望的状态码 (默认 [200, 201, 202, 204])
          - auth_type: "none" | "basic" | "bearer" | "header" (默认 "none")
          - response_jsonpath: str, JSONPath 提取响应字段 (可选)

        输出:
          - status_code: int
          - response_body: dict | list | str
          - response_headers: dict
          - extracted: any (如果指定了 response_jsonpath)
        """
        method = inputs.get("method", "GET").upper()
        url = inputs.get("url", "")
        headers = inputs.get("headers", {}) or {}
        body = inputs.get("body")
        timeout = inputs.get("timeout", 30)
        expected = inputs.get("expected_status", [200, 201, 202, 204])

        if not url:
            return ExecuteResult(False, {}, "缺少 url")

        # 认证
        auth = None
        auth_type = inputs.get("auth_type", "none")
        if auth_type == "basic":
            auth = HTTPBasicAuth(
                os.getenv("HTTP_API_USER", ""),
                os.getenv("HTTP_API_PASSWORD", ""),
            )
        elif auth_type == "bearer":
            token = os.getenv("HTTP_API_TOKEN", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        # 请求
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                auth=auth,
                timeout=timeout,
                verify=os.getenv("HTTP_API_VERIFY_SSL", "0") == "1",
            )

            # 解析响应
            try:
                response_body = resp.json()
            except (json.JSONDecodeError, ValueError):
                response_body = resp.text

            # 状态码校验
            if resp.status_code not in expected:
                error_msg = f"HTTP {resp.status_code}, expected {expected}"
                if isinstance(response_body, dict) and response_body.get("message"):
                    error_msg += f": {response_body['message']}"
                return ExecuteResult(False, {
                    "status_code": resp.status_code,
                    "response_body": response_body,
                    "response_headers": dict(resp.headers),
                }, error_msg)

            # 可选: JSONPath 提取 (简易点号路径)
            extracted = None
            jsonpath = inputs.get("response_jsonpath", "")
            if jsonpath and isinstance(response_body, (dict, list)):
                extracted = self._jsonpath_get(response_body, jsonpath)

            return ExecuteResult(True, {
                "status_code": resp.status_code,
                "response_body": response_body,
                "response_headers": dict(resp.headers),
                "extracted": extracted,
            })

        except requests.Timeout:
            return ExecuteResult(False, {}, f"HTTP 请求超时 (timeout={timeout}s)")
        except requests.ConnectionError:
            return ExecuteResult(False, {}, f"无法连接: {url}")
        except requests.RequestException as e:
            return ExecuteResult(False, {}, f"HTTP 请求失败: {e}")

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """HTTP 回滚 — 发送补偿请求

        设计: 如果 inputs 中有 rollback_url/rollback_method,
        则发送回滚请求; 否则发送相反的请求 (POST→DELETE, PUT→旧值)

        【待完善】
          - 幂等设计: 回滚请求需要考虑幂等性 (DELETE 可能已经成功)
          - 补偿事务: 复杂场景需要 Saga 模式
        """
        # 如果有显式的回滚请求定义
        rollback_url = inputs.get("rollback_url", "")
        rollback_method = inputs.get("rollback_method", "DELETE")

        if rollback_url:
            rb_inputs = dict(inputs)
            rb_inputs["url"] = rollback_url
            rb_inputs["method"] = rollback_method
            rb_inputs["body"] = inputs.get("rollback_body", inputs.get("body"))
            return self.execute(rb_inputs)

        # 自动回滚: POST → DELETE, PUT → 旧值
        method = inputs.get("method", "GET").upper()
        if method == "POST":
            rb_inputs = dict(inputs)
            rb_inputs["method"] = "DELETE"
            # 如果上下文中有关联 ID, 追加到 URL
            resource_id = context.get("id") or context.get("resource_id")
            if resource_id and not rb_inputs.get("url", "").endswith(resource_id):
                rb_inputs["url"] = rb_inputs["url"].rstrip("/") + f"/{resource_id}"
            return self.execute(rb_inputs)

        return ExecuteResult(False, {}, f"HTTP 无可用回滚策略 (method={method})")

    @staticmethod
    def _jsonpath_get(data, path: str):
        """简易点号路径提取, 例如 "data.items.0.id"

        完整 JSONPath 支持建议使用 jmespath 库
        """
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if 0 <= idx < len(current) else None
                except ValueError:
                    # list of dicts: 按 key 查找
                    current = [item for item in current if isinstance(item, dict) and item.get(part)]
                    if len(current) == 1:
                        current = current[0]
                    elif not current:
                        current = None
                    else:
                        return current  # 返回列表
            else:
                return None
            if current is None:
                break
        return current
