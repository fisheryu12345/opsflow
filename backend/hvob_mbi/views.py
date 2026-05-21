"""
HVOB-MBI viewsets
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import HvobMbiWatchlistItem, HvobMbiDailyState
from .serializers import HvobMbiWatchlistItemSerializer, HvobMbiDailyStateSerializer


class HvobMbiWatchlistViewSet(viewsets.ReadOnlyModelViewSet):
    """HVOB 观察池条目 - 只读"""
    queryset = HvobMbiWatchlistItem.objects.all()
    serializer_class = HvobMbiWatchlistItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'account': ['exact'],
        'trade_date': ['exact', 'gte', 'lte', 'gt', 'lt'],
        'product_code': ['exact'],
    }
    ordering = ['-trade_date', 'rank']


class HvobMbiDailyStateViewSet(viewsets.ReadOnlyModelViewSet):
    """HVOB 每日状态 - 只读（含 MBI / traded / banned 摘要）"""
    queryset = HvobMbiDailyState.objects.all()
    serializer_class = HvobMbiDailyStateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'account': ['exact'],
        'trade_date': ['exact', 'gte', 'lte'],
    }
    ordering = ['-trade_date']
