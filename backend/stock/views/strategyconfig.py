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
from dvadmin.utils.json_response import DetailResponse, ErrorResponse


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return ErrorResponse(msg=str(serializer.errors), code=4000)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg="新增成功")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return ErrorResponse(msg=str(serializer.errors), code=4000)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg="更新成功")