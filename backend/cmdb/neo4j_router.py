# -*- coding: utf-8 -*-
"""Django database router for Neo4j dual datasource

MySQL → Django ORM (默认数据库，存模型定义、权限、审计)
Neo4j → neomodel (存 CMDB 节点实例、拓扑关系)

Neo4j 配置通过 neomodel.config 全局初始化 (在 apps.py ready 或 settings 中)
"""

NEO4J_DB = 'neo4j'  # database router label


class CmdbNeo4jRouter:
    """
    Django 多数据库路由
    cmdb 中的 Neo4j 节点模型（以 'Neo4j' 结尾的模型名）路由到 neo4j 数据库。
    其他模型使用默认 MySQL 数据库。
    """

    route_app_labels = {'cmdb'}

    def db_for_read(self, model, **hints):
        """Neo4j base models → neo4j db, others → default"""
        if model.__name__ in ('ModelDefinition', 'ModelField'):
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model.__name__ in ('ModelDefinition', 'ModelField'):
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'cmdb':
            if model_name in ('modeldefinition', 'modelfield'):
                return db == 'default'
            # Neo4j models are not migrated by Django
            return db == 'default'
        return None
