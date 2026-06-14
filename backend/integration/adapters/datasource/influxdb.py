# -*- coding: utf-8 -*-
"""InfluxDB datasource connector adapter for Integration Hub

通过 InfluxDB HTTP API (v2) 查询指标数据，作为 Integration Hub 的标准连接器。
从关联的 ConnectorCredential (type=token) 中读取 token。
"""

import logging
from typing import Any, Optional

import requests

from ..base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class InfluxdbConnector(BaseConnector):
    """InfluxDB 数据源连接器适配器 (v2 / Flux)"""

    def __init__(self, instance):
        super().__init__(instance)
        self.api_url = self.config.get('api_url', 'http://localhost:8086').rstrip('/')
        self.org = self.config.get('org', '')
        self.bucket = self.config.get('bucket', '')
        self.timeout = self.config.get('timeout', 10)
        self._token: Optional[str] = None
        self._session: Optional[requests.Session] = None

    # ---- BaseConnector abstract methods ----

    def health_check(self) -> HealthResult:
        """检查 InfluxDB API 可达性 - GET /health"""
        session = self._get_session()
        try:
            resp = session.get(f'{self.api_url}/health', timeout=self.timeout)
            if resp.status_code == 200:
                return HealthResult(is_healthy=True, message='InfluxDB API reachable')
            return HealthResult(is_healthy=False, message=f'Status: {resp.status_code}')
        except requests.RequestException as e:
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self) -> Any:
        """返回内部 requests.Session (InfluxDB v2 无官方 Python SDK 依赖)"""
        return self._get_session()

    # ---- InfluxDB-specific query methods ----

    def query(self, query_text: str) -> list:
        """Flux 查询 - POST /api/v2/query

        :param query_text: Flux 查询语句
        :return: 解析后的 CSV/JSON 结果列表
        """
        session = self._get_session()
        headers = {'Authorization': f'Token {self._get_token()}'}
        params = {'org': self.org}

        try:
            resp = session.post(
                f'{self.api_url}/api/v2/query',
                headers=headers, params=params,
                json={'query': query_text, 'type': 'flux', 'dialect': {'annotations': ['datatype', 'group', 'default']}},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"InfluxDB Flux query failed: {e}")
            return []

        # InfluxDB v2 returns CSV with annotation headers; parse into dict list
        return self._parse_csv_response(resp.text)

    def close(self):
        """释放请求 Session"""
        if self._session:
            self._session.close()
            self._session = None
        super().close()

    # ---- Internal helpers ----

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _get_token(self) -> str:
        """从 ConnectorCredential (type=token) 中获取 token

        优先使用 instance 关联的第一个 token 类型凭证；若未配置则回退到 config 中的 token 字段。
        """
        if self._token:
            return self._token

        # 尝试从关联凭证中读取
        if self.instance and hasattr(self.instance, 'credentials'):
            token_creds = self.instance.credentials.filter(cred_type='token')
            token_cred = token_creds.first()
            if token_cred:
                from integration.utils.crypto import decrypt_value
                self._token = decrypt_value(token_cred.encrypted_value)
                return self._token  # type: ignore[return-value]

        # 回退到 config 中的明文 token
        self._token = self.config.get('token', '')
        return self._token

    @staticmethod
    def _parse_csv_response(raw: str) -> list:
        """将 InfluxDB v2 Flux CSV 响应解析为 dict 列表

        CSV 格式：
          #datatype,string,long,dateTime:RFC3339,double
          #group,false,false,true,false
          #default,_result,,,,,
          ,result,table,_time,_value
          ,_result,0,2024-01-01T00:00:00Z,42.0

        返回: [{'table': 0, '_time': '...', '_value': 42.0}, ...]
        """
        import csv
        import io

        lines = [line for line in raw.splitlines() if line.strip() and not line.startswith('#')]
        if not lines:
            return []

        reader = csv.DictReader(io.StringIO('\n'.join(lines)))
        results = []
        for row in reader:
            # 跳过完全为空的注释行
            cleaned = {k.strip(): v.strip() for k, v in row.items() if k and k.strip()}
            if cleaned:
                results.append(cleaned)
        return results
