"""Ansible Tower — HTTP 客户端层"""
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from opsflow.core.tower.base import TowerConfigError

logger = logging.getLogger(__name__)


class TowerClientMixin:
    """Tower HTTP 客户端 — 配置加载、Session 管理、统一请求"""

    _session: Optional[requests.Session] = None
    _config: Optional[dict] = None

    def _load_config(self):
        """从 Django settings / env 加载 Tower 配置"""
        try:
            from conf.env import (
                ANSIBLE_API_URL, ANSIBLE_API_TOKEN,
                ANSIBLE_TEMPLATE_ID, ANSIBLE_VERIFY_SSL,
            )
            self._config = {
                "url": (ANSIBLE_API_URL or "").rstrip("/"),
                "token": ANSIBLE_API_TOKEN or "",
                "template_id": ANSIBLE_TEMPLATE_ID or 1,
                "verify_ssl": bool(ANSIBLE_VERIFY_SSL) if "ANSIBLE_VERIFY_SSL" in dir() else False,
            }
        except (ImportError, AttributeError):
            self._config = {
                "url": "",
                "token": "",
                "template_id": 1,
                "verify_ssl": False,
            }

    def _get_session(self) -> requests.Session:
        """获取可复用的 requests Session（含重试）"""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = (self._config["token"], "") if self._config["token"] else None
            self._session.headers.update({
                "Content-Type": "application/json",
            })
            adapter = requests.adapters.HTTPAdapter(
                max_retries=requests.packages.urllib3.util.retry.Retry(
                    total=2, backoff_factor=0.5,
                    allowed_methods=["GET", "POST"],
                )
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        return self._session

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """统一的 Tower API 请求"""
        url = urljoin(self._config["url"] + "/", path.lstrip("/"))
        session = self._get_session()
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("verify", self._config["verify_ssl"])

        if self._config["token"]:
            kwargs.setdefault("headers", {})
            kwargs["headers"].setdefault("Authorization", f"Bearer {self._config['token']}")

        resp = session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def is_configured(self) -> bool:
        """Tower 是否已配置（URL 非空且非 localhost）"""
        url = self._config.get("url", "")
        return bool(url) and "localhost" not in url
