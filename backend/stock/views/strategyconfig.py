"""
策略参数配置视图集

权限规则:
- TqSDK 密码字段（tqapi_account / tqapi_password）仅在序列化器层对管理员可见
- UserAccountFilterBackend 自动过滤到用户有权限的账户
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import StrategyConfigSerializer
from stock.models import StrategyConfig
from stock.filters import UserAccountFilterBackend


class StrategyConfigViewSet(viewsets.ModelViewSet):
    """
    策略参数配置视图集 - 支持增删改查
    """
    queryset = StrategyConfig.objects.all()
    serializer_class = StrategyConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'account']
    search_fields = ['name']
    ordering_fields = ['name']