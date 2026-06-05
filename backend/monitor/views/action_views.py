# -*- coding: utf-8 -*-
"""Action views — AlertAssignGroup, ActionPlugin ViewSets

告警分派规则组与动作插件管理
"""

from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse

from ..models import AlertAssignGroup, ActionPlugin
from ..serializers import AlertAssignGroupSerializer, ActionPluginSerializer


class AlertAssignGroupViewSet(CustomModelViewSet):
    """
    告警分派规则组管理

    list: 规则组列表
    create: 创建
    update: 更新
    retrieve: 详情(含分派规则)
    destroy: 删除
    reorder: 优先级排序
    """
    model = AlertAssignGroup
    queryset = AlertAssignGroup.objects.all()
    serializer_class = AlertAssignGroupSerializer
    filter_fields = ['bk_biz_id', 'is_enabled']
    search_fields = ['name']
    ordering = ['priority']

    @action(methods=['POST'], detail=False)
    def reorder(self, request):
        """批量调整优先级"""
        ids = request.data.get('ids', [])
        for idx, pk in enumerate(ids):
            AlertAssignGroup.objects.filter(pk=pk).update(priority=idx)
        return DetailResponse(msg='排序成功')


class ActionPluginViewSet(CustomModelViewSet):
    """动作插件管理"""
    model = ActionPlugin
    queryset = ActionPlugin.objects.all()
    serializer_class = ActionPluginSerializer
    filter_fields = ['plugin_type', 'plugin_source', 'is_builtin']
    search_fields = ['name', 'plugin_key']
    ordering = ['name']

    @action(methods=['POST'], detail=True)
    def test(self, request, pk=None):
        """测试动作插件"""
        instance = self.get_object()
        return DetailResponse(data={'plugin': instance.plugin_key}, msg='测试执行完成')
