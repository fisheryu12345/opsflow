"""
每日策略信号视图集
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import PositionStateSerializer
from stock.models import PositionState


class PositionStateViewSet(viewsets.ModelViewSet):
    """
    策略持仓状态视图集 - 支持增删改查
    """
    queryset = PositionState.objects.all()
    serializer_class = PositionStateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 精确过滤字段配置（使用字典格式以支持多种过滤类型）
    filterset_fields = {
        'account': ['exact'],
        'symbol': ['exact', 'icontains'],
        'product_code': ['exact', 'icontains'],
        'direction': ['exact'],
        'units': ['exact', 'gt', 'gte', 'lt', 'lte'],
        'contract_total_position': ['exact', 'gt', 'gte', 'lt', 'lte'],  # 支持大于、小于等范围查询
        'is_rollover_needed': ['exact'],
    }
    
    # 搜索字段（模糊搜索）
    search_fields = ['symbol', 'product_code']
    ordering_fields = '__all__'
