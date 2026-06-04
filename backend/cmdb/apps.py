# -*- coding: utf-8 -*-
"""AppConfig for cmdb app

在 ready() 中初始化 Neo4j 驱动连接池（纯 Cypher 模式），
不再使用 neomodel。
"""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CmdbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cmdb'
    verbose_name = 'CMDB 配置管理'

    def ready(self):
        """应用启动时初始化 Neo4j 驱动"""
        try:
            from .services.neo4j_client import graph_driver
            graph_driver.initialize()
            logger.info("Neo4j 驱动连接池已初始化")
        except Exception as e:
            logger.warning(f"Neo4j 未就绪，跳过初始化: {e}")
