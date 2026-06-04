# -*- coding: utf-8 -*-
"""Topology views (Neo4j traversal)

拓扑查询 — 力导向图数据、影响分析路径
"""

from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..services.topology_service import (
    get_impact_analysis,
    get_host_graph,
    search_nodes,
)


class TopologyViewSet(CustomModelViewSet):
    """
    拓扑视图（只读查询）

    list: 查询所有拓扑节点摘要
    host_graph: 主机为中心的关联图
    impact: 影响分析 — 给定节点，找出受影响的范围
    search: 全局搜索 CMDB 节点
    """
    model = None  # 非标准 ORM 模型
    queryset = None

    def list(self, request):
        """查询所有节点摘要（供前端拓扑图初始化）"""
        from ..models.node_types import Biz, Set, Module, Host, Process

        nodes = []
        edges = []

        # 收集所有业务
        for biz in Biz.nodes.all():
            nodes.append({'id': biz.biz_id, 'label': biz.name, 'type': 'biz'})
            for s in biz.sets.all():
                nodes.append({'id': s.set_id, 'label': s.name, 'type': 'set'})
                edges.append({'from': biz.biz_id, 'to': s.set_id, 'type': 'contains'})
                for m in s.modules.all():
                    nodes.append({'id': m.module_id, 'label': m.name, 'type': 'module'})
                    edges.append({'from': s.set_id, 'to': m.module_id, 'type': 'contains'})
                    for h in m.hosts.all():
                        nodes.append({'id': h.host_id, 'label': h.hostname or h.ip, 'type': 'host'})
                        edges.append({'from': m.module_id, 'to': h.host_id, 'type': 'contains'})
                        for p in h.processes.all():
                            nodes.append({'id': p.process_id, 'label': f"{p.name}:{p.port}", 'type': 'process'})
                            edges.append({'from': h.host_id, 'to': p.process_id, 'type': 'runs'})

        return DetailResponse(data={'nodes': nodes, 'edges': edges})

    @action(methods=['GET'], detail=False)
    def host_graph(self, request):
        """以主机为中心的关联图"""
        ip = request.query_params.get('ip')
        hostname = request.query_params.get('hostname')
        if not ip and not hostname:
            return ErrorResponse(msg='请提供 ip 或 hostname')

        from ..models.node_types import Host
        try:
            if ip:
                host = Host.nodes.get(ip=ip)
            else:
                host = Host.nodes.get(hostname=hostname)
        except Host.DoesNotExist:
            return ErrorResponse(msg='主机不存在')

        graph = get_host_graph(host)
        return DetailResponse(data=graph)

    @action(methods=['GET'], detail=False)
    def impact(self, request):
        """影响分析"""
        node_id = request.query_params.get('node_id')
        node_type = request.query_params.get('node_type', 'host')
        if not node_id:
            return ErrorResponse(msg='请提供 node_id')

        result = get_impact_analysis(node_id, node_type)
        return DetailResponse(data=result)

    @action(methods=['GET'], detail=False)
    def search(self, request):
        """全局搜索"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(msg='请提供搜索关键词 q')

        results = search_nodes(query)
        return DetailResponse(data=results)
