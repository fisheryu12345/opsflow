"""
交易账户视图集 — 仅返回当前用户有权限的账户列表，供前端账户选择器使用
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from stock.models import TradingAccount
from stock.serializers.serializers import TradingAccountSerializer
from stock.filters import UserAccountFilterBackend


class TradingAccountViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    交易账户视图集 - 只读，仅返回当前用户的活跃账户
    """
    queryset = TradingAccount.objects.filter(is_active=True)
    serializer_class = TradingAccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend]
