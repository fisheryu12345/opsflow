# -*- coding: utf-8 -*-
from __future__ import annotations

"""TopologyService — 拓扑查询、影响分析、全局搜索（全 Cypher 驱动）

利用 Neo4j 原生图遍历能力实现高效的拓扑查询。
"""

import logging

from .neo4j_client import graph_driver

logger = logging.getLogger(__name__)


class TopologyService:
    """拓扑查询服务"""

    def get_tree(self, root_id: str, rel_types: list[str] = None,
                 max_depth: int = 5) -> dict:
        """以 root_id 为根展开子树

        返回嵌套的树结构，适用于前端的树形展示。
        """
        type_filter = ''
        if rel_types:
            type_filter = ':' + '|'.join(rel_types)

        cypher = (
            "MATCH path = (root {instance_id: $root_id}) "
            f"-[{type_filter}*0..{max_depth}]->(descendant) "
            "RETURN descendant, "
            "       [rel IN relationships(path) | type(rel)] as rel_chain, "
            "       length(path) as depth "
            "ORDER BY depth"
        )

        nodes = []
        with graph_driver.session() as session:
            result = session.run(cypher, root_id=root_id)
            for record in result:
                node = record['descendant']
                nodes.append({
                    'instance_id': node.get('instance_id'),
                    '__model_code': node.get('__model_code'),
                    'name': node.get('name') or node.get('hostname') or node.get('ip', ''),
                    'depth': record['depth'],
                    'rel_chain': record['rel_chain'],
                })

        return {'root_id': root_id, 'nodes': nodes, 'total': len(nodes)}

    def get_impact(self, instance_id: str,
                   direction: str = 'downstream',
                   max_depth: int = 5) -> dict:
        """影响分析 — 某节点故障时受影响的上/下游

        Args:
            instance_id: 节点 ID
            direction: downstream(下游影响) / upstream(上游溯源)
            max_depth: 分析深度

        Returns:
            {impacted: [{id, model_code, label, depth}], paths: [...]}
        """
        dir_sym = '-' if direction == 'downstream' else '<-'
        end_sym = '->' if direction == 'downstream' else '-'

        cypher = (
            "MATCH (src {instance_id: $id}) "
            f"MATCH path = (src){dir_sym}[*1..{max_depth}]{end_sym}(affected) "
            "RETURN affected, "
            "       [rel IN relationships(path) | type(rel)] as rel_types, "
            "       length(path) as depth "
            "ORDER BY depth"
        )

        impacted = []
        paths = []

        with graph_driver.session() as session:
            result = session.run(cypher, id=instance_id)
            for record in result:
                node = record['affected']
                nid = node.get('instance_id')
                label = (node.get('name')
                         or node.get('hostname')
                         or node.get('ip')
                         or nid)
                impacted.append({
                    'instance_id': nid,
                    'model_code': node.get('__model_code'),
                    'label': label,
                    'depth': record['depth'],
                })
                paths.append({
                    'from': instance_id,
                    'to': nid,
                    'rel_types': record['rel_types'],
                    'depth': record['depth'],
                })

        return {
            'impacted': impacted,
            'paths': paths,
            'total': len(impacted),
        }

    def full_topology(self) -> dict:
        """全局力导向图数据 — 所有节点和关系"""
        nodes_map = {}
        edges = []

        # 查询所有节点
        with graph_driver.session() as session:
            result = session.run("MATCH (n) RETURN n")
            for record in result:
                node = record['n']
                nid = node.get('instance_id')
                if nid:
                    nodes_map[nid] = {
                        'id': nid,
                        'label': (node.get('name')
                                  or node.get('hostname')
                                  or node.get('ip')
                                  or nid),
                        'model_code': node.get('__model_code'),
                    }

        # 查询所有关系
        with graph_driver.session() as session:
            result = session.run(
                "MATCH (src)-[r]->(dst) "
                "RETURN src.instance_id as src_id, "
                "       dst.instance_id as dst_id, "
                "       type(r) as rel_type, "
                "       r.rel_id as rel_id"
            )
            for record in result:
                edges.append({
                    'id': record['rel_id'],
                    'from': record['src_id'],
                    'to': record['dst_id'],
                    'type': record['rel_type'],
                })

        return {
            'nodes': list(nodes_map.values()),
            'edges': edges,
        }

    def global_search(self, query: str, model_codes: list[str] = None,
                      limit: int = 50) -> list[dict]:
        """全局搜索 — 跨所有模型类型

        使用 CONTAINS 模糊搜索所有字符串属性。
        如果安装了 Neo4j 全文索引，优先使用。
        """
        q = query.lower()
        results = []

        # 先尝试全文索引
        try:
            fts_cypher = (
                "CALL db.index.fulltext.queryNodes('cmdb_search_index', $q) "
                "YIELD node, score "
                "RETURN node, score "
                "LIMIT $limit"
            )
            with graph_driver.session() as session:
                result = session.run(fts_cypher, q=q, limit=limit)
                for record in result:
                    node = record['node']
                    results.append(self._node_to_search_result(node))
                if results:
                    return results
        except Exception:
            # 全文索引不存在，降级为 CONTAINS 遍历
            pass

        # 降级方案：根据 model_codes 遍历查询
        label_filter = f":{'|'.join(model_codes)}" if model_codes else ""
        cypher = (
            f"MATCH (n{label_filter}) "
            "WHERE ANY(key IN keys(n) WHERE "
            "  toString(n[key]) CONTAINS $q "
            ") "
            "RETURN n LIMIT $limit"
        )
        with graph_driver.session() as session:
            result = session.run(cypher, q=q, limit=limit)
            for record in result:
                node = record['n']
                results.append(self._node_to_search_result(node))

        return results

    def _node_to_search_result(self, node) -> dict:
        nid = node.get('instance_id')
        return {
            'instance_id': nid,
            'label': (node.get('name')
                      or node.get('hostname')
                      or node.get('ip')
                      or nid),
            'model_code': node.get('__model_code'),
        }
