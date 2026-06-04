# -*- coding: utf-8 -*-
"""Business management views (Neo4j)

业务/集群/模块的 CRUD，操作 Neo4j 图数据库。
"""

from rest_framework.decorators import action

from dvadmin.utils.json_response import DetailResponse

from .base import Neo4jViewSet
from ..models.node_types import Biz, Set, Module
from ..serializers import BizSerializer, SetSerializer, ModuleSerializer


class BizViewSet(Neo4jViewSet):
    """
    业务管理

    list: 查询业务列表
    create: 创建业务
    update: 修改业务
    retrieve: 业务详情
    destroy: 删除业务
    topology: 获取业务的完整拓扑树
    """
    model_class = Biz
    serializer_class = BizSerializer
    search_fields = ['name']
    ordering = ['name']

    @action(methods=['GET'], detail=True)
    def topology(self, request, pk=None):
        """获取业务拓扑树"""
        from ..services.topology_service import get_biz_topology
        try:
            biz = self.model_class.nodes.get(biz_id=pk)
        except self.model_class.DoesNotExist:
            return DetailResponse(data={'nodes': [], 'edges': []})

        tree = get_biz_topology(biz)
        return DetailResponse(data=tree)


class SetViewSet(Neo4jViewSet):
    """
    集群管理

    list: 查询集群列表
    create: 创建集群(关联到指定业务)
    update: 修改集群
    retrieve: 集群详情
    destroy: 删除集群
    """
    model_class = Set
    serializer_class = SetSerializer


class ModuleViewSet(Neo4jViewSet):
    """
    模块管理

    list: 查询模块列表
    create: 创建模块(关联到指定集群)
    update: 修改模块
    retrieve: 模块详情
    destroy: 删除模块
    """
    model_class = Module
    serializer_class = ModuleSerializer
