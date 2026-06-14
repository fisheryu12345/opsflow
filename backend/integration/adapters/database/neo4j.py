# -*- coding: utf-8 -*-
"""Neo4j 图数据库连接器适配器

通过集成中心管理 Neo4j 连接配置和凭证，代替 settings 直接配置。
"""

import logging
from typing import Optional

from integration.adapters.base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class Neo4jConnector(BaseConnector):
    """
    Neo4j 图数据库连接器

    配置项 (config):
        host: 主机地址 (默认 127.0.0.1)
        port: 端口 (默认 7687)
        protocol: 协议 (默认 bolt)

    凭证 (credential):
        cred_type='password': password 为数据库密码，user 从 config 读取
        cred_type='custom': encrypted_value 为 JSON {"user": "...", "password": "..."}
    """

    def __init__(self, instance):
        super().__init__(instance)
        self._credential = None

    def _load_credential(self) -> Optional[dict]:
        """从凭证明文存储中加载 (user, password)"""
        if self._credential:
            return self._credential
        try:
            from integration.models.credential import ConnectorCredential
            from integration.services.credential_service import decrypt_credential

            cred = ConnectorCredential.objects.filter(
                instance=self.instance,
                cred_type__in=['password', 'custom'],
            ).first()
            if not cred:
                return None

            decrypted = decrypt_credential(cred.encrypted_value)

            if cred.cred_type == 'custom':
                import json
                data = json.loads(decrypted)
                self._credential = {
                    'user': data.get('user', self.config.get('user', 'neo4j')),
                    'password': data.get('password', decrypted),
                }
            else:
                self._credential = {
                    'user': self.config.get('user', 'neo4j'),
                    'password': decrypted,
                }
            return self._credential
        except Exception as e:
            logger.warning("[Neo4jConnector] Failed to load credential: %s", e)
            return None

    def get_client(self):
        """返回 neo4j.GraphDatabase.driver 实例"""
        if self._client:
            return self._client

        cred = self._load_credential()
        host = self.config.get('host', '127.0.0.1')
        port = self.config.get('port', 7687)
        protocol = self.config.get('protocol', 'bolt')
        uri = f"{protocol}://{host}:{port}"

        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("neo4j package not installed. Run: pip install neo4j")

        if cred:
            self._client = GraphDatabase.driver(
                uri, auth=(cred['user'], cred['password'])
            )
        else:
            self._client = GraphDatabase.driver(uri)
        return self._client

    def health_check(self) -> HealthResult:
        """连接 Neo4j 并执行 RETURN 1 检查连通性"""
        try:
            driver = self.get_client()
            with driver.session() as session:
                result = session.run("RETURN 1 AS ok")
                record = result.single()
                if record and record.get("ok") == 1:
                    return HealthResult(is_healthy=True, message="Neo4j connection OK")
                return HealthResult(is_healthy=False, message="Unexpected response")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        super().close()
