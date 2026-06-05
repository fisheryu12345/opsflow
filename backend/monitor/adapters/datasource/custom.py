# -*- coding: utf-8 -*-
"""Custom DataSource adapter stub — 自建采集数据源适配器"""

from .. import BaseDataSourceAdapter, MetricValue, HealthResult


class CustomDataSource(BaseDataSourceAdapter):
    """自定义数据源适配器 — 由自建采集插件推流的数据"""

    def fetch_metrics(self, query_config: dict) -> list:
        # 从本地存储/缓存查询最近的自定义指标
        return []

    def health_check(self) -> HealthResult:
        return HealthResult(is_healthy=True, message='Custom data source ready')
