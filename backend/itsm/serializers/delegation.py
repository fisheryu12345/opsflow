# -*- coding: utf-8 -*-
"""Delegation serializers — 审批委托序列化器"""

from dvadmin.utils.serializers import CustomModelSerializer
from itsm.models.delegation import ApprovalDelegate


class DelegationSerializer(CustomModelSerializer):
    """委托列表/详情序列化器"""

    class Meta:
        model = ApprovalDelegate
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime']


class DelegationCreateUpdateSerializer(CustomModelSerializer):
    """委托创建/更新序列化器"""

    class Meta:
        model = ApprovalDelegate
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime']
