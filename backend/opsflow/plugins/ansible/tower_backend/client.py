"""Ansible Tower — HTTP 客户端层"""
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from opsflow.plugins.ansible.tower_backend.base import TowerConfigError

logger = logging.getLogger(__name__)


class TowerClientMixin:
    """Tower HTTP 客户端 — 配置加载、Session 管理、统一请求"""

    _session: Optional[requests.Session] = None
    _config: Optional[dict] = None

    def _load_config(self):
        """从集成中心 AWX 连接器加载 Tower 配置"""
        cfg = self._load_config_from_integration()
        if not cfg:
            raise TowerConfigError(
                "AWX 连接器未配置。请先在集成中心创建 awx 连接器实例并添加 Token 凭证。"
            )
        self._config = cfg

    def _load_config_from_integration(self) -> Optional[dict]:
        """从集成中心 AWX 连接器加载配置"""
        try:
            from integration.models.connector import ConnectorInstance
            from integration.models.credential import ConnectorCredential
            from integration.services.credential_service import decrypt_credential

            inst = ConnectorInstance.objects.filter(
                definition__code='awx', is_active=True
            ).order_by('-id').first()
            if not inst:
                return None

            cfg = inst.config or {}
            token = ""
            cred = ConnectorCredential.objects.filter(
                instance=inst, cred_type__in=['token', 'password', 'custom']
            ).first()
            if cred:
                token = decrypt_credential(cred.encrypted_value) or ""

            return {
                "url": (cfg.get('url') or cfg.get('api_url') or '').rstrip("/"),
                "token": token,
                "template_id": int(cfg.get('template_id', 1)),
                "verify_ssl": bool(cfg.get('verify_ssl', False)),
            }
        except Exception as e:
            logger.warning("Failed to load AWX config from Integration Hub: %s", e)
            return None

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
