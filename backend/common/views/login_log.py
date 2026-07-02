# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 按钮权限管理
"""
from django.utils import timezone
from rest_framework.decorators import action

from common.models import LoginLog
from common.utils.json_response import DetailResponse
from common.utils.serializers import CustomModelSerializer
from common.utils.viewset import CustomModelViewSet


class LoginLogSerializer(CustomModelSerializer):
    """
    登录日志权限-序列化器
    """

    class Meta:
        model = LoginLog
        fields = "__all__"
        read_only_fields = ["id"]


class LoginLogViewSet(CustomModelViewSet):
    """
    登录日志接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = LoginLog.objects.all()
    serializer_class = LoginLogSerializer
    extra_filter_class = []
    required_permission = 'system:log:view'

    @action(methods=['get'], detail=False)
    def stats(self, request):
        """获取登录日志统计信息"""
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = queryset.filter(create_datetime__gte=today_start).count()
        unique_ips = queryset.values('ip').distinct().count()
        return DetailResponse(data={
            'total': total,
            'unique_ips': unique_ips,
            'today_count': today_count,
        })
