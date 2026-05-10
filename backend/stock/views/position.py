"""
每日策略信号视图集
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django.db.models import OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import PositionStateSerializer
from stock.models import PositionState, FullContractList
from stock.filters import UserAccountFilterBackend


class PositionStateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    策略持仓状态视图集 - 只读（数据由系统自动生成和维护）
    """
    queryset = PositionState.objects.annotate(
        volume_multiple=Subquery(
            FullContractList.objects.filter(product_code=OuterRef('product_code'))
            .values('volume_multiple')[:1]
        )
    )
    serializer_class = PositionStateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
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
