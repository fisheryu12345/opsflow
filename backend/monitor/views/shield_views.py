# -*- coding: utf-8 -*-
"""Shield views — ShieldPlan ViewSet

告警静默/屏蔽计划管理
"""

from rest_framework.decorators import action

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse

from ..models import ShieldPlan
from ..serializers import ShieldPlanSerializer


class ShieldPlanViewSet(CustomModelViewSet):
    """
    告警屏蔽计划管理

    list: 屏蔽计划列表
    create: 创建
    update: 更新
    retrieve: 详情
    destroy: 删除
    toggle: 启用/禁用
    """
    model = ShieldPlan
    queryset = ShieldPlan.objects.all()
    serializer_class = ShieldPlanSerializer
    filter_fields = ['bk_biz_id', 'shield_type', 'is_enabled']
    search_fields = ['name']
    ordering = ['-id']

    @action(methods=['POST'], detail=True)
    def toggle(self, request, pk=None):
        """启用/禁用"""
        instance = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(update_fields=['is_enabled'])
        return DetailResponse(data={'is_enabled': instance.is_enabled}, msg='操作成功')
