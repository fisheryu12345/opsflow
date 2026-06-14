# -*- coding: utf-8 -*-
"""AWX / Ansible Tower connector adapter

通过 AWX REST API (v2) 管理作业模板的执行、状态查询与取消。
支持 Bearer Token 或 Basic Auth (username:password) 两种凭证类型。
"""

import logging
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class AWXConnector(BaseConnector):
    """
    AWX / Ansible Tower REST API v2 连接器适配器

    配置项 (config):
        api_url: AWX API 地址 (默认 https://localhost:8080/api/v2)
        verify_ssl: 是否验证 SSL 证书 (默认 false)
        timeout: 请求超时秒数 (默认 30)

    凭证 (credential):
        token 类型: 直接使用 Bearer Token
        password 类型: username:password 格式，使用 Basic Auth
    """

    def __init__(self, instance):
        super().__init__(instance)
        self._credential_value: Optional[str] = None
        self._session: Optional[requests.Session] = None

    # ------------------------------------------------------------------
    # Credential loading
    # ------------------------------------------------------------------

    def _load_credential(self) -> Optional[str]:
        """从 ConnectorCredential 解密加载凭证值

        支持两种凭证模式:
        1. token 类型 — 值直接作为 Bearer Token
        2. password 类型 — 值格式为 ``username:password``，用于 Basic Auth
        """
        if self._credential_value:
            return self._credential_value

        try:
            from integration.models.credential import ConnectorCredential
            cred = ConnectorCredential.objects.filter(
                instance=self.instance,
                cred_type__in=['token', 'password', 'custom'],
            ).first()
            if cred:
                from integration.services.credential_service import decrypt_credential
                self._credential_value = decrypt_credential(cred.encrypted_value)
                self._credential_type = cred.cred_type  # 'token' | 'password'
                return self._credential_value
        except Exception as e:
            logger.warning("[AWXConnector] Failed to load credential: %s", e)

        return None

    # ------------------------------------------------------------------
    # Session management (requests.Session + retry)
    # ------------------------------------------------------------------

    def _get_session(self) -> requests.Session:
        """获取可复用的 requests Session（含重试）"""
        if self._session is not None:
            return self._session

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
        })

        # Auth setup
        cred_value = self._load_credential()
        if cred_value:
            if getattr(self, '_credential_type', None) == 'password':
                parts = cred_value.split(":", 1)
                username = parts[0]
                password = parts[1] if len(parts) > 1 else ""
                self._session.auth = requests.auth.HTTPBasicAuth(username, password)
            else:
                # token / custom — use Bearer
                self._session.headers["Authorization"] = f"Bearer {cred_value}"

        # Retry adapter
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        return self._session

    # ------------------------------------------------------------------
    # Unified request helper
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """统一的 AWX API 请求

        :param method: HTTP 方法 (GET / POST / …)
        :param path:   API 路径，如 ``jobs/42/``
        :param kwargs: 透传给 ``requests.Session.request`` 的参数
        :return:       ``requests.Response``
        :raises requests.HTTPError: 非 2xx 状态码
        """
        api_url = self.config.get("api_url", "https://localhost:8080/api/v2").rstrip("/")
        url = urljoin(api_url + "/", path.lstrip("/"))
        session = self._get_session()

        kwargs.setdefault("timeout", int(self.config.get("timeout", 30)))
        kwargs.setdefault("verify", bool(self.config.get("verify_ssl", False)))

        resp = session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    def health_check(self) -> HealthResult:
        """检查 AWX API 是否可达 — GET /api/v2/me/ 或 /api/v2/ping/"""
        try:
            resp = self._request("GET", "me/")
            data = resp.json()
            username = data.get("results", [{}])[0].get("username", "") if "results" in data else data.get("username", "")
            return HealthResult(
                is_healthy=True,
                message=f"AWX reachable. Authenticated as '{username}'" if username else "AWX reachable.",
            )
        except Exception as e:
            # Fallback: try /ping/
            try:
                resp = self._request("GET", "ping/")
                ping = resp.json()
                return HealthResult(
                    is_healthy=True,
                    message=f"AWX reachable. Version {ping.get('version', 'unknown')}",
                )
            except Exception as fallback_e:
                return HealthResult(is_healthy=False, message=str(fallback_e))

    def get_client(self) -> Any:
        """返回内部 requests.Session 作为客户端"""
        return self._get_session()

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    def launch_job(self, template_id: int, extra_vars: Optional[dict] = None) -> dict:
        """启动 AWX Job Template

        :param template_id: Job Template ID
        :param extra_vars:  额外变量 (可选)，会被序列化为 JSON
        :return:            包含 job_id, status, url 的字典
        """
        import json as _json
        payload: dict = {}
        if extra_vars:
            payload["extra_vars"] = _json.dumps(extra_vars, ensure_ascii=False)

        resp = self._request("POST", f"job_templates/{template_id}/launch/", json=payload)
        result = resp.json()
        job_id = result.get("id") or result.get("job", 0)

        logger.info("[AWXConnector] Launched template=%s -> job_id=%s", template_id, job_id)
        return {
            "job_id": int(job_id) if job_id else 0,
            "status": result.get("status", "pending"),
            "url": result.get("url", ""),
            "related": result.get("related", {}),
        }

    def get_job_status(self, job_id: int) -> dict:
        """查询作业当前状态

        :return: 包含 status, started, finished, elapsed, failed 的字典
        """
        resp = self._request("GET", f"jobs/{job_id}/")
        job = resp.json()
        return {
            "status": job.get("status", "unknown"),
            "started": job.get("started", ""),
            "finished": job.get("finished", ""),
            "elapsed": job.get("elapsed", 0.0),
            "failed": job.get("failed", False),
            "result_stdout": job.get("result_stdout", ""),
        }

    def cancel_job(self, job_id: int) -> bool:
        """取消运行中的作业

        :return: True 表示取消请求已发出，False 表示失败
        """
        try:
            self._request("POST", f"jobs/{job_id}/cancel/")
            logger.info("[AWXConnector] Cancelled job_id=%s", job_id)
            return True
        except requests.RequestException as e:
            logger.warning("[AWXConnector] Cancel failed job_id=%s: %s", job_id, e)
            return False

    def get_job_stdout(self, job_id: int, max_length: int = 0) -> str:
        """获取作业标准输出 (txt 格式)

        :param job_id:     作业 ID
        :param max_length: 最大返回字符数 (0 表示不截断)
        :return:           标准输出文本
        """
        try:
            resp = self._request(
                "GET", f"jobs/{job_id}/stdout/",
                params={"format": "txt"},
            )
            text = resp.text
            if max_length and len(text) > max_length:
                return text[:max_length]
            return text
        except requests.RequestException as e:
            logger.warning("[AWXConnector] Get stdout failed job_id=%s: %s", job_id, e)
            return ""

    # ------------------------------------------------------------------
    # Resource cleanup
    # ------------------------------------------------------------------

    def close(self):
        """关闭 requests Session"""
        if self._session:
            self._session.close()
            self._session = None
        self._credential_value = None
        super().close()
