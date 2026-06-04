# -*- coding: utf-8 -*-
from __future__ import annotations

"""AssociationService — 实例关联管理（纯 Cypher 驱动）

对标 bk-cmdb 的三级关联体系中的实例关联 (InstAsst) 层。
关联类型 (Relationship Type) 取自 AssociationType.asst_id。
"""

import logging
from datetime import datetime
from uuid import uuid4

from django.core.exceptions import ValidationError

from ..models.association import AssociationType, ModelAssociation
from .neo4j_client import graph_driver

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


class AssociationService:
    """实例关联管理"""

    # ─── 创建/删除关系 ───

    def create_relation(self, src_id: str, dst_id: str,
                        asst_type_id: str) -> dict:
        """
        创建实例间关联

        Args:
            src_id: 源实例 instance_id
            dst_id: 目标实例 instance_id
            asst_type_id: AssociationType.asst_id（如 'CONTAINS'）

        Returns:
            关系数据 dict
        """
        # 验证关联类型存在
        asst_type = AssociationType.objects.filter(asst_id=asst_type_id).first()
        if not asst_type:
            raise ValidationError(f"关联类型 '{asst_type_id}' 不存在")

        rel_id = str(uuid4())
        now = _now_iso()

        cypher = (
            "MATCH (src {instance_id: $src_id}) "
            "MATCH (dst {instance_id: $dst_id}) "
            f"CREATE (src)-[r:{asst_type_id} {{"
            "  rel_id: $rel_id, "
            "  __asst_type: $asst_type, "
            "  __created_at: $now, "
            "  src_model: src.__model_code, "
            "  dst_model: dst.__model_code "
            "}}]->(dst) "
            "RETURN r, src.__model_code as src_model, "
            "       dst.__model_code as dst_model"
        )

        with graph_driver.session() as session:
            result = session.run(
                cypher,
                src_id=src_id, dst_id=dst_id,
                rel_id=rel_id, asst_type=asst_type_id, now=now,
            )
            record = result.single()
            if not record:
                raise ValidationError("创建关联失败：源或目标节点不存在")

            rel = record['r']
            logger.info(f"创建关联 {asst_type_id}: {src_id} → {dst_id}")
            return self._rel_to_dict(rel, asst_type_id)

    def delete_relation(self, rel_id: str) -> bool:
        """按 rel_id 删除关系"""
        cypher = (
            "MATCH ()-[r {rel_id: $rel_id}]->() "
            "DELETE r "
            "RETURN count(r) as deleted"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, rel_id=rel_id)
            record = result.single()
            deleted = record['deleted'] if record else 0
            if deleted:
                logger.info(f"删除关联: {rel_id}")
            return bool(deleted)

    # ─── 查询关系 ───

    def list_relations(self, instance_id: str = None,
                       asst_type: str = None,
                       src_model: str = None, dst_model: str = None,
                       page: int = 1, page_size: int = 20) -> dict:
        """按条件查询实例关联"""
        params = {
            'skip': (page - 1) * page_size,
            'limit': page_size,
        }
        where_clauses = []

        if instance_id:
            where_clauses.append(
                "(src.instance_id = $inst_id OR dst.instance_id = $inst_id)"
            )
            params['inst_id'] = instance_id
        if asst_type:
            where_clauses.append("r.__asst_type = $asst_type")
            params['asst_type'] = asst_type

        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

        # 查询关联
        cypher = (
            "MATCH (src)-[r]->(dst) "
            f"WHERE {where_sql} "
            "RETURN r, src.__model_code as src_model, "
            "       dst.__model_code as dst_model, "
            "       src.instance_id as src_id, "
            "       dst.instance_id as dst_id "
            "SKIP $skip LIMIT $limit"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, **params)
            items = []
            for record in result:
                items.append({
                    'rel_id': record['r'].get('rel_id'),
                    'asst_type': record['r'].get('__asst_type'),
                    'src_id': record['src_id'],
                    'dst_id': record['dst_id'],
                    'src_model': record['src_model'],
                    'dst_model': record['dst_model'],
                    'created_at': record['r'].get('__created_at'),
                })

        # 查询总数
        count_cypher = (
            "MATCH (src)-[r]->(dst) "
            f"WHERE {where_sql} "
            "RETURN count(r) as total"
        )
        count_params = {k: v for k, v in params.items()
                        if k not in ('skip', 'limit')}
        with graph_driver.session() as session:
            result = session.run(count_cypher, **count_params)
            total = result.single()['total'] if result else 0

        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def get_neighbors(self, instance_id: str, direction: str = 'out',
                      max_depth: int = 1,
                      asst_types: list[str] = None) -> dict:
        """获取邻接节点（图遍历）

        Args:
            instance_id: 起始节点
            direction: out / in / both
            max_depth: 遍历深度
            asst_types: 限定关系类型列表

        Returns:
            {nodes: [...], edges: [...]}
        """
        dir_map = {'out': '->', 'in': '<-', 'both': '-'}
        dir_sym = dir_map.get(direction, '->')

        type_filter = ''
        if asst_types:
            type_filter = ':' + '|'.join(asst_types)

        cypher = (
            "MATCH (n {instance_id: $id}) "
            f"MATCH path = (n)-[r{type_filter}*1..{max_depth}]{dir_sym}(neighbor) "
            "RETURN neighbor, [rel IN r | rel.__asst_type] as rel_types, "
            "       length(path) as depth "
            "ORDER BY depth"
        )

        seen_nodes = {}
        edges = []

        with graph_driver.session() as session:
            result = session.run(cypher, id=instance_id)
            for record in result:
                node = record['neighbor']
                nid = node.get('instance_id')
                if nid and nid not in seen_nodes:
                    seen_nodes[nid] = dict(node)
                edges.append({
                    'src': instance_id,
                    'dst': nid,
                    'types': record['rel_types'],
                    'depth': record['depth'],
                })

        return {
            'nodes': list(seen_nodes.values()),
            'edges': edges,
        }

    # ─── 内部工具 ───

    def _rel_to_dict(self, rel, asst_type_id: str = None) -> dict:
        return {
            'rel_id': rel.get('rel_id'),
            'asst_type': asst_type_id or rel.get('__asst_type'),
            'created_at': rel.get('__created_at'),
            'src_model': rel.get('src_model'),
            'dst_model': rel.get('dst_model'),
        }
