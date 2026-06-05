# -*- coding: utf-8 -*-
"""EventSubscriptionViewSet — 事件订阅管理 CRUD"""

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.event_subscription import EventSubscription
from ..serializers import EventSubscriptionSerializer


class EventSubscriptionViewSet(CustomModelViewSet):
    """
    事件订阅管理

    list: 查询订阅列表（支持按 model_code / event_type 过滤）
    create: 创建订阅
    update: 修改订阅
    destroy: 删除订阅
    """
    model = EventSubscription
    queryset = EventSubscription.objects.all()
    serializer_class = EventSubscriptionSerializer
    search_fields = ['name', 'endpoint', 'model_code']
    filter_fields = ['model_code', 'event_type', 'is_active']
    ordering = ['-create_datetime']
