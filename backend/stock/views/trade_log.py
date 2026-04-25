"""
期货合约列表视图集
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import TradeLogSerializer,ErrorLogSerializer
from stock.models import TradeLog,ErrorLog
"""
交易日志视图集
"""

class TradeLogViewSet(viewsets.ModelViewSet):
    """
    交易日志视图集 - 支持增删改查
    """
    queryset = TradeLog.objects.all()
    serializer_class = TradeLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['function_name', 'log_level', 'symbol', 'timestamp']
    search_fields = ['function_name', 'log_message', 'symbol']
    ordering_fields = ['timestamp', 'log_level']
    ordering = ['-timestamp']

class ErrorLogViewSet(viewsets.ModelViewSet):
    """
    错误日志视图集 - 支持增删改查
    """
    queryset = ErrorLog.objects.all()
    serializer_class = ErrorLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['function_name', 'error_type', 'timestamp']
    search_fields = ['function_name', 'error_message', 'traceback']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
