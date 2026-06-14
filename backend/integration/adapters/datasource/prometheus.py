# -*- coding: utf-8 -*-
"""Prometheus datasource connector adapter for Integration Hub

通过 Prometheus HTTP API 查询指标数据，作为 Integration Hub 的标准连接器。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from ..base import BaseConnector, HealthResult

logger = logging.getLogger(__name__)


class PrometheusConnector(BaseConnector):
    """Prometheus 数据源连接器适配器"""

    def __init__(self, instance):
        super().__init__(instance)
        self.api_url = self.config.get('api_url', 'http://localhost:9090').rstrip('/')
        self.timeout = self.config.get('timeout', 10)
        self._session: Optional[requests.Session] = None

    # ---- BaseConnector abstract methods ----

    def health_check(self) -> HealthResult:
        """检查 Prometheus API 可达性 - GET /api/v1/status/config"""
        session = self._get_session()
        try:
            resp = session.get(f'{self.api_url}/api/v1/status/config', timeout=self.timeout)
            if resp.status_code == 200:
                return HealthResult(is_healthy=True, message='Prometheus API reachable')
            return HealthResult(is_healthy=False, message=f'Status: {resp.status_code}')
        except requests.RequestException as e:
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self) -> Any:
        """返回内部 requests.Session (Prometheus 无官方 SDK)"""
        return self._get_session()

    # ---- Prometheus-specific query methods ----

    def query(self, query_text: str, time: Optional[float] = None) -> list:
        """即时查询 - GET /api/v1/query

        :param query_text: PromQL 查询语句
        :param time: 可选，UNIX 时间戳
        :return: 解析后的 result 列表
        """
        session = self._get_session()
        params = {'query': query_text}
        if time is not None:
            params['time'] = time

        try:
            resp = session.get(f'{self.api_url}/api/v1/query', params=params,
                               timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Prometheus instant query failed: {e}")
            return []

        if data.get('status') == 'success':
            return data.get('data', {}).get('result', [])
        logger.warning("Prometheus query returned status: %s", data.get('status'))
        return []

    def query_range(self, query_text: str, start: float, end: float,
                    step: float) -> list:
        """范围查询 - GET /api/v1/query_range

        :param query_text: PromQL 查询语句
        :param start: 起始 UNIX 时间戳
        :param end: 结束 UNIX 时间戳
        :param step: 步长（秒）
        :return: 解析后的 result 列表
        """
        session = self._get_session()
        params = {
            'query': query_text,
            'start': start,
            'end': end,
            'step': step,
        }

        try:
            resp = session.get(f'{self.api_url}/api/v1/query_range', params=params,
                               timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Prometheus range query failed: {e}")
            return []

        if data.get('status') == 'success':
            return data.get('data', {}).get('result', [])
        logger.warning("Prometheus range query returned status: %s", data.get('status'))
        return []

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
