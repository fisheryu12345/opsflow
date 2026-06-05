# -*- coding: utf-8 -*-
"""Notification views — NotifyGroup, DutyPlan, DutyArrange ViewSets

通知组管理 + 值班排班
"""

from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse

from ..models import NotifyGroup, DutyPlan, DutyArrange
from ..serializers import (
    NotifyGroupListSerializer, NotifyGroupSerializer,
    DutyPlanSerializer, DutyArrangeSerializer,
)


class NotifyGroupViewSet(CustomModelViewSet):
    """
    通知组管理

    list: 通知组列表
    create: 创建
    update: 更新
    retrieve: 详情(含值班计划、通知配置)
    destroy: 删除
    test_notify: 测试通知
    """
    model = NotifyGroup
    queryset = NotifyGroup.objects.all()
    serializer_class = NotifyGroupListSerializer
    filter_fields = ['bk_biz_id', 'is_enabled']
    search_fields = ['name']
    ordering = ['name']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = NotifyGroupSerializer(instance)
        return DetailResponse(data=serializer.data)

    @action(methods=['POST'], detail=True)
    def test_notify(self, request, pk=None):
        """测试通知发送"""
        instance = self.get_object()
        channel = request.data.get('channel', '')
        if not channel:
            return DetailResponse(msg='请指定通知通道')
        # TODO: 调用 Notify Adapter 发送测试通知
        return DetailResponse(msg=f'测试通知已发送(通道:{channel})')


class DutyPlanViewSet(CustomModelViewSet):
    """值班计划管理"""
    model = DutyPlan
    queryset = DutyPlan.objects.all()
    serializer_class = DutyPlanSerializer
    filter_fields = ['group', 'plan_type', 'is_enabled']
    ordering = ['id']

    @action(methods=['GET'], detail=True)
    def calendar(self, request, pk=None):
        """值班日历 — 按年月查询排班"""
        import calendar
        from datetime import datetime
        year = int(request.query_params.get('year', datetime.now().year))
        month = int(request.query_params.get('month', datetime.now().month))
        instance = self.get_object()
        arranges = instance.arranges.filter(
            date_from__year=year, date_from__month=month,
        )
        data = DutyArrangeSerializer(arranges, many=True).data
        return DetailResponse(data={
            'year': year, 'month': month,
            'days': calendar.monthrange(year, month)[1],
            'arranges': data,
        })


class DutyArrangeViewSet(CustomModelViewSet):
    """排班明细管理"""
    model = DutyArrange
    queryset = DutyArrange.objects.all()
    serializer_class = DutyArrangeSerializer
    filter_fields = ['plan', 'user_id', 'duty_type']
    ordering = ['date_from']
