# -*- coding: utf-8 -*-
"""Strategy views — MonitorStrategy & MonitorItem ViewSets

监控策略的四层管理: Strategy → Item → QueryConfig → Detect → Algorithm
"""

from django.utils import timezone

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse

from ..models import (
    MonitorStrategy, MonitorItem, MonitorQueryConfig,
    MonitorDetectConfig, MonitorAlgorithmConfig,
    MonitorStrategyLabel, MonitorStrategyHistory,
)
from ..serializers import (
    MonitorStrategyListSerializer, MonitorStrategyDetailSerializer,
    MonitorStrategyCreateUpdateSerializer,
    MonitorItemSerializer, MonitorAlgorithmConfigSerializer,
    MonitorStrategyLabelSerializer, MonitorStrategyHistorySerializer,
)


class MonitorStrategyViewSet(CustomModelViewSet):
    """
    监控策略管理

    list: 策略列表 (含 item_count)
    create: 创建策略
    update: 更新策略(含嵌套子级)
    retrieve: 策略详情(含 items/detects/algorithms)
    destroy: 删除策略
    toggle: 启用/禁用
    clone: 克隆策略
    validate: 验证策略配置
    """
    model = MonitorStrategy
    queryset = MonitorStrategy.objects.all()
    serializer_class = MonitorStrategyListSerializer
    create_serializer_class = MonitorStrategyCreateUpdateSerializer
    update_serializer_class = MonitorStrategyCreateUpdateSerializer
    filter_fields = ['bk_biz_id', 'scenario', 'type', 'is_enabled', 'source']
    search_fields = ['name']
    ordering = ['-create_time']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = MonitorStrategyDetailSerializer(instance)
        return DetailResponse(data=serializer.data)

    from rest_framework.decorators import action

    @action(methods=['POST'], detail=True)
    def toggle(self, request, pk=None):
        """启用/禁用策略"""
        instance = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(update_fields=['is_enabled', 'update_time'])
        return DetailResponse(data={'is_enabled': instance.is_enabled}, msg='操作成功')

    @action(methods=['POST'], detail=True)
    def clone(self, request, pk=None):
        """克隆策略（复制所有子级配置）"""
        from django.db import transaction
        original = self.get_object()
        with transaction.atomic():
            new_strategy = MonitorStrategy.objects.create(
                name=f"{original.name} (副本)",
                bk_biz_id=original.bk_biz_id,
                scenario=original.scenario,
                source=original.source,
                type=original.type,
                is_enabled=False,
                create_user=request.user.name or '',
            )
            # 复制 items
            for item in original.items.all():
                item.pk = None
                item.strategy = new_strategy
                item.save()
        return DetailResponse(data={'id': new_strategy.id, 'name': new_strategy.name}, msg='克隆成功')

    @action(methods=['POST'], detail=False)
    def validate(self, request):
        """验证策略配置的基本合法性"""
        name = request.data.get('name', '')
        bk_biz_id = request.data.get('bk_biz_id')
        items = request.data.get('items', [])
        errors = []
        if not name:
            errors.append('策略名称不能为空')
        if not bk_biz_id:
            errors.append('业务ID不能为空')
        if not items:
            errors.append('至少需要一个监控项')
        if errors:
            return ErrorResponse(msg='; '.join(errors))
        return DetailResponse(msg='验证通过')


class MonitorItemViewSet(CustomModelViewSet):
    """监控项管理"""
    model = MonitorItem
    queryset = MonitorItem.objects.all()
    serializer_class = MonitorItemSerializer
    filter_fields = ['strategy', 'metric_type']
    search_fields = ['name']
    ordering = ['id']
