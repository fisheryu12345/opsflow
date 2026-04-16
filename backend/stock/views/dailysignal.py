"""
每日策略信号视图集
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import DailyStrategySignalSerializer
from stock.models import DailyStrategySignal


class DailyStrategySignalViewSet(viewsets.ModelViewSet):
    """
    每日策略信号视图集 - 支持增删改查
    """
    queryset = DailyStrategySignal.objects.all().order_by('-trade_date')
    serializer_class = DailyStrategySignalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['symbol', 'remark']
    ordering_fields = ['trade_date', 'trend_factor']
    ordering = ['-trade_date']
