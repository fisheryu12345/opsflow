"""
每日策略信号视图集
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import DailyStrategySignalSerializer
from stock.models import DailyStrategySignal
from stock.filters import UserAccountFilterBackend


class DailyStrategySignalViewSet(viewsets.ModelViewSet):
    """
    每日策略信号视图集 - 支持增删改查
    """
    queryset = DailyStrategySignal.objects.all().order_by('-trade_date')
    serializer_class = DailyStrategySignalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['executed_status', 'trade_type', 'symbol', 'is_breakout', 'signal_direction', 'account']
    search_fields = ['symbol', 'remark','executed_status', 'trade_type']
    ordering_fields = ['trade_date', 'trend_factor']
    ordering = ['-trade_date']
