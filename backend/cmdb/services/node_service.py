# -*- coding: utf-8 -*-
from __future__ import annotations

"""NodeService — CMDB 节点统一 CRUD（纯 Cypher 驱动）

所有模型类型的实例通过此服务创建/查询/更新/删除。
内置模型与自定义模型使用同一套 Cypher 逻辑。
"""

import logging
from datetime import datetime
from uuid import uuid4

from django.core.exceptions import ValidationError

from ..models.model_definition import ModelDefinition
from .neo4j_client import graph_driver
from .validation_service import ValidationService

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


class NodeService:
    """统一节点 CRUD

    用法:
        svc = NodeService('Host')        # 通过 model_code
        svc.create({'ip': '10.0.0.1', 'hostname': 'web-01'})
        svc.list({'status': 'normal'}, page=1, page_size=20)
    """

    def __init__(self, model_code: str):
        self.model_code = model_code
        try:
            self.model_def = ModelDefinition.objects.get(code=model_code)
        except ModelDefinition.DoesNotExist:
            raise ValidationError(f"模型 '{model_code}' 不存在")

    def create(self, data: dict) -> dict:
        """创建节点"""
        validator = ValidationService(self.model_def)
        validated = validator.validate(data)

        props = dict(validated)
        props['instance_id'] = str(uuid4())
        props['__model_code'] = self.model_code
        props['__created_at'] = now_iso()
        props['__updated_at'] = now_iso()

        cypher = f"CREATE (n:{self.model_code} $props) RETURN n"

        with graph_driver.session() as session:
            result = session.run(cypher, props=props)
            node = result.single()[0]
            logger.info(f"创建 {self.model_code} 实例: {props.get('name', props.get('ip', props['instance_id']))}")
            return self._node_to_dict(node)

    def retrieve(self, instance_id: str) -> dict | None:
        """查询单个节点"""
        cypher = f"MATCH (n:{self.model_code} {{instance_id: $id}}) RETURN n"
        with graph_driver.session() as session:
            result = session.run(cypher, id=instance_id)
            record = result.single()
            if not record:
                return None
            return self._node_to_dict(record[0])

    def list(self, filters: dict = None, page: int = 1,
             page_size: int = 20, order_by: str = None) -> dict:
        """列表查询，支持字段过滤、分页、排序"""
        filters = filters or {}
        params = {'skip': (page - 1) * page_size, 'limit': page_size}

        where_clauses = []
        for k, v in filters.items():
            if v is not None:
                where_clauses.append(f"n.{k} = ${k}")
                params[k] = v

        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

        # 查询数据
        order_sql = f"n.{order_by}" if order_by else "n.__created_at"
        cypher = (
            f"MATCH (n:{self.model_code}) "
            f"WHERE {where_sql} "
            f"RETURN n ORDER BY {order_sql} "
            f"SKIP $skip LIMIT $limit"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, **params)
            items = [self._node_to_dict(r[0]) for r in result]

        # 查询总数
        count_cypher = (
            f"MATCH (n:{self.model_code}) "
            f"WHERE {where_sql} "
            f"RETURN count(n) as total"
        )
        with graph_driver.session() as session:
            count_result = session.run(count_cypher, **{
                k: v for k, v in params.items()
                if k not in ('skip', 'limit')
            })
            total = count_result.single()['total']

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        }

    def search(self, query: str, fields: list[str] = None,
               limit: int = 50) -> list[dict]:
        """模糊搜索 — 对指定字段做 CONTAINS 匹配"""
        if not fields:
            fields = ['name', 'ip', 'hostname', 'label']
        params = {'q': query.lower(), 'limit': limit}

        or_clauses = ' OR '.join(
            f"toLower(n.{f}) CONTAINS $q" for f in fields
        )
        cypher = (
            f"MATCH (n:{self.model_code}) "
            f"WHERE {or_clauses} "
            f"RETURN n LIMIT $limit"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, **params)
            return [self._node_to_dict(r[0]) for r in result]

    def update(self, instance_id: str, data: dict) -> dict | None:
        """更新节点属性"""
        validator = ValidationService(self.model_def)
        validated = validator.validate_update(data)

        if not validated:
            return self.retrieve(instance_id)

        validated['__updated_at'] = now_iso()

        cypher = (
            f"MATCH (n:{self.model_code} {{instance_id: $id}}) "
            f"SET n += $props "
            f"RETURN n"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, id=instance_id, props=validated)
            record = result.single()
            if not record:
                return None
            logger.info(f"更新 {self.model_code} 实例: {instance_id}")
            return self._node_to_dict(record[0])

    def delete(self, instance_id: str) -> bool:
        """删除节点及其所有关联关系"""
        cypher = (
            f"MATCH (n:{self.model_code} {{instance_id: $id}}) "
            f"DETACH DELETE n "
            f"RETURN count(n) as deleted"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, id=instance_id)
            record = result.single()
            deleted = record['deleted'] if record else 0
            if deleted:
                logger.info(f"删除 {self.model_code} 实例: {instance_id}")
            return bool(deleted)

    def _node_to_dict(self, node) -> dict:
        """将 Neo4j Node 转换为 Python dict"""
        data = dict(node)
        # 将 Neo4j 时间戳对象转字符串
        for k, v in data.items():
            if hasattr(v, 'iso_format'):
                data[k] = v.iso_format()
        return data
