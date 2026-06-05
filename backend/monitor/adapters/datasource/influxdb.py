# -*- coding: utf-8 -*-
"""InfluxDB DataSource adapter

通过 InfluxDB HTTP API (v1/v2) 查询指标数据。
"""

import logging
from datetime import datetime, timedelta

import requests

from .. import BaseDataSourceAdapter, MetricValue, HealthResult

logger = logging.getLogger(__name__)
FSM = 'influxdb_adapter'


class InfluxdbDataSource(BaseDataSourceAdapter):
    """InfluxDB 数据源适配器 (兼容 v1 + v2)"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.url = config.get('url', 'http://localhost:8086').rstrip('/')
        self.version = config.get('version', 'v1')
        self.database = config.get('database', 'telegraf')
        self.org = config.get('org', '')
        self.token = config.get('token', '')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.timeout = config.get('timeout', 30)

    def fetch_metrics(self, query_config: dict) -> list:
        query = query_config.get('influxql', query_config.get('promql', ''))
        if not query:
            query = f'SELECT * FROM "{query_config.get("metric_id", "")}"'
        time_range = query_config.get('time_range', 300)

        if self.version == 'v2':
            return self._query_v2(query, time_range)
        return self._query_v1(query, time_range)

    def _query_v1(self, query: str, time_range: int) -> list:
        params = {'db': self.database, 'q': query}
        auth = (self.username, self.password) if self.username else None
        try:
            resp = requests.get(
                f'{self.url}/query', params=params, auth=auth,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"InfluxDB v1 query failed: {e}")
            return []

        results = []
        for series in data.get('results', [{}])[0].get('series', []):
            columns = series.get('columns', [])
            name = series.get('name', '')
            tags = series.get('tags', {})
            for row in series.get('values', []):
                ts = row[0] if row else 0
                for i, col in enumerate(columns):
                    if col != 'time' and i < len(row) and row[i] is not None:
                        try:
                            results.append(MetricValue(
                                metric=f'{name}.{col}',
                                value=float(row[i]),
                                timestamp=datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp() if isinstance(ts, str) else float(ts),
                                tags={**tags, 'column': col},
                            ))
                        except (ValueError, TypeError, AttributeError):
                            continue
        return results

    def _query_v2(self, query: str, time_range: int) -> list:
        headers = {'Authorization': f'Token {self.token}'} if self.token else {}
        params = {'org': self.org}
        try:
            resp = requests.post(
                f'{self.url}/api/v2/query',
                headers=headers, params=params,
                json={'query': query, 'type': 'flux'},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.text
        except requests.RequestException as e:
            logger.error(f"InfluxDB v2 query failed: {e}")
            return []
        return []

    def health_check(self) -> HealthResult:
        try:
            if self.version == 'v2':
                resp = requests.get(f'{self.url}/health', timeout=10)
            else:
                resp = requests.get(f'{self.url}/ping', timeout=10)
            if resp.status_code < 300:
                return HealthResult(is_healthy=True, message='InfluxDB reachable')
            return HealthResult(is_healthy=False, message=f'Status: {resp.status_code}')
        except requests.RequestException as e:
            return HealthResult(is_healthy=False, message=str(e))
