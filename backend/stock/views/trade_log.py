"""
交易日志与错误日志视图集
"""
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import TradeLogSerializer, ErrorLogSerializer
from stock.models import TradeLog, ErrorLog
from stock.filters import UserAccountFilterBackend


class TradeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    交易日志视图集 - 只读（日志由系统自动生成）
    """
    queryset = TradeLog.objects.all()
    serializer_class = TradeLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['function_name', 'log_level', 'symbol', 'timestamp', 'account']
    search_fields = ['function_name', 'log_message', 'symbol']
    ordering_fields = ['timestamp', 'log_level']
    ordering = ['-timestamp']


class ErrorLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    错误日志视图集 - 只读+删除（保留清理功能，禁止修改）
    """
    queryset = ErrorLog.objects.all()
    serializer_class = ErrorLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['function_name', 'timestamp', 'account']
    search_fields = ['function_name', 'error_message']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
