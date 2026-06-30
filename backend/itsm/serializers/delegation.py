# -*- coding: utf-8 -*-
"""Delegation serializers — 审批委托序列化器"""

from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer
from itsm.models.delegation import ApprovalDelegate


class DelegationSerializer(CustomModelSerializer):
    """委托列表/详情序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    delegate_to_name = serializers.CharField(source='delegate_to.name', read_only=True, default='')

    class Meta:
        model = ApprovalDelegate
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime']


class DelegationCreateUpdateSerializer(CustomModelSerializer):
    """委托创建/更新序列化器 — user 由视图自动设置"""

    class Meta:
        model = ApprovalDelegate
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime', 'user']
