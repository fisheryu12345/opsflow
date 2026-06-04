# -*- coding: utf-8 -*-
"""Neo4j database client — 统一连接管理

提供全局 graph_driver 实例和便捷函数。
所有 CMDB 服务层通过此模块访问 Neo4j。
"""

import logging
from contextlib import contextmanager

from django.conf import settings
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 驱动单例管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
        return cls._instance

    def initialize(self):
        """初始化驱动连接池"""
        if self._driver is not None:
            return
        protocol = getattr(settings, 'NEO4J_PROTOCOL', 'bolt')
        host = getattr(settings, 'NEO4J_HOST', 'localhost')
        port = getattr(settings, 'NEO4J_PORT', 7687)
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'password')

        self._driver = GraphDatabase.driver(
            f"{protocol}://{host}:{port}",
            auth=(user, password),
            max_connection_lifetime=3600,
            connection_acquisition_timeout=60,
        )
        logger.info(f"Neo4j 驱动已初始化: {protocol}://{user}@{host}:{port}")

    @property
    def driver(self):
        if self._driver is None:
            self.initialize()
        return self._driver

    def close(self):
        """关闭驱动"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j 驱动已关闭")

    @contextmanager
    def session(self):
        """获取会话上下文"""
        if self._driver is None:
            self.initialize()
        with self._driver.session() as session:
            yield session


# 全局单例
graph_driver = Neo4jClient()
