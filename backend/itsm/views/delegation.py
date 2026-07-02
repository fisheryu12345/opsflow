# -*- coding: utf-8 -*-
"""Delegation views — 审批委托 CRUD

用户可创建/编辑/删除自己的审批委托规则，将审批权限临时转交他人。
"""

from rest_framework.decorators import action

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse

from itsm.models.delegation import ApprovalDelegate
from itsm.serializers.delegation import (
    DelegationSerializer,
    DelegationCreateUpdateSerializer,
)


class DelegationViewSet(CustomModelViewSet):
    """审批委托 CRUD"""
    model = ApprovalDelegate
    queryset = ApprovalDelegate.objects.all()
    serializer_class = DelegationSerializer
    create_serializer_class = DelegationCreateUpdateSerializer
    update_serializer_class = DelegationCreateUpdateSerializer
    filter_fields = ['user', 'delegate_to', 'is_active', 'ticket_type']
    search_fields = ['remark']
    ordering = ['-create_datetime']

    def get_queryset(self):
        """默认只显示当前用户的委托规则，管理员可看全部"""
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        """创建委托时自动设置委托人（当前用户）为 user 字段"""
        user = self.request.user
        if 'user' not in self.request.data or not self.request.data.get('user'):
            serializer.save(user=user, creator=user.username)
        else:
            serializer.save(creator=user.username)

    @action(methods=['POST'], detail=True)
    def toggle_active(self, request, pk=None):
        """切换委托启用/停用"""
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save(update_fields=['is_active'])
        return DetailResponse(data={'is_active': instance.is_active}, msg='状态已切换')

    @action(methods=['GET'], detail=False)
    def my_delegations(self, request):
        """获取当前用户的委托（作为委托人和被委托人）"""
        qs = ApprovalDelegate.objects.filter(
            user=request.user
        ) | ApprovalDelegate.objects.filter(
            delegate_to=request.user
        )
        qs = qs.order_by('-create_datetime')
        serializer = self.get_serializer(qs, many=True)
        return DetailResponse(data=serializer.data)
