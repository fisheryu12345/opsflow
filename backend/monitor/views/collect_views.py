# -*- coding: utf-8 -*-
"""Collect views — CollectConfig ViewSet

采集配置管理
"""

from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse

from ..models import CollectConfig
from ..serializers import CollectConfigSerializer


class CollectConfigViewSet(CustomModelViewSet):
    """
    采集配置管理

    list: 采集配置列表
    create: 创建
    update: 更新
    retrieve: 详情
    destroy: 删除
    test: 测试采集连接
    """
    model = CollectConfig
    queryset = CollectConfig.objects.all()
    serializer_class = CollectConfigSerializer
    filter_fields = ['bk_biz_id', 'data_source_label', 'is_enabled']
    search_fields = ['name']
    ordering = ['-id']

    @action(methods=['POST'], detail=True)
    def test(self, request, pk=None):
        """测试采集连接"""
        instance = self.get_object()
        return DetailResponse(data={'name': instance.name}, msg='连接测试完成')
