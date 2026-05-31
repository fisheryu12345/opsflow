"""节点视图 — 提供 TemplateNode / ExecutionNode 的只读查询接口"""

from rest_framework import viewsets, mixins
from opsflow.models import TemplateNode, ExecutionNode
from opsflow.serializers import TemplateNodeSerializer, ExecutionNodeSerializer


class TemplateNodeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """模板节点 — 只读，支持按 template / node_type / atom_type 过滤"""
    queryset = TemplateNode.objects.all()
    serializer_class = TemplateNodeSerializer
    filterset_fields = ['template', 'node_type', 'atom_type', 'risk_level', 'is_subprocess']
    search_fields = ['node_id', 'label']
    ordering_fields = ['node_id', 'node_type', 'created_at']
    ordering = ['template', 'node_id']


class ExecutionNodeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """执行节点 — 只读，支持按 execution / node_type / status 过滤"""
    queryset = ExecutionNode.objects.all()
    serializer_class = ExecutionNodeSerializer
    filterset_fields = ['execution', 'node_type', 'status', 'atom_type']
    search_fields = ['node_id', 'label']
    ordering_fields = ['node_id', 'node_type', 'status', 'created_at']
    ordering = ['execution', 'node_id']
