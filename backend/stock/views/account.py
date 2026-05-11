"""
交易账户视图集 — 仅返回当前用户有权限的账户列表
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from dvadmin.utils.json_response import SuccessResponse
from stock.models import TradingAccount
from stock.serializers.serializers import TradingAccountSerializer
from stock.filters import UserAccountFilterBackend


class IsAdminUserOrReadOnly(BasePermission):
    """非管理员仅可读，管理员可写"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_superuser


class TradingAccountViewSet(viewsets.ModelViewSet):
    """
    交易账户视图集 - 支持增删改查
    - 所有已认证用户可查看有权限的账户
    - 仅超级管理员可创建/修改/删除
    """
    queryset = TradingAccount.objects.all()
    serializer_class = TradingAccountSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend]

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return SuccessResponse(serializer.data, msg='更新成功')
