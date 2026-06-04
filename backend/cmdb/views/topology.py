# -*- coding: utf-8 -*-
"""Topology views — 拓扑查询、影响分析、全局搜索"""

from rest_framework.decorators import action
from rest_framework import viewsets

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..services.topology_service import TopologyService


class TopologyViewSet(viewsets.GenericViewSet):
    """
    拓扑视图（只读查询）

    list (graph): 全局力导向图数据
    tree: 业务拓扑树
    impact: 影响分析
    search: 全局搜索
    """
    serializer_class = None

    def list(self, request):
        """全局力导向图数据 — 所有节点+关系"""
        service = TopologyService()
        data = service.full_topology()
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def tree(self, request):
        """业务拓扑树"""
        root_id = request.query_params.get('root_id')
        if not root_id:
            return ErrorResponse(msg='请提供 root_id')
        depth = int(request.query_params.get('depth', 5))
        rel_types = request.query_params.getlist('rel_types') or None

        service = TopologyService()
        data = service.get_tree(root_id, rel_types=rel_types, max_depth=depth)
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def impact(self, request):
        """影响分析"""
        node_id = request.query_params.get('node_id')
        if not node_id:
            return ErrorResponse(msg='请提供 node_id')

        direction = request.query_params.get('direction', 'downstream')
        depth = int(request.query_params.get('depth', 5))

        service = TopologyService()
        data = service.get_impact(node_id, direction=direction, max_depth=depth)
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def search(self, request):
        """全局搜索"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(msg='请提供搜索关键词 q')

        model_codes = request.query_params.getlist('model_codes') or None
        limit = int(request.query_params.get('limit', 50))

        service = TopologyService()
        results = service.global_search(query, model_codes=model_codes, limit=limit)
        return DetailResponse(data=results)
