# -*- coding: utf-8 -*-
"""Prometheus DataSource adapter

通过 Prometheus HTTP API 查询指标数据。
配置参数通过 Integration Hub ConnectorInstance 管理。
"""

import logging
from datetime import datetime, timedelta

import requests

from .. import BaseDataSourceAdapter, MetricValue, HealthResult

logger = logging.getLogger(__name__)
FSM = 'prometheus_adapter'


class PrometheusDataSource(BaseDataSourceAdapter):
    """Prometheus 数据源适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get('url', 'http://localhost:9090').rstrip('/')
        self.timeout = config.get('timeout', 30)
        self.auth_token = config.get('auth_token', '')
        self._session = None

    def _get_session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.timeout = self.timeout
            if self.auth_token:
                self._session.headers['Authorization'] = f'Bearer {self.auth_token}'
        return self._session

    def fetch_metrics(self, query_config: dict) -> list:
        """
        查询 Prometheus 指标
        query_config:
            - promql: 查询语句 (如 'cpu_usage{instance="..."}')
            - time_range: 查询时间范围(秒), default 300
            - step: 步长(秒), default 15
        """
        session = self._get_session()
        promql = query_config.get('promql', query_config.get('metric_id', ''))
        time_range = query_config.get('time_range', 300)
        step = query_config.get('step', 15)

        now = datetime.now()
        params = {
            'query': promql,
            'start': (now - timedelta(seconds=time_range)).timestamp(),
            'end': now.timestamp(),
            'step': step,
        }

        try:
            resp = session.get(f'{self.base_url}/api/v1/query_range', params=params)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Prometheus query failed: {e}")
            return []

        results = []
        if data.get('status') == 'success':
            for result in data.get('data', {}).get('result', []):
                metric = result.get('metric', {})
                values = result.get('values', [])
                for ts, val in values:
                    try:
                        results.append(MetricValue(
                            metric=metric.get('__name__', promql),
                            value=float(val),
                            timestamp=float(ts),
                            tags=metric,
                        ))
                    except (ValueError, TypeError):
                        continue
        return results

    def query_instant(self, promql: str) -> list:
        """即时查询"""
        session = self._get_session()
        try:
            resp = session.get(f'{self.base_url}/api/v1/query', params={'query': promql})
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Prometheus instant query failed: {e}")
            return []
        results = []
        if data.get('status') == 'success':
            for result in data.get('data', {}).get('result', []):
                metric = result.get('metric', {})
                val = result.get('value', [None, None])
                try:
                    results.append(MetricValue(
                        metric=metric.get('__name__', promql),
                        value=float(val[1]),
                        timestamp=float(val[0]),
                        tags=metric,
                    ))
                except (ValueError, TypeError):
                    continue
        return results

    def health_check(self) -> HealthResult:
        session = self._get_session()
        try:
            resp = session.get(f'{self.base_url}/api/v1/targets', timeout=10)
            if resp.status_code == 200:
                return HealthResult(is_healthy=True, message='Prometheus API reachable')
            return HealthResult(is_healthy=False, message=f'Status: {resp.status_code}')
        except requests.RequestException as e:
            return HealthResult(is_healthy=False, message=str(e))

    def list_metrics(self) -> list:
        """列出所有指标名"""
        session = self._get_session()
        try:
            resp = session.get(f'{self.base_url}/api/v1/label/__name__/values')
            resp.raise_for_status()
            data = resp.json()
            if data.get('status') == 'success':
                return data.get('data', [])
        except requests.RequestException as e:
            logger.error(f"Prometheus list metrics failed: {e}")
        return []
