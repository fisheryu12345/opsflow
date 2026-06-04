# -*- coding: utf-8 -*-
"""ViewSet for ConnectorDefinition and ConnectorInstance

连接器定义与实例 CRUD + 额外动作（启停、健康检查）
"""

from rest_framework.decorators import action
from rest_framework import filters

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.connector import ConnectorDefinition, ConnectorInstance
from ..serializers import (
    ConnectorDefinitionSerializer,
    ConnectorDefinitionCreateUpdateSerializer,
    ConnectorInstanceSerializer,
    ConnectorInstanceCreateUpdateSerializer,
)

FSM = 'connector_viewset'


class ConnectorDefinitionViewSet(CustomModelViewSet):
    """
    连接器定义管理

    list: 查询连接器定义列表
    create: 创建连接器定义
    update: 修改连接器定义
    retrieve: 连接器定义详情
    destroy: 删除连接器定义
    """
    model = ConnectorDefinition
    queryset = ConnectorDefinition.objects.all()
    serializer_class = ConnectorDefinitionSerializer
    create_serializer_class = ConnectorDefinitionCreateUpdateSerializer
    update_serializer_class = ConnectorDefinitionCreateUpdateSerializer
    filter_fields = ['category', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['sort_order', 'name']


class ConnectorInstanceViewSet(CustomModelViewSet):
    """
    连接器实例管理

    list: 查询实例列表
    create: 创建实例
    update: 修改实例
    retrieve: 实例详情
    destroy: 删除实例
    health_check: 手动触发健康检查
    toggle_active: 启用/禁用
    """
    model = ConnectorInstance
    queryset = ConnectorInstance.objects.all()
    serializer_class = ConnectorInstanceSerializer
    create_serializer_class = ConnectorInstanceCreateUpdateSerializer
    update_serializer_class = ConnectorInstanceCreateUpdateSerializer
    filter_fields = ['definition', 'status', 'is_active']
    search_fields = ['name']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def health_check(self, request, pk=None):
        """手动触发健康检查"""
        instance = self.get_object()
        from integration.services.health_service import run_health_check
        healthy, msg = run_health_check(instance)
        from django.utils import timezone
        instance.status = 'online' if healthy else 'error'
        instance.last_health_check = timezone.now()
        instance.last_health_message = msg
        instance.save(update_fields=['status', 'last_health_check', 'last_health_message'])
        return DetailResponse(data={
            'status': instance.status,
            'message': msg,
        }, msg='健康检查完成')

    @action(methods=['POST'], detail=True)
    def toggle_active(self, request, pk=None):
        """启用/禁用实例"""
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save(update_fields=['is_active'])
        status_text = '已启用' if instance.is_active else '已禁用'
        return DetailResponse(data={'is_active': instance.is_active}, msg=status_text)
