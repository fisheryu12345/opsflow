# -*- coding: utf-8 -*-
"""AppConfig for cmdb app"""

import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class CmdbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cmdb'
    verbose_name = 'CMDB 配置管理'

    def ready(self):
        """应用启动时初始化 neomodel Neo4j 连接"""
        try:
            from neomodel import config as neomodel_config
            protocol = getattr(settings, 'NEO4J_PROTOCOL', 'bolt')
            host = getattr(settings, 'NEO4J_HOST', 'localhost')
            port = getattr(settings, 'NEO4J_PORT', 7687)
            user = getattr(settings, 'NEO4J_USER', 'neo4j')
            password = getattr(settings, 'NEO4J_PASSWORD', 'password')

            neomodel_config.DATABASE_URL = f"{protocol}://{user}:{password}@{host}:{port}"
            logger.info(f"Neo4j 连接已配置: {protocol}://{user}@{host}:{port}")
        except Exception as e:
            logger.warning(f"Neo4j 未就绪，跳过连接初始化: {e}")
