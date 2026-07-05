# -*- coding: utf-8 -*-
"""ServiceItem serializers"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from itsm.models import ServiceItem


class ServiceItemSerializer(CustomModelSerializer):
    """服务项列表/详情序列化器"""
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    workflow_name = serializers.CharField(source='workflow.name', read_only=True, default='')

    class Meta:
        model = ServiceItem
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime']


class ServiceItemCreateUpdateSerializer(CustomModelSerializer):
    """服务项创建/更新序列化器"""

    class Meta:
        model = ServiceItem
        fields = '__all__'

    def validate(self, attrs):
        """flow 模式必须绑定 workflow"""
        if attrs.get('mode') == 'flow' and not attrs.get('workflow'):
            raise serializers.ValidationError("流程驱动模式必须绑定 Workflow")
        return attrs


class ServiceItemSubmitSerializer(serializers.Serializer):
    """提交服务申请序列化器"""
    form_data = serializers.JSONField(default=dict, label="表单数据")
    title = serializers.CharField(required=False, allow_blank=True, default='', label="工单标题")
    priority = serializers.ChoiceField(
        choices=['P1', 'P2', 'P3', 'P4'], default='P3', label="优先级",
    )
