"""
平仓记录视图集 - 支持平仓记录的增删改查
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import ClosedPositionRecordSerializer
from stock.models import ClosedPositionRecord
from stock.filters import UserAccountFilterBackend


class ClosedPositionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    【平仓记录视图集】

    💡 用途：
    - 查询历史平仓记录
    - 品种胜率统计分析
    - 盈亏分布分析

    📊 典型查询：
    - GET /api/closed-positions/?account=1&ordering=-executed_at
    - GET /api/closed-positions/?account=1&symbol__icontains=rb&direction=1
    - GET /api/closed-positions/?account=1&pnl__gt=0&trade_date__gte=2024-01-01
    """
    queryset = ClosedPositionRecord.objects.all()
    serializer_class = ClosedPositionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 过滤字段配置
    filterset_fields = {
        'account': ['exact'],
        'symbol': ['exact', 'icontains'],
        'product_code': ['exact', 'icontains'],
        'direction': ['exact'],
        'volume': ['exact', 'gte', 'lte'],
        'pnl': ['exact', 'gt', 'gte', 'lt', 'lte'],
        'trade_date': ['exact', 'gte', 'lte', 'range'],
        'executed_at': ['exact', 'gte', 'lte', 'range'],
        'holding_days': ['exact', 'gte', 'lte'],
    }

    # 搜索字段（模糊搜索）
    search_fields = ['account__name', 'symbol', 'product_code']

    # 排序字段
    ordering_fields = [
        'executed_at', 'trade_date', 'symbol', 'pnl',
        'volume', 'holding_days', 'direction'
    ]
    ordering = ['-executed_at']  # 默认按执行时间倒序