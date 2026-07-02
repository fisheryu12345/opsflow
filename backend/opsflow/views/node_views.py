"""节点视图 — 提供 TemplateNode / ExecutionNode 的只读查询接口"""

from rest_framework import viewsets, mixins
from rest_framework.response import Response
from opsflow.models import TemplateNode, ExecutionNode
from opsflow.serializers import TemplateNodeSerializer, ExecutionNodeSerializer
from common.utils.json_response import DetailResponse, SuccessResponse


class TemplateNodeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """模板节点 — 只读，支持按 template / node_type / atom_type 过滤"""
    queryset = TemplateNode.objects.all()
    serializer_class = TemplateNodeSerializer
    filterset_fields = ['template', 'node_type', 'atom_type', 'risk_level', 'is_subprocess']
    search_fields = ['node_id', 'label']
    ordering_fields = ['node_id', 'node_type', 'created_at']
    ordering = ['template', 'node_id']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")


class ExecutionNodeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """执行节点 — 只读，支持按 execution / node_type / status 过滤"""
    queryset = ExecutionNode.objects.all()
    serializer_class = ExecutionNodeSerializer
    filterset_fields = ['execution', 'node_type', 'status', 'atom_type']
    search_fields = ['node_id', 'label']
    ordering_fields = ['node_id', 'node_type', 'status', 'created_at']
    ordering = ['execution', 'node_id']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")
